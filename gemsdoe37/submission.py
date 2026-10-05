"""Competition-grid GeoTIFF writing and fail-closed format validation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import rasterio


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_geotiff(
    path: str | Path,
    template_path: str | Path,
    *,
    expected_budget: int | None = None,
    expected_epsg: int = 32611,
    expected_resolution_m: float = 100.0,
) -> dict[str, Any]:
    """Reopen a TIFF and check every stored value and grid field.

    The entire raster, not only an estimated in-footprint region, must be finite
    and inside `[0,1]`; output writers should use zeros outside the candidate
    footprint and omit the nodata tag to avoid leaking a sentinel into portal
    range validation.
    """
    path = Path(path)
    template_path = Path(template_path)
    with rasterio.open(template_path) as template, rasterio.open(path) as src:
        if template.crs is None or template.crs.to_epsg() != expected_epsg:
            raise ValueError(f"template must use EPSG:{expected_epsg}; got {template.crs}")
        if not np.allclose(template.res, (expected_resolution_m, expected_resolution_m), atol=1e-8):
            raise ValueError(f"template resolution must be {expected_resolution_m} m; got {template.res}")
        array = src.read(1)
        finite = np.isfinite(array)
        checks: dict[str, Any] = {
            "driver_is_gtiff": src.driver == "GTiff",
            "single_band": src.count == 1,
            "dtype_float32": src.dtypes == ("float32",),
            "shape_matches_template": (src.height, src.width) == (template.height, template.width),
            "crs_matches_template": src.crs == template.crs,
            "epsg_matches": bool(src.crs and src.crs.to_epsg() == expected_epsg),
            "transform_matches_template": np.allclose(
                tuple(src.transform)[:6], tuple(template.transform)[:6], atol=1e-8
            ),
            "resolution_matches_template": np.allclose(src.res, template.res, atol=1e-8),
            "bounds_match_template": np.allclose(
                (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top),
                (template.bounds.left, template.bounds.bottom, template.bounds.right, template.bounds.top),
                atol=1e-7,
            ),
            "nodata_tag_absent": src.nodata is None,
            "all_cells_finite": bool(np.all(finite)),
            "min": float(np.min(array[finite])) if np.any(finite) else None,
            "max": float(np.max(array[finite])) if np.any(finite) else None,
            "range_0_1_all_cells": bool(np.all((array >= 0.0) & (array <= 1.0))),
            "positive_pixels": int(np.count_nonzero(array > 0.0)),
        }
        if expected_budget is not None:
            checks["positive_pixels_match_budget"] = checks["positive_pixels"] == int(expected_budget)
        if not all(value for key, value in checks.items() if key not in {"min", "max", "positive_pixels"}):
            failed = [
                key
                for key, value in checks.items()
                if key not in {"min", "max", "positive_pixels"} and not value
            ]
            raise ValueError(f"GeoTIFF failed format checks: {failed}")
        checks["sha256"] = sha256_file(path)
        checks["size_bytes"] = path.stat().st_size
        return checks


def write_submission_geotiff(
    path: str | Path,
    prediction: np.ndarray,
    template_path: str | Path,
    *,
    expected_budget: int | None = None,
) -> dict[str, Any]:
    """Write a single-band float32 GeoTIFF on the exact example-template grid."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite an existing submission file: {path}")
    values = np.asarray(prediction, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("prediction must be a 2-D single-band array")
    if not np.all(np.isfinite(values)):
        raise ValueError("prediction contains NaN or infinity; no TIFF was written")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("prediction contains values outside [0,1]; no TIFF was written")
    if expected_budget is not None and int(np.count_nonzero(values > 0.0)) != int(expected_budget):
        raise ValueError("prediction positive-pixel count differs from expected matched budget")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.stem}.partial.tif")
    if temporary_path.exists():
        raise FileExistsError(f"refusing to overwrite stale partial submission file: {temporary_path}")
    try:
        with rasterio.open(template_path) as template:
            if values.shape != (template.height, template.width):
                raise ValueError("prediction shape differs from template")
            if template.crs is None or template.crs.to_epsg() != 32611:
                raise ValueError("template CRS is not EPSG:32611")
            if not np.allclose(template.res, (100.0, 100.0), atol=1e-8):
                raise ValueError(f"template pixel size is not 100 m: {template.res}")
            profile = template.profile.copy()
            profile.update(
                driver="GTiff",
                count=1,
                dtype="float32",
                nodata=None,
                compress="deflate",
                predictor=3,
                tiled=True,
                blockxsize=256,
                blockysize=256,
                BIGTIFF="IF_SAFER",
            )
            with rasterio.open(temporary_path, "w", **profile) as dst:
                dst.write(values, 1)
        validate_geotiff(temporary_path, template_path, expected_budget=expected_budget)
        temporary_path.replace(path)
        return validate_geotiff(path, template_path, expected_budget=expected_budget)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise
