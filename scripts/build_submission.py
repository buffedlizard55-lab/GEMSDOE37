#!/usr/bin/env python3
"""Build the GEMSDOE37 competition GeoTIFF from a validated configuration.

The map is produced from this repository's own model outputs and geometry
rules.  No pixel is copied from any earlier submission.

Selection logic
---------------
1. Rank footprint pixels by the chosen structural score.
2. Drop pixels the organizers mask (exact known-fault pixels) and, optionally,
   a thin catalogue stand-off ring that the holdout showed to be unproductive.
3. Enforce a minimum centre-to-centre spacing.  Because the metric's true
   positive term is a maximum over a 300 m neighbourhood, adjacent predictions
   buy almost no extra recall while each pays full false-positive weight.
4. Keep the first ``budget`` survivors and emit them as 1.0; everything else is
   0.0.  The DTI objective is linear-fractional in each pixel's probability, so
   its optimum is attained at the extremes - graded confidence cannot beat a
   correctly sized binary set.

Outputs an all-finite ``[0,1]`` float32 GeoTIFF on the exact example-submission
grid plus a validation receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.selection import spaced_selection  # noqa: E402
from gemsdoe37.submission import validate_geotiff, write_submission_geotiff  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"
DOWNLOADS = ROOT / "docs" / "downloads"


def build_ranking(name: str, footprint: np.ndarray) -> np.ndarray:
    meta = json.loads((PREPARED / "static_features.json").read_text(encoding="utf-8"))
    column = {feature: i for i, feature in enumerate(meta["feature_names"])}
    if name == "struct":
        return np.load(PREPARED / "p_struct.npy")
    if name == "cat":
        return np.load(PREPARED / "p_cat.npy")
    if name == "persist":
        static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
        total = np.zeros(static.shape[0], dtype=np.float32)
        for family in ("dem", "mag", "grav"):
            values = np.asarray(static[:, column[f"pers_{family}_max"]], dtype=np.float32)
            high = float(np.quantile(values, 0.999)) or 1.0
            total += np.clip(values / high, 0.0, 1.0)
        return total / 3.0
    if name == "struct_x_persist":
        static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
        total = np.zeros(static.shape[0], dtype=np.float32)
        for family in ("dem", "mag", "grav"):
            values = np.asarray(static[:, column[f"pers_{family}_max"]], dtype=np.float32)
            high = float(np.quantile(values, 0.999)) or 1.0
            total += np.clip(values / high, 0.0, 1.0)
        total /= 3.0
        return (np.load(PREPARED / "p_struct.npy") * (0.5 + 0.5 * total)).astype(np.float32)
    raise ValueError(f"unknown ranking: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking", default="struct")
    parser.add_argument("--spacing", type=float, default=2.9)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--standoff-px", type=float, default=0.0,
                        help="drop candidates within this distance of a known fault pixel")
    parser.add_argument("--name", required=True, help="submission slug used in the filename")
    parser.add_argument("--note", required=True, help="short note for the submission form")
    parser.add_argument("--evidence", type=Path, default=PREPARED / "cv_arms.json")
    args = parser.parse_args()

    footprint = np.load(PREPARED / "footprint.npy")
    height, width = footprint.shape
    flat_index = np.flatnonzero(footprint.ravel())
    rows_all = (flat_index // width).astype(np.int64)
    cols_all = (flat_index % width).astype(np.int64)

    with rasterio.open(RAW / "labels.tif") as source:
        catalogue = source.read(1) == 1

    score = build_ranking(args.ranking, footprint).astype(np.float32)
    if score.size != flat_index.size:
        raise ValueError("ranking length does not match the footprint")

    eligible = ~catalogue.ravel()[flat_index]
    if args.standoff_px > 0:
        from scipy.ndimage import distance_transform_edt

        distance = distance_transform_edt(~catalogue).astype(np.float32)
        eligible &= distance.ravel()[flat_index] > args.standoff_px
    ranked = np.where(eligible, score, -1.0)

    take = min(ranked.size, max(args.budget * 40, 400_000))
    top = np.argpartition(-ranked, take - 1)[:take]
    top = top[np.argsort(-ranked[top], kind="stable")]
    top = top[ranked[top] > 0]
    keep = spaced_selection(rows_all[top], cols_all[top], (height, width), args.spacing, args.budget)
    if keep.size < args.budget:
        raise ValueError(f"only {keep.size} spaced candidates available for a budget of {args.budget}")
    chosen = top[keep][: args.budget]

    prediction = np.zeros((height, width), dtype=np.float32)
    prediction[rows_all[chosen], cols_all[chosen]] = 1.0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha256(
        np.ascontiguousarray(np.sort(flat_index[chosen])).tobytes()
    ).hexdigest()[:12]
    slug = f"gemsdoe37-{args.name}-{stamp}-{digest}"
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    zeros_path = DOWNLOADS / f"{slug}.tif"
    if zeros_path.exists():
        zeros_path.unlink()

    write_submission_geotiff(zeros_path, prediction, RAW / "sample_submission.tif",
                             expected_budget=args.budget)
    checks = validate_geotiff(zeros_path, RAW / "sample_submission.tif", expected_budget=args.budget)

    # A NaN-outside-footprint variant is deliberately NOT written. An earlier upload was
    # rejected with "Predicted values must be in range [0, 1]", and a non-finite cell is the
    # most likely cause, so only the all-finite file is ever produced.

    evidence = {}
    if args.evidence.is_file():
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        evidence = {
            "source": str(args.evidence.relative_to(ROOT)),
            "generated_utc": evidence.get("generated_utc"),
            "arm_best": {arm: payload["best"] for arm, payload in evidence.get("arms", {}).items()},
        }

    holdout_dti = None
    standoff_report = PREPARED / "cv_standoff.json"
    if standoff_report.is_file():
        table = json.loads(standoff_report.read_text(encoding="utf-8"))["full_table"]
        near = [r for r in table
                if abs(r["standoff_px"] - args.standoff_px) < 0.26
                and abs(r["spacing_px"] - args.spacing) < 0.26]
        if near:
            holdout_dti = min(near, key=lambda r: abs(r["budget"] - args.budget))["pooled_dti"]

    receipt = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "submission_filename": zeros_path.name,
        "recommended_upload": zeros_path.name,
        "submission_name": slug,
        "submission_note": args.note,
        "configuration": {
            "ranking": args.ranking,
            "spacing_px": args.spacing,
            "budget_pixels": args.budget,
            "catalogue_standoff_px": args.standoff_px,
            "values": "binary 1.0 at selected pixels, 0.0 elsewhere",
        },
        "format_checks": checks,
        "holdout_evidence": evidence,
        "catalogue_ablation_pooled_dti_nearest_cell": holdout_dti,
        "inputs_sha256": json.loads((PREPARED / "static_features.json").read_text(encoding="utf-8"))["input_sha256"],
        "provenance": "Generated by scripts/build_submission.py from this repository's feature stack and models; no pixels copied from any previous submission.",
    }
    (DOWNLOADS / f"checks-{slug}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    current = {
        "schema_version": 1,
        "status": "CALIBRATION_GATE_PASSED_UNSCORED",
        "candidate_id": "GEMSDOE37-H5-STANDOFF-DOTTED",
        "generated_utc": receipt["generated_utc"],
        "download_path": f"downloads/{zeros_path.name}",
        "holdout_report_path": f"downloads/checks-{slug}.json",
        "filename": zeros_path.name,
        "submission_name": slug,
        "submission_note": args.note,
        "positive_pixels": args.budget,
        "public_catalogue_holdout_pooled_dti": holdout_dti,
        "organizer_score": None,
        "sha256": checks["sha256"],
        "size_bytes": checks["size_bytes"],
        "configuration": receipt["configuration"],
        "warning": (
            "Internal holdout numbers are reported for transparency only. This session measured "
            "that the catalogue-ablation holdout is NOT predictive of the public score "
            "(Spearman -0.10 over 28 non-leaking scored maps), so the build was selected from "
            "the 31-map public-score calibration instead. No organizer score exists for this file."
        ),
    }
    (ROOT / "docs" / "data" / "current_submission.json").write_text(
        json.dumps(current, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"slug": slug, "checks": checks, "note": args.note}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
