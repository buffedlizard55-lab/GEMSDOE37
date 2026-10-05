#!/usr/bin/env python3
"""Build the static (label-free) feature matrix for the GEMS grid.

Writes ``data/prepared/static_features.f32`` as a float32 memmap of shape
``(n_footprint_pixels, n_features)`` plus ``static_features.json`` with the
column names, the footprint index, and SHA-256 hashes of the inputs.

Run time on 2 CPU cores: roughly 10-15 minutes, peak RSS under ~1.5 GB.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.stack import (  # noqa: E402
    BAND_INDEX,
    MULTISCALE_FIELDS,
    PERSISTENCE_EPSILON,
    SCALES,
    fill_invalid,
    gradient_magnitude,
    max_abs_curvature,
    persistence_features,
    robust_scale,
    structure_coherence,
)

def expected_feature_names() -> list[str]:
    """Deterministic column order of the static feature matrix."""
    names = [f"raw_{name}" for name in BAND_INDEX]
    for field in MULTISCALE_FIELDS:
        for sigma in SCALES:
            names.append(f"grad_{field}_s{int(sigma)}")
            names.append(f"curv_{field}_s{int(sigma)}")
        names.append(f"coh_{field}")
    for family in ("dem", "mag", "grav"):
        names.append(f"pers_{family}_s2")
        names.append(f"pers_{family}_max")
        names.append(f"pers_{family}_scales")
    return names


RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
FEATURES_TIF = RAW / "training_features.tif"
TEMPLATE_TIF = RAW / "sample_submission.tif"
LABELS_TIF = RAW / "labels.tif"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 22), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    PREPARED.mkdir(parents=True, exist_ok=True)
    for path in (FEATURES_TIF, TEMPLATE_TIF, LABELS_TIF):
        if not path.is_file():
            print(f"missing input: {path}", file=sys.stderr)
            return 2

    with rasterio.open(TEMPLATE_TIF) as template:
        grid = {
            "width": int(template.width),
            "height": int(template.height),
            "crs": template.crs.to_string(),
            "transform": [float(v) for v in template.transform[:6]],
            "res": [float(v) for v in template.res],
        }
        footprint = np.isfinite(template.read(1))

    height, width = footprint.shape
    n_valid = int(footprint.sum())
    print(f"grid {width}x{height}, footprint pixels {n_valid}", flush=True)

    with rasterio.open(FEATURES_TIF) as source:
        if (source.width, source.height) != (width, height):
            print("feature grid does not match the template", file=sys.stderr)
            return 2
        band_names = [source.tags(i).get("band_name", "") for i in range(1, source.count + 1)]
        for name, index in BAND_INDEX.items():
            if band_names[index - 1] != name:
                print(f"band tag mismatch at {index}: {band_names[index-1]!r} != {name!r}", file=sys.stderr)
                return 2

        names = expected_feature_names()
        out_path = PREPARED / "static_features.npy"
        matrix = np.lib.format.open_memmap(
            out_path, mode="w+", dtype=np.float32, shape=(n_valid, len(names))
        )
        column_of = {name: j for j, name in enumerate(names)}
        written: set[str] = set()

        def emit(name: str, raster: np.ndarray) -> None:
            matrix[:, column_of[name]] = raster[footprint]
            written.add(name)
            print(f"  + {name}", flush=True)

        raw_cache: dict[str, np.ndarray] = {}
        for name, index in BAND_INDEX.items():
            band = source.read(index).astype(np.float32)
            valid = np.isfinite(band) & (band > -1e38)
            band = fill_invalid(np.where(valid, band, np.nan), valid)
            scaled = robust_scale(band, footprint & valid)
            emit(f"raw_{name}", scaled)
            if name in MULTISCALE_FIELDS:
                raw_cache[name] = scaled

        # Multiscale differential responses on the physically motivated fields.
        responses: dict[str, np.ndarray] = {}
        for name in MULTISCALE_FIELDS:
            field = raw_cache[name]
            for sigma in SCALES:
                grad = robust_scale(gradient_magnitude(field, sigma), footprint, 1.0, 99.5)
                emit(f"grad_{name}_s{int(sigma)}", grad)
                curv = robust_scale(max_abs_curvature(field, sigma), footprint, 1.0, 99.5)
                emit(f"curv_{name}_s{int(sigma)}", curv)
                if name == "det_elev":
                    responses[f"dem_curv_s{int(sigma)}"] = curv
                elif name == "rtp":
                    responses[f"mag_grad_s{int(sigma)}"] = grad
                elif name == "iso_grav_anom":
                    responses[f"grav_grad_s{int(sigma)}"] = grad
            emit(f"coh_{name}", structure_coherence(field, 2.0))
            del field
        raw_cache.clear()

    # Topological persistence: H0 bars of the superlevel filtration of each
    # response field, at each smoothing scale, plus the cross-scale survival
    # count (how many scales the pixel's bar is certified stable across).
    families = {
        "dem": [responses[f"dem_curv_s{int(s)}"] for s in SCALES],
        "mag": [responses[f"mag_grad_s{int(s)}"] for s in SCALES],
        "grav": [responses[f"grav_grad_s{int(s)}"] for s in SCALES],
    }
    for family, fields in families.items():
        survival = np.zeros((height, width), dtype=np.float32)
        best = np.zeros((height, width), dtype=np.float32)
        for sigma, field in zip(SCALES, fields):
            prominence, certified = persistence_features(field, footprint, PERSISTENCE_EPSILON)
            survival += certified
            np.maximum(best, prominence, out=best)
            if sigma == 2.0:
                emit(f"pers_{family}_s2", prominence)
            del prominence, certified
        emit(f"pers_{family}_max", best)
        emit(f"pers_{family}_scales", survival / len(SCALES))
        del survival, best
    del responses, families

    missing = sorted(set(names) - written)
    if missing:
        print(f"feature columns never written: {missing}", file=sys.stderr)
        return 2
    n_features = len(names)
    matrix.flush()
    del matrix

    np.save(PREPARED / "footprint.npy", footprint)
    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grid": grid,
        "n_footprint_pixels": n_valid,
        "feature_names": names,
        "n_features": n_features,
        "persistence_epsilon": PERSISTENCE_EPSILON,
        "scales_px": list(SCALES),
        "input_sha256": {
            "training_features.tif": sha256_file(FEATURES_TIF),
            "labels.tif": sha256_file(LABELS_TIF),
            "sample_submission.tif": sha256_file(TEMPLATE_TIF),
        },
    }
    (PREPARED / "static_features.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n_features": n_features, "n_pixels": n_valid}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
