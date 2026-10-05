#!/usr/bin/env python3
"""Audit the downloaded GEMS rasters without assuming their provenance or band order.

Inputs are the user-provided public Dropbox mirrors named in ``data_sources.json``.
This script checks that their grids match, identifies feature bands from GeoTIFF tags
rather than guessed indices, derives an in-footprint mask, hashes every input, and
writes an audit manifest under ignored ``data/prepared/``. It does not train a model.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.features import identify_layers  # noqa: E402


RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def band_descriptions(src: rasterio.io.DatasetReader) -> list[str]:
    descriptions: list[str] = []
    for index in range(1, src.count + 1):
        tags = src.tags(index)
        description = (
            tags.get("description")
            or tags.get("band_name")
            or tags.get("long_name")
            or src.descriptions[index - 1]
            or ""
        )
        descriptions.append(str(description).strip())
    return descriptions


def _grid(src: rasterio.io.DatasetReader) -> dict[str, Any]:
    return {
        "driver": src.driver,
        "width": int(src.width),
        "height": int(src.height),
        "count": int(src.count),
        "dtypes": list(src.dtypes),
        "crs": src.crs.to_string() if src.crs else None,
        "epsg": src.crs.to_epsg() if src.crs else None,
        "transform": [float(value) for value in src.transform[:6]],
        "resolution": [float(value) for value in src.res],
        "bounds": [float(value) for value in src.bounds],
        "nodata": float(src.nodata) if src.nodata is not None and np.isfinite(src.nodata) else (
            "nan" if src.nodata is not None else None
        ),
    }


def prepare() -> dict[str, Any]:
    paths = {
        "features": RAW / "training_features.tif",
        "labels": RAW / "labels.tif",
        "template": RAW / "sample_submission.tif",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing required mirror TIFF(s): " + ", ".join(missing) + ". Run `bash scripts/download_competition_data.sh`."
        )

    with rasterio.open(paths["features"]) as features, rasterio.open(paths["labels"]) as labels, rasterio.open(
        paths["template"]
    ) as template:
        grids = {"features": _grid(features), "labels": _grid(labels), "template": _grid(template)}
        reference = grids["template"]
        if reference["crs"] is None:
            raise ValueError("Template has no CRS")
        if reference["epsg"] != 32611:
            raise ValueError(f"Expected EPSG:32611 from the competition specification, got {reference['crs']}")
        if not np.allclose(reference["resolution"], [100.0, 100.0], atol=1e-8):
            raise ValueError(f"Expected 100 m pixels, got {reference['resolution']}")
        for name, grid in grids.items():
            if grid["width"] != reference["width"] or grid["height"] != reference["height"]:
                raise ValueError(f"{name} dimensions do not match the example template")
            if grid["crs"] != reference["crs"] or not np.allclose(
                grid["transform"], reference["transform"], atol=1e-8
            ):
                raise ValueError(f"{name} CRS/transform does not match the example template")
        if features.count < 3:
            raise ValueError(f"Expected a multiband feature TIFF, found {features.count} band(s)")
        if labels.count != 1 or template.count != 1:
            raise ValueError("Labels and example template must be single-band rasters")

        descriptions = band_descriptions(features)
        layer_selection: dict[str, Any]
        selection_error: str | None = None
        try:
            selected = identify_layers(descriptions)
            layer_selection = {
                "dem_index_1based": selected.dem_index + 1,
                "magnetic_index_1based": selected.magnetic_index + 1,
                "gravity_index_1based": selected.gravity_index + 1,
                "descriptions": selected.descriptions,
            }
            selected_indices = sorted(
                {selected.dem_index + 1, selected.magnetic_index + 1, selected.gravity_index + 1}
            )
        except ValueError as exc:
            layer_selection = {"selected": None}
            selected_indices = []
            selection_error = str(exc)

        # Derive a conservative valid mask from finite template values plus the
        # required detector bands. Do not infer a mask from a prior output TIFF.
        template_values = template.read(1)
        footprint = (template.dataset_mask() > 0) & np.isfinite(template_values)
        band_validity: dict[str, int] = {}
        for band_index in selected_indices:
            band = features.read(band_index)
            band_valid = (features.read_masks(band_index) > 0) & np.isfinite(band) & (band > -1e38)
            footprint &= band_valid
            band_validity[str(band_index)] = int(band_valid.sum())

        raw_labels = labels.read(1)
        label_valid = (labels.dataset_mask() > 0) & np.isfinite(raw_labels) & (raw_labels > -1e38)
        footprint &= label_valid
        values_inside = np.unique(raw_labels[footprint])
        allowed_labels = np.isin(values_inside, np.array([0, 1], dtype=values_inside.dtype))
        if not bool(np.all(allowed_labels)):
            raise ValueError(f"Labels contain values other than 0/1 in the derived footprint: {values_inside[:20]!r}")
        positive = footprint & (raw_labels == 1)
        if not np.any(positive):
            raise ValueError("No positive fault labels remain inside the derived footprint")

        template_unique = np.unique(template_values[np.isfinite(template_values)])
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "prepared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "provenance": "User-provided public Dropbox mirrors; not authenticated against DrivenData source files.",
            "official_data_tab_access": "login required in this environment; no credentials used",
            "grid": reference,
            "input_grids": grids,
            "band_descriptions": descriptions,
            "layer_selection": layer_selection,
            "layer_selection_error": selection_error,
            "selected_feature_band_valid_pixels": band_validity,
            "template_unique_finite_values_sample": [float(value) for value in template_unique[:20]],
            "footprint_pixels": int(footprint.sum()),
            "outside_footprint_pixels": int(footprint.size - footprint.sum()),
            "positive_label_pixels": int(positive.sum()),
            "negative_label_pixels": int(footprint.sum() - positive.sum()),
            "model_inputs_ready": selection_error is None and bool(selected_indices),
            "source_hashes_sha256": {name: sha256_file(path) for name, path in paths.items()},
            "files": {name: {"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size} for name, path in paths.items()},
            "warnings": [
                "Mirror provenance is not organizer-verified; compare hashes to authenticated official data if available.",
                "The template-derived footprint is intersected with required-band and label validity; inspect mask counts before using it.",
                "A catalogue pseudo-holdout cannot establish discovery of expert-only faults.",
            ],
        }

    PREPARED.mkdir(parents=True, exist_ok=True)
    footprint_path = PREPARED / "footprint.npy"
    labels_path = PREPARED / "labels.npy"
    np.save(footprint_path, footprint.astype(np.bool_, copy=False))
    np.save(labels_path, positive.astype(np.bool_, copy=False))
    manifest["derived_array_hashes_sha256"] = {
        "footprint.npy": sha256_file(footprint_path),
        "labels.npy": sha256_file(labels_path),
    }
    output = PREPARED / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": str(output.relative_to(ROOT)),
        "grid": {key: manifest["grid"][key] for key in ("epsg", "width", "height", "resolution")},
        "feature_bands": len(descriptions),
        "footprint_pixels": manifest["footprint_pixels"],
        "positive_label_pixels": manifest["positive_label_pixels"],
        "layer_selection": manifest["layer_selection"],
        "model_inputs_ready": manifest["model_inputs_ready"],
        "provenance": manifest["provenance"],
    }, indent=2))
    if selection_error:
        print(f"WARNING: bands not selected by metadata; modeling will refuse to guess: {selection_error}")
    return manifest


def main() -> int:
    try:
        manifest = prepare()
    except Exception as exc:
        print(f"DATA PREPARATION BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0 if manifest["model_inputs_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
