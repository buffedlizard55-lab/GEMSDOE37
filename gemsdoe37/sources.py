"""Open-source raster loading, quantisation decoding, and label-free features.

Every layer handled here is a public, freely redistributable product:

* ``training_features.tif`` / ``labels.tif`` / ``sample_submission.tif`` — the
  competition inputs, reassembled by ``scripts/fetch_open_data.sh`` from the
  byte-split public mirror and hash-checked against the mirror manifest.
* ``lidar_scarp_features_u8.tif`` — 1 m LiDAR scarp metrics resampled to the
  competition grid; provenance and quantisation in
  ``data/raw/lidar_scarp_features.json`` (USGS 3DEP / GeoDAWN LiDAR).
* ``geodawn_rad_u8.tif`` — GeoDAWN airborne K/Th/U/TC radiometrics
  (USGS ScienceBase item 657e1d85d34e23d3533209f7, DOI 10.5066/P93LGLVQ).
* ``geodawn_extensions_u8.tif`` — derived Th/K, U/K, U/Th ratios and upward
  continued TMI from the same survey.

No prior submission raster is ever read by this module. Everything downstream of
these layers is computed from the open inputs and the label catalogue.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import rasterio
from scipy import ndimage as ndi

NODATA_SENTINEL_BELOW = -1.0e30


@dataclass(frozen=True)
class RasterSpec:
    """One source raster and how to decode it into finite float32 values."""

    key: str
    path: Path
    kind: str  # "float" | "quantised"
    band_names: tuple[str, ...]
    nodata: float | None
    scales: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0)

    @property
    def n_bands(self) -> int:
        return len(self.band_names)


def _quantised_to_float(array: np.ndarray, xmax: float, transform: str) -> np.ndarray:
    """Invert the documented uint8 quantisation ``q = 1 + round(254 * t(x/xmax))``."""
    q = array.astype(np.float32)
    norm = np.clip((q - 1.0) / 254.0, 0.0, 1.0)
    if transform == "sqrt":
        return (norm ** 2) * np.float32(xmax)
    if transform == "linear":
        return norm * np.float32(xmax)
    raise ValueError(f"unknown quantisation transform {transform!r}")


def load_specs(data_dir: Path) -> list[RasterSpec]:
    """Build the raster specification list from the fetched ``data/raw`` tree."""
    data_dir = Path(data_dir)
    specs: list[RasterSpec] = []

    with rasterio.open(data_dir / "training_features.tif") as src:
        names = tuple((d or f"band{i}").split(" - ")[0] for i, d in enumerate(src.descriptions, 1))
        specs.append(RasterSpec("gems", data_dir / "training_features.tif", "float", names,
                                float(src.nodata) if src.nodata is not None else None))

    for key, fname, meta in (
        ("lidar", "lidar_scarp_features_u8.tif", "lidar_scarp_features.json"),
        ("rad", "geodawn_rad_u8.tif", "geodawn_rad.json"),
        ("gdawnx", "geodawn_extensions_u8.tif", "geodawn_extensions.json"),
    ):
        path = data_dir / fname
        if not path.exists():
            continue
        with rasterio.open(path) as src:
            names = tuple(src.descriptions) if src.descriptions[0] else tuple(
                f"{key}{i}" for i in range(1, src.count + 1))
            specs.append(RasterSpec(key, path, "quantised", names,
                                    float(src.nodata) if src.nodata is not None else 0.0))
    return specs


def quantisation_table(data_dir: Path, key: str) -> dict[str, tuple[float, str]]:
    """Return ``{band_name: (xmax, transform)}`` for physically scaled products.

    ``lidar_scarp_features_u8.tif`` is quantised from physical units with the
    documented rule ``q = 1 + round(254 * t(clip(x / xmax, 0, 1)))`` and carries a
    per-band ``(xmax, transform)`` table, which this function returns.

    The radiometric and extension products are instead stored as *percentile
    ranks* (their sidecars say so verbatim: "Bytes are ranks, not physical
    units"), so there is no physical scale to invert. Those keys raise
    ``KeyError`` and ``read_band`` treats the bytes as ranks directly.
    """
    data_dir = Path(data_dir)
    files = {"lidar": "lidar_scarp_features.json", "rad": "geodawn_rad.json",
             "gdawnx": "geodawn_extensions.json"}
    payload = json.loads((data_dir / files[key]).read_text())
    table = payload.get("quantisation")
    if not isinstance(table, dict):
        raise KeyError(f"{files[key]} stores ranks, not physical units")
    return {k: (float(v[0]), str(v[1])) for k, v in table.items()}


def read_band(spec: RasterSpec, index: int, data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Read one band as finite float32 plus a validity mask (competition footprint)."""
    with rasterio.open(spec.path) as src:
        raw = src.read(index)
    if spec.kind == "float":
        values = raw.astype(np.float32)
        valid = np.isfinite(values) & (values > NODATA_SENTINEL_BELOW)
        if spec.nodata is not None and np.isfinite(spec.nodata):
            valid &= values != np.float32(spec.nodata)
    else:
        valid = raw != 0 if spec.nodata == 0 else np.ones(raw.shape, bool)
        try:
            xmax, transform = quantisation_table(data_dir, spec.key)[spec.band_names[index - 1]]
            values = _quantised_to_float(raw, xmax, transform)
        except KeyError:
            # Rank-scaled products: the byte already *is* the percentile rank.
            values = raw.astype(np.float32) / np.float32(255.0)
    if not valid.any():
        raise ValueError(f"{spec.path} band {index} has no valid cells")
    fill = float(np.median(values[valid]))
    values = np.where(valid, values, np.float32(fill))
    return values.astype(np.float32, copy=False), valid


def rank_uint8(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Rank-normalise to uint8 inside ``valid`` (0 elsewhere). Deterministic."""
    v = values[valid]
    order = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    out = np.zeros(values.shape, np.uint8)
    out[valid] = (order.astype(np.float64) * (255.0 / max(v.size - 1, 1))).astype(np.uint8)
    return out


def band_features(values: np.ndarray, valid: np.ndarray,
                  scales: tuple[float, ...], *, persistence_quantile: float = 0.95,
                  ) -> dict[str, np.ndarray]:
    """Label-free structural features for one band.

    ``e{s}``      scale-normalised gradient magnitude (edge/line response).
    ``lin``       Hessian eigenvalue-ratio line-ness at sigma = 2 (1 = line).
    ``pers``      topological persistence: how many of the four scales keep this
                  cell inside the top ``1 - persistence_quantile`` of that scale's
                  response, i.e. how far a structure survives across the
                  scale filtration. This is the discrete stability certificate
                  the project brief asks for: single-scale speckle scores 1, a
                  structure present at every scale scores ``len(scales)``.
    """
    feats: dict[str, np.ndarray] = {}
    survival = np.zeros(values.shape, np.uint8)
    for scale in scales:
        smooth = ndi.gaussian_filter(values, scale, mode="nearest")
        gy, gx = np.gradient(smooth)
        response = np.hypot(gx, gy) * np.float32(scale * scale)
        feats[f"e{scale:g}"] = rank_uint8(response, valid)
        threshold = float(np.quantile(response[valid], persistence_quantile))
        survival += (response >= threshold).astype(np.uint8)
        del smooth, gy, gx, response
    smooth = ndi.gaussian_filter(values, 2.0, mode="nearest")
    hyy = ndi.gaussian_filter(smooth, 0.0, order=(2, 0))
    hxx = ndi.gaussian_filter(smooth, 0.0, order=(0, 2))
    hxy = ndi.gaussian_filter(smooth, 0.0, order=(1, 1))
    del smooth
    root = np.sqrt(np.maximum((hxx - hyy) ** 2 + np.float32(4.0) * hxy ** 2, 0.0))
    small = np.float32(0.5) * (hxx + hyy - root)
    large = np.float32(0.5) * (hxx + hyy + root)
    del hxx, hyy, hxy, root
    line_ness = np.abs(large) / (np.abs(small) + np.abs(large) + np.float32(1e-9))
    del small, large
    feats["lin"] = rank_uint8(line_ness, valid)
    feats["pers"] = survival
    return feats


def build_feature_store(specs: list[RasterSpec], data_dir: Path, output: Path,
                        *, persistence_quantile: float = 0.95) -> dict[str, Any]:
    """Write every band's features into one uint8 memmap of shape (n_feat, H, W)."""
    output = Path(output)
    shape: tuple[int, int] | None = None
    per_band_names: list[str] = []
    total = 0
    for spec in specs:
        with rasterio.open(spec.path) as src:
            if shape is None:
                shape = (src.height, src.width)
            elif (src.height, src.width) != shape:
                raise ValueError(f"{spec.path} is not on the competition grid")
        for index in range(1, spec.n_bands + 1):
            total += len(spec.scales) + 2
            for suffix in [f"e{s:g}" for s in spec.scales] + ["lin", "pers"]:
                per_band_names.append(f"{spec.key}:{spec.band_names[index - 1]}:{suffix}")
    assert shape is not None

    store = np.lib.format.open_memmap(output, mode="w+", dtype=np.uint8,
                                      shape=(total, *shape))
    reached = 0
    for spec in specs:
        for index in range(1, spec.n_bands + 1):
            values, valid = read_band(spec, index, data_dir)
            feats = band_features(values, valid, spec.scales,
                                  persistence_quantile=persistence_quantile)
            for name in [f"e{s:g}" for s in spec.scales] + ["lin", "pers"]:
                store[reached] = feats[name]
                reached += 1
            del values, valid, feats
    assert reached == total, (reached, total)
    store.flush()
    del store
    return {"path": str(output), "n_features": total, "shape": list(shape),
            "names": per_band_names}


def iter_band_plan(specs: list[RasterSpec]) -> Iterator[tuple[RasterSpec, int]]:
    for spec in specs:
        for index in range(1, spec.n_bands + 1):
            yield spec, index
