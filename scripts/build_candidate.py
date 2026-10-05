#!/usr/bin/env python3
"""Build the registered candidate and spatial-fold-specific score surfaces.

All score arrays are ignored intermediates under ``data/prepared``. No TIFF is
written here. For each spatial pseudo-holdout fold, robust input/response
normalization percentiles are fitted on the other three quadrants only; full-grid
feature values remain available as prediction covariates.
"""

from __future__ import annotations

import gzip
import hashlib
import io
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

from gemsdoe37.features import dem_curvature_ridge, potential_field_edge  # noqa: E402
from gemsdoe37.holdout import spatial_quadrant_region_masks  # noqa: E402
from gemsdoe37.ridge import combine_independent_layers, conventional_single_scale_baseline, persistent_layer_score  # noqa: E402

RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
PREREG = ROOT / "research" / "preregistration.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_track_detail(result: Any, split_name: str, layer_name: str) -> dict[str, Any]:
    """Persist every accepted track's per-scale birth/death observations compactly."""
    path = PREPARED / f"persistence-tracks-{split_name}-{layer_name}.jsonl.gz"
    observation_count = 0
    with path.open("wb") as raw_stream:
        with gzip.GzipFile(fileobj=raw_stream, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as stream:
                for track_index, track in enumerate(result.accepted_tracks):
                    observations = [
                        {
                            "sigma_m": float(item.sigma_m),
                            "row": int(item.bar.row),
                            "column": int(item.bar.col),
                            "birth": float(item.bar.birth),
                            "death": float(item.bar.death),
                            "persistence": float(item.bar.persistence),
                        }
                        for item in track.observations
                    ]
                    observation_count += len(observations)
                    record = {
                        "track_id": track_index,
                        "minimum_persistence": float(track.min_persistence),
                        "epsilon": float(track.epsilon),
                        "stability_margin": float(track.stability_margin),
                        "sigma_span_m": float(track.sigma_span_m),
                        "observations": observations,
                    }
                    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "format": "gzip-compressed JSON Lines; all accepted tracks and their scale observations",
        "track_count": len(result.accepted_tracks),
        "bar_observation_count": observation_count,
    }


def build_score_pair(
    feature_fields: dict[str, np.ndarray],
    footprint: np.ndarray,
    normalization_fit_mask: np.ndarray,
    prereg: dict[str, Any],
    split_name: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Compute topological and same-scale control maps with a fixed fit mask."""
    parameters = prereg["persistence"]
    sigma_px = tuple(float(value) for value in parameters["gaussian_sigma_pixels"])
    epsilon = float(parameters["conditional_sup_norm_perturbation_epsilon"])
    min_persistence = float(parameters["minimum_bar_persistence"])
    minimum_stability_margin = float(parameters["minimum_stability_margin"])
    min_scale_count = int(parameters["minimum_adjacent_scales"])
    peak_distance = float(parameters["cross_scale_match_max_peak_distance_pixels"])
    fusion = prereg["fusion"]
    family_scores: dict[str, np.ndarray] = {}
    layer_receipts: dict[str, Any] = {}
    transforms = {
        "dem_curvature": dem_curvature_ridge,
        "magnetic_edge": potential_field_edge,
        "gravity_edge": potential_field_edge,
    }
    for name in ("dem_curvature", "magnetic_edge", "gravity_edge"):
        print(
            f"  persistent {name}: sigma={sigma_px} px; fit cells={int(normalization_fit_mask.sum()):,}",
            flush=True,
        )
        result = persistent_layer_score(
            feature_fields[name],
            footprint,
            layer_name=name,
            transform=transforms[name],
            sigma_px_values=sigma_px,
            pixel_size_m=float(parameters["pixel_size_m"]),
            min_persistence=min_persistence,
            epsilon=epsilon,
            minimum_stability_margin=minimum_stability_margin,
            min_scale_count=min_scale_count,
            max_peak_distance_px=peak_distance,
            peak_neighbourhood_px=int(fusion["peak_neighborhood_radius_pixels"]),
            max_bars=int(parameters["maximum_bars_per_scale"]),
            require_numba=True,
            normalization_fit_mask=normalization_fit_mask,
        )
        family_scores[name] = result.score
        layer_receipts[name] = {
            **result.receipt,
            "track_detail": write_track_detail(result, split_name, name),
        }

    topology_score, _, fusion_receipt = combine_independent_layers(
        family_scores,
        footprint,
        minimum_layer_support=int(fusion["minimum_independent_layer_families"]),
    )
    single_scale_score, single_scale_support = conventional_single_scale_baseline(
        feature_fields["dem_curvature"],
        feature_fields["magnetic_edge"],
        feature_fields["gravity_edge"],
        footprint,
        sigma_px=2.0,
        pixel_size_m=float(parameters["pixel_size_m"]),
        normalization_fit_mask=normalization_fit_mask,
    )
    topology_score[~footprint] = 0.0
    single_scale_score[~footprint] = 0.0
    receipt = {
        "normalization_fit_pixels": int(normalization_fit_mask.sum()),
        "topological_layers": layer_receipts,
        "fusion": fusion_receipt,
        "candidate_score_nonzero_valid_pixels": int(np.count_nonzero(topology_score[footprint])),
        "candidate_score_max": float(np.max(topology_score[footprint])) if np.any(footprint) else 0.0,
        "single_scale_valid_pixels": int(single_scale_support.sum()),
        "single_scale_nonzero_valid_pixels": int(np.count_nonzero(single_scale_score[footprint])),
        "normalization_scope": "robust input and response percentiles fitted only on normalization_fit_mask",
    }
    return topology_score, single_scale_score, receipt


def build() -> dict[str, Any]:
    manifest_path = PREPARED / "manifest.json"
    footprint_path = PREPARED / "footprint.npy"
    if not manifest_path.is_file() or not footprint_path.is_file():
        raise FileNotFoundError("Run `python scripts/prepare_data.py` successfully before this command")
    manifest = load_json(manifest_path)
    prereg = load_json(PREREG)
    raw_paths = {
        "features": RAW / "training_features.tif",
        "labels": RAW / "labels.tif",
        "template": RAW / "sample_submission.tif",
    }
    for name, path in raw_paths.items():
        if not path.is_file() or sha256_file(path) != manifest["source_hashes_sha256"].get(name):
            raise RuntimeError(f"raw input {name} is missing or changed since preparation; rerun prepare_data.py")
    for name, path in {
        "footprint.npy": PREPARED / "footprint.npy",
        "labels.npy": PREPARED / "labels.npy",
    }.items():
        expected = manifest.get("derived_array_hashes_sha256", {}).get(name)
        if not path.is_file() or not expected or sha256_file(path) != expected:
            raise RuntimeError(f"prepared array {name} is missing or changed; rerun prepare_data.py")
    if not manifest.get("model_inputs_ready"):
        raise RuntimeError("Metadata layer selection failed; refusing to infer band order")
    selection = manifest["layer_selection"]
    index_by_layer = {
        "dem_curvature": int(selection["dem_index_1based"]),
        "magnetic_edge": int(selection["magnetic_index_1based"]),
        "gravity_edge": int(selection["gravity_index_1based"]),
    }
    feature_path = RAW / "training_features.tif"
    footprint = np.load(footprint_path).astype(bool, copy=False)
    feature_fields: dict[str, np.ndarray] = {}
    with rasterio.open(feature_path) as src:
        if src.count != len(manifest["band_descriptions"]):
            raise RuntimeError("Feature band count changed after preparation; rerun the audit")
        for name, one_based_index in index_by_layer.items():
            if not 1 <= one_based_index <= src.count:
                raise RuntimeError(f"Bad tag-selected band for {name}: {one_based_index}")
            raw = src.read(one_based_index).astype(np.float32, copy=False)
            valid = footprint & (src.read_masks(one_based_index) > 0) & np.isfinite(raw) & (raw > -1e38)
            if not np.any(valid):
                raise RuntimeError(f"No valid pixels in required layer {name}")
            feature_fields[name] = np.where(valid, raw, np.nan).astype(np.float32, copy=False)

    PREPARED.mkdir(parents=True, exist_ok=True)
    region_masks = spatial_quadrant_region_masks(footprint.shape)
    fit_masks = {"full": footprint}
    fit_masks.update({name: footprint & ~region for name, region in region_masks.items()})
    split_receipts: dict[str, Any] = {}
    full_topology_path = PREPARED / "topology_score.npy"
    full_control_path = PREPARED / "single_scale_score.npy"
    full_result: dict[str, Any] | None = None

    for split_name, fit_mask in fit_masks.items():
        if int(fit_mask.sum()) < 100:
            raise RuntimeError(f"Only {int(fit_mask.sum()):,} normalization-fit cells remain for {split_name}")
        print(f"Building {split_name} normalization split...", flush=True)
        topology_score, control_score, split_receipt = build_score_pair(
            feature_fields, footprint, fit_mask, prereg, split_name
        )
        if split_name == "full":
            topology_path, control_path = full_topology_path, full_control_path
            full_result = split_receipt
        else:
            topology_path = PREPARED / f"topology_score_fit_excluding_{split_name}.npy"
            control_path = PREPARED / f"single_scale_score_fit_excluding_{split_name}.npy"
        np.save(topology_path, topology_score.astype(np.float32, copy=False))
        np.save(control_path, control_score.astype(np.float32, copy=False))
        split_receipt["candidate_score"] = {
            "path": str(topology_path.relative_to(ROOT)),
            "sha256": sha256_file(topology_path),
        }
        split_receipt["single_scale_control"] = {
            "path": str(control_path.relative_to(ROOT)),
            "sha256": sha256_file(control_path),
        }
        split_receipts[split_name] = split_receipt
        del topology_score, control_score

    if full_result is None:
        raise RuntimeError("full-grid score build was not completed")
    receipt: dict[str, Any] = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_id": prereg["candidate_id"],
        "preregistration_sha256": sha256_file(PREREG),
        "manifest_sha256": sha256_file(manifest_path),
        "input_hashes_sha256": manifest["source_hashes_sha256"],
        "prepared_array_hashes_sha256": manifest["derived_array_hashes_sha256"],
        "provenance": manifest["provenance"],
        "grid": manifest["grid"],
        "selected_bands": {
            name: {
                "index_1based": index,
                "description": manifest["band_descriptions"][index - 1],
            }
            for name, index in index_by_layer.items()
        },
        "parameters": prereg["persistence"],
        "normalization_and_spatial_folds": {
            "rule": "fit robust input and response percentiles on the three non-held-out quadrants; predict across the full unsupervised feature grid",
            "guarded_evaluation_masks": "four inner quadrants with 300 m boundary guards; see validation script",
            "folds": {name: record for name, record in split_receipts.items() if name != "full"},
            "full_grid_fit_pixels": full_result["normalization_fit_pixels"],
        },
        "full_grid": {
            "candidate_score": split_receipts["full"]["candidate_score"],
            "single_scale_control": split_receipts["full"]["single_scale_control"],
            "topological_layers": full_result["topological_layers"],
            "fusion": full_result["fusion"],
            "note": "Full-grid normalization is used only to form the eventual candidate map after the held-out folds pass.",
        },
        "note": "Ranking surfaces are not calibrated probabilities and are not a submission TIFF.",
    }
    output = PREPARED / "candidate-build-receipt.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_id": receipt["candidate_id"],
        "folds_built": list(split_receipts),
        "full_candidate_nonzero_pixels": full_result["candidate_score_nonzero_valid_pixels"],
        "build_receipt": str(output.relative_to(ROOT)),
        "submission_tif_written": False,
    }, indent=2))
    return receipt


def main() -> int:
    try:
        build()
    except Exception as exc:
        print(f"CANDIDATE BUILD BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
