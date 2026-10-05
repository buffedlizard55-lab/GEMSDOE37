"""Budget-aware selection and fast exact DTI sweeps.

The competition metric is

    DTI = TPw / (TPw + alpha*FPw + beta*FNw + eps),  alpha=0.2, beta=0.8

with ``TPw = sum_g max_{d(x,g)<=R} p(x) k(d)``, ``FNw = |G| - TPw`` and
``FPw = sum_x p(x) [1 - max_g k(d(x,g))]`` for the triangular kernel
``k(d) = max(1 - d/R, 0)``, ``R = 300 m = 3 px``
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

Two consequences drive the code here.

*Binary predictions are optimal at a fixed budget.*  Writing ``D = 0.8|G| +
0.2 TPw + 0.2 FPw``, the derivative of the objective with respect to a single
pixel's probability is ``(dTP*(D - 0.2 TPw) - 0.2 TPw*dFP)/D^2``; it has a
constant sign in ``p(x)``, so each pixel's optimum lies at 0 or 1 and the
break-even condition is ``dTP/dFP > 0.2 * DTI``.  At a leaderboard DTI near
0.3 a predicted pixel only pays for itself if it adds about 6% of a unit of
kernel-weighted recall.  That is why the budget, not the raw map, dominates
the score.

*TPw saturates per truth pixel.*  Because the truth term is a maximum over the
300 m neighbourhood, two predictions 1 px apart largely pay twice for the same
recall.  Enforcing a minimum spacing ("dotting") buys nearly the same TPw for a
fraction of the FPw.
"""

from __future__ import annotations

import numpy as np

try:
    from numba import njit

    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False

    def njit(*args, **kwargs):  # type: ignore[misc]
        def wrap(func):
            return func

        if args and callable(args[0]):
            return args[0]
        return wrap


ALPHA = 0.2
BETA = 0.8
RADIUS_M = 300.0
PIXEL_SIZE_M = 100.0
EPSILON = 1e-8


def kernel_offsets(radius_m: float = RADIUS_M, pixel_size_m: float = PIXEL_SIZE_M):
    """Offsets and triangular-kernel weights inside the scoring radius."""
    reach = int(np.floor(radius_m / pixel_size_m))
    rows: list[int] = []
    cols: list[int] = []
    weights: list[float] = []
    for dr in range(-reach, reach + 1):
        for dc in range(-reach, reach + 1):
            distance = np.hypot(dr * pixel_size_m, dc * pixel_size_m)
            if distance > radius_m:
                continue
            rows.append(dr)
            cols.append(dc)
            weights.append(1.0 - distance / radius_m)
    return (
        np.asarray(rows, dtype=np.int64),
        np.asarray(cols, dtype=np.int64),
        np.asarray(weights, dtype=np.float64),
    )


@njit(cache=True, nogil=True)
def _sweep(cand_rows, cand_cols, truth_id, best, off_r, off_c, off_w, fp_cost):  # pragma: no cover
    n = cand_rows.shape[0]
    height, width = truth_id.shape
    tp_curve = np.zeros(n, dtype=np.float64)
    fp_curve = np.zeros(n, dtype=np.float64)
    tp = 0.0
    fp = 0.0
    for i in range(n):
        r = cand_rows[i]
        c = cand_cols[i]
        fp += fp_cost[i]
        for k in range(off_r.shape[0]):
            rr = r + off_r[k]
            cc = c + off_c[k]
            if rr < 0 or rr >= height or cc < 0 or cc >= width:
                continue
            tid = truth_id[rr, cc]
            if tid < 0:
                continue
            w = off_w[k]
            if w > best[tid]:
                tp += w - best[tid]
                best[tid] = w
        tp_curve[i] = tp
        fp_curve[i] = fp
    return tp_curve, fp_curve


def dti_sweep(
    candidate_rows: np.ndarray,
    candidate_cols: np.ndarray,
    truth: np.ndarray,
    *,
    scoring_valid: np.ndarray,
    alpha: float = ALPHA,
    beta: float = BETA,
    radius_m: float = RADIUS_M,
    pixel_size_m: float = PIXEL_SIZE_M,
) -> dict[str, np.ndarray]:
    """Exact DTI for every prefix of a ranked binary candidate list.

    ``candidate_rows/cols`` must be ordered best-first and must already exclude
    pixels outside ``scoring_valid`` (masked known faults, out-of-footprint).
    """
    from scipy.ndimage import distance_transform_edt

    truth_valid = np.asarray(truth, dtype=bool) & np.asarray(scoring_valid, dtype=bool)
    n_truth = int(truth_valid.sum())
    if n_truth == 0:
        raise ValueError("no truth pixels in the scoring domain")

    truth_id = np.full(truth.shape, -1, dtype=np.int64)
    truth_id[truth_valid] = np.arange(n_truth, dtype=np.int64)

    nearest = distance_transform_edt(~truth_valid, sampling=pixel_size_m)
    nearest_kernel = np.clip(1.0 - nearest / radius_m, 0.0, 1.0)
    fp_cost = (1.0 - nearest_kernel)[candidate_rows, candidate_cols].astype(np.float64)

    off_r, off_c, off_w = kernel_offsets(radius_m, pixel_size_m)
    best = np.zeros(n_truth, dtype=np.float64)
    tp_curve, fp_curve = _sweep(
        candidate_rows.astype(np.int64),
        candidate_cols.astype(np.int64),
        truth_id,
        best,
        off_r,
        off_c,
        off_w,
        fp_cost,
    )
    fn_curve = n_truth - tp_curve
    dti = tp_curve / (tp_curve + alpha * fp_curve + beta * fn_curve + EPSILON)
    return {
        "k": np.arange(1, candidate_rows.size + 1),
        "tp": tp_curve,
        "fp": fp_curve,
        "fn": fn_curve,
        "dti": dti,
        "n_truth": n_truth,
    }


@njit(cache=True, nogil=True)
def _spaced(rows, cols, blocked, spacing, limit):  # pragma: no cover
    height, width = blocked.shape
    keep = np.zeros(rows.shape[0], dtype=np.uint8)
    reach = int(np.ceil(spacing))
    spacing_sq = spacing * spacing
    taken = 0
    for i in range(rows.shape[0]):
        if taken >= limit:
            break
        r = rows[i]
        c = cols[i]
        if blocked[r, c]:
            continue
        keep[i] = 1
        taken += 1
        for dr in range(-reach, reach + 1):
            rr = r + dr
            if rr < 0 or rr >= height:
                continue
            for dc in range(-reach, reach + 1):
                cc = c + dc
                if cc < 0 or cc >= width:
                    continue
                if dr * dr + dc * dc <= spacing_sq:
                    blocked[rr, cc] = True
    return keep


def spaced_selection(
    rows: np.ndarray,
    cols: np.ndarray,
    shape: tuple[int, int],
    spacing: float,
    limit: int,
    *,
    blocked: np.ndarray | None = None,
) -> np.ndarray:
    """Greedy best-first selection with a minimum centre-to-centre spacing.

    ``spacing <= 0`` disables thinning.  Returns the indices (into ``rows``)
    of the kept candidates, in rank order.
    """
    if limit <= 0:
        return np.empty(0, dtype=np.int64)
    if spacing <= 0:
        return np.arange(min(limit, rows.size), dtype=np.int64)
    grid = np.zeros(shape, dtype=np.bool_) if blocked is None else blocked.copy()
    keep = _spaced(rows.astype(np.int64), cols.astype(np.int64), grid, float(spacing), int(limit))
    return np.flatnonzero(keep.astype(bool))
