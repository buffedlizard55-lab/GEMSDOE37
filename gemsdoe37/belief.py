"""Blocked spatial belief model and the probability-thresholded emitter.

The two ideas that distinguish this module from the earlier sessions' work:

1. **The belief surface is trained and validated with fault-level spatial
   blocking**, so the held-out faults are never seen by the model at any
   distance closer than the guard band.
2. **The emitter is derived from the metric algebra, not from a fixed budget.**
   ``research/metric_algebra.md`` proves a dot is worth emitting iff its kernel
   credit exceeds ``alpha * DTI``. In expectation over a calibrated belief field
   ``p`` with mean hit credit ``kappa`` this becomes a *probability* threshold

       p  >  alpha / (kappa * (1 / DTI - alpha) + alpha)                     (E1)

   Emitting every candidate above the threshold (with a suppression radius so
   that two dots cannot compete for the same truth pixel) solves the
   expected-DTI objective exactly, and the number of dots falls out of the data
   instead of being chosen by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import ndimage as ndi


def quadrant_blocks(shape: tuple[int, int], *, guard_px: int = 40) -> dict[str, np.ndarray]:
    """Four rectangular blocks with a guard band so folds cannot leak spatially."""
    height, width = map(int, shape)
    mid_r, mid_c = height // 2, width // 2
    extents = {
        "NW": (guard_px, mid_r - guard_px, guard_px, mid_c - guard_px),
        "NE": (guard_px, mid_r - guard_px, mid_c + guard_px, width - guard_px),
        "SW": (mid_r + guard_px, height - guard_px, guard_px, mid_c - guard_px),
        "SE": (mid_r + guard_px, height - guard_px, mid_c + guard_px, width - guard_px),
    }
    out: dict[str, np.ndarray] = {}
    for name, (r0, r1, c0, c1) in extents.items():
        mask = np.zeros((height, width), bool)
        mask[r0:r1, c0:c1] = True
        out[name] = mask
    return out


def sample_training_pixels(
    positives: np.ndarray,
    valid: np.ndarray,
    region: np.ndarray,
    *,
    n_negatives: int,
    positive_exclusion_px: int = 10,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return flat indices of positive and clean negative training cells.

    Negatives are drawn only from ``valid & region`` cells at least
    ``positive_exclusion_px`` away from any positive, so the model is not asked
    to separate a fault pixel from its own edge.
    """
    rng = np.random.default_rng(seed)
    pos_mask = positives & region
    pos_idx = np.flatnonzero(pos_mask.ravel())
    distance = ndi.distance_transform_edt(~positives)
    candidates = valid & region & (distance > positive_exclusion_px)
    cand_idx = np.flatnonzero(candidates.ravel())
    if cand_idx.size == 0:
        raise ValueError("no negative candidates available")
    take = min(n_negatives, cand_idx.size)
    neg_idx = rng.choice(cand_idx, size=take, replace=False)
    return pos_idx, np.sort(neg_idx)


def gather_features(store: np.lib.format.open_memmap, index: np.ndarray,
                    rows_per_chunk: int = 4000) -> np.ndarray:
    """Gather ``(n_features, n_samples)`` uint8 features for flat indices."""
    n_features = store.shape[0]
    height, width = store.shape[1], store.shape[2]
    out = np.empty((index.size, n_features), dtype=np.uint8)
    for start in range(0, index.size, rows_per_chunk):
        chunk = index[start:start + rows_per_chunk]
        rr, cc = np.divmod(chunk, width)
        for feature in range(n_features):
            plane = store[feature]
            # rows are contiguous: read the min..max row span once per feature
            lo, hi = int(rr.min()), int(rr.max())
            block = plane[lo:hi + 1]
            out[start:start + chunk.size, feature] = block[rr - lo, cc]
    return out


@dataclass
class BeliefModel:
    """Blocked cross-validated histogram gradient-boosting belief field."""

    n_negatives: int = 600_000
    guard_px: int = 40
    positive_exclusion_px: int = 10
    max_iter: int = 300
    learning_rate: float = 0.08
    max_leaf_nodes: int = 31
    min_samples_leaf: int = 40
    l2_regularization: float = 1.0
    seed: int = 0
    fold_metrics: dict[str, Any] = field(default_factory=dict)

    def _make_estimator(self, seed: int):
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(
            max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            max_leaf_nodes=self.max_leaf_nodes,
            min_samples_leaf=self.min_samples_leaf,
            l2_regularization=self.l2_regularization,
            early_stopping=False,
            random_state=seed,
        )

    def fit_predict_oof(
        self,
        store: np.lib.format.open_memmap,
        positives: np.ndarray,
        valid: np.ndarray,
        *,
        chunks: int = 24,
    ) -> np.ndarray:
        """Return an out-of-fold belief field over the whole grid.

        The field is produced fold-block by block: the model never predicts a
        cell whose block contributed training labels, and the guard band keeps
        the 300 m scoring kernel from bridging fold boundaries.
        """
        height, width = positives.shape
        blocks = quadrant_blocks((height, width), guard_px=self.guard_px)
        belief = np.zeros((height, width), np.float32)
        for fold, (name, block) in enumerate(blocks.items()):
            region = ~block
            pos_idx, neg_idx = sample_training_pixels(
                positives, valid, region,
                n_negatives=self.n_negatives,
                positive_exclusion_px=self.positive_exclusion_px,
                seed=self.seed + fold,
            )
            index = np.concatenate([pos_idx, neg_idx])
            labels = np.concatenate([np.ones(pos_idx.size, np.uint8),
                                     np.zeros(neg_idx.size, np.uint8)])
            features = gather_features(store, index).astype(np.float32)
            estimator = self._make_estimator(self.seed + fold)
            estimator.fit(features, labels)
            self.fold_metrics[name] = {
                "n_pos": int(pos_idx.size), "n_neg": int(neg_idx.size),
                "train_domain_px": int(region.sum()),
            }
            self._predict_into(estimator, store, belief, block, chunks=chunks)
            del features, estimator
        return belief

    def _predict_into(self, estimator, store, belief: np.ndarray, block: np.ndarray,
                      *, chunks: int) -> None:
        height, width = belief.shape
        rows = np.flatnonzero(block.any(axis=1))
        if rows.size == 0:
            return
        edges = np.linspace(rows[0], rows[-1] + 1, chunks + 1).astype(int)
        for start, stop in zip(edges[:-1], edges[1:]):
            if stop <= start:
                continue
            sub_block = block[start:stop]
            cols = np.flatnonzero(sub_block.any(axis=0))
            if cols.size == 0:
                continue
            c0, c1 = int(cols[0]), int(cols[-1]) + 1
            flat = (np.arange(start, stop)[:, None] * width +
                    np.arange(c0, c1)[None, :]).ravel()
            features = gather_features(store, flat)
            probability = estimator.predict_proba(features)[:, 1]
            belief[start:stop, c0:c1] = np.where(sub_block[:, c0:c1], probability.reshape(
                stop - start, c1 - c0), 0.0).astype(np.float32)
            del features, probability


def emission_probability_threshold(dti: float, *, kappa: float = 0.5,
                                   alpha: float = 0.2) -> float:
    """Solve equation (E1): the hit probability a dot must clear at score ``dti``."""
    if not 0.0 < dti < 1.0:
        raise ValueError("dti must lie in (0, 1)")
    if not 0.0 < kappa <= 1.0:
        raise ValueError("kappa must lie in (0, 1]")
    return alpha / (kappa * (1.0 / dti - alpha) + alpha)


def emit_thresholded(
    belief: np.ndarray,
    valid: np.ndarray,
    *,
    threshold: float,
    suppression_px: float = 3.0,
    exclusion: np.ndarray | None = None,
    exclusion_px: float = 3.0,
    max_dots: int | None = None,
) -> np.ndarray:
    """Greedy suppression emitter: highest belief first, then Poisson-disk thinning.

    ``suppression_px`` is the radius inside which a chosen dot steals the
    marginal value of every other candidate, and ``exclusion``/``exclusion_px``
    is the catalogue stand-off.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    score = np.where(valid, belief, 0.0).astype(np.float32)
    if exclusion is not None:
        if exclusion.shape != score.shape:
            raise ValueError("exclusion mask shape must match")
        stand_off = ndi.distance_transform_edt(~np.asarray(exclusion, bool)) <= exclusion_px
        score = np.where(stand_off, 0.0, score)
    selected = np.zeros(score.shape, bool)
    eligible = score > np.float32(threshold)
    order_idx = np.flatnonzero(eligible.ravel())
    if order_idx.size == 0:
        return selected
    order = order_idx[np.argsort(-score.ravel()[order_idx], kind="stable")]
    radius = int(np.ceil(suppression_px))
    height, width = score.shape
    taken = 0
    for flat in order:
        if selected.ravel()[flat]:
            continue
        row, col = divmod(int(flat), width)
        r0, r1 = max(0, row - radius), min(height, row + radius + 1)
        c0, c1 = max(0, col - radius), min(width, col + radius + 1)
        window = np.ogrid[r0 - row:r1 - row, c0 - col:c1 - col]
        disk = (window[0] ** 2 + window[1] ** 2) <= suppression_px ** 2
        local = selected[r0:r1, c0:c1]
        if local[disk].any():
            continue
        selected[row, col] = True
        taken += 1
        if max_dots is not None and taken >= max_dots:
            break
    return selected
