#!/usr/bin/env python3
"""Final configuration sweep on the catalogue-ablation holdout.

Fixes the ranking to the validated label-free structural model and sweeps the
two geometry knobs that the holdout showed to matter: the catalogue stand-off
radius and the minimum prediction spacing.  TP/FP/FN are pooled across folds
before a single DTI is computed, matching the organizer's pooled aggregation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.catalogue import make_ablation_folds  # noqa: E402
from gemsdoe37.selection import ALPHA, BETA, dti_sweep, spaced_selection  # noqa: E402
from scripts.run_cv import SEED, fit_fold, predict_all  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"

STANDOFFS = (0.0, 1.5, 2.0, 3.0, 4.5)
SPACINGS = (2.0, 2.5, 2.9, 3.5, 4.5)
BUDGETS = tuple(int(x) for x in np.unique(np.round(np.geomspace(10_000, 110_000, 26)).astype(int)))
MAX_CANDIDATES = 500_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--max-iter", type=int, default=150)
    parser.add_argument("--out", type=Path, default=PREPARED / "cv_standoff.json")
    args = parser.parse_args()

    footprint = np.load(PREPARED / "footprint.npy")
    static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
    with rasterio.open(RAW / "labels.tif") as source:
        faults = source.read(1) == 1

    height, width = footprint.shape
    flat_index = np.flatnonzero(footprint.ravel())
    rows_all = (flat_index // width).astype(np.int64)
    cols_all = (flat_index % width).astype(np.int64)

    folds = make_ablation_folds(faults, n_folds=args.folds, seed=SEED)
    rng = np.random.default_rng(SEED)
    pooled = {
        (standoff, spacing, budget): {"tp": 0.0, "fp": 0.0, "fn": 0.0}
        for standoff in STANDOFFS
        for spacing in SPACINGS
        for budget in BUDGETS
    }
    fold_best = []

    for fold in range(args.folds):
        hidden = folds.hidden_mask(fold)
        visible = folds.visible_mask(fold)
        excluded = (visible & footprint).ravel()[flat_index]
        scoring_valid = footprint & ~visible
        positives_idx = np.flatnonzero(excluded)
        negative_pool = np.flatnonzero(~excluded)
        print(f"fold {fold}", flush=True)

        empty = np.zeros((static.shape[0], 0), dtype=np.float32)
        model = fit_fold(static, empty, positives_idx, negative_pool, rng, args.max_iter)
        score = predict_all(model, static, empty)
        del model

        distance = distance_transform_edt(~visible).astype(np.float32).ravel()[flat_index]
        entry = {"fold": fold, "best": None}
        for standoff in STANDOFFS:
            eligible = (~excluded) & (distance > standoff)
            ranked = np.where(eligible, score, -1.0)
            take = min(MAX_CANDIDATES, ranked.size)
            top = np.argpartition(-ranked, take - 1)[:take]
            top = top[np.argsort(-ranked[top], kind="stable")]
            top = top[ranked[top] > 0]
            for spacing in SPACINGS:
                keep = spaced_selection(
                    rows_all[top], cols_all[top], (height, width), spacing, max(BUDGETS)
                )
                sweep = dti_sweep(
                    rows_all[top][keep], cols_all[top][keep], hidden, scoring_valid=scoring_valid
                )
                for budget in BUDGETS:
                    if budget > sweep["k"].size:
                        continue
                    agg = pooled[(standoff, spacing, budget)]
                    agg["tp"] += float(sweep["tp"][budget - 1])
                    agg["fp"] += float(sweep["fp"][budget - 1])
                    agg["fn"] += float(sweep["fn"][budget - 1])
                best = int(np.argmax(sweep["dti"]))
                candidate = {
                    "standoff": standoff,
                    "spacing": spacing,
                    "k": int(sweep["k"][best]),
                    "dti": float(sweep["dti"][best]),
                }
                if entry["best"] is None or candidate["dti"] > entry["best"]["dti"]:
                    entry["best"] = candidate
            print(f"  standoff {standoff}: fold best so far {entry['best']}", flush=True)
        fold_best.append(entry)
        del score

    table = []
    for (standoff, spacing, budget), agg in pooled.items():
        if agg["tp"] == 0 and agg["fn"] == 0:
            continue
        dti = agg["tp"] / (agg["tp"] + ALPHA * agg["fp"] + BETA * agg["fn"] + 1e-8)
        table.append({
            "standoff_px": standoff, "spacing_px": spacing, "budget": budget,
            "pooled_dti": dti, "tp": agg["tp"], "fp": agg["fp"], "fn": agg["fn"],
        })
    table.sort(key=lambda row: -row["pooled_dti"])

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ranking": "label-free structural gradient boosting (63 features)",
        "n_folds": args.folds,
        "best": table[0],
        "top25": table[:25],
        "full_table": table,
        "fold_best": fold_best,
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["top25"][:10], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
