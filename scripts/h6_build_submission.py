#!/usr/bin/env python
"""Build the GEMSDOE37 H6 competition GeoTIFF.

Pipeline (every step is validated in research/receipts/):
  1. physics-only HistGradientBoosting model fitted on the full public
     USGS/INGENIOUS catalogue with 94 label-free multi-scale, persistence
     certified geophysical features,
  2. full-grid ranking,
  3. catalogue stand-off (no emission within `--standoff` px of a mapped fault,
     because the scoring truth is by definition NOT in the catalogue),
  4. score-ordered Poisson-disk dotting at `--spacing` px,
  5. binary 1.0 emission of the top `--budget` dots (binary is provably optimal
     for a fixed support under the official metric),
  6. strict GeoTIFF validation against the competition grid template.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from gemsdoe37.discovery import catalogue_standoff, greedy_spaced_selection, local_mass
from gemsdoe37.submission import validate_geotiff, write_submission_geotiff
from gemsdoe37.workspace import load_columns, load_meta

SEED = 20261005


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="data/work")
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--out-dir", default="docs/downloads")
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--spacing", type=float, required=True)
    parser.add_argument("--standoff", type=float, required=True)
    parser.add_argument("--negatives", type=int, default=600_000)
    parser.add_argument("--tag", default="h6-physics-dotted")
    parser.add_argument("--holdout-dti", type=float, required=True)
    args = parser.parse_args()

    work = Path(args.work)
    raw = Path(args.raw)
    meta = load_meta(work)
    shape = tuple(meta["shape"])
    columns = list(range(len(meta["columns"])))
    valid_index = np.load(work / "valid_index.npy")
    known = np.load(work / "known.npy")
    footprint = np.load(work / "footprint.npy")

    from sklearn.ensemble import HistGradientBoostingClassifier

    rng = np.random.default_rng(SEED)
    known_flat = known.ravel()[valid_index]
    far = (distance_transform_edt(~known) >= 3.0).ravel()[valid_index]
    positives = np.flatnonzero(known_flat)
    pool = np.flatnonzero(~known_flat & far)
    negatives = rng.choice(pool, size=min(args.negatives, pool.size), replace=False)
    rows = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size, np.int8), np.zeros(negatives.size, np.int8)])
    print(f"training on {positives.size} catalogue positives and {negatives.size} negatives", flush=True)

    model = HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=SEED,
    )
    model.fit(load_columns(work, columns, rows), target)

    scores = np.empty(valid_index.size, dtype=np.float32)
    step = 400_000
    for start in range(0, valid_index.size, step):
        chunk = np.arange(start, min(start + step, valid_index.size))
        scores[start : start + chunk.size] = model.predict_proba(load_columns(work, columns, chunk))[:, 1]
        print(f"  scored {start + chunk.size}/{valid_index.size}", flush=True)
    score_map = np.zeros(shape, dtype=np.float32)
    score_map.ravel()[valid_index] = scores

    allowed = footprint & catalogue_standoff(known, args.standoff)
    selection = greedy_spaced_selection(score_map, allowed, budget=args.budget, spacing_px=args.spacing)
    emitted = int(selection.sum())
    if emitted != args.budget:
        raise SystemExit(f"selector returned {emitted} dots, expected {args.budget}")

    prediction = np.zeros(shape, dtype=np.float32)
    prediction[selection] = 1.0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    import hashlib

    signature = hashlib.sha256(np.flatnonzero(selection.ravel()).tobytes()).hexdigest()[:12]
    name = f"gemsdoe37-{args.tag}-{emitted//1000}k-{stamp}-{signature}"
    out_dir = Path(args.out_dir)
    tif_path = out_dir / f"{name}.tif"
    checks = write_submission_geotiff(tif_path, prediction, raw / "sample_submission.tif", expected_budget=emitted)
    checks |= validate_geotiff(tif_path, raw / "sample_submission.tif", expected_budget=emitted)

    distance = distance_transform_edt(~known)
    descriptors = {
        "positive_pixels": emitted,
        "spacing_proxy_local_mass": local_mass(selection),
        "min_catalogue_distance_px": float(distance[selection].min()),
        "median_catalogue_distance_px": float(np.median(distance[selection])),
        "pixels_outside_footprint": int((selection & ~footprint).sum()),
        "pixels_on_catalogue": int((selection & known).sum()),
        "mean_model_score_selected": float(score_map[selection].mean()),
        "mean_model_score_footprint": float(score_map[footprint].mean()),
    }

    # uniqueness against every prior submission raster available locally
    uniqueness = []
    for prior in sorted(Path("docs/downloads").glob("*.tif")) + sorted(Path("/tmp/prior").glob("*.tif")):
        if prior.resolve() == tif_path.resolve():
            continue
        with rasterio.open(prior) as src:
            if (src.height, src.width) != shape:
                continue
            other = np.nan_to_num(src.read(1)) > 0
        intersection = int((selection & other).sum())
        union = int((selection | other).sum())
        uniqueness.append(
            {"file": prior.name, "jaccard": intersection / union if union else 0.0, "shared_pixels": intersection}
        )
    uniqueness.sort(key=lambda item: -item["jaccard"])

    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "submission_name": name,
        "file": tif_path.name,
        "submission_note": (
            f"H6 physics-only GBM on 94 multi-scale persistence-certified GEMS features; "
            f"{args.standoff:g}px catalogue stand-off; {args.spacing:g}px Poisson-disk dotting; {emitted} dots"
        ),
        "configuration": {
            "model": "HistGradientBoostingClassifier(max_iter=250, lr=0.08, leaves=31)",
            "features": len(columns),
            "budget": emitted,
            "spacing_px": args.spacing,
            "standoff_px": args.standoff,
            "values": "binary 1.0 at emitted dots, 0.0 elsewhere, all cells finite",
        },
        "segment_holdout_pooled_dti": args.holdout_dti,
        "organizer_score": None,
        "format_checks": checks,
        "descriptors": descriptors,
        "uniqueness_vs_prior_submissions": uniqueness[:10],
    }
    receipt_path = out_dir / f"receipt-{name}.json"
    receipt_path.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    note_path = out_dir / f"{name}.note.txt"
    note_path.write_text(
        f"Submission name: {name}\nNote for the DrivenData form:\n{receipt['submission_note']}\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=1))
    print(f"\nwrote {tif_path}")


if __name__ == "__main__":
    main()
