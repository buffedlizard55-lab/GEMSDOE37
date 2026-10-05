"""Static multiscale geophysical/topographic feature stack for the GEMS grid.

Every derived field is produced from the organizer-supplied 19-band
``training_features.tif`` only.  Nothing in this module uses fault labels, so
the stack can be built once and reused by every cross-validation fold without
leaking catalogue information.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from .persistence import h0_prominence

# 1-based band indices in training_features.tif, verified from the GeoTIFF
# per-band ``band_name`` tags (see data/prepared/manifest.json).
BAND_INDEX = {
    "mag_anom": 1,
    "rtp": 2,
    "tmi_hg": 3,
    "geod_2ndinv": 4,
    "iso_grav_anom_slope": 5,
    "tc": 6,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "tmi_vg": 9,
    "deq_n100a15": 10,
    "iso_grav_anom_vg": 11,
    "det_elev": 12,
    "iso_grav_anom": 13,
    "tmi": 14,
    "depth_to_base_surf": 15,
    "ieq_n100a15": 16,
    "cond_surf": 17,
    "iso_grav_anom_hg": 18,
    "det_elev_slope": 19,
}

# Fields that get the full multiscale differential treatment.
MULTISCALE_FIELDS = ("det_elev", "rtp", "iso_grav_anom", "cond_surf", "depth_to_base_surf")
SCALES = (1.0, 2.0, 4.0)
PIXEL_SIZE_M = 100.0
# Registered sup-norm perturbation assumption for the stability margin, in the
# units of the robustly normalised [0, 1] response fields.
PERSISTENCE_EPSILON = 0.01


@dataclass(frozen=True)
class Normalisation:
    low: float
    high: float


def robust_scale(values: np.ndarray, valid: np.ndarray, low_pct: float = 1.0, high_pct: float = 99.0) -> np.ndarray:
    """Clip to robust percentiles of the valid pixels and rescale to [0, 1]."""
    sample = values[valid]
    if sample.size == 0:
        return np.zeros_like(values, dtype=np.float32)
    low, high = np.percentile(sample.astype(np.float64), [low_pct, high_pct])
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return np.zeros_like(values, dtype=np.float32)
    out = (values.astype(np.float32) - np.float32(low)) / np.float32(high - low)
    return np.clip(out, 0.0, 1.0, out=out)


def fill_invalid(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Replace invalid pixels with the nearest valid value (edge-artifact guard)."""
    if valid.all():
        return values.astype(np.float32, copy=False)
    indices = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return values[tuple(indices)].astype(np.float32, copy=False)


def gradient_magnitude(field: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalised Gaussian gradient magnitude ``sigma * |grad G_sigma f|``."""
    gr = gaussian_filter(field, sigma, order=[1, 0], mode="nearest")
    gc = gaussian_filter(field, sigma, order=[0, 1], mode="nearest")
    return (np.hypot(gr, gc) * np.float32(sigma)).astype(np.float32)


def max_abs_curvature(field: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalised largest-magnitude Hessian eigenvalue ``sigma^2 max|lambda|``.

    Ridges, scarps and slope breaks all appear as extrema of the cross-profile
    second derivative, so the magnitude of the dominant principal curvature is
    the sign-agnostic edge/ridge response.
    """
    grr = gaussian_filter(field, sigma, order=[2, 0], mode="nearest")
    gcc = gaussian_filter(field, sigma, order=[0, 2], mode="nearest")
    grc = gaussian_filter(field, sigma, order=[1, 1], mode="nearest")
    mean = 0.5 * (grr + gcc)
    delta = np.sqrt(np.square(0.5 * (grr - gcc)) + np.square(grc))
    lam1 = mean + delta
    lam2 = mean - delta
    return (np.maximum(np.abs(lam1), np.abs(lam2)) * np.float32(sigma * sigma)).astype(np.float32)


def structure_coherence(field: np.ndarray, sigma: float) -> np.ndarray:
    """Structure-tensor coherence in [0, 1]; 1 means a locally linear texture."""
    gr = gaussian_filter(field, sigma, order=[1, 0], mode="nearest")
    gc = gaussian_filter(field, sigma, order=[0, 1], mode="nearest")
    jrr = gaussian_filter(gr * gr, 2.0 * sigma, mode="nearest")
    jcc = gaussian_filter(gc * gc, 2.0 * sigma, mode="nearest")
    jrc = gaussian_filter(gr * gc, 2.0 * sigma, mode="nearest")
    trace = jrr + jcc
    delta = np.sqrt(np.square(jrr - jcc) + 4.0 * np.square(jrc))
    with np.errstate(invalid="ignore", divide="ignore"):
        coherence = np.where(trace > 0, delta / trace, 0.0)
    return np.clip(coherence, 0.0, 1.0).astype(np.float32)


def persistence_features(response: np.ndarray, valid: np.ndarray, epsilon: float = PERSISTENCE_EPSILON):
    """Return ``(prominence, certified)`` for a robustly normalised response.

    ``prominence`` is the H0 persistence of the superlevel component each pixel
    belongs to; ``certified`` is 1 where the bar exceeds ``2*epsilon`` and is
    therefore stable under any sup-norm perturbation below ``epsilon``
    (Cohen-Steiner et al. 2007).
    """
    prominence = h0_prominence(response, valid)
    certified = (prominence > np.float32(2.0 * epsilon)).astype(np.float32)
    return prominence, certified
