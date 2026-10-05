"""Distance-weighted Tversky index (DTI) and the emission arithmetic it implies.

Official definitions, transcribed from the competition problem description
(DrivenData competition 306, page 967) and reproduced verbatim in
``research/sources.md``:

    k(d)  = max(1 - d / R, 0)                      R = 300 m
    TP_w  = sum_{g in G} max_{x: d(x,g) <= R} p(x) * k(d(x,g))
    FP_w  = sum_{x: p(x) > 0} p(x) * (1 - max_{g in G} k(d(x,g)))
    FN_w  = sum_{g in G} (1 - max_{x: d(x,g) <= R} p(x) * k(d(x,g)))
    DTI   = TP_w / (TP_w + alpha * FP_w + beta * FN_w + eps),  alpha = 0.2, beta = 0.8

Because ``FN_w = G - TP_w`` when the truth indicator is binary, the index can be
written exactly as

    DTI = T / (alpha * (T + F) + beta * G)      T = TP_w, F = FP_w, G = truth px

Two corollaries are used by the emitter and are proven in
``research/metric_algebra.md``:

1. **Binary dominates graded.**  Scaling a support set by lambda scales
   ``T -> lambda T`` and ``F -> lambda F``, so
   ``DTI(lambda) = lambda T / (alpha lambda (T + F) + beta G)`` which is strictly
   increasing in lambda: a graded field is dominated by its own support.
2. **Marginal inclusion rule.**  Adding one unit prediction whose kernel credit
   against the truth is ``k`` raises ``T`` by at most ``k`` and raises
   ``alpha (T + F)`` by exactly ``alpha`` (since ``Delta F = 1 - k``).  It pays
   iff ``k > alpha * DTI``.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

DEFAULT_RADIUS_M = 300.0
DEFAULT_PIXEL_M = 100.0
DEFAULT_ALPHA = 0.2
DEFAULT_BETA = 0.8


def dti_components(
    prediction: np.ndarray,
    truth: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    pixel_size_m: float = DEFAULT_PIXEL_M,
    radius_m: float = DEFAULT_RADIUS_M,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    epsilon: float = 1e-8,
) -> dict[str, float]:
    """Exact competition metric on a grid, using the closed forms above.

    ``prediction`` is a float array in ``[0, 1]``; ``valid_mask`` restricts both
    terms to the scored domain (competition footprint, minus the known catalogue
    for the truth set). Unlike the training-loss surrogate shipped in
    ``gemsdoe37/metric.py`` this implementation uses the radial max directly on a
    window of radius ``R`` and is therefore exact for the published equations.
    """
    pred = np.asarray(prediction, dtype=np.float64)
    gt = np.asarray(truth, dtype=bool)
    if pred.shape != gt.shape or pred.ndim != 2:
        raise ValueError("prediction and truth must be equal-shaped 2-D arrays")
    if not np.all(np.isfinite(pred)):
        raise ValueError("prediction contains non-finite values")
    if np.any(pred < 0.0) or np.any(pred > 1.0):
        raise ValueError("prediction values must be in [0, 1]")
    valid = np.ones(pred.shape, bool) if valid_mask is None else np.asarray(valid_mask, bool)
    if valid.shape != pred.shape:
        raise ValueError("valid_mask shape must match")
    truth_here = gt & valid
    pred_here = np.where(valid, pred, 0.0)
    offset = int(math.floor(radius_m / pixel_size_m))
    h, w = pred.shape
    if truth_here.any():
        best = np.zeros(pred.shape, dtype=np.float64)
        for dr in range(-offset, offset + 1):
            for dc in range(-offset, offset + 1):
                dist_px = math.hypot(dr, dc)
                if dist_px > offset + 1e-9:
                    continue
                kernel = 1.0 - (dist_px * pixel_size_m) / radius_m
                if kernel <= 0.0:
                    continue
                shifted = np.roll(np.roll(pred_here, dr, axis=0), dc, axis=1)
                if dr > 0:
                    shifted[:dr, :] = 0.0
                elif dr < 0:
                    shifted[dr:, :] = 0.0
                if dc > 0:
                    shifted[:, :dc] = 0.0
                elif dc < 0:
                    shifted[:, dc:] = 0.0
                contribution = shifted * kernel
                np.maximum(best, contribution, out=best)
        credit = np.where(truth_here, best, 0.0)
        tp = float(credit.sum())
    else:
        best = np.zeros(pred.shape, dtype=np.float64)
        tp = 0.0
    truth_count = int(truth_here.sum())
    fn = float(truth_count) - tp
    # FP uses the distance to the nearest truth pixel.
    if truth_count:
        distance = ndi.distance_transform_edt(~truth_here, sampling=pixel_size_m)
        kernel = np.clip(1.0 - distance / radius_m, 0.0, 1.0)
        fp = float((pred_here * (1.0 - kernel)).sum())
    else:
        fp = float(pred_here.sum())
    denominator = tp + alpha * fp + beta * fn + epsilon
    return {"tp": tp, "fp": fp, "fn": fn, "truth_px": float(truth_count),
            "dti": float(tp / denominator) if denominator > 0 else 0.0}


def marginal_threshold(dti: float, *, alpha: float = DEFAULT_ALPHA) -> float:
    """Kernel credit a new dot must reach to be worth emitting at score ``dti``."""
    if not 0.0 <= dti <= 1.0:
        raise ValueError("dti must lie in [0, 1]")
    return alpha * dti


def kernel_credit(distance_px: np.ndarray | float, *,
                  pixel_size_m: float = DEFAULT_PIXEL_M,
                  radius_m: float = DEFAULT_RADIUS_M) -> np.ndarray | float:
    """``k(d)`` for distances in pixels."""
    return np.clip(1.0 - (np.asarray(distance_px) * pixel_size_m) / radius_m, 0.0, 1.0)


def implied_truth_pixels(tp: float, dti: float, fp: float, *,
                         alpha: float = DEFAULT_ALPHA, beta: float = DEFAULT_BETA) -> float:
    """Invert ``DTI = T / (alpha(T + F) + beta G)`` for the scored truth count ``G``."""
    if dti <= 0.0:
        raise ValueError("dti must be positive")
    return (tp / dti - alpha * (tp + fp)) / beta
