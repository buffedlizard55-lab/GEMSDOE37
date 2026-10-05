#!/usr/bin/env python3
"""Catalogue-ablation cross-validation for the GEMSDOE37 H5 candidate.

Protocol (registered in research/preregistration_h5.json before any sweep):

* Split the 3,199 mapped fault objects in ``labels.tif`` into 4 folds of equal
  pixel mass.  In fold ``f`` the other three folds are the *visible catalogue*
  and fold ``f`` is hidden.
* Every feature that touches the catalogue is rebuilt from the visible subset
  only; the hidden objects are labelled 0 during training, exactly as genuinely
  unmapped faults are in the competition's own training data.
* Candidates exclude the visible catalogue pixels, which the organizers mask
  out of scoring.
* Score the hidden objects with the published distance-weighted Tversky index
  and pool TP/FP/FN across folds before computing one DTI, matching the
  organizer's pooled public-leaderboard aggregation.

Outputs ``data/prepared/cv_report.json``.
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

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"

SPACINGS = (0.0, 1.5, 2.0, 2.9, 4.0, 5.0)
MAX_CANDIDATES = 600_000
BUDGETS = tuple(int(x) for x in np.unique(np.round(np.geomspace(2_000, 150_000, 45)).astype(int)))
NEGATIVE_MULTIPLIER = 10
SEED = 20261005


def load_inputs():
    footprint = np.load(PREPARED / "footprint.npy")
    meta = json.loads((PREPARED / "static_features.json").read_text(encoding="utf-8"))
    static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
    with rasterio.open(RAW / "labels.tif") as source:
        faults = source.read(1) == 1
    if static.shape[0] != int(footprint.sum()):
        raise ValueError("static feature matrix does not match the footprint")
    return footprint, meta, static, faults


def fit_fold(
    static: np.ndarray,
    cat_columns: np.ndarray,
    positives_idx: np.ndarray,
    negative_pool: np.ndarray,
    rng: np.random.Generator,
    max_iter: int,
):
    from sklearn.ensemble import HistGradientBoostingClassifier

    n_negative = min(negative_pool.size, positives_idx.size * NEGATIVE_MULTIPLIER)
    negatives_idx = rng.choice(negative_pool, size=n_negative, replace=False)
    train_idx = np.concatenate([positives_idx, negatives_idx])
    y = np.concatenate([
        np.ones(positives_idx.size, dtype=np.int8),
        np.zeros(negatives_idx.size, dtype=np.int8),
    ])
    order = np.argsort(train_idx, kind="stable")
    train_idx = train_idx[order]
    y = y[order]
    X = np.hstack([np.asarray(static[train_idx, :]), cat_columns[train_idx, :]])
    model = HistGradientBoostingClassifier(
        max_iter=max_iter,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=SEED,
    )
    model.fit(X, y)
    return model


def predict_all(model, static: np.ndarray, cat_columns: np.ndarray, chunk: int = 400_000) -> np.ndarray:
    n = static.shape[0]
    out = np.empty(n, dtype=np.float32)
    for start in range(0, n, chunk):
        stop = min(start + chunk, n)
        block = np.hstack([np.asarray(static[start:stop, :]), cat_columns[start:stop, :]])
        out[start:stop] = model.predict_proba(block)[:, 1].astype(np.float32)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--max-iter", type=int, default=200)
    parser.add_argument("--out", type=Path, default=PREPARED / "cv_report.json")
    args = parser.parse_args()

    footprint, meta, static, faults = load_inputs()
    height, width = footprint.shape
    flat_index = np.flatnonzero(footprint.ravel())
    rows_all = (flat_index // width).astype(np.int32)
    cols_all = (flat_index % width).astype(np.int32)
    compact_of_flat = np.full(height * width, -1, dtype=np.int64)
    compact_of_flat[flat_index] = np.arange(flat_index.size)

    folds = make_ablation_folds(faults, n_folds=args.folds, seed=SEED)
    rng = np.random.default_rng(SEED)

    curves: dict[float, dict[int, dict[str, float]]] = {
        spacing: {budget: {"tp": 0.0, "fp": 0.0, "fn": 0.0} for budget in BUDGETS}
        for spacing in SPACINGS
    }
    fold_reports = []

    for fold in range(args.folds):
        hidden = folds.hidden_mask(fold)
        visible = folds.visible_mask(fold)
        visible_ids = np.flatnonzero(folds.fold_of_component != fold) + 1
        print(f"fold {fold}: visible {int(visible.sum())} px, hidden {int(hidden.sum())} px", flush=True)

        cat = catalogue_features(visible, folds.component_labels, visible_ids)
        cat_columns = np.column_stack([raster[footprint] for raster in cat.values()]).astype(np.float32)
        del cat

        positives_idx = compact_of_flat[np.flatnonzero((visible & footprint).ravel())]
        positives_idx = positives_idx[positives_idx >= 0]
        excluded = (visible & footprint).ravel()[flat_index]
        negative_pool = np.flatnonzero(~excluded)
        model = fit_fold(static, cat_columns, positives_idx, negative_pool, rng, args.max_iter)
        scores = predict_all(model, static, cat_columns)
        del cat_columns

        # Candidate set: footprint pixels that are not masked known faults.
        scores_candidate = np.where(excluded, -1.0, scores)
        top = np.argpartition(-scores_candidate, MAX_CANDIDATES)[:MAX_CANDIDATES]
        top = top[np.argsort(-scores_candidate[top], kind="stable")]
        top = top[scores_candidate[top] > 0]
        cand_rows = rows_all[top].astype(np.int64)
        cand_cols = cols_all[top].astype(np.int64)

        scoring_valid = footprint & ~visible
        fold_entry = {"fold": fold, "hidden_px": int((hidden & scoring_valid).sum()), "spacings": {}}
        for spacing in SPACINGS:
            keep = spaced_selection(cand_rows, cand_cols, (height, width), spacing, max(BUDGETS))
            sel_rows = cand_rows[keep]
            sel_cols = cand_cols[keep]
            sweep = dti_sweep(sel_rows, sel_cols, hidden, scoring_valid=scoring_valid)
            available = sweep["k"].size
            per_budget = {}
            for budget in BUDGETS:
                if budget > available:
                    continue
                i = budget - 1
                curves[spacing][budget]["tp"] += float(sweep["tp"][i])
                curves[spacing][budget]["fp"] += float(sweep["fp"][i])
                curves[spacing][budget]["fn"] += float(sweep["fn"][i])
                per_budget[budget] = float(sweep["dti"][i])
            best_i = int(np.argmax(sweep["dti"]))
            fold_entry["spacings"][str(spacing)] = {
                "available_candidates": int(available),
                "best_k": int(sweep["k"][best_i]),
                "best_dti": float(sweep["dti"][best_i]),
                "dti_by_budget": per_budget,
            }
            print(
                f"  spacing {spacing}: best fold DTI {sweep['dti'][best_i]:.4f} at k={int(sweep['k'][best_i])}",
                flush=True,
            )
        fold_reports.append(fold_entry)
        del scores, scores_candidate

    pooled = []
    for spacing in SPACINGS:
        for budget in BUDGETS:
            agg = curves[spacing][budget]
            tp, fp, fn = agg["tp"], agg["fp"], agg["fn"]
            if tp == 0 and fn == 0:
                continue
            dti = tp / (tp + ALPHA * fp + BETA * fn + 1e-8)
            pooled.append({"spacing": spacing, "budget": budget, "dti": dti, "tp": tp, "fp": fp, "fn": fn})
    pooled.sort(key=lambda row: -row["dti"])

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": "catalogue-ablation (fault-object holdout), pooled TP/FP/FN then one DTI",
        "n_folds": args.folds,
        "max_iter": args.max_iter,
        "feature_names": meta["feature_names"] + [
            "cat_distance_px",
            "cat_log_density_1500m",
            "cat_log_density_6000m",
            "cat_tip_distance_px",
            "cat_tip_continuation",
        ],
        "input_sha256": meta["input_sha256"],
        "best_pooled": pooled[0] if pooled else None,
        "pooled_top50": pooled[:50],
        "pooled_all": pooled,
        "folds": fold_reports,
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["best_pooled"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
