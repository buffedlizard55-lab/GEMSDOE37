#!/usr/bin/env python3
"""Train the final structural models on the complete catalogue and score the grid.

Produces two probability fields over the footprint (compact float32 vectors):

* ``p_struct`` - gradient boosting on the 63 label-free geophysical/topographic
  features only (19 provided bands, multiscale gradient/curvature responses,
  structure-tensor coherence and H0-persistence prominence/stability layers).
* ``p_cat``    - the same model plus the five catalogue-geometry features
  (distance, two density scales, tip distance, tip-continuation cone).

Neither field is a submission.  They are structural priors that the
leaderboard-feedback inverse model is free to weight or discard.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.catalogue import catalogue_features  # noqa: E402
from scripts.run_cv import NEGATIVE_MULTIPLIER, SEED, predict_all  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"
STRUCTURE_8 = np.ones((3, 3), dtype=bool)


def train(X_static, cat_columns, positives_idx, negative_pool, rng, max_iter=250):
    from sklearn.ensemble import HistGradientBoostingClassifier

    n_negative = min(negative_pool.size, positives_idx.size * NEGATIVE_MULTIPLIER)
    negatives_idx = rng.choice(negative_pool, size=n_negative, replace=False)
    train_idx = np.concatenate([positives_idx, negatives_idx])
    y = np.concatenate([
        np.ones(positives_idx.size, dtype=np.int8),
        np.zeros(negatives_idx.size, dtype=np.int8),
    ])
    order = np.argsort(train_idx, kind="stable")
    train_idx, y = train_idx[order], y[order]
    blocks = [np.asarray(X_static[train_idx, :])]
    if cat_columns is not None:
        blocks.append(cat_columns[train_idx, :])
    model = HistGradientBoostingClassifier(
        max_iter=max_iter,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=50,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=SEED,
    )
    model.fit(np.hstack(blocks), y)
    return model


def main() -> int:
    from scipy.ndimage import label

    footprint = np.load(PREPARED / "footprint.npy")
    static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
    with rasterio.open(RAW / "labels.tif") as source:
        catalogue = source.read(1) == 1

    labels_img, count = label(catalogue, structure=STRUCTURE_8)
    all_ids = np.arange(1, count + 1)
    cat = catalogue_features(catalogue, labels_img.astype(np.int32), all_ids)
    cat_names = list(cat.keys())
    cat_columns = np.column_stack([raster[footprint] for raster in cat.values()]).astype(np.float32)
    np.save(PREPARED / "catalogue_features.npy", cat_columns)
    tip_continuation = cat["cat_tip_continuation"][footprint].astype(np.float32)
    np.save(PREPARED / "tip_continuation.npy", tip_continuation)
    del cat

    flat_index = np.flatnonzero(footprint.ravel())
    inside = catalogue.ravel()[flat_index]
    positives_idx = np.flatnonzero(inside)
    negative_pool = np.flatnonzero(~inside)
    rng = np.random.default_rng(SEED)

    print(f"training p_struct on {positives_idx.size} positives", flush=True)
    model_struct = train(static, None, positives_idx, negative_pool, rng)
    p_struct = predict_all(model_struct, static, np.zeros((static.shape[0], 0), dtype=np.float32))
    np.save(PREPARED / "p_struct.npy", p_struct)
    del model_struct

    print("training p_cat", flush=True)
    model_cat = train(static, cat_columns, positives_idx, negative_pool, rng)
    p_cat = predict_all(model_cat, static, cat_columns)
    np.save(PREPARED / "p_cat.npy", p_cat)

    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "catalogue_feature_names": cat_names,
        "n_catalogue_components": int(count),
        "n_catalogue_pixels": int(catalogue.sum()),
        "p_struct": {"mean": float(p_struct.mean()), "max": float(p_struct.max())},
        "p_cat": {"mean": float(p_cat.mean()), "max": float(p_cat.max())},
    }
    (PREPARED / "full_model.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
