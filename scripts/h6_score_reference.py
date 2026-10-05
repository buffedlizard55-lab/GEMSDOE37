#!/usr/bin/env python
"""Score historical submission rasters on the leave-fault-segment-out holdout.

This is the like-for-like comparator for "can we beat 0.2778?": the previously
best-scoring public map is evaluated with the identical folds, mask and metric
as the new candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

from gemsdoe37.metric import distance_weighted_tversky
from scripts.h6_sweep import fold_masks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="data/work")
    parser.add_argument("--maps", nargs="+", required=True)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--out", default="research/receipts/h6_reference_maps.json")
    args = parser.parse_args()

    work = Path(args.work)
    known = np.load(work / "known.npy")
    footprint = np.load(work / "footprint.npy")

    results = {}
    for path in args.maps:
        with rasterio.open(path) as src:
            array = np.nan_to_num(src.read(1).astype(np.float64), nan=0.0)
        array = np.clip(array, 0.0, 1.0)
        totals = {"tp": 0.0, "fp": 0.0, "fn": 0.0}
        folds = []
        for fold, hidden, _visible in fold_masks(known, args.folds):
            parts = distance_weighted_tversky(array, hidden, valid_mask=footprint)
            for key in totals:
                totals[key] += parts[key]
            folds.append({"fold": fold, "dti": parts["dti"]})
            value = parts["dti"]
            print(f"{Path(path).name} fold {fold} dti={value:.5f}", flush=True)
        denominator = totals["tp"] + 0.2 * totals["fp"] + 0.8 * totals["fn"]
        results[Path(path).name] = {
            "pooled_dti": totals["tp"] / denominator if denominator else 0.0,
            "positive_pixels": int((array > 0).sum()),
            "per_fold": folds,
        }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
