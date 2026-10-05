#!/usr/bin/env python3
"""Catalogue-ablation CV comparing ranking arms against the random-coverage floor.

Arms
----
``struct``   gradient boosting on the 63 label-free geophysical features only
             (no catalogue-geometry inputs, so it cannot simply retrace the
             mapped catalogue).
``cat``      the same model plus the five catalogue-geometry features.
``offcat``   ``struct`` restricted to pixels more than 2 px from the visible
             catalogue.
``persist``  pure multi-physics H0-persistence consensus, no learning: the mean
             of the DEM / magnetic / gravity cross-scale persistence layers.
``random``   uniform random placement - the floor any method must beat.

All arms are scored with the published distance-weighted Tversky index against
the hidden fault objects, pooled over folds.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.catalogue import catalogue_features, make_ablation_folds  # noqa: E402
from gemsdoe37.selection import ALPHA, BETA, dti_sweep, spaced_selection  # noqa: E402
from scripts.run_cv import SEED, fit_fold, predict_all  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"

SPACINGS = (0.0, 2.0, 2.9, 4.0)
BUDGETS = tuple(int(x) for x in np.unique(np.round(np.geomspace(5_000, 120_000, 30)).astype(int)))
MAX_CANDIDATES = 500_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--max-iter", type=int, default=150)
    parser.add_argument("--out", type=Path, default=PREPARED / "cv_arms.json")
    args = parser.parse_args()

    footprint = np.load(PREPARED / "footprint.npy")
    meta = json.loads((PREPARED / "static_features.json").read_text(encoding="utf-8"))
    static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
    column = {name: i for i, name in enumerate(meta["feature_names"])}
    with rasterio.open(RAW / "labels.tif") as source:
        faults = source.read(1) == 1

    height, width = footprint.shape
    flat_index = np.flatnonzero(footprint.ravel())
    rows_all = (flat_index // width).astype(np.int64)
    cols_all = (flat_index % width).astype(np.int64)
    compact_of_flat = np.full(height * width, -1, dtype=np.int64)
    compact_of_flat[flat_index] = np.arange(flat_index.size)

    persistence = np.zeros(flat_index.size, dtype=np.float32)
    for family in ("dem", "mag", "grav"):
        values = np.asarray(static[:, column[f"pers_{family}_max"]], dtype=np.float32)
        high = float(np.quantile(values, 0.999)) or 1.0
        persistence += np.clip(values / high, 0.0, 1.0)
    persistence /= 3.0

    folds = make_ablation_folds(faults, n_folds=args.folds, seed=SEED)
    rng = np.random.default_rng(SEED)
    arms = ("struct", "cat", "offcat", "persist", "random")
    pooled = {
        arm: {s: {b: {"tp": 0.0, "fp": 0.0, "fn": 0.0} for b in BUDGETS} for s in SPACINGS}
        for arm in arms
    }
    fold_log = []

    for fold in range(args.folds):
        hidden = folds.hidden_mask(fold)
        visible = folds.visible_mask(fold)
        visible_ids = np.flatnonzero(folds.fold_of_component != fold) + 1
        excluded = (visible & footprint).ravel()[flat_index]
        scoring_valid = footprint & ~visible
        positives_idx = np.flatnonzero(excluded)
        negative_pool = np.flatnonzero(~excluded)
        print(f"fold {fold}: visible {positives_idx.size}, hidden {int((hidden & scoring_valid).sum())}", flush=True)

        cat = catalogue_features(visible, folds.component_labels, visible_ids)
        cat_columns = np.column_stack([r[footprint] for r in cat.values()]).astype(np.float32)
        cat_distance = cat["cat_distance_px"][footprint].astype(np.float32)
        del cat

        empty = np.zeros((static.shape[0], 0), dtype=np.float32)
        model_struct = fit_fold(static, empty, positives_idx, negative_pool, rng, args.max_iter)
        score_struct = predict_all(model_struct, static, empty)
        del model_struct
        model_cat = fit_fold(static, cat_columns, positives_idx, negative_pool, rng, args.max_iter)
        score_cat = predict_all(model_cat, static, cat_columns)
        del model_cat, cat_columns

        rankings = {
            "struct": score_struct,
            "cat": score_cat,
            "offcat": np.where(cat_distance > 2.0, score_struct, -1.0),
            "persist": persistence,
            "random": rng.random(flat_index.size).astype(np.float32),
        }

        entry = {"fold": fold, "arms": {}}
        for arm, score in rankings.items():
            ranked = np.where(excluded, -1.0, score)
            take = min(MAX_CANDIDATES, ranked.size)
            top = np.argpartition(-ranked, take - 1)[:take]
            top = top[np.argsort(-ranked[top], kind="stable")]
            top = top[ranked[top] > 0]
            cand_rows, cand_cols = rows_all[top], cols_all[top]
            arm_entry = {}
            for spacing in SPACINGS:
                keep = spaced_selection(cand_rows, cand_cols, (height, width), spacing, max(BUDGETS))
                sweep = dti_sweep(
                    cand_rows[keep], cand_cols[keep], hidden, scoring_valid=scoring_valid
                )
                for budget in BUDGETS:
                    if budget > sweep["k"].size:
                        continue
                    i = budget - 1
                    agg = pooled[arm][spacing][budget]
                    agg["tp"] += float(sweep["tp"][i])
                    agg["fp"] += float(sweep["fp"][i])
                    agg["fn"] += float(sweep["fn"][i])
                best = int(np.argmax(sweep["dti"]))
                arm_entry[str(spacing)] = {
                    "best_k": int(sweep["k"][best]),
                    "best_dti": float(sweep["dti"][best]),
                }
            entry["arms"][arm] = arm_entry
            print(f"  {arm:8s} " + "  ".join(
                f"s={s}:{arm_entry[str(s)]['best_dti']:.4f}@{arm_entry[str(s)]['best_k']}" for s in SPACINGS
            ), flush=True)
        fold_log.append(entry)
        del score_struct, score_cat, rankings

    summary = {}
    for arm in arms:
        best = None
        table = []
        for spacing in SPACINGS:
            for budget in BUDGETS:
                agg = pooled[arm][spacing][budget]
                if agg["tp"] == 0 and agg["fn"] == 0:
                    continue
                dti = agg["tp"] / (agg["tp"] + ALPHA * agg["fp"] + BETA * agg["fn"] + 1e-8)
                row = {"spacing": spacing, "budget": budget, "pooled_dti": dti}
                table.append(row)
                if best is None or dti > best["pooled_dti"]:
                    best = row
        summary[arm] = {"best": best, "curve": table}

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": "catalogue-ablation holdout of whole mapped fault objects; pooled TP/FP/FN then one DTI",
        "n_folds": args.folds,
        "arms": summary,
        "folds": fold_log,
        "interpretation": "An arm is only credible evidence of discovery skill if its pooled DTI exceeds the random arm at matched spacing and budget.",
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({arm: summary[arm]["best"] for arm in arms}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
