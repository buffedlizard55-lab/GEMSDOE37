"""Build the label-free feature store and the blocked belief field.

Stage ``features``
    reads ``data/raw`` (assembled and hash-verified by
    ``scripts/fetch_open_data.sh``) and writes a uint8 feature memmap.

Stage ``oof``
    4-fold quadrant-blocked out-of-fold belief field for honest validation.

Stage ``full``
    one model on all in-footprint labels, used for the shipped emission.

Usage:
    python scripts/build_belief_field.py features
    python scripts/build_belief_field.py oof
    python scripts/build_belief_field.py full
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gemsdoe37.belief import BeliefModel, quadrant_blocks, sample_training_pixels  # noqa: E402
from gemsdoe37.sources import build_feature_store, load_specs  # noqa: E402

DATA = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
WORK.mkdir(parents=True, exist_ok=True)
FEATURE_SIZES = (1.0, 2.0, 4.0, 8.0)


def load_labels() -> tuple[np.ndarray, np.ndarray, dict]:
    with rasterio.open(DATA / "labels.tif") as src:
        raw = src.read(1)
        profile = {"transform": list(src.transform)[:6], "crs": src.crs.to_string(),
                   "shape": [src.height, src.width], "dtype": str(src.dtypes[0])}
    valid = raw >= 0
    positives = raw == 1
    return positives, valid, profile


def stage_features() -> dict:
    specs = load_specs(DATA)
    for spec in specs:
        spec_scales = tuple(FEATURE_SIZES)
        object.__setattr__(spec, "scales", spec_scales)
    started = time.time()
    report = build_feature_store(specs, DATA, WORK / "features_uint8.npy",
                                 persistence_quantile=0.95)
    report["seconds"] = round(time.time() - started, 1)
    report["sources"] = [
        {"key": s.key, "path": str(s.path.relative_to(ROOT)), "bands": list(s.band_names),
         "kind": s.kind}
        for s in specs
    ]
    (WORK / "feature_store.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("n_features", "shape", "seconds")}, indent=2))
    return report


def _store():
    return np.load(WORK / "features_uint8.npy", mmap_mode="r")


def stage_oof() -> dict:
    positives, valid, profile = load_labels()
    store = _store()
    model = BeliefModel(n_negatives=200_000, guard_px=40, max_iter=220, seed=0)
    started = time.time()
    belief = model.fit_predict_oof(store, positives, valid, chunks=40)
    np.save(WORK / "belief_oof.npy", belief)
    report = {"stage": "oof", "seconds": round(time.time() - started, 1),
              "folds": model.fold_metrics, "profile": profile,
              "belief_stats": {"max": float(belief.max()), "mean": float(belief[valid].mean())}}
    (WORK / "belief_oof_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["folds"], indent=2))
    return report


def stage_full() -> dict:
    from sklearn.ensemble import HistGradientBoostingClassifier

    positives, valid, profile = load_labels()
    store = _store()
    pos_idx, neg_idx = sample_training_pixels(
        positives, valid, np.ones_like(valid), n_negatives=200_000, seed=99)
    index = np.concatenate([pos_idx, neg_idx])
    labels = np.concatenate([np.ones(pos_idx.size, np.uint8), np.zeros(neg_idx.size, np.uint8)])
    from gemsdoe37.belief import gather_features
    started = time.time()
    features = gather_features(store, index, rows_per_chunk=4000).astype(np.float32)
    estimator = HistGradientBoostingClassifier(
        max_iter=250, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=40,
        l2_regularization=1.0, early_stopping=False, random_state=7)
    estimator.fit(features, labels)
    del features
    belief = _predict_full(estimator, store, valid)
    np.save(WORK / "belief_full.npy", belief)
    report = {"stage": "full", "seconds": round(time.time() - started, 1),
              "n_pos": int(pos_idx.size), "n_neg": int(neg_idx.size),
              "belief_stats": {"max": float(belief.max()), "mean": float(belief[valid].mean())},
              "profile": profile}
    (WORK / "belief_full_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["belief_stats"], indent=2))
    return report


def _predict_full(estimator, store, valid: np.ndarray) -> np.ndarray:
    from gemsdoe37.belief import gather_features
    height, width = valid.shape
    belief = np.zeros((height, width), np.float32)
    rows = np.flatnonzero(valid.any(axis=1))
    edges = np.linspace(rows[0], rows[-1] + 1, 40).astype(int)
    for start, stop in zip(edges[:-1], edges[1:]):
        if stop <= start:
            continue
        sub = valid[start:stop]
        cols = np.flatnonzero(sub.any(axis=0))
        if cols.size == 0:
            continue
        c0, c1 = int(cols[0]), int(cols[-1]) + 1
        flat = (np.arange(start, stop)[:, None] * width + np.arange(c0, c1)[None, :]).ravel()
        keep = valid.ravel()[flat]
        probability = estimator.predict_proba(gather_features(store, flat[keep]).astype(np.float32))[:, 1]
        block = np.zeros((stop - start, c1 - c0), np.float32)
        block.ravel()[keep] = probability
        belief[start:stop, c0:c1] = block
        print(f"  predicted rows {start}:{stop}", flush=True)
    return belief


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["features", "oof", "full"])
    args = parser.parse_args()
    if args.stage == "features":
        stage_features()
    elif args.stage == "oof":
        stage_oof()
    else:
        stage_full()


if __name__ == "__main__":
    main()
