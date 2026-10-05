"""Local implementation of the published GEMS distance-weighted Tversky metric.

Formula source: DrivenData competition 306 problem description, linked in the
project charter. This code is a transparent proxy implementation; it must be
checked against the organizer implementation on its published worked example
and is not a replacement for the official scorer.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import distance_transform_edt


def distance_weighted_tversky(
    prediction: np.ndarray,
    truth: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    exclusion_mask: np.ndarray | None = None,
    pixel_size_m: float = 100.0,
    radius_m: float = 300.0,
    alpha: float = 0.2,
    beta: float = 0.8,
    epsilon: float = 1e-8,
) -> dict[str, float]:
    """Compute the published distance-weighted Tversky components and score.

    For each ground-truth pixel, ``TP_w`` uses the maximum nearby prediction
    multiplied by the triangular distance kernel. ``FN_w`` is the complement of
    that matched value. Each prediction contributes ``FP_w`` according to the
    nearest truth pixel's kernel. The raster is assumed to be square, projected,
    and sampled at ``pixel_size_m``; invalid/out-of-footprint cells are excluded.
    ``exclusion_mask`` removes exact pixels from both prediction and truth
    scoring. It models the organizer's pixel-exact known-fault mask; no buffer
    around excluded cells is implied.
    """
    pred = np.asarray(prediction, dtype=np.float64)
    gt = np.asarray(truth, dtype=bool)
    if pred.ndim != 2 or gt.ndim != 2 or pred.shape != gt.shape:
        raise ValueError("prediction and truth must be 2-D arrays with equal shapes")
    if not np.all(np.isfinite(pred)):
        raise ValueError("prediction contains NaN or infinity")
    if np.any(pred < 0.0) or np.any(pred > 1.0):
        raise ValueError("prediction values must be in [0, 1]")
    if pixel_size_m <= 0 or radius_m <= 0:
        raise ValueError("pixel_size_m and radius_m must be positive")
    if alpha < 0 or beta < 0 or epsilon < 0:
        raise ValueError("alpha, beta, and epsilon must be non-negative")

    valid = np.ones(pred.shape, dtype=bool)
    if valid_mask is not None:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != pred.shape:
            raise ValueError("valid_mask shape must match rasters")
    scoring_valid = valid.copy()
    if exclusion_mask is not None:
        excluded = np.asarray(exclusion_mask, dtype=bool)
        if excluded.shape != pred.shape:
            raise ValueError("exclusion_mask shape must match rasters")
        scoring_valid &= ~excluded
    truth_valid = gt & scoring_valid
    pred_valid = np.where(scoring_valid, pred, 0.0)
    truth_count = int(truth_valid.sum())
    if truth_count == 0:
        return {"tp": 0.0, "fp": float(pred_valid.sum()), "fn": 0.0, "dti": 0.0}

    # Distance to the nearest truth centre. SciPy's EDT returns zero on truth.
    nearest_distance = distance_transform_edt(~truth_valid, sampling=pixel_size_m)
    nearest_kernel = np.clip(1.0 - nearest_distance / radius_m, 0.0, 1.0)
    fp_weight = np.where(scoring_valid, pred_valid * (1.0 - nearest_kernel), 0.0)
    fp_weight[pred_valid == 0.0] = 0.0
    fp = float(fp_weight.sum(dtype=np.float64))

    truth_rows, truth_cols = np.nonzero(truth_valid)
    truth_best = np.zeros(truth_rows.size, dtype=np.float64)
    max_offset = int(math.floor(radius_m / pixel_size_m))
    height, width = pred.shape
    for dr in range(-max_offset, max_offset + 1):
        for dc in range(-max_offset, max_offset + 1):
            distance = math.hypot(dr * pixel_size_m, dc * pixel_size_m)
            if distance > radius_m:
                continue
            rows = truth_rows + dr
            cols = truth_cols + dc
            inside = (rows >= 0) & (rows < height) & (cols >= 0) & (cols < width)
            if not np.any(inside):
                continue
            indices = np.flatnonzero(inside)
            rr, cc = rows[inside], cols[inside]
            inside_valid = scoring_valid[rr, cc]
            if not np.any(inside_valid):
                continue
            indices = indices[inside_valid]
            rr, cc = rr[inside_valid], cc[inside_valid]
            contribution = pred_valid[rr, cc] * (1.0 - distance / radius_m)
            truth_best[indices] = np.maximum(truth_best[indices], contribution)

    tp = float(truth_best.sum(dtype=np.float64))
    fn = float((1.0 - truth_best).sum(dtype=np.float64))
    denominator = tp + alpha * fp + beta * fn + epsilon
    dti = tp / denominator if denominator > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "dti": float(dti)}


def marginal_credit_bar(dti: float, *, alpha: float = 0.2) -> float:
    """Return the simplified credit-kernel break-even threshold ``alpha * DTI``.

    This follows from the published metric only for a small added prediction
    that (i) raises one truth pixel's current maximum by its kernel-weighted
    amount, (ii) adds corresponding distance-weighted FP mass, and (iii) uses
    alpha + beta = 1. It is not a universal per-pixel scoring rule; overlapping
    truths, clipping at a current maximum, and discretization require the full
    metric.
    """
    if not 0.0 <= dti <= 1.0 or alpha < 0.0:
        raise ValueError("dti must be in [0,1] and alpha must be non-negative")
    return alpha * dti
