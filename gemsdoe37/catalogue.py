"""Catalogue-ablation folds and catalogue-geometry features.

Design rationale
----------------
DrivenData staff confirmed two facts that drive this module:

1. "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded
   from evaluation, so they do not count towards penalty terms."
   https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2
2. "'new fault' means 'any fault pixel not already captured by
   USGS/INGENIOUS' and can include newly mapped geometry of an existing fault
   system" - i.e. continuations beyond mapped tips, splays and parallel
   strands count as test truth.
   https://community.drivendata.org/t/where-do-you-draw-the-line/11536/2

Fact (2) means the hidden labels are *conditionally* concentrated around the
architecture of the catalogue, while fact (1) means the catalogue pixels
themselves are worth zero.  The features below encode that geometry explicitly:
distance to the visible catalogue, catalogue density at two scales, distance to
mapped fault *tips*, and a directional tip-continuation cone that extrapolates
each mapped segment along its own strike.

The fold design is a *catalogue ablation*: whole mapped fault objects are
hidden from the model and then used as the evaluation truth, reproducing the
competition's own structure (predict faults that are missing from the
catalogue you were trained on).  This is strictly more faithful than a
geographic block split, which only tests interpolation inside a mapped region.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label

STRUCTURE_8 = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True)
class AblationFolds:
    """Assignment of catalogue connected components to folds."""

    component_labels: np.ndarray   # int32 label image, 0 = background
    fold_of_component: np.ndarray  # fold index per component id (1-based ids at position id-1)
    n_folds: int

    def hidden_mask(self, fold: int) -> np.ndarray:
        ids = np.flatnonzero(self.fold_of_component == fold) + 1
        return np.isin(self.component_labels, ids)

    def visible_mask(self, fold: int) -> np.ndarray:
        ids = np.flatnonzero((self.fold_of_component != fold)) + 1
        return np.isin(self.component_labels, ids)


def make_ablation_folds(faults: np.ndarray, n_folds: int = 4, seed: int = 20261005) -> AblationFolds:
    """Split catalogue fault objects into ``n_folds`` groups of similar pixel mass.

    Components are shuffled and dealt to the currently lightest fold, so each
    fold hides a comparable number of fault pixels even though component sizes
    are heavy-tailed.
    """
    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")
    labels, count = label(np.asarray(faults, dtype=bool), structure=STRUCTURE_8)
    if count == 0:
        raise ValueError("no catalogue fault components found")
    sizes = np.bincount(labels.ravel())[1:]
    rng = np.random.default_rng(seed)
    order = rng.permutation(count)
    fold_of_component = np.zeros(count, dtype=np.int32)
    load = np.zeros(n_folds, dtype=np.int64)
    for component in order:
        target = int(np.argmin(load))
        fold_of_component[component] = target
        load[target] += int(sizes[component])
    return AblationFolds(labels.astype(np.int32), fold_of_component, n_folds)


def _component_endpoints(labels: np.ndarray, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (rows, cols, strike_angle) of the two extreme tips of each component.

    The strike is the principal axis of the component's pixel coordinates; the
    tips are the two pixels with the most extreme projection onto that axis.
    The returned angle is measured as ``atan2(d_row, d_col)`` of the outward
    direction at each tip.
    """
    rows_out: list[int] = []
    cols_out: list[int] = []
    angles: list[float] = []
    flat = labels.ravel()
    order = np.argsort(flat, kind="stable")
    sorted_labels = flat[order]
    starts = np.searchsorted(sorted_labels, ids, side="left")
    ends = np.searchsorted(sorted_labels, ids, side="right")
    width = labels.shape[1]
    for component_id, start, end in zip(ids, starts, ends):
        if end - start < 2:
            continue
        pixels = order[start:end]
        rr = (pixels // width).astype(np.float64)
        cc = (pixels % width).astype(np.float64)
        rr0 = rr - rr.mean()
        cc0 = cc - cc.mean()
        cov = np.array([[np.dot(rr0, rr0), np.dot(rr0, cc0)], [np.dot(rr0, cc0), np.dot(cc0, cc0)]])
        eigvals, eigvecs = np.linalg.eigh(cov)
        axis = eigvecs[:, int(np.argmax(eigvals))]
        projection = rr0 * axis[0] + cc0 * axis[1]
        hi = int(np.argmax(projection))
        lo = int(np.argmin(projection))
        rows_out.extend([int(rr[hi]), int(rr[lo])])
        cols_out.extend([int(cc[hi]), int(cc[lo])])
        angles.extend([
            float(np.arctan2(axis[0], axis[1])),
            float(np.arctan2(-axis[0], -axis[1])),
        ])
    return (
        np.asarray(rows_out, dtype=np.int64),
        np.asarray(cols_out, dtype=np.int64),
        np.asarray(angles, dtype=np.float64),
    )


def tip_continuation_field(
    visible: np.ndarray,
    labels: np.ndarray,
    visible_ids: np.ndarray,
    *,
    reach_px: float = 30.0,
    half_angle_deg: float = 25.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(tip_distance, continuation_score)`` rasters.

    ``continuation_score`` accumulates, for every mapped fault tip, a cone that
    extends ``reach_px`` pixels along the component's own strike with a
    half-angle of ``half_angle_deg``.  The score decays linearly with distance
    along the cone and with angular deviation, so a pixel directly beyond a
    mapped tip along strike scores highest.  This targets exactly the class of
    test truth the organizers described as "newly mapped geometry of an
    existing fault system".
    """
    height, width = visible.shape
    rows, cols, angles = _component_endpoints(labels, visible_ids)
    score = np.zeros((height, width), dtype=np.float32)
    tip_mask = np.zeros((height, width), dtype=bool)
    if rows.size == 0:
        return np.full((height, width), reach_px, dtype=np.float32), score
    tip_mask[rows, cols] = True

    reach = int(np.ceil(reach_px))
    cos_limit = float(np.cos(np.deg2rad(half_angle_deg)))
    dr, dc = np.mgrid[-reach : reach + 1, -reach : reach + 1]
    distance = np.hypot(dr, dc)
    inside = (distance > 0) & (distance <= reach_px)
    dr_in = dr[inside].astype(np.float64)
    dc_in = dc[inside].astype(np.float64)
    dist_in = distance[inside]
    unit_r = dr_in / dist_in
    unit_c = dc_in / dist_in
    radial_weight = (1.0 - dist_in / reach_px).astype(np.float32)

    for row, col, angle in zip(rows, cols, angles):
        axis_r = np.sin(angle)
        axis_c = np.cos(angle)
        cosine = unit_r * axis_r + unit_c * axis_c
        keep = cosine >= cos_limit
        if not np.any(keep):
            continue
        target_r = row + dr_in[keep].astype(np.int64)
        target_c = col + dc_in[keep].astype(np.int64)
        valid = (target_r >= 0) & (target_r < height) & (target_c >= 0) & (target_c < width)
        if not np.any(valid):
            continue
        angular = (cosine[keep][valid] - cos_limit) / max(1.0 - cos_limit, 1e-9)
        contribution = (radial_weight[keep][valid] * angular).astype(np.float32)
        np.maximum.at(score, (target_r[valid], target_c[valid]), contribution)

    tip_distance = distance_transform_edt(~tip_mask).astype(np.float32)
    np.clip(tip_distance, 0.0, reach_px, out=tip_distance)
    return tip_distance, score


def catalogue_features(
    visible: np.ndarray,
    labels: np.ndarray,
    visible_ids: np.ndarray,
    *,
    max_distance_px: float = 50.0,
) -> dict[str, np.ndarray]:
    """Build the per-fold catalogue-geometry feature rasters.

    All inputs are derived from the *visible* catalogue only, so the hidden
    fold contributes nothing to the features.
    """
    distance = distance_transform_edt(~visible).astype(np.float32)
    np.clip(distance, 0.0, max_distance_px, out=distance)
    density_near = gaussian_filter(visible.astype(np.float32), 15.0, mode="constant")
    density_far = gaussian_filter(visible.astype(np.float32), 60.0, mode="constant")
    tip_distance, continuation = tip_continuation_field(visible, labels, visible_ids)
    return {
        "cat_distance_px": distance,
        "cat_log_density_1500m": np.log1p(density_near * 1e3).astype(np.float32),
        "cat_log_density_6000m": np.log1p(density_far * 1e3).astype(np.float32),
        "cat_tip_distance_px": tip_distance,
        "cat_tip_continuation": continuation.astype(np.float32),
    }
