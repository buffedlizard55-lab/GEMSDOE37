#!/usr/bin/env python3
"""Run the preregistered spatial pseudo-holdout and gate TIFF creation.

The evaluation truth is the public catalogue raster, so it is a catalogue
pseudo-holdout, not the hidden expert-label test set. A TIFF is written only if
the topological candidate beats both the single-scale control and the pinned
owner-reported historical reference at a matched positive-pixel budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.holdout import spatial_quadrant_masks, top_budget_binary  # noqa: E402
from gemsdoe37.metric import distance_weighted_tversky  # noqa: E402
from gemsdoe37.submission import write_submission_geotiff  # noqa: E402

RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
REFERENCE = ROOT / "data" / "reference" / "prior-h33-h33-2-b2-evaluation-only.tif"
REFERENCE_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
PREREG = ROOT / "research" / "preregistration.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def score_one_fold(
    prediction: np.ndarray,
    labels: np.ndarray,
    footprint: np.ndarray,
    block: np.ndarray,
    prereg: dict[str, Any],
) -> dict[str, Any]:
    valid = footprint & block
    truth = labels & valid
    if not np.any(truth):
        raise ValueError("evaluation fold has no positive truth pixels after its guard")
    metric_spec = prereg["evaluation"]["metric"]
    metric = distance_weighted_tversky(
        prediction.astype(np.float32, copy=False),
        truth,
        valid_mask=valid,
        pixel_size_m=float(metric_spec["pixel_size_m"]),
        radius_m=float(metric_spec["radius_m"]),
        alpha=float(metric_spec["alpha"]),
        beta=float(metric_spec["beta"]),
        epsilon=float(metric_spec["denominator_epsilon"]),
    )
    return {
        **metric,
        "truth_pixels": int(truth.sum()),
        "valid_pixels": int(valid.sum()),
        "emitted_pixels": int(np.count_nonzero(prediction & valid)),
    }


def score_fold_surfaces(
    score_paths: dict[str, Path],
    labels: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int,
    prereg: dict[str, Any],
) -> dict[str, Any]:
    """Score a fold-specific surface fitted without that fold's quadrant."""
    pixel_m = float(prereg["persistence"]["pixel_size_m"])
    guard_m = float(prereg["evaluation"]["guard_distance_m"])
    if guard_m % pixel_m != 0:
        raise ValueError("holdout guard must be an integer number of pixels")
    masks = spatial_quadrant_masks(labels.shape, guard_px=int(guard_m / pixel_m))
    folds: dict[str, Any] = {}
    for name, block in masks.items():
        path = score_paths[name]
        if not path.is_file():
            raise FileNotFoundError(f"missing fold-specific score surface: {path}")
        score = np.load(path, mmap_mode="r")
        if score.shape != footprint.shape or labels.shape != footprint.shape:
            raise ValueError("score, label, and footprint shapes do not match")
        if not np.all(np.isfinite(score[footprint])):
            raise ValueError(f"score surface for fold {name} contains non-finite valid cells")
        prediction = top_budget_binary(score, footprint, budget=budget)
        folds[name] = score_one_fold(prediction, labels, footprint, block, prereg)
    return folds


def score_reference_across_folds(
    prediction: np.ndarray,
    labels: np.ndarray,
    footprint: np.ndarray,
    prereg: dict[str, Any],
) -> dict[str, Any]:
    pixel_m = float(prereg["persistence"]["pixel_size_m"])
    guard_m = float(prereg["evaluation"]["guard_distance_m"])
    if guard_m % pixel_m != 0:
        raise ValueError("holdout guard must be an integer number of pixels")
    masks = spatial_quadrant_masks(labels.shape, guard_px=int(guard_m / pixel_m))
    return {
        name: score_one_fold(prediction, labels, footprint, block, prereg)
        for name, block in masks.items()
    }


def _fold_values(record: dict[str, Any]) -> list[float]:
    return [float(record[name]["dti"]) for name in ("NW", "NE", "SW", "SE")]


def summarize_folds(record: dict[str, Any]) -> dict[str, Any]:
    values = _fold_values(record)
    return {
        "mean_dti": float(np.mean(values)),
        "std_dti_population": float(np.std(values)),
        "per_fold_dti": {name: float(record[name]["dti"]) for name in ("NW", "NE", "SW", "SE")},
        "truth_pixels_by_fold": {name: int(record[name]["truth_pixels"]) for name in ("NW", "NE", "SW", "SE")},
    }


def validate(*, publish: bool) -> dict[str, Any]:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    build_receipt_path = PREPARED / "candidate-build-receipt.json"
    build_receipt = json.loads(build_receipt_path.read_text(encoding="utf-8"))
    manifest_path = PREPARED / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if build_receipt.get("preregistration_sha256") != sha256_file(PREREG):
        raise RuntimeError("preregistration changed after candidate build; rebuild and revalidate")
    if build_receipt.get("manifest_sha256") != sha256_file(manifest_path):
        raise RuntimeError("prepared manifest changed after candidate build; rebuild and revalidate")
    if build_receipt.get("input_hashes_sha256") != manifest.get("source_hashes_sha256"):
        raise RuntimeError("candidate build and preparation input hashes do not agree")
    for name, path in {
        "features": RAW / "training_features.tif",
        "labels": RAW / "labels.tif",
        "template": RAW / "sample_submission.tif",
    }.items():
        if not path.is_file() or sha256_file(path) != manifest["source_hashes_sha256"].get(name):
            raise RuntimeError(f"raw input {name} is missing or changed after preparation")
    for name, path in {
        "footprint.npy": PREPARED / "footprint.npy",
        "labels.npy": PREPARED / "labels.npy",
    }.items():
        expected = manifest.get("derived_array_hashes_sha256", {}).get(name)
        if not path.is_file() or not expected or sha256_file(path) != expected:
            raise RuntimeError(f"prepared array {name} is missing or changed after preparation")
    topology_path = PREPARED / "topology_score.npy"
    control_path = PREPARED / "single_scale_score.npy"
    footprint = np.load(PREPARED / "footprint.npy").astype(bool, copy=False)
    labels = np.load(PREPARED / "labels.npy").astype(bool, copy=False)
    if not REFERENCE.is_file():
        raise FileNotFoundError(
            "Missing evaluation-only historical reference. Run `bash scripts/fetch_educational_baseline.sh`; "
            "this raster is for holdout comparison only and must never be offered as the generated output."
        )
    reference_sha256 = sha256_file(REFERENCE)
    if reference_sha256 != REFERENCE_SHA256:
        raise RuntimeError(
            f"evaluation-only reference SHA-256 mismatch: expected {REFERENCE_SHA256}, got {reference_sha256}"
        )
    if not topology_path.is_file() or not control_path.is_file():
        raise FileNotFoundError("Run `python scripts/build_candidate.py` before validation")
    if labels.shape != footprint.shape:
        raise ValueError("label and footprint shapes do not match")
    fold_topology_paths = {
        name: PREPARED / f"topology_score_fit_excluding_{name}.npy"
        for name in ("NW", "NE", "SW", "SE")
    }
    fold_control_paths = {
        name: PREPARED / f"single_scale_score_fit_excluding_{name}.npy"
        for name in ("NW", "NE", "SW", "SE")
    }
    fold_receipts = build_receipt.get("normalization_and_spatial_folds", {}).get("folds", {})
    track_receipt_sets = {
        **fold_receipts,
        "full": {"topological_layers": build_receipt.get("full_grid", {}).get("topological_layers", {})},
    }
    for split_name, split_receipt in track_receipt_sets.items():
        layer_receipts = split_receipt.get("topological_layers", {})
        for layer_name, layer_receipt in layer_receipts.items():
            detail = layer_receipt.get("track_detail", {})
            detail_path = ROOT / str(detail.get("path", ""))
            expected = detail.get("sha256")
            if not detail_path.is_file() or not expected or sha256_file(detail_path) != expected:
                raise RuntimeError(f"accepted-track detail for {split_name}/{layer_name} is missing or changed")
    for name in ("NW", "NE", "SW", "SE"):
        for label, path, receipt_key in (
            ("topological", fold_topology_paths[name], "candidate_score"),
            ("single-scale", fold_control_paths[name], "single_scale_control"),
        ):
            expected = fold_receipts.get(name, {}).get(receipt_key, {}).get("sha256")
            if not path.is_file() or not expected or sha256_file(path) != expected:
                raise RuntimeError(f"{label} score surface for {name} is missing or changed after build")

    with rasterio.open(RAW / "sample_submission.tif") as template:
        template_grid = {
            "height": template.height,
            "width": template.width,
            "crs": template.crs.to_string() if template.crs else None,
            "transform": [float(v) for v in template.transform[:6]],
            "resolution": [float(v) for v in template.res],
        }
        if (template.height, template.width) != footprint.shape:
            raise ValueError("prepared footprint does not match example template")
        with rasterio.open(REFERENCE) as ref_src:
            if ref_src.count != 1:
                raise ValueError("historical comparison TIFF is not single-band")
            if (ref_src.height, ref_src.width) != footprint.shape:
                raise ValueError("historical comparison raster shape differs from input grid")
            if ref_src.crs != template.crs or not np.allclose(
                tuple(ref_src.transform)[:6], tuple(template.transform)[:6], atol=1e-8
            ):
                raise ValueError("historical comparison raster CRS/transform differs from template")
            raw_reference = ref_src.read(1).astype(np.float32, copy=False)
            if not np.all(np.isfinite(raw_reference[footprint])):
                raise ValueError("historical comparison raster has non-finite values inside footprint")
            if np.any((raw_reference[footprint] < 0) | (raw_reference[footprint] > 1)):
                raise ValueError("historical comparison raster has values outside [0,1]")
            reference_prediction = raw_reference > 0.0

    budget = int(np.count_nonzero(reference_prediction & footprint))
    if budget <= 0:
        raise ValueError("historical reference contains no positive pixels inside the prepared footprint")
    folds = {
        "topological_candidate": score_fold_surfaces(
            fold_topology_paths, labels, footprint, budget=budget, prereg=prereg
        ),
        "single_scale_control": score_fold_surfaces(
            fold_control_paths, labels, footprint, budget=budget, prereg=prereg
        ),
        "historical_reference": score_reference_across_folds(
            reference_prediction, labels, footprint, prereg
        ),
    }
    summaries = {name: summarize_folds(value) for name, value in folds.items()}
    top = _fold_values(folds["topological_candidate"])
    hist = _fold_values(folds["historical_reference"])
    single = _fold_values(folds["single_scale_control"])
    gain_hist = [a - b for a, b in zip(top, hist)]
    gain_single = [a - b for a, b in zip(top, single)]
    gate = prereg["evaluation"]["promotion_gate"]
    hist_mean_gain = float(np.mean(gain_hist))
    single_mean_gain = float(np.mean(gain_single))
    pass_historical = (
        hist_mean_gain >= float(gate["mean_dti_gain_over_historical_control"])
        and sum(delta > 0.0 for delta in gain_hist) >= int(gate["minimum_positive_folds"])
        and min(gain_hist) >= -float(gate["maximum_allowed_single_fold_regression"])
    )
    pass_single_scale = (
        single_mean_gain > 0.0
        and sum(delta > 0.0 for delta in gain_single) >= int(gate["minimum_positive_folds"])
        and min(gain_single) >= -float(gate["maximum_allowed_single_fold_regression"])
    )
    slot_eligible = bool(pass_historical and pass_single_scale)
    report: dict[str, Any] = {
        "schema_version": 1,
        "validated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_id": prereg["candidate_id"],
        "truth_class": "public-catalogue pseudo-holdout; not expert-only hidden truth",
        "reference_status": "owner-reported historical artifact, score/file attribution not organizer-verified",
        "input_hashes_sha256": build_receipt["input_hashes_sha256"],
        "build_receipt_sha256": sha256_file(build_receipt_path),
        "preregistration_sha256": build_receipt["preregistration_sha256"],
        "normalization_fit_scope": prereg["evaluation"]["normalization_fit_scope"],
        "persistence_track_details": {
            "full_grid": {
                name: record["track_detail"]
                for name, record in build_receipt["full_grid"]["topological_layers"].items()
            },
            "spatial_folds": {
                split: {
                    name: record["track_detail"]
                    for name, record in split_record["topological_layers"].items()
                }
                for split, split_record in fold_receipts.items()
            },
        },
        "historical_reference_sha256": reference_sha256,
        "budget_positive_pixels": budget,
        "grid": template_grid,
        "folds": folds,
        "summaries": summaries,
        "paired_gains": {
            "topological_minus_historical_per_fold": dict(zip(("NW", "NE", "SW", "SE"), gain_hist)),
            "topological_minus_historical_mean": hist_mean_gain,
            "topological_minus_single_scale_per_fold": dict(zip(("NW", "NE", "SW", "SE"), gain_single)),
            "topological_minus_single_scale_mean": single_mean_gain,
        },
        "gate": {
            "rule": gate,
            "beats_historical_reference": bool(pass_historical),
            "beats_single_scale_control": bool(pass_single_scale),
            "slot_eligible": slot_eligible,
            "organizer_score_claimed": False,
        },
        "submission_written": False,
        "notes": [
            "Each quadrant is an evaluation-only spatial block with 300 m inner guard; the detector itself is unsupervised.",
            "Historical reference pixels are read only for comparison and fixed positive-pixel budget; they are not copied into the candidate map.",
            "The public-catalogue pseudo-holdout cannot prove discovery of hidden expert faults or predict the private leaderboard.",
        ],
    }
    report_path = PREPARED / "holdout-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_id": report["candidate_id"],
        "budget_positive_pixels": budget,
        "summaries": summaries,
        "paired_gains": report["paired_gains"],
        "gate": report["gate"],
        "report": str(report_path.relative_to(ROOT)),
    }, indent=2))

    if not publish:
        return report
    if not slot_eligible:
        raise RuntimeError("HOLDOUT GATE FAIL: no submission TIFF written; do not spend a weekly slot")

    # The output is generated from this run's full-grid score map, never from the historical raster.
    full_score_meta = build_receipt.get("full_grid", {}).get("candidate_score", {})
    if not topology_path.is_file() or sha256_file(topology_path) != full_score_meta.get("sha256"):
        raise RuntimeError("full-grid candidate score is missing or differs from the audited build receipt")
    topology_score = np.load(topology_path, mmap_mode="r")
    if topology_score.shape != footprint.shape or not np.all(np.isfinite(topology_score[footprint])):
        raise ValueError("full-grid candidate score is malformed or contains non-finite valid cells")
    topology_prediction = top_budget_binary(topology_score, footprint, budget=budget)
    run_time = datetime.now(timezone.utc)
    utc_stamp = run_time.strftime("%Y%m%dT%H%M%S%fZ")
    run_nonce = uuid4().hex[:8].upper()
    unique_digest = hashlib.sha256(
        topology_prediction.tobytes()
        + build_receipt["preregistration_sha256"].encode("ascii")
        + full_score_meta["sha256"].encode("ascii")
        + run_nonce.encode("ascii")
    ).hexdigest()[:8].upper()
    filename = f"gemsdoe37-topo-persistence-{utc_stamp}-{unique_digest.lower()}.tif"
    submission_id = f"GEMSDOE37-TOPO-PH-{utc_stamp}-{unique_digest}"
    note = (
        f"{submission_id} | H0 persistence, DEM curvature + mag/gravity edges; "
        f"{budget} px; 4-block catalogue holdout mean {summaries['topological_candidate']['mean_dti']:.4f}; "
        "unscored"
    )
    if len(note) > 200:
        raise RuntimeError(f"Submission note exceeds the configured 200-character limit ({len(note)} chars)")
    output_path = ROOT / "docs" / "downloads" / filename
    try:
        check = write_submission_geotiff(
            output_path,
            topology_prediction.astype(np.float32),
            RAW / "sample_submission.tif",
            expected_budget=budget,
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    report["submission_written"] = True
    report["submission"] = {
        "filename": filename,
        "relative_path": str(output_path.relative_to(ROOT)),
        "submission_name": submission_id,
        "submission_note": note,
        "format_receipt": check,
        "sha256": check["sha256"],
        "origin": "GEMSDOE37 H1 score surface; historical TIFF used only as budget/reference",
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    note_path = output_path.with_suffix(".note.txt")
    note_path.write_text(
        f"Submission name: {submission_id}\nNote: {note}\nFilename: {filename}\nSHA-256: {check['sha256']}\n",
        encoding="utf-8",
    )
    public_report = dict(report)
    local_details = report["persistence_track_details"]
    public_report["persistence_track_details"] = {
        "publication_note": "Hash-pinned full accepted-track sidecars are retained in the local ignored data/prepared directory; this small Pages receipt publishes their counts and hashes, not the large per-bar payloads.",
        "full_grid": {
            name: {
                "sha256": detail["sha256"],
                "track_count": detail["track_count"],
                "bar_observation_count": detail["bar_observation_count"],
            }
            for name, detail in local_details["full_grid"].items()
        },
        "spatial_folds": {
            split: {
                name: {
                    "sha256": detail["sha256"],
                    "track_count": detail["track_count"],
                    "bar_observation_count": detail["bar_observation_count"],
                }
                for name, detail in layers.items()
            }
            for split, layers in local_details["spatial_folds"].items()
        },
    }
    public_report_dir = ROOT / "docs" / "reports" / submission_id
    public_report_dir.mkdir(parents=True, exist_ok=False)
    public_report_path = public_report_dir / "holdout-report.json"
    public_report_path.write_text(json.dumps(public_report, indent=2) + "\n", encoding="utf-8")
    public_record = {
        "status": "HOLDOUT_GATE_PASSED_UNSCORED",
        "candidate_id": prereg["candidate_id"],
        "generated_utc": report["validated_utc"],
        "download_path": f"downloads/{filename}",
        "holdout_report_path": f"reports/{submission_id}/holdout-report.json",
        "filename": filename,
        "submission_name": submission_id,
        "submission_note": note,
        "sha256": check["sha256"],
        "positive_pixels": budget,
        "public_catalogue_holdout_mean_dti": summaries["topological_candidate"]["mean_dti"],
        "organizer_score": None,
        "format_receipt": check,
        "warning": "A pseudo-holdout pass is not an organizer score or proof of private-label performance.",
    }
    public_path = ROOT / "docs" / "data" / "current_submission.json"
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public_record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"submission": report["submission"]}, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--publish",
        action="store_true",
        help="write a TIFF only when both preregistered holdout gates pass; otherwise fail closed",
    )
    args = parser.parse_args()
    try:
        validate(publish=bool(args.publish))
    except Exception as exc:
        print(f"VALIDATION BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
