#!/usr/bin/env python3
"""Build, validate, and publish the H2 rank-mix candidate.

H2 uses the competition's internal geodetic strain fields as the primary signal,
then adds (not replaces) a structural prior from the DEM/magnetic/gravity
single-scale control and a smaller topological-persistence prior from the H1
multiscale candidate. The baseline for promotion is the strain-only ranking on
identical folds, mask rules, and matched budget.

The script assumes `scripts/prepare_data.py` and `scripts/build_candidate.py`
have already been run successfully. It writes only a unique GeoTIFF derived from
this repository's own full-grid score surface; no prior submission pixels are
reused.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.features import robust_standardize  # noqa: E402
from gemsdoe37.holdout import spatial_quadrant_region_masks, top_budget_binary  # noqa: E402
from gemsdoe37.submission import sha256_file, write_submission_geotiff  # noqa: E402
from scripts.validate_candidate import score_fold_surfaces, summarize_folds  # noqa: E402

RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
SPEC = ROOT / "research" / "preregistration_rankmix.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def _valid_read(src: rasterio.io.DatasetReader, band_index: int, footprint: np.ndarray) -> np.ndarray:
    raw = src.read(band_index).astype(np.float32, copy=False)
    valid = footprint & (src.read_masks(band_index) > 0) & np.isfinite(raw) & (raw > -1e38)
    if not np.any(valid):
        raise RuntimeError(f"band {band_index} has no valid footprint pixels")
    return np.where(valid, raw, np.nan).astype(np.float32, copy=False)


def strain_abs_surface(
    strain_inv: np.ndarray,
    shear: np.ndarray,
    dilat: np.ndarray,
    footprint: np.ndarray,
    fit_mask: np.ndarray,
) -> np.ndarray:
    inv = robust_standardize(np.abs(strain_inv), footprint, fit_mask=fit_mask)[0]
    shr = robust_standardize(np.abs(shear), footprint, fit_mask=fit_mask)[0]
    dil = robust_standardize(np.abs(dilat), footprint, fit_mask=fit_mask)[0]
    output = (inv + shr + dil) / 3.0
    output[~footprint] = 0.0
    return output.astype(np.float32, copy=False)


def build_rankmix_surfaces() -> dict[str, Path]:
    spec = load_json(SPEC)
    manifest = load_json(PREPARED / "manifest.json")
    ensure_file(RAW / "training_features.tif")
    ensure_file(RAW / "labels.tif")
    ensure_file(RAW / "sample_submission.tif")
    for path in (
        PREPARED / "footprint.npy",
        PREPARED / "labels.npy",
        PREPARED / "topology_score.npy",
        PREPARED / "single_scale_score.npy",
        PREPARED / "topology_score_fit_excluding_NW.npy",
        PREPARED / "topology_score_fit_excluding_NE.npy",
        PREPARED / "topology_score_fit_excluding_SW.npy",
        PREPARED / "topology_score_fit_excluding_SE.npy",
        PREPARED / "single_scale_score_fit_excluding_NW.npy",
        PREPARED / "single_scale_score_fit_excluding_NE.npy",
        PREPARED / "single_scale_score_fit_excluding_SW.npy",
        PREPARED / "single_scale_score_fit_excluding_SE.npy",
    ):
        ensure_file(path)
    if not manifest.get("model_inputs_ready"):
        raise RuntimeError("data preparation manifest says model inputs are not ready")

    footprint = np.load(PREPARED / "footprint.npy").astype(bool, copy=False)
    out_dir = PREPARED / "rankmix_h2"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Verified by metadata audit in prepare_data.py; indices are 1-based.
    with rasterio.open(RAW / "training_features.tif") as src:
        strain_inv = _valid_read(src, int(spec["layers"]["second_invariant_band_index_1based"]), footprint)
        shear = _valid_read(src, int(spec["layers"]["shear_rate_band_index_1based"]), footprint)
        dilat = _valid_read(src, int(spec["layers"]["dilatation_rate_band_index_1based"]), footprint)

    region_masks = spatial_quadrant_region_masks(footprint.shape)
    fit_masks = {"full": footprint}
    fit_masks.update({name: footprint & ~region for name, region in region_masks.items()})

    saved: dict[str, Path] = {}
    for split_name, fit_mask in fit_masks.items():
        baseline = strain_abs_surface(strain_inv, shear, dilat, footprint, fit_mask)
        if split_name == "full":
            structural = np.load(PREPARED / "single_scale_score.npy", mmap_mode="r")
            topology = np.load(PREPARED / "topology_score.npy", mmap_mode="r")
        else:
            structural = np.load(PREPARED / f"single_scale_score_fit_excluding_{split_name}.npy", mmap_mode="r")
            topology = np.load(PREPARED / f"topology_score_fit_excluding_{split_name}.npy", mmap_mode="r")
        candidate = (
            float(spec["weights"]["strain_abs_primary"]) * baseline
            + float(spec["weights"]["structural_single_scale"]) * structural
            + float(spec["weights"]["topological_persistence"]) * topology
        ).astype(np.float32, copy=False)
        candidate[~footprint] = 0.0
        if split_name == "full":
            baseline_path = out_dir / "baseline_score.npy"
            candidate_path = out_dir / "candidate_score.npy"
        else:
            baseline_path = out_dir / f"baseline_score_fit_excluding_{split_name}.npy"
            candidate_path = out_dir / f"candidate_score_fit_excluding_{split_name}.npy"
        np.save(baseline_path, baseline)
        np.save(candidate_path, candidate)
        saved[f"baseline_{split_name}"] = baseline_path
        saved[f"candidate_{split_name}"] = candidate_path

    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_id": spec["candidate_id"],
        "spec_sha256": sha256_file(SPEC),
        "manifest_sha256": sha256_file(PREPARED / "manifest.json"),
        "input_hashes_sha256": manifest["source_hashes_sha256"],
        "weights": spec["weights"],
        "layers": spec["layers"],
        "outputs": {
            key: {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "nonzero_pixels": int(np.count_nonzero(np.load(path, mmap_mode="r") > 0)),
            }
            for key, path in saved.items()
        },
        "note": (
            "The baseline is the strain-only magnitude ranking. The published candidate "
            "adds the existing DEM/magnetic/gravity single-scale structural prior and the "
            "existing H1 topological-persistence prior with fixed positive weights."
        ),
    }
    (out_dir / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return saved


def validate_and_publish() -> dict:
    spec = load_json(SPEC)
    manifest = load_json(PREPARED / "manifest.json")
    footprint = np.load(PREPARED / "footprint.npy").astype(bool, copy=False)
    labels = np.load(PREPARED / "labels.npy").astype(bool, copy=False)
    saved = build_rankmix_surfaces()
    folds = ("NW", "NE", "SW", "SE")
    metric_spec = spec["evaluation"]["metric"]
    budget = int(spec["evaluation"]["matched_positive_pixel_budget"])

    baseline_paths = {fold: saved[f"baseline_{fold}"] for fold in folds}
    candidate_paths = {fold: saved[f"candidate_{fold}"] for fold in folds}
    baseline_folds = score_fold_surfaces(baseline_paths, labels, footprint, budget=budget, prereg=spec)
    candidate_folds = score_fold_surfaces(candidate_paths, labels, footprint, budget=budget, prereg=spec)
    baseline_summary = summarize_folds(baseline_folds, metric_spec)
    candidate_summary = summarize_folds(candidate_folds, metric_spec)

    gain_per_fold = {
        fold: float(candidate_summary["per_fold_dti"][fold] - baseline_summary["per_fold_dti"][fold])
        for fold in folds
    }
    pooled_gain = float(candidate_summary["pooled_dti"] - baseline_summary["pooled_dti"])
    gate = spec["evaluation"]["promotion_gate"]
    pass_gate = (
        pooled_gain >= float(gate["minimum_pooled_dti_gain_over_current_holdout_best"])
        and sum(delta > 0.0 for delta in gain_per_fold.values()) >= int(gate["minimum_positive_folds"])
        and min(gain_per_fold.values()) >= -float(gate["maximum_allowed_single_fold_regression"])
    )

    base_report = {
        "schema_version": 1,
        "validated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_id": spec["baseline_id"],
        "truth_class": spec["evaluation"]["truth"],
        "input_hashes_sha256": manifest["source_hashes_sha256"],
        "spec_sha256": sha256_file(SPEC),
        "budget_positive_pixels": budget,
        "folds": baseline_folds,
        "summary": baseline_summary,
        "description": spec["baseline_description"],
    }
    base_report_path = PREPARED / "rankmix_h2" / "baseline-report.json"
    base_report_path.write_text(json.dumps(base_report, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "validated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate_id": spec["candidate_id"],
        "truth_class": spec["evaluation"]["truth"],
        "input_hashes_sha256": manifest["source_hashes_sha256"],
        "spec_sha256": sha256_file(SPEC),
        "budget_positive_pixels": budget,
        "baseline_report": {
            "path": str(base_report_path.relative_to(ROOT)),
            "sha256": sha256_file(base_report_path),
            "candidate_id": spec["baseline_id"],
        },
        "baseline_description": spec["baseline_description"],
        "folds": candidate_folds,
        "summary": candidate_summary,
        "paired_gains_vs_baseline": {
            "per_fold": gain_per_fold,
            "pooled": pooled_gain,
        },
        "gate": {
            "rule": gate,
            "pass": bool(pass_gate),
            "slot_blockers": [] if pass_gate else [
                "candidate did not beat the registered current holdout best by the required pooled/fold margins"
            ],
        },
        "notes": [
            "Only exact provided known-fault pixels are excluded; there is no competition scoring buffer around them.",
            "This is a catalogue pseudo-holdout, not the organizer's hidden new-fault label set.",
            "The candidate is primary-strain, secondary-structural, tertiary-topological; it is not a calibrated probability.",
        ],
    }
    report_path = PREPARED / "rankmix_h2" / "holdout-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if not pass_gate:
        raise RuntimeError(
            "HOLDOUT GATE FAIL: no submission TIFF written; "
            + "; ".join(report["gate"]["slot_blockers"])
        )

    full_score_path = saved["candidate_full"]
    full_score = np.load(full_score_path, mmap_mode="r")
    if full_score.shape != footprint.shape:
        raise RuntimeError("full-grid candidate score shape does not match footprint")
    known_fault_mask = labels & footprint
    prediction = top_budget_binary(full_score, footprint & ~known_fault_mask, budget=budget)

    now = datetime.now(timezone.utc)
    utc_stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    nonce = uuid4().hex[:8].upper()
    unique_digest = hashlib.sha256(
        prediction.tobytes()
        + sha256_file(SPEC).encode("ascii")
        + sha256_file(full_score_path).encode("ascii")
        + nonce.encode("ascii")
    ).hexdigest()[:10].lower()
    filename = f"gemsdoe37-rankmix-strain-topo-{utc_stamp}-{unique_digest}.tif"
    submission_id = f"GEMSDOE37-H2-RANKMIX-{utc_stamp}-{unique_digest.upper()}"
    note = (
        f"{submission_id} | strain abs×2 + structural + PH prior; {budget} px; "
        f"exact-mask pooled pseudo-holdout {candidate_summary['pooled_dti']:.4f}; unscored"
    )
    if len(note) > 200:
        raise RuntimeError(f"submission note is too long ({len(note)})")

    output_path = ROOT / "docs" / "downloads" / filename
    check = write_submission_geotiff(
        output_path,
        prediction.astype(np.float32),
        RAW / "sample_submission.tif",
        expected_budget=budget,
    )

    report["submission"] = {
        "filename": filename,
        "relative_path": str(output_path.relative_to(ROOT)),
        "submission_name": submission_id,
        "submission_note": note,
        "format_receipt": check,
        "sha256": check["sha256"],
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    public_dir = ROOT / "docs" / "reports" / submission_id
    public_dir.mkdir(parents=True, exist_ok=False)
    public_report_path = public_dir / "holdout-report.json"
    public_report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    note_path = output_path.with_suffix(".note.txt")
    note_path.write_text(
        f"Submission name: {submission_id}\nNote: {note}\nFilename: {filename}\nSHA-256: {check['sha256']}\n",
        encoding="utf-8",
    )

    public_record = {
        "schema_version": 1,
        "status": "HOLDOUT_GATE_PASSED_UNSCORED",
        "candidate_id": spec["candidate_id"],
        "generated_utc": report["validated_utc"],
        "download_path": f"downloads/{filename}",
        "holdout_report_path": f"reports/{submission_id}/holdout-report.json",
        "filename": filename,
        "submission_name": submission_id,
        "submission_note": note,
        "sha256": check["sha256"],
        "positive_pixels": budget,
        "public_catalogue_holdout_pooled_dti": candidate_summary["pooled_dti"],
        "organizer_score": None,
        "format_receipt": check,
        "warning": (
            "This TIFF is unique to GEMSDOE37 and passed the repository's exact-mask "
            "pseudo-holdout gate against the registered strain-only incumbent. It is not "
            "an organizer score or a guarantee of private-label performance."
        ),
    }
    public_path = ROOT / "docs" / "data" / "current_submission.json"
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public_record, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "candidate_id": spec["candidate_id"],
        "baseline_pooled_dti": baseline_summary["pooled_dti"],
        "candidate_pooled_dti": candidate_summary["pooled_dti"],
        "paired_gain_pooled": pooled_gain,
        "paired_gain_per_fold": gain_per_fold,
        "report": str(report_path.relative_to(ROOT)),
        "submission": report["submission"],
    }, indent=2))
    return report


def main() -> int:
    try:
        validate_and_publish()
    except Exception as exc:
        print(f"PUBLISH BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
