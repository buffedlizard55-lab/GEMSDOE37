#!/usr/bin/env python3
"""Run the preregistered spatial pseudo-holdout and gate TIFF creation.

The evaluation truth is the public catalogue raster, so this is a catalogue
pseudo-holdout, not the hidden expert-label test set. The scorer applies the
organizer-confirmed exact known-fault mask to each fold. A TIFF is never written
unless the topological candidate beats its same-budget control and a separately
registered current holdout-best report on the same inputs and protocol.
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

from gemsdoe37.holdout import (  # noqa: E402
    spatial_quadrant_masks,
    spatial_quadrant_region_masks,
    top_budget_binary,
)
from gemsdoe37.metric import distance_weighted_tversky  # noqa: E402
from gemsdoe37.submission import write_submission_geotiff  # noqa: E402

RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
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
    known_fault_mask: np.ndarray,
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
        exclusion_mask=known_fault_mask,
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
        "visible_known_fault_pixels": int(known_fault_mask.sum()),
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
    """Score fold-specific surfaces using only visible exact known-fault masks."""
    pixel_m = float(prereg["persistence"]["pixel_size_m"])
    guard_m = float(prereg["evaluation"]["guard_distance_m"])
    if guard_m % pixel_m != 0:
        raise ValueError("holdout guard must be an integer number of pixels")
    region_masks = spatial_quadrant_region_masks(labels.shape)
    evaluation_masks = spatial_quadrant_masks(labels.shape, guard_px=int(guard_m / pixel_m))
    folds: dict[str, Any] = {}
    for name, block in evaluation_masks.items():
        path = score_paths[name]
        if not path.is_file():
            raise FileNotFoundError(f"missing fold-specific score surface: {path}")
        score = np.load(path, mmap_mode="r")
        if score.shape != footprint.shape or labels.shape != footprint.shape:
            raise ValueError("score, label, and footprint shapes do not match")
        if not np.all(np.isfinite(score[footprint])):
            raise ValueError(f"score surface for fold {name} contains non-finite valid cells")

        # The complete spatial quadrant is held out. Only catalogued pixels
        # outside it are known and excluded from this fold's metric.
        visible_known = labels & footprint & ~region_masks[name]
        candidate_domain = footprint & ~visible_known
        prediction = top_budget_binary(score, candidate_domain, budget=budget)
        folds[name] = score_one_fold(
            prediction, labels, footprint, block, visible_known, prereg
        )
    return folds


def _fold_values(record: dict[str, Any]) -> list[float]:
    return [float(record[name]["dti"]) for name in ("NW", "NE", "SW", "SE")]


def summarize_folds(record: dict[str, Any], metric_spec: dict[str, Any]) -> dict[str, Any]:
    values = _fold_values(record)
    tp = float(sum(record[name]["tp"] for name in ("NW", "NE", "SW", "SE")))
    fp = float(sum(record[name]["fp"] for name in ("NW", "NE", "SW", "SE")))
    fn = float(sum(record[name]["fn"] for name in ("NW", "NE", "SW", "SE")))
    denominator = (
        tp
        + float(metric_spec["alpha"]) * fp
        + float(metric_spec["beta"]) * fn
        + float(metric_spec["denominator_epsilon"])
    )
    return {
        "pooled_dti": float(tp / denominator) if denominator > 0.0 else 0.0,
        "mean_fold_dti_descriptive_only": float(np.mean(values)),
        "std_fold_dti_population_descriptive_only": float(np.std(values)),
        "pooled_components": {"tp": tp, "fp": fp, "fn": fn},
        "per_fold_dti": {name: float(record[name]["dti"]) for name in ("NW", "NE", "SW", "SE")},
        "truth_pixels_by_fold": {name: int(record[name]["truth_pixels"]) for name in ("NW", "NE", "SW", "SE")},
    }


def validation_protocol_sha256(prereg: dict[str, Any], budget: int) -> str:
    evaluation = prereg["evaluation"]
    implementation_files = {
        "validator": Path(__file__).resolve(),
        "metric": ROOT / "gemsdoe37" / "metric.py",
        "holdout": ROOT / "gemsdoe37" / "holdout.py",
    }
    protocol = {
        "protocol_schema": 1,
        "truth": evaluation["truth"],
        "spatial_blocks": evaluation["spatial_blocks"],
        "guard_distance_m": evaluation["guard_distance_m"],
        "known_fault_mask_rule": evaluation["known_fault_mask_rule"],
        "metric": evaluation["metric"],
        "matched_positive_pixel_budget": int(budget),
        "top_budget_rule": evaluation["top_budget_rule"],
        "normalization_fit_scope": evaluation["normalization_fit_scope"],
        "promotion_gate": evaluation["promotion_gate"],
        "implementation_sha256": {
            name: sha256_file(path) for name, path in implementation_files.items()
        },
    }
    canonical = json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_registered_current_best(
    prereg: dict[str, Any],
    *,
    budget: int,
    input_hashes: dict[str, str],
    protocol_sha256: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Load a hash-pinned previous local holdout report, if preregistered."""
    record = prereg["evaluation"].get("current_holdout_best")
    if record is None:
        return None, "No local current holdout-best report is registered."
    if not isinstance(record, dict):
        raise ValueError("current_holdout_best must be null or a report registration object")
    report_name = record.get("report_path")
    expected_hash = record.get("report_sha256")
    if not report_name or not expected_hash:
        raise ValueError("registered current holdout best needs report_path and report_sha256")
    report_path = (ROOT / str(report_name)).resolve()
    if ROOT.resolve() not in report_path.parents:
        raise ValueError("registered current holdout-best report must be inside the repository")
    if not report_path.is_file() or sha256_file(report_path) != expected_hash:
        raise ValueError("registered current holdout-best report is missing or changed")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("candidate_id") != record.get("candidate_id"):
        raise ValueError("registered current holdout-best candidate ID does not match its report")
    if report.get("input_hashes_sha256") != input_hashes:
        raise ValueError("current holdout-best report uses different raw input hashes")
    if report.get("validation_protocol_sha256") != protocol_sha256:
        raise ValueError("current holdout-best report uses a different scoring/split protocol")
    if int(report.get("budget_positive_pixels", -1)) != int(budget):
        raise ValueError("current holdout-best report uses a different positive-pixel budget")
    summaries = report.get("summaries")
    summary = summaries.get("topological_candidate") if isinstance(summaries, dict) else None
    fold_scores = summary.get("per_fold_dti") if isinstance(summary, dict) else None
    fold_names = ("NW", "NE", "SW", "SE")
    if not isinstance(summary, dict) or not isinstance(fold_scores, dict):
        raise ValueError("current holdout-best report has no compatible pooled/per-fold scores")
    if "pooled_dti" not in summary or any(name not in fold_scores for name in fold_names):
        raise ValueError("current holdout-best report has incomplete pooled/per-fold scores")
    try:
        score_values = [float(summary["pooled_dti"])] + [float(fold_scores[name]) for name in fold_names]
    except (TypeError, ValueError) as exc:
        raise ValueError("current holdout-best report scores are malformed") from exc
    if not all(np.isfinite(value) and 0.0 <= value <= 1.0 for value in score_values):
        raise ValueError("current holdout-best report contains out-of-range scores")
    return summary, None


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

    budget = int(prereg["evaluation"]["matched_positive_pixel_budget"])
    if budget <= 0:
        raise ValueError("preregistered matched positive-pixel budget must be positive")
    metric_spec = prereg["evaluation"]["metric"]
    folds = {
        "topological_candidate": score_fold_surfaces(
            fold_topology_paths, labels, footprint, budget=budget, prereg=prereg
        ),
        "single_scale_control": score_fold_surfaces(
            fold_control_paths, labels, footprint, budget=budget, prereg=prereg
        ),
    }
    summaries = {
        name: summarize_folds(value, metric_spec) for name, value in folds.items()
    }
    top = _fold_values(folds["topological_candidate"])
    single = _fold_values(folds["single_scale_control"])
    gain_single = [a - b for a, b in zip(top, single)]
    gate = prereg["evaluation"]["promotion_gate"]
    single_pooled_gain = (
        summaries["topological_candidate"]["pooled_dti"]
        - summaries["single_scale_control"]["pooled_dti"]
    )
    pass_single_scale = (
        single_pooled_gain >= float(gate["minimum_pooled_dti_gain_over_single_scale_control"])
        and sum(delta > 0.0 for delta in gain_single) >= int(gate["minimum_positive_folds"])
        and min(gain_single) >= -float(gate["maximum_allowed_single_fold_regression"])
    )

    protocol_sha = validation_protocol_sha256(prereg, budget)
    current_best_summary, current_best_error = load_registered_current_best(
        prereg,
        budget=budget,
        input_hashes=build_receipt["input_hashes_sha256"],
        protocol_sha256=protocol_sha,
    )
    gain_current_best: list[float] | None = None
    current_best_pooled_gain: float | None = None
    pass_current_best = False
    if current_best_summary is not None:
        best_fold_scores = current_best_summary["per_fold_dti"]
        current_best_values = [
            float(best_fold_scores[name]) for name in ("NW", "NE", "SW", "SE")
        ]
        if not all(np.isfinite(value) and 0.0 <= value <= 1.0 for value in current_best_values):
            raise ValueError("registered current holdout-best fold scores are malformed")
        gain_current_best = [a - b for a, b in zip(top, current_best_values)]
        current_best_pooled_gain = (
            summaries["topological_candidate"]["pooled_dti"]
            - float(current_best_summary["pooled_dti"])
        )
        pass_current_best = (
            current_best_pooled_gain
            >= float(gate["minimum_pooled_dti_gain_over_current_holdout_best"])
            and sum(delta > 0.0 for delta in gain_current_best)
            >= int(gate["minimum_positive_folds"])
            and min(gain_current_best)
            >= -float(gate["maximum_allowed_single_fold_regression"])
        )
    slot_eligible = bool(pass_single_scale and pass_current_best)
    report: dict[str, Any] = {
        "schema_version": 2,
        "validated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_id": prereg["candidate_id"],
        "truth_class": "public-catalogue spatial pseudo-holdout; not expert-only hidden truth",
        "known_fault_mask_rule": prereg["evaluation"]["known_fault_mask_rule"],
        "current_holdout_best_status": current_best_error or "hash-pinned local baseline loaded",
        "input_hashes_sha256": build_receipt["input_hashes_sha256"],
        "build_receipt_sha256": sha256_file(build_receipt_path),
        "preregistration_sha256": build_receipt["preregistration_sha256"],
        "validation_protocol_sha256": protocol_sha,
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
        "budget_positive_pixels": budget,
        "grid": template_grid,
        "folds": folds,
        "summaries": summaries,
        "paired_gains": {
            "topological_minus_single_scale_per_fold": dict(zip(("NW", "NE", "SW", "SE"), gain_single)),
            "topological_minus_single_scale_pooled": single_pooled_gain,
            "topological_minus_current_holdout_best_per_fold": (
                dict(zip(("NW", "NE", "SW", "SE"), gain_current_best))
                if gain_current_best is not None else None
            ),
            "topological_minus_current_holdout_best_pooled": current_best_pooled_gain,
        },
        "gate": {
            "rule": gate,
            "beats_single_scale_control": bool(pass_single_scale),
            "beats_registered_current_holdout_best": bool(pass_current_best),
            "slot_eligible": slot_eligible,
            "slot_blockers": [
                reason
                for passed, reason in (
                    (pass_single_scale, "topological candidate did not pass the preregistered single-scale comparison"),
                    (pass_current_best, current_best_error or "topological candidate did not beat the registered current holdout best"),
                )
                if not passed
            ],
            "organizer_score_claimed": False,
        },
        "submission_written": False,
        "notes": [
            "Scores are pooled across the four spatial blocks by summing TP, FP, and FN before calculating one DTI; the mean fold DTI is descriptive only.",
            "The fold scorer applies the official exact known-fault pixel mask with no proximity buffer. The 300 m guard is a spatial-validation design choice, not an organizer scoring mask.",
            "The 37,654-pixel budget is fixed from an owner-reported H33 artifact count; it is not an organizer score and its submission attribution is unverified.",
            "The static H33 B=2 raster is not used as a fold comparator because its catalogue-buffer pruning used labels from the full area, including held-out folds.",
            "The public-catalogue pseudo-holdout cannot prove discovery of hidden expert faults, especially corrections or splays within 300 m of known traces, or predict the private leaderboard.",
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
        blockers = "; ".join(report["gate"]["slot_blockers"])
        raise RuntimeError(f"HOLDOUT GATE FAIL: no submission TIFF written; {blockers}")

    # The output is generated from this run's full-grid score map, never from a prior raster.
    full_score_meta = build_receipt.get("full_grid", {}).get("candidate_score", {})
    if not topology_path.is_file() or sha256_file(topology_path) != full_score_meta.get("sha256"):
        raise RuntimeError("full-grid candidate score is missing or differs from the audited build receipt")
    topology_score = np.load(topology_path, mmap_mode="r")
    if topology_score.shape != footprint.shape or not np.all(np.isfinite(topology_score[footprint])):
        raise ValueError("full-grid candidate score is malformed or contains non-finite valid cells")
    known_fault_mask = labels & footprint
    topology_prediction = top_budget_binary(
        topology_score, footprint & ~known_fault_mask, budget=budget
    )
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
        f"{budget} px; 4-block catalogue pooled DTI {summaries['topological_candidate']['pooled_dti']:.4f}; "
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
        "origin": "GEMSDOE37 H1 score surface; fixed owner-reported pixel count used only as the matched budget",
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
        "public_catalogue_holdout_pooled_dti": summaries["topological_candidate"]["pooled_dti"],
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
