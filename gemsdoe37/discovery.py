"""H6 discovery pipeline: multi-scale, persistence-certified, supervised fault discovery.

Design notes (all verified against the official competition definitions):

* Metric (DrivenData competition 306, problem description):
  ``DTI = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)`` with a triangular kernel
  ``k(d) = max(1 - d/300m, 0)``.  Because ``FN_w = |G| - TP_w`` exactly, the
  index can be rewritten as

      DTI = T / (0.8 |G| + 0.2 T + 0.2 F)

  which is strictly increasing in a global scaling of the prediction values.
  Therefore, for a fixed support, a *binary* 1.0-valued prediction dominates any
  fractional one.  This is a proof, not an assumption, and it is the reason the
  builder emits binary rasters.

* The marginal value of one extra emitted pixel is positive when
  ``dT > (0.2 DTI / (1 - 0.2 DTI)) * dF``.  At DTI ~ 0.28 that bar is ~0.059
  units of newly covered truth mass, which is why sparse "dotted" placement with
  spacing just under the 3-pixel kernel support is efficient: it maximises newly
  covered truth per emitted pixel.

* Topological persistence (H0 on superlevel sets) is used as a *stability
  certificate* on the multi-scale structural response, not as a detector.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
    maximum_filter,
    uniform_filter,
)


# --------------------------------------------------------------------------
# Scale-space structural responses
# --------------------------------------------------------------------------
def gradient_magnitude(field: np.ndarray, sigma: float) -> np.ndarray:
    """|grad| of a Gaussian-smoothed field (edge / lineament response)."""
    gy = gaussian_filter(field, sigma, order=(1, 0), mode="nearest")
    gx = gaussian_filter(field, sigma, order=(0, 1), mode="nearest")
    return np.hypot(gy, gx).astype(np.float32)


def ridge_strength(field: np.ndarray, sigma: float) -> np.ndarray:
    """Hessian ridge strength: ``max(-lambda_min, 0)`` of the smoothed Hessian.

    A fault scarp or a potential-field edge appears as an elongated extremum of
    the second-derivative field; ``-lambda_min`` is the classical Frangi-style
    ridge response for bright ridges and is rotation invariant.
    """
    fyy = gaussian_filter(field, sigma, order=(2, 0), mode="nearest")
    fxx = gaussian_filter(field, sigma, order=(0, 2), mode="nearest")
    fxy = gaussian_filter(field, sigma, order=(1, 1), mode="nearest")
    trace = fxx + fyy
    diff = fxx - fyy
    root = np.sqrt(np.maximum(diff * diff + 4.0 * fxy * fxy, 0.0))
    lambda_min = 0.5 * (trace - root)
    return np.maximum(-lambda_min, 0.0).astype(np.float32)


def rank_normalize(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Map valid cells to their [0,1] rank; invalid cells to 0.

    Rank normalisation is robust to the wildly different physical units and
    heavy tails of magnetic, gravimetric, geodetic and conductivity layers.
    """
    out = np.zeros(values.shape, dtype=np.float32)
    sample = values[valid]
    finite = np.isfinite(sample)
    if not finite.any():
        return out
    order = np.argsort(sample, kind="stable")
    ranks = np.empty(sample.size, dtype=np.float64)
    ranks[order] = np.arange(sample.size, dtype=np.float64)
    ranks /= max(sample.size - 1, 1)
    ranks[~finite] = 0.0
    out[valid] = ranks.astype(np.float32)
    return out


def scales_survived(
    responses: list[np.ndarray], valid: np.ndarray, quantile: float = 0.90
) -> np.ndarray:
    """Count how many scales a pixel stays in the upper tail of the response.

    This is the discrete, directly computable form of the stability statement
    asked for: a candidate that only exists at a single smoothing level scores
    1, one that survives the whole filtration scores ``len(responses)``.
    """
    count = np.zeros(responses[0].shape, dtype=np.float32)
    for response in responses:
        threshold = np.quantile(response[valid], quantile)
        count += (response >= threshold) & valid
    return count


# --------------------------------------------------------------------------
# Geometry of the emitted prediction
# --------------------------------------------------------------------------
def nonmax_suppress(score: np.ndarray, valid: np.ndarray, size: int = 3) -> np.ndarray:
    """Keep only local maxima of ``score`` in a ``size x size`` window."""
    peak = maximum_filter(np.where(valid, score, -np.inf), size=size, mode="nearest")
    return valid & (score >= peak) & (score > 0)


def greedy_spaced_selection(
    score: np.ndarray,
    allowed: np.ndarray,
    *,
    budget: int,
    spacing_px: float,
) -> np.ndarray:
    """Pick the top-``budget`` cells subject to a minimum pairwise spacing.

    Implemented as a deterministic greedy sweep in descending score order with
    an occupancy grid, i.e. a score-ordered Poisson-disk thinning.  Spacing just
    under the 3-pixel kernel support keeps near-complete kernel coverage while
    removing the redundant mass that the summed false-positive term punishes.
    """
    if budget <= 0:
        raise ValueError("budget must be positive")
    if spacing_px <= 0:
        raise ValueError("spacing_px must be positive")
    height, width = score.shape
    candidates = np.flatnonzero(allowed.ravel() & (score.ravel() > 0))
    if candidates.size == 0:
        return np.zeros(score.shape, dtype=bool)
    values = score.ravel()[candidates]
    # deterministic tie-break on flat index
    order = np.lexsort((candidates, -values))
    candidates = candidates[order]

    radius = float(spacing_px)
    cell = max(radius / np.sqrt(2.0), 1e-6)
    grid_w = int(width / cell) + 2
    grid_h = int(height / cell) + 2
    occupied: dict[int, list[tuple[float, float]]] = {}
    chosen: list[int] = []
    radius_sq = radius * radius
    for flat in candidates:
        r = flat // width
        c = flat % width
        gr = int(r / cell)
        gc = int(c / cell)
        blocked = False
        for dr in (-1, 0, 1):
            if blocked:
                break
            for dc in (-1, 0, 1):
                key = (gr + dr) * grid_w + (gc + dc)
                bucket = occupied.get(key)
                if not bucket:
                    continue
                for (pr, pc) in bucket:
                    if (pr - r) ** 2 + (pc - c) ** 2 < radius_sq:
                        blocked = True
                        break
                if blocked:
                    break
        if blocked:
            continue
        occupied.setdefault(gr * grid_w + gc, []).append((float(r), float(c)))
        chosen.append(int(flat))
        if len(chosen) >= budget:
            break
    mask = np.zeros(height * width, dtype=bool)
    if chosen:
        mask[np.asarray(chosen, dtype=np.int64)] = True
    _ = grid_h  # retained for clarity of the occupancy-grid geometry
    return mask.reshape(score.shape)


def catalogue_standoff(known: np.ndarray, standoff_px: float) -> np.ndarray:
    """Cells at least ``standoff_px`` away from every known-fault cell."""
    if standoff_px <= 0:
        return np.ones(known.shape, dtype=bool)
    distance = distance_transform_edt(~known)
    return distance >= float(standoff_px)


def local_mass(mask: np.ndarray, size: int = 3) -> float:
    """Mass-weighted mean neighbourhood occupancy; 1.0 means perfectly dotted."""
    binary = mask.astype(np.float32)
    total = binary.sum()
    if total == 0:
        return 0.0
    neighbourhood = uniform_filter(binary, size=size, mode="constant") * (size * size)
    return float((binary * neighbourhood).sum() / total)
