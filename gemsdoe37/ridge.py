"""Multiscale ridge transforms and persistence-weighted candidate scores."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import ndimage

from .features import dem_curvature_ridge, potential_field_edge
from .topology import PersistenceBar, PersistenceTrack, h0_superlevel_persistence, match_adjacent_scale_bars


Transform = Callable[..., tuple[np.ndarray, np.ndarray]]


@dataclass(frozen=True, slots=True)
class LayerPersistenceResult:
    score: np.ndarray
    support: np.ndarray
    receipt: dict[str, Any]
    accepted_tracks: tuple[PersistenceTrack, ...]


def persistent_layer_score(
    field: np.ndarray,
    valid_mask: np.ndarray,
    *,
    layer_name: str,
    transform: Transform,
    sigma_px_values: tuple[float, ...] = (1.0, 2.0, 4.0),
    pixel_size_m: float = 100.0,
    min_persistence: float = 0.05,
    epsilon: float = 0.01,
    minimum_stability_margin: float = 0.0,
    min_scale_count: int = 2,
    max_peak_distance_px: float = 2.0,
    peak_neighbourhood_px: int = 2,
    max_bars: int = 250_000,
    require_numba: bool = False,
    normalization_fit_mask: np.ndarray | None = None,
) -> LayerPersistenceResult:
    """Build a layer score from H0 bars stable in threshold and observed scales.

    For each Gaussian smoothing sigma, this computes an H0 superlevel diagram of
    a robustly normalized ridge/edge response. Bars at adjacent sigma values are
    greedily matched by peak location. A track contributes only if it appears at
    least ``min_scale_count`` scales and its minimum persistence exceeds
    ``2*epsilon``. The smoothing-scale track is a registered heuristic; the
    formal certificate is the per-sigma persistence lifetime margin under the
    stated sup-norm perturbation bound.
    """
    if not sigma_px_values or any(s <= 0 for s in sigma_px_values):
        raise ValueError("sigma_px_values must contain positive smoothing scales")
    if len(set(sigma_px_values)) != len(sigma_px_values):
        raise ValueError("sigma_px_values must be unique")
    if min_scale_count < 1 or min_scale_count > len(sigma_px_values):
        raise ValueError("min_scale_count must be within the number of scales")
    if min_persistence <= 0 or epsilon < 0 or min_persistence <= 2 * epsilon:
        raise ValueError("require min_persistence > 2*epsilon >= 0")
    if not np.isfinite(minimum_stability_margin) or minimum_stability_margin < 0:
        raise ValueError("minimum_stability_margin must be finite and non-negative")
    if peak_neighbourhood_px < 0:
        raise ValueError("peak_neighbourhood_px must be non-negative")

    values = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(values)
    if values.ndim != 2 or values.shape != valid.shape:
        raise ValueError("field and valid_mask must be matching 2-D arrays")

    responses: dict[float, np.ndarray] = {}
    support_by_sigma: dict[float, np.ndarray] = {}
    bars_by_sigma: dict[float, list[PersistenceBar]] = {}
    scale_receipts: list[dict[str, Any]] = []
    for sigma_px in sorted(float(s) for s in sigma_px_values):
        response, support = transform(
            values,
            valid,
            sigma_px=sigma_px,
            pixel_size_m=float(pixel_size_m),
            fit_mask=normalization_fit_mask,
        )
        response = np.asarray(response, dtype=np.float32)
        support = np.asarray(support, dtype=bool) & valid
        if response.shape != values.shape or support.shape != values.shape:
            raise ValueError("transform returned an unexpected array shape")
        sigma_m = sigma_px * float(pixel_size_m)
        bars = h0_superlevel_persistence(
            response,
            support,
            connectivity=8,
            min_persistence=float(min_persistence),
            max_bars=int(max_bars),
            require_numba=require_numba,
        )
        responses[sigma_m] = response
        support_by_sigma[sigma_m] = support
        bars_by_sigma[sigma_m] = bars
        scale_receipts.append(
            {
                "sigma_px": sigma_px,
                "sigma_m": sigma_m,
                "support_pixels": int(support.sum()),
                "finite_response_pixels": int(np.isfinite(response[support]).sum()),
                "bars_at_or_above_cutoff": len(bars),
            }
        )

    tracks = match_adjacent_scale_bars(
        bars_by_sigma,
        max_peak_distance_px=float(max_peak_distance_px),
        epsilon=float(epsilon),
    )
    accepted = [
        track
        for track in tracks
        if track.scale_count >= min_scale_count
        and track.stability_margin >= float(minimum_stability_margin)
    ]
    peak_weights: dict[float, np.ndarray] = {
        sigma_m: np.zeros(values.shape, dtype=np.float32) for sigma_m in responses
    }
    scale_count = len(responses)
    persistence_scale = max(min_persistence, 1e-8)
    for track in accepted:
        track_strength = min(1.0, track.stability_margin / persistence_scale)
        track_strength *= track.scale_count / scale_count
        for observation in track.observations:
            r, c = observation.bar.row, observation.bar.col
            peak_weights[observation.sigma_m][r, c] = max(
                peak_weights[observation.sigma_m][r, c], track_strength
            )

    score = np.zeros(values.shape, dtype=np.float32)
    radius = int(peak_neighbourhood_px)
    size = 2 * radius + 1
    for sigma_m, response in responses.items():
        peaks = peak_weights[sigma_m]
        if radius:
            neighborhood = ndimage.maximum_filter(peaks, size=size, mode="constant", cval=0.0)
        else:
            neighborhood = peaks
        score = np.maximum(score, response * neighborhood)
    support_union = np.zeros(values.shape, dtype=bool)
    for sigma_m in responses:
        support_union |= support_by_sigma[sigma_m]
    score[~support_union] = 0.0

    persistences = [track.min_persistence for track in accepted]
    margins = [track.stability_margin for track in accepted]
    receipt: dict[str, Any] = {
        "layer": layer_name,
        "transform": "H0 superlevel persistence of robustly normalized ridge response",
        "connectivity": 8,
        "sigma_px": list(sorted(float(s) for s in sigma_px_values)),
        "sigma_m": [float(s) * float(pixel_size_m) for s in sorted(sigma_px_values)],
        "minimum_bar_persistence": float(min_persistence),
        "sup_norm_perturbation_bound_epsilon": float(epsilon),
        "minimum_persistence_margin": float(min_persistence - 2.0 * epsilon),
        "minimum_required_stability_margin": float(minimum_stability_margin),
        "cross_scale_matching": {
            "rule": "one-to-one greedy matching of H0 peak coordinates at adjacent ordered scales",
            "max_peak_distance_px": float(max_peak_distance_px),
            "min_scale_count": int(min_scale_count),
            "formal_multiparameter_guarantee": False,
        },
        "scale_results": scale_receipts,
        "tracked_features": len(tracks),
        "accepted_tracks": len(accepted),
        "accepted_min_persistence_min": float(min(persistences)) if persistences else None,
        "accepted_min_persistence_median": float(np.median(persistences)) if persistences else None,
        "accepted_stability_margin_min": float(min(margins)) if margins else None,
        "accepted_stability_margin_median": float(np.median(margins)) if margins else None,
        "score_nonzero_pixels": int(np.count_nonzero(score)),
        "interpretation": (
            "Per-sigma persistence margins are conditional mathematical stability certificates. "
            "Scale tracks are a spatially matched empirical survival summary, not a proof of geology."
        ),
    }
    return LayerPersistenceResult(
        score=score,
        support=support_union,
        receipt=receipt,
        accepted_tracks=tuple(accepted),
    )



def combine_independent_layers(
    layer_scores: dict[str, np.ndarray],
    valid_mask: np.ndarray,
    *,
    minimum_layer_support: int = 2,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Fuse layer scores only where at least two independent families agree.

    Scores are dimensionless `[0,1]` persistence-weighted responses. An arithmetic
    mean over supported layers prevents an absent layer from forcing the product
    to zero. The minimum-family requirement is a preregistered design choice,
    not a learned posterior probability.
    """
    if len(layer_scores) < minimum_layer_support:
        raise ValueError("not enough independent layers to apply the agreement gate")
    if minimum_layer_support < 1:
        raise ValueError("minimum_layer_support must be positive")
    arrays = [np.asarray(value, dtype=np.float32) for value in layer_scores.values()]
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all layer scores must have the same shape")
    valid = np.asarray(valid_mask, dtype=bool)
    if valid.shape != shape:
        raise ValueError("valid_mask shape must match layer scores")
    if any(not np.all(np.isfinite(array[valid])) for array in arrays):
        raise ValueError("layer scores contain non-finite values inside the valid mask")
    if any(np.any(array[valid] < 0) or np.any(array[valid] > 1) for array in arrays):
        raise ValueError("valid layer scores must lie in [0,1]")

    stacked = np.stack(arrays, axis=0)
    supported = stacked > 0.0
    count = supported.sum(axis=0)
    sums = np.where(supported, stacked, 0.0).sum(axis=0, dtype=np.float32)
    fused = np.zeros(shape, dtype=np.float32)
    enough = valid & (count >= minimum_layer_support)
    np.divide(sums, count, out=fused, where=enough)
    # Modest explicit bonus for 3-way independent agreement; no calibration claim.
    if len(arrays) >= 3:
        fused[enough] *= (0.75 + 0.25 * count[enough] / len(arrays))
    fused[~valid] = 0.0
    receipt = {
        "layer_count": len(arrays),
        "minimum_layer_support": int(minimum_layer_support),
        "cells_with_0_layers": int(np.count_nonzero(valid & (count == 0))),
        "cells_with_1_layer": int(np.count_nonzero(valid & (count == 1))),
        "cells_with_2_or_more_layers": int(np.count_nonzero(valid & (count >= 2))),
        "cells_with_all_layers": int(np.count_nonzero(valid & (count == len(arrays)))),
    }
    return fused, enough, receipt


def conventional_single_scale_baseline(
    dem: np.ndarray,
    magnetic: np.ndarray,
    gravity: np.ndarray,
    valid_mask: np.ndarray,
    *,
    sigma_px: float = 2.0,
    pixel_size_m: float = 100.0,
    normalization_fit_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Matched-budget control: mean normalized single-scale transforms, no PH."""
    dem_score, dem_valid = dem_curvature_ridge(
        dem,
        valid_mask,
        sigma_px=sigma_px,
        pixel_size_m=pixel_size_m,
        fit_mask=normalization_fit_mask,
    )
    mag_score, mag_valid = potential_field_edge(
        magnetic,
        valid_mask,
        sigma_px=sigma_px,
        pixel_size_m=pixel_size_m,
        fit_mask=normalization_fit_mask,
    )
    grav_score, grav_valid = potential_field_edge(
        gravity,
        valid_mask,
        sigma_px=sigma_px,
        pixel_size_m=pixel_size_m,
        fit_mask=normalization_fit_mask,
    )
    support = dem_valid & mag_valid & grav_valid
    baseline = (dem_score + mag_score + grav_score) / 3.0
    baseline[~support] = 0.0
    return baseline, support
