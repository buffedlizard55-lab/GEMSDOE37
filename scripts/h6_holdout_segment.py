#!/usr/bin/env python
"""H6 leave-fault-segment-out discovery holdout.

Why this protocol
-----------------
The competition's truth is a set of *whole faults* that experts mapped and the
public USGS/INGENIOUS catalogue does not contain, sitting inside a region where
the rest of the catalogue IS public.  A quadrant block hides the catalogue
everywhere in the scored area, which is a harder and different problem.  Here we
instead:

  1. label the catalogue into 8-connected fault segments,
  2. randomly hide 1/3 of the segments (the simulated "new faults"),
  3. show the model only the remaining 2/3 (the simulated "public catalogue"),
  4. score the official DTI of a dotted emission against the hidden segments.

This makes it possible to test, honestly and without leakage, whether
catalogue-relative geometry (distance to the visible catalogue, along-strike
continuation past mapped tips) helps or hurts discovery of unmapped faults -
the single question that most distinguishes the strategies tried so far.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label

from gemsdoe37.discovery import greedy_spaced_selection, local_mass
from gemsdoe37.metric import distance_weighted_tversky
from gemsdoe37.workspace import load_columns, load_meta


def catalogue_geometry(visible: np.ndarray, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Label-free-of-the-hidden-set geometry derived from the VISIBLE catalogue."""
    distance = distance_transform_edt(~visible).astype(np.float32)
    density = gaussian_filter(visible.astype(np.float32), 10.0, mode="nearest")
    density_wide = gaussian_filter(visible.astype(np.float32), 30.0, mode="nearest")
    halo = np.exp(-distance / 6.0).astype(np.float32)
    out = {
        "cat:distance": np.minimum(distance, 200.0),
        "cat:halo": halo,
        "cat:density10": density,
        "cat:density30": density_wide,
    }
    for value in out.values():
        value[~footprint] = 0.0
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="data/work")
    parser.add_argument("--out", default="research/receipts/h6_segment_holdout.json")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--negatives", type=int, default=300_000)
    parser.add_argument("--budgets", type=int, nargs="+", default=[20_000, 40_000, 80_000, 160_000])
    parser.add_argument("--spacing", type=float, default=2.9)
    parser.add_argument("--seed", type=int, default=20261005)
    args = parser.parse_args()

    work = Path(args.work)
    meta = load_meta(work)
    shape = tuple(meta["shape"])
    columns = meta["columns"]
    valid_index = np.load(work / "valid_index.npy")
    known = np.load(work / "known.npy")
    footprint = np.load(work / "footprint.npy")

    structure = np.ones((3, 3), dtype=np.int8)
    segments, n_segments = label(known, structure=structure)
    rng = np.random.default_rng(args.seed)
    assignment = rng.integers(0, args.folds, size=n_segments + 1)
    assignment[0] = -1
    print(f"catalogue segments: {n_segments}", flush=True)

    physics_cols = list(range(len(columns)))
    geometry_names = ["cat:distance", "cat:halo", "cat:density10", "cat:density30"]

    pooled: dict[str, dict[int, dict[str, float]]] = {}
    per_fold: list[dict] = []
    halo_stats: list[dict] = []

    for fold in range(args.folds):
        hidden = known & (assignment[segments] == fold)
        visible = known & ~hidden
        geometry = catalogue_geometry(visible, footprint)

        distance_to_visible = distance_transform_edt(~visible)
        hidden_distance = distance_to_visible[hidden]
        halo_stats.append(
            {
                "fold": fold,
                "hidden_pixels": int(hidden.sum()),
                "visible_pixels": int(visible.sum()),
                "hidden_within_3px_of_visible": float(np.mean(hidden_distance <= 3.0)),
                "hidden_within_6px_of_visible": float(np.mean(hidden_distance <= 6.0)),
                "hidden_within_20px_of_visible": float(np.mean(hidden_distance <= 20.0)),
                "median_hidden_distance_px": float(np.median(hidden_distance)),
                "footprint_within_3px_of_visible": float(
                    np.mean(distance_to_visible[footprint] <= 3.0)
                ),
                "footprint_within_6px_of_visible": float(
                    np.mean(distance_to_visible[footprint] <= 6.0)
                ),
            }
        )
        print(json.dumps(halo_stats[-1]), flush=True)

        visible_flat = visible.ravel()[valid_index]
        far_from_visible = (distance_to_visible >= 3.0).ravel()[valid_index]
        positive_rows = np.flatnonzero(visible_flat)
        negative_pool = np.flatnonzero(~visible_flat & far_from_visible)
        negative_rows = rng.choice(
            negative_pool, size=min(args.negatives, negative_pool.size), replace=False
        )
        rows = np.concatenate([positive_rows, negative_rows])
        target = np.concatenate(
            [np.ones(positive_rows.size, np.int8), np.zeros(negative_rows.size, np.int8)]
        )

        physics_train = load_columns(work, physics_cols, rows)
        geometry_train = np.stack(
            [geometry[name].ravel()[valid_index][rows] for name in geometry_names], axis=1
        )

        from sklearn.ensemble import HistGradientBoostingClassifier

        def fit(matrix: np.ndarray):
            model = HistGradientBoostingClassifier(
                max_iter=250,
                learning_rate=0.08,
                max_leaf_nodes=31,
                min_samples_leaf=50,
                l2_regularization=1.0,
                early_stopping=False,
                random_state=args.seed + fold,
            )
            model.fit(matrix, target)
            return model

        arms_models = {
            "physics": (fit(physics_train), physics_cols, []),
            "physics_geom": (
                fit(np.concatenate([physics_train, geometry_train], axis=1)),
                physics_cols,
                geometry_names,
            ),
            "geom_only": (fit(geometry_train), [], geometry_names),
        }
        del physics_train, geometry_train

        geometry_valid = np.stack(
            [geometry[name].ravel()[valid_index] for name in geometry_names], axis=1
        )

        for arm, (model, phys, geom) in arms_models.items():
            # Predict in row chunks: the full 5.17M x 94 matrix does not fit in
            # this sandbox's memory, so each chunk is assembled on demand.
            scores = np.empty(valid_index.size, dtype=np.float32)
            step = 400_000
            for start in range(0, valid_index.size, step):
                chunk = np.arange(start, min(start + step, valid_index.size))
                parts_list = []
                if phys:
                    parts_list.append(load_columns(work, phys, chunk))
                if geom:
                    parts_list.append(geometry_valid[chunk])
                matrix = parts_list[0] if len(parts_list) == 1 else np.concatenate(parts_list, axis=1)
                scores[start : start + chunk.size] = model.predict_proba(matrix)[:, 1]
                del matrix, parts_list
            score_map = np.zeros(shape, dtype=np.float32)
            score_map.ravel()[valid_index] = scores
            # the visible catalogue is not a discovery target: never emit on it
            allowed = footprint & ~visible
            pooled.setdefault(arm, {})
            for budget in args.budgets:
                selection = greedy_spaced_selection(
                    score_map, allowed, budget=budget, spacing_px=args.spacing
                )
                parts = distance_weighted_tversky(
                    selection.astype(np.float64), hidden, valid_mask=footprint
                )
                bucket = pooled[arm].setdefault(
                    budget, {"tp": 0.0, "fp": 0.0, "fn": 0.0, "n": 0, "dot": 0.0}
                )
                bucket["tp"] += parts["tp"]
                bucket["fp"] += parts["fp"]
                bucket["fn"] += parts["fn"]
                bucket["n"] += int(selection.sum())
                bucket["dot"] += local_mass(selection)
                per_fold.append(
                    {
                        "fold": fold,
                        "arm": arm,
                        "budget": budget,
                        "selected": int(selection.sum()),
                        "dti": parts["dti"],
                    }
                )
                print(
                    f"fold {fold} {arm:13s} budget {budget:7d} n={int(selection.sum()):7d} "
                    f"dti={parts['dti']:.5f}",
                    flush=True,
                )
        del geometry_valid

    summary = {}
    for arm, budgets in pooled.items():
        summary[arm] = {}
        for budget, bucket in budgets.items():
            denominator = bucket["tp"] + 0.2 * bucket["fp"] + 0.8 * bucket["fn"]
            summary[arm][str(budget)] = {
                "pooled_dti": bucket["tp"] / denominator if denominator else 0.0,
                "tp": bucket["tp"],
                "fp": bucket["fp"],
                "fn": bucket["fn"],
                "selected": bucket["n"],
                "mean_local_mass": bucket["dot"] / args.folds,
            }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "protocol": "leave-fault-segment-out; 1/3 of catalogue segments hidden per fold",
                "metric": "official distance-weighted Tversky, alpha=0.2, beta=0.8, R=300 m",
                "spacing_px": args.spacing,
                "segments": int(n_segments),
                "halo_statistics": halo_stats,
                "pooled": summary,
                "per_fold": per_fold,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
