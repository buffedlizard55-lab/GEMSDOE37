#!/usr/bin/env python
"""Fine emission-geometry sweep on the leave-fault-segment-out holdout.

Stage 1 trains one physics-only model per fold (catalogue segments hidden) and
caches its full-grid score raster.  Stage 2 sweeps budget x spacing x catalogue
stand-off over those cached rasters, so the expensive fit happens once.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label

from gemsdoe37.discovery import greedy_spaced_selection, local_mass
from gemsdoe37.metric import distance_weighted_tversky
from gemsdoe37.workspace import load_columns, load_meta

SEED = 20261005


def fold_masks(known: np.ndarray, folds: int, seed: int = SEED):
    segments, n_segments = label(known, structure=np.ones((3, 3), dtype=np.int8))
    rng = np.random.default_rng(seed)
    assignment = rng.integers(0, folds, size=n_segments + 1)
    assignment[0] = -1
    for fold in range(folds):
        hidden = known & (assignment[segments] == fold)
        yield fold, hidden, known & ~hidden


def train_fold_scores(work: Path, cache: Path, folds: int, negatives: int) -> None:
    from sklearn.ensemble import HistGradientBoostingClassifier

    meta = load_meta(work)
    columns = list(range(len(meta["columns"])))
    valid_index = np.load(work / "valid_index.npy")
    known = np.load(work / "known.npy")
    rng = np.random.default_rng(SEED + 7)
    cache.mkdir(parents=True, exist_ok=True)

    for fold, hidden, visible in fold_masks(known, folds):
        target_path = cache / f"scores_fold{fold}.npy"
        if target_path.exists():
            print(f"fold {fold}: cached", flush=True)
            continue
        visible_flat = visible.ravel()[valid_index]
        far = (distance_transform_edt(~visible) >= 3.0).ravel()[valid_index]
        positives = np.flatnonzero(visible_flat)
        pool = np.flatnonzero(~visible_flat & far)
        negatives_rows = rng.choice(pool, size=min(negatives, pool.size), replace=False)
        rows = np.concatenate([positives, negatives_rows])
        labels = np.concatenate(
            [np.ones(positives.size, np.int8), np.zeros(negatives_rows.size, np.int8)]
        )
        model = HistGradientBoostingClassifier(
            max_iter=250,
            learning_rate=0.08,
            max_leaf_nodes=31,
            min_samples_leaf=50,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=SEED + fold,
        )
        model.fit(load_columns(work, columns, rows), labels)
        scores = np.empty(valid_index.size, dtype=np.float32)
        step = 400_000
        for start in range(0, valid_index.size, step):
            chunk = np.arange(start, min(start + step, valid_index.size))
            scores[start : start + chunk.size] = model.predict_proba(
                load_columns(work, columns, chunk)
            )[:, 1]
        np.save(target_path, scores)
        print(f"fold {fold}: trained and cached {target_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="data/work")
    parser.add_argument("--cache", default="data/work/cache")
    parser.add_argument("--out", default="research/receipts/h6_sweep.json")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--negatives", type=int, default=300_000)
    parser.add_argument("--budgets", type=int, nargs="+", default=[60_000, 80_000, 100_000, 120_000])
    parser.add_argument("--spacings", type=float, nargs="+", default=[2.9, 3.5])
    parser.add_argument("--standoffs", type=float, nargs="+", default=[0.0, 2.0, 3.0])
    args = parser.parse_args()

    work = Path(args.work)
    cache = Path(args.cache)
    train_fold_scores(work, cache, args.folds, args.negatives)

    meta = load_meta(work)
    shape = tuple(meta["shape"])
    valid_index = np.load(work / "valid_index.npy")
    known = np.load(work / "known.npy")
    footprint = np.load(work / "footprint.npy")

    pooled: dict[str, dict[str, float]] = {}
    per_fold: list[dict] = []
    for fold, hidden, visible in fold_masks(known, args.folds):
        scores = np.load(cache / f"scores_fold{fold}.npy")
        score_map = np.zeros(shape, dtype=np.float32)
        score_map.ravel()[valid_index] = scores
        distance_visible = distance_transform_edt(~visible)
        for standoff in args.standoffs:
            allowed = footprint & (distance_visible > standoff)
            for spacing in args.spacings:
                for budget in args.budgets:
                    selection = greedy_spaced_selection(
                        score_map, allowed, budget=budget, spacing_px=spacing
                    )
                    parts = distance_weighted_tversky(
                        selection.astype(np.float64), hidden, valid_mask=footprint
                    )
                    key = f"b{budget}_s{spacing}_o{standoff}"
                    bucket = pooled.setdefault(
                        key, {"tp": 0.0, "fp": 0.0, "fn": 0.0, "n": 0, "dot": 0.0}
                    )
                    bucket["tp"] += parts["tp"]
                    bucket["fp"] += parts["fp"]
                    bucket["fn"] += parts["fn"]
                    bucket["n"] += int(selection.sum())
                    bucket["dot"] += local_mass(selection)
                    per_fold.append(
                        {"fold": fold, "key": key, "dti": parts["dti"], "n": int(selection.sum())}
                    )
                    print(f"fold {fold} {key:28s} dti={parts['dti']:.5f}", flush=True)

    summary = {}
    for key, bucket in pooled.items():
        denominator = bucket["tp"] + 0.2 * bucket["fp"] + 0.8 * bucket["fn"]
        summary[key] = {
            "pooled_dti": bucket["tp"] / denominator if denominator else 0.0,
            "tp": bucket["tp"],
            "fp": bucket["fp"],
            "fn": bucket["fn"],
            "selected": bucket["n"],
            "mean_local_mass": bucket["dot"] / args.folds,
        }
    best = max(summary.items(), key=lambda item: item[1]["pooled_dti"])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "protocol": "leave-fault-segment-out, physics-only model, emission-geometry sweep",
                "folds": args.folds,
                "best_key": best[0],
                "best": best[1],
                "pooled": summary,
                "per_fold": per_fold,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\nbest: {best[0]} -> {best[1]['pooled_dti']:.5f}\nwrote {out}")


if __name__ == "__main__":
    main()
