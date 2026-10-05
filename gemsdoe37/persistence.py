"""H0 (connected-component) persistence on superlevel sets of a scalar field.

Why this module exists
----------------------
A fixed threshold on a curvature or gradient-magnitude surface cannot separate a
genuinely continuous ridge from a feature that only exists at one smoothing
level.  Persistent homology instead records, for the *whole* sweep of
thresholds, when each connected component of the superlevel set
``{x : f(x) >= t}`` is born (at a local maximum) and when it dies (when it
merges into an older, higher component).  The difference ``birth - death`` is
the component's persistence / topological prominence.

The classical stability theorem (Cohen-Steiner, Edelsbrunner & Harer, 2007,
*Stability of Persistence Diagrams*, Discrete & Computational Geometry 37:103-120,
https://doi.org/10.1007/s00454-006-1276-5) states that the bottleneck distance
between the diagrams of two tame functions is bounded by the sup-norm distance
between the functions.  A bar of persistence ``p`` therefore survives any
perturbation with sup-norm below ``p / 2``.  That is a statement about the
diagram, not about geology: a high-persistence ridge is a *scale-stable*
structure in the data, not a proven fault.

Implementation
--------------
Elder-rule union-find over pixels sorted in descending value (8-connectivity).
Each pixel is given the persistence of the component it joins at the moment it
is added, which yields a per-pixel "prominence of the dominating peak" map.
Pure NumPy/Python; runs in O(n alpha(n)) over the valid pixels.
"""

from __future__ import annotations

import numpy as np

try:  # optional acceleration; the pure-Python fallback is numerically identical
    from numba import njit

    HAVE_NUMBA = True
except Exception:  # pragma: no cover - exercised only without numba
    HAVE_NUMBA = False

    def njit(*args, **kwargs):  # type: ignore[misc]
        def wrap(func):
            return func

        if args and callable(args[0]):
            return args[0]
        return wrap


def _find(parent: np.ndarray, index: int) -> int:
    root = index
    while parent[root] != root:
        root = parent[root]
    while parent[index] != root:
        parent[index], index = root, parent[index]
    return root


@njit(cache=True, nogil=True)
def _h0_core(ordered_values, neighbour_ranks):  # pragma: no cover - jitted
    n = ordered_values.shape[0]
    degree = neighbour_ranks.shape[1]
    parent = np.arange(n).astype(np.int64)
    birth = ordered_values.copy()
    prominence = np.zeros(n, dtype=np.float64)
    died = np.zeros(n, dtype=np.uint8)
    assigned = np.arange(n).astype(np.int64)
    roots = np.empty(degree, dtype=np.int64)
    global_min = ordered_values[n - 1]

    for i in range(n):
        current = ordered_values[i]
        count = 0
        for k in range(degree):
            nb = neighbour_ranks[i, k]
            if nb < 0 or nb >= i:
                continue
            # find with path compression
            root = nb
            while parent[root] != root:
                root = parent[root]
            node = nb
            while parent[node] != root:
                nxt = parent[node]
                parent[node] = root
                node = nxt
            seen = False
            for j in range(count):
                if roots[j] == root:
                    seen = True
                    break
            if not seen:
                roots[count] = root
                count += 1
        if count == 0:
            # pixel i is a new regional maximum: it leads its own component
            continue
        oldest = roots[0]
        for j in range(1, count):
            r = roots[j]
            if birth[r] > birth[oldest] or (birth[r] == birth[oldest] and r < oldest):
                oldest = r
        parent[i] = oldest
        assigned[i] = oldest
        for j in range(count):
            r = roots[j]
            if r == oldest:
                continue
            prominence[r] = birth[r] - current
            died[r] = 1
            parent[r] = oldest

    out = np.zeros(n, dtype=np.float64)
    for i in range(n):
        root = assigned[i]
        if died[root] == 1:
            out[i] = prominence[root]
        else:
            # component never merged into an older one: it survives the whole sweep
            out[i] = birth[root] - global_min
    return out


def h0_prominence(
    field: np.ndarray,
    valid: np.ndarray | None = None,
    *,
    connectivity: int = 8,
) -> np.ndarray:
    """Return the per-pixel H0 persistence (prominence) map of ``field``.

    Parameters
    ----------
    field:
        2-D scalar response.  Superlevel sets are swept from high to low.
    valid:
        Optional boolean domain mask.  Invalid pixels get ``0.0``.
    connectivity:
        4 or 8 pixel connectivity for the filtration.

    Returns
    -------
    numpy.ndarray
        ``float32`` array, same shape as ``field``.  Each valid pixel carries
        the persistence ``birth - death`` of the superlevel component it
        belongs to when it enters the filtration.  Pixels belonging to the
        single global (never-dying) component receive the full range
        ``global_max - min_valid_value``.
    """
    if field.ndim != 2:
        raise ValueError("field must be 2-D")
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")
    height, width = field.shape
    if valid is None:
        valid = np.isfinite(field)
    else:
        valid = np.asarray(valid, dtype=bool) & np.isfinite(field)
    if valid.shape != field.shape:
        raise ValueError("valid mask shape must match field")

    values = np.asarray(field, dtype=np.float64)
    flat_valid = np.flatnonzero(valid.ravel())
    if flat_valid.size == 0:
        return np.zeros(field.shape, dtype=np.float32)

    flat_values = values.ravel()[flat_valid]
    order = np.argsort(-flat_values, kind="stable")
    ordered_flat = flat_valid[order]
    ordered_values = flat_values[order]

    # rank[p] = position of pixel p in the descending-value order (-1 if absent)
    rank = np.full(height * width, -1, dtype=np.int64)
    rank[ordered_flat] = np.arange(ordered_flat.size, dtype=np.int64)

    rows = (ordered_flat // width).astype(np.int64)
    cols = (ordered_flat % width).astype(np.int64)

    if connectivity == 4:
        offsets = ((-1, 0), (1, 0), (0, -1), (0, 1))
    else:
        offsets = (
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1),
        )

    # Precompute, for each ordered pixel, the ranks of its neighbours.
    neighbour_ranks = np.full((ordered_flat.size, len(offsets)), -1, dtype=np.int64)
    for k, (dr, dc) in enumerate(offsets):
        nr = rows + dr
        nc = cols + dc
        inside = (nr >= 0) & (nr < height) & (nc >= 0) & (nc < width)
        idx = np.where(inside, nr * width + nc, 0)
        neighbour_ranks[:, k] = np.where(inside, rank[idx], -1)

    out = _h0_core(np.ascontiguousarray(ordered_values), np.ascontiguousarray(neighbour_ranks))

    result = np.zeros(height * width, dtype=np.float32)
    result[ordered_flat] = out.astype(np.float32)
    return result.reshape(height, width)


def persistence_stability_margin(prominence: np.ndarray, epsilon: float) -> np.ndarray:
    """Return ``prominence - 2*epsilon`` clipped at zero.

    By the stability theorem a bar survives every perturbation whose sup-norm is
    below half its persistence, so ``prominence > 2*epsilon`` is the certified
    survival condition for an assumed noise bound ``epsilon``.  ``epsilon`` is a
    modelling assumption that must be registered, not a measured error bound.
    """
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    return np.clip(np.asarray(prominence, dtype=np.float32) - 2.0 * float(epsilon), 0.0, None)
