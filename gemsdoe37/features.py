"""Mask-aware, scale-normalized transforms for fault-candidate surfaces."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass(frozen=True, slots=True)
class LayerSelection:
    """Metadata-identified feature bands used by the registered hypothesis."""

    dem_index: int
    magnetic_index: int
    gravity_index: int
    descriptions: dict[str, str]


def normalize_description(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def identify_layers(descriptions: list[str]) -> LayerSelection:
    """Select DEM, magnetic-potential, and gravity-potential bands by tags.

    The function deliberately refuses to guess a band index from file order.
    The order of bands in this challenge must be checked from the raster tags or
    documented source metadata before modeling.
    """
    normalized = [normalize_description(item) for item in descriptions]

    def choose(family: str, predicates: list[tuple[int, str, object]]) -> int:
        for priority, description, predicate in predicates:
            for index, name in enumerate(normalized):
                if predicate(name):
                    return index
        raise ValueError(
            f"could not identify a {family} band from GeoTIFF descriptions: {descriptions!r}"
        )

    dem = choose(
        "detrended elevation",
        [
            (
                0,
                "detrended elevation",
                lambda s: ("detrended elevation" in s or "det elev" in s)
                and not any(term in s for term in ("slope", "gradient", "curvature")),
            ),
            (
                1,
                "digital elevation model",
                lambda s: (s == "dem" or "digital elevation model" in s)
                and not any(term in s for term in ("slope", "gradient", "curvature")),
            ),
        ],
    )
    magnetic = choose(
        "magnetic potential field",
        [
            (
                0,
                "total magnetic intensity",
                lambda s: ("total magnetic intensity" in s or s == "tmi")
                and not any(term in s for term in ("slope", "gradient", "vertical", "horizontal")),
            ),
            (
                1,
                "reduced-to-pole magnetic anomaly",
                lambda s: ("reduced to pole magnetic" in s or s == "rtp")
                and not any(term in s for term in ("slope", "gradient", "vertical", "horizontal")),
            ),
            (
                2,
                "magnetic anomaly",
                lambda s: ("magnetic anomaly" in s or "mag anomaly" in s)
                and not any(term in s for term in ("slope", "gradient", "vertical", "horizontal")),
            ),
        ],
    )
    gravity = choose(
        "gravity potential field",
        [
            (
                0,
                "isostatic gravity anomaly",
                lambda s: ("isostatic gravity anomaly" in s or "iso grav anom" in s)
                and not any(term in s for term in ("slope", "gradient", "vertical", "horizontal")),
            ),
            (
                1,
                "gravity anomaly",
                lambda s: ("gravity anomaly" in s or "grav anom" in s)
                and not any(term in s for term in ("slope", "gradient", "vertical", "horizontal")),
            ),
        ],
    )
    return LayerSelection(
        dem_index=dem,
        magnetic_index=magnetic,
        gravity_index=gravity,
        descriptions={
            "dem_curvature": descriptions[dem],
            "magnetic_edge": descriptions[magnetic],
            "gravity_edge": descriptions[gravity],
        },
    )


def robust_standardize(
    field: np.ndarray,
    valid_mask: np.ndarray,
    *,
    fit_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Robustly map a band, optionally fitting percentiles on training blocks only."""
    values = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(values)
    if values.shape != valid.shape:
        raise ValueError("field and valid_mask shapes differ")
    fit = valid if fit_mask is None else np.asarray(fit_mask, dtype=bool)
    if fit.shape != values.shape:
        raise ValueError("fit_mask shape differs from field")
    sample = values[valid & fit]
    if sample.size < 100:
        raise ValueError("too few valid pixels for robust normalization")
    q_low, q_high = np.percentile(sample, [2.0, 98.0]).astype(np.float64)
    if not np.isfinite(q_low + q_high) or q_high <= q_low:
        raise ValueError("input layer has no usable robust dynamic range")
    standardized = np.zeros(values.shape, dtype=np.float32)
    standardized[valid] = np.clip((values[valid] - q_low) / (q_high - q_low), 0.0, 1.0)
    return standardized, valid


def masked_gaussian(
    field: np.ndarray,
    valid_mask: np.ndarray,
    *,
    sigma_px: float,
    support_floor: float = 0.95,
) -> tuple[np.ndarray, np.ndarray]:
    """Normalized Gaussian smooth that does not treat nodata as zero.

    The returned support mask excludes pixels with insufficient valid kernel
    support; this reduces false edges at nodata/footprint boundaries.
    """
    if sigma_px <= 0 or not np.isfinite(sigma_px):
        raise ValueError("sigma_px must be finite and positive")
    if not 0.0 < support_floor <= 1.0:
        raise ValueError("support_floor must be in (0, 1]")
    values = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(values)
    if values.shape != valid.shape:
        raise ValueError("field and valid_mask shapes differ")
    weights = valid.astype(np.float32)
    numerator = ndimage.gaussian_filter(
        np.where(valid, values, 0.0), sigma=sigma_px, mode="constant", cval=0.0, truncate=3.0
    )
    denominator = ndimage.gaussian_filter(
        weights, sigma=sigma_px, mode="constant", cval=0.0, truncate=3.0
    )
    smooth = np.zeros_like(values)
    enough = denominator >= support_floor
    np.divide(numerator, denominator, out=smooth, where=enough)
    return smooth, enough


def robust_unit_response(
    response: np.ndarray,
    valid_mask: np.ndarray,
    *,
    fit_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Map response strength to [0,1], fitting quantiles on training blocks only."""
    values = np.asarray(response, dtype=np.float32)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(values)
    fit = valid if fit_mask is None else np.asarray(fit_mask, dtype=bool)
    if fit.shape != values.shape:
        raise ValueError("fit_mask shape differs from response")
    sample = values[valid & fit]
    if sample.size < 100:
        raise ValueError("too few valid response pixels")
    q50, q995 = np.percentile(sample, [50.0, 99.5]).astype(np.float64)
    result = np.zeros(values.shape, dtype=np.float32)
    if q995 > q50:
        result[valid] = np.clip((values[valid] - q50) / (q995 - q50), 0.0, 1.0)
    return result, valid


def dem_curvature_ridge(
    field: np.ndarray,
    valid_mask: np.ndarray,
    *,
    sigma_px: float,
    pixel_size_m: float = 100.0,
    fit_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Scale-normalized Hessian anisotropy of detrended elevation.

    The transform emphasizes locations where cross-ridge curvature exceeds
    along-ridge curvature, for either convex or concave topographic expression.
    It is a geomorphic lineament proxy, not a fault classifier.
    """
    standardized, valid = robust_standardize(field, valid_mask, fit_mask=fit_mask)
    smooth, support = masked_gaussian(standardized, valid, sigma_px=sigma_px)
    spacing = float(pixel_size_m)
    gy, gx = np.gradient(smooth, spacing, spacing)
    gyy, gyx = np.gradient(gy, spacing, spacing)
    gxy, gxx = np.gradient(gx, spacing, spacing)
    mixed = 0.5 * (gyx + gxy)
    trace = gxx + gyy
    discriminant = np.sqrt(np.maximum((gxx - gyy) ** 2 + 4.0 * mixed**2, 0.0))
    eig_hi = 0.5 * (trace + discriminant)
    eig_lo = 0.5 * (trace - discriminant)
    # Difference of absolute principal curvatures suppresses isotropic bowls/peaks.
    response = (np.abs(eig_hi) - np.abs(eig_lo))
    response = np.maximum(response, 0.0) * (sigma_px * spacing) ** 2
    response[~support] = 0.0
    return robust_unit_response(response, support, fit_mask=fit_mask)


def potential_field_edge(
    field: np.ndarray,
    valid_mask: np.ndarray,
    *,
    sigma_px: float,
    pixel_size_m: float = 100.0,
    fit_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Scale-normalized horizontal gradient magnitude of a potential field."""
    standardized, valid = robust_standardize(field, valid_mask, fit_mask=fit_mask)
    smooth, support = masked_gaussian(standardized, valid, sigma_px=sigma_px)
    gy, gx = np.gradient(smooth, pixel_size_m, pixel_size_m)
    response = np.hypot(gx, gy) * (sigma_px * pixel_size_m)
    response[~support] = 0.0
    return robust_unit_response(response, support, fit_mask=fit_mask)


def select_named_indices(descriptions: list[str]) -> LayerSelection:
    """Public wrapper used by the data preparation and inference scripts."""
    if len(descriptions) < 3:
        raise ValueError("at least three described bands are required")
    return identify_layers(descriptions)
