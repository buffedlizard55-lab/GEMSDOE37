#!/usr/bin/env python
"""H6 spatially-blocked *discovery* holdout.

Protocol (this is the methodological change versus every earlier GEMSDOE run):

  For each of four spatial quadrants, the known-fault catalogue inside that
  quadrant is treated as completely unknown.  A model is fitted only on the
  other three quadrants, it then ranks the held-out quadrant, the ranking is
  thinned to a dotted emission, and the official distance-weighted Tversky
  index is computed against the quadrant's hidden catalogue.

  That simulates the real task - find faults nobody told you about - without
  leakage, unlike a same-quadrant ablation where the model has already seen the
  structures it is being scored on.

Scores are pooled (TP/FP/FN summed over the four blocks, then divided) because
the organizer computes one index over the whole region, not a mean of folds.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from gemsdoe37.discovery import (
    catalogue_standoff,
    greedy_spaced_selection,
    local_mass,
    nonmax_suppress,
)
from gemsdoe37.metric import distance_weighted_tversky
from gemsdoe37.workspace import load_columns, load_meta


def quadrant_ids(shape: tuple[int, int], footprint: np.ndarray) -> np.ndarray:
    rows, cols = np.nonzero(footprint)
    row_split = int(np.median(rows))
    col_split = int(np.median(cols))
    grid = np.full(shape, -1, dtype=np.int8)
    rr, cc = np.mgrid[0 : shape[0], 0 : shape[1]]
    quad = ((rr >= row_split).astype(np.int8) * 2) + (cc >= col_split).astype(np.int8)
    grid[footprint] = quad[footprint]
    return grid


def fit_model(features: np.ndarray, target: np.ndarray, seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier

    model = HistGradientBoostingClassifier(
        max_iter=250,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=seed,
    )
    model.fit(features, target)
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="data/work")
    parser.add_argument("--out", default="research/receipts/h6_holdout.json")
    parser.add_argument("--negatives", type=int, default=300_000)
    parser.add_argument("--budgets", type=int, nargs="+", default=[20_000, 40_000, 80_000, 160_000])
    parser.add_argument("--spacings", type=float, nargs="+", default=[0.0, 2.0, 2.9, 4.0])
    parser.add_argument("--seed", type=int, default=20261005)
    args = parser.parse_args()

    work = Path(args.work)
    meta = load_meta(work)
    shape = tuple(meta["shape"])
    columns = meta["columns"]
    valid_index = np.load(work / "valid_index.npy")
    known = np.load(work / "known.npy")
    footprint = np.load(work / "footprint.npy")
    quads = quadrant_ids(shape, footprint)
    quad_flat = quads.ravel()[valid_index]
    known_flat = known.ravel()[valid_index]

    # label-free arm: cross-family consensus x persistence, no learning
    xfam_mean = columns.index("xfam:mean")
    persist_cols = [i for i, name in enumerate(columns) if name.startswith("persist:")]
    model_cols = list(range(len(columns)))

    rng = np.random.default_rng(args.seed)

    results: dict[str, dict] = {}
    arms = ["gbm", "labelfree", "random"]
    pooled = {
        arm: {
            (b, s): {"tp": 0.0, "fp": 0.0, "fn": 0.0, "mass": 0, "dots": 0.0}
            for b in args.budgets
            for s in args.spacings
        }
        for arm in arms
    }
    per_fold: list[dict] = []

    for fold in range(4):
        test_rows = np.flatnonzero(quad_flat == fold)
        train_rows_all = np.flatnonzero((quad_flat >= 0) & (quad_flat != fold))
        # positives: known faults outside the held-out quadrant
        positive_rows = train_rows_all[known_flat[train_rows_all] == 1]
        # negatives: sampled cells that are not within 3 px of any known fault
        far = catalogue_standoff(known, 3.0).ravel()[valid_index]
        negative_pool = train_rows_all[(known_flat[train_rows_all] == 0) & far[train_rows_all]]
        negative_rows = rng.choice(negative_pool, size=min(args.negatives, negative_pool.size), replace=False)
        rows = np.concatenate([positive_rows, negative_rows])
        target = np.concatenate([np.ones(positive_rows.size, np.int8), np.zeros(negative_rows.size, np.int8)])
        features = load_columns(work, model_cols, rows)
        model = fit_model(features, target, args.seed + fold)
        del features

        test_features = load_columns(work, model_cols, test_rows)
        gbm_scores = model.predict_proba(test_features)[:, 1].astype(np.float32)
        del test_features

        labelfree = np.load(work / "feat" / f"{xfam_mean:03d}.npy", mmap_mode="r")[test_rows].astype(np.float32)
        persist = np.zeros_like(labelfree)
        for index in persist_cols:
            persist += np.load(work / "feat" / f"{index:03d}.npy", mmap_mode="r")[test_rows]
        labelfree = labelfree * (persist / max(len(persist_cols), 1))
        random_scores = rng.random(test_rows.size).astype(np.float32)

        test_mask = np.zeros(shape, dtype=bool)
        test_mask.ravel()[valid_index[test_rows]] = True
        truth = known & test_mask
        quad_share = test_rows.size / valid_index.size

        for arm, values in (("gbm", gbm_scores), ("labelfree", labelfree), ("random", random_scores)):
            score_map = np.zeros(shape, dtype=np.float32)
            score_map.ravel()[valid_index[test_rows]] = values
            # No catalogue stand-off is applied inside the held-out quadrant:
            # there the catalogue is, by construction, unknown to the model and
            # it is exactly the truth being recovered.
            allowed = test_mask.copy()
            for spacing in args.spacings:
                if spacing <= 0:
                    pool = nonmax_suppress(score_map, allowed, size=3)
                else:
                    pool = allowed
                for budget in args.budgets:
                    quota = max(int(round(budget * quad_share)), 1)
                    if spacing <= 0:
                        flat = np.flatnonzero(pool.ravel())
                        order = np.argsort(-score_map.ravel()[flat], kind="stable")
                        chosen = flat[order[:quota]]
                        selection = np.zeros(shape, dtype=bool)
                        selection.ravel()[chosen] = True
                    else:
                        selection = greedy_spaced_selection(score_map, pool, budget=quota, spacing_px=spacing)
                    parts = distance_weighted_tversky(
                        selection.astype(np.float64), truth, valid_mask=test_mask
                    )
                    bucket = pooled[arm][(budget, spacing)]
                    bucket["tp"] += parts["tp"]
                    bucket["fp"] += parts["fp"]
                    bucket["fn"] += parts["fn"]
                    bucket["mass"] += int(selection.sum())
                    bucket["dots"] += local_mass(selection)
                    per_fold.append(
                        {
                            "fold": fold,
                            "arm": arm,
                            "budget": budget,
                            "spacing": spacing,
                            "selected": int(selection.sum()),
                            "dti": parts["dti"],
                        }
                    )
                    print(
                        f"fold {fold} {arm:9s} budget {budget:7d} spacing {spacing:3.1f} "
                        f"n={int(selection.sum()):6d} dti={parts['dti']:.5f}",
                        flush=True,
                    )

    for arm in arms:
        results[arm] = {}
        for (budget, spacing), bucket in pooled[arm].items():
            denominator = bucket["tp"] + 0.2 * bucket["fp"] + 0.8 * bucket["fn"]
            results[arm][f"b{budget}_s{spacing}"] = {
                "pooled_dti": bucket["tp"] / denominator if denominator > 0 else 0.0,
                "tp": bucket["tp"],
                "fp": bucket["fp"],
                "fn": bucket["fn"],
                "selected": bucket["mass"],
                "mean_local_mass": bucket["dots"] / 4.0,
            }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "protocol": "blocked discovery holdout; catalogue hidden inside the scored quadrant",
                "metric": "official distance-weighted Tversky, alpha=0.2, beta=0.8, R=300 m",
                "aggregation": "pooled TP/FP/FN over four quadrants",
                "n_features": len(columns),
                "pooled": results,
                "per_fold": per_fold,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
