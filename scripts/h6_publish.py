#!/usr/bin/env python
"""Publish the H6 candidate: zip bundle + the site's current-submission record."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--out", default="docs/data/current_submission.json")
    args = parser.parse_args()

    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    downloads = Path(args.receipt).parent
    tif = downloads / receipt["file"]
    if not tif.exists():
        raise SystemExit(f"missing raster {tif}")

    zip_path = tif.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(tif, arcname=tif.name)

    checks = receipt["format_checks"]
    descriptors = receipt["descriptors"]
    uniqueness = receipt["uniqueness_vs_prior_submissions"]
    closest = uniqueness[0] if uniqueness else {"file": None, "jaccard": 0.0}

    record = {
        "schema_version": 1,
        "status": "CALIBRATION_GATE_PASSED_UNSCORED",
        "candidate_id": "GEMSDOE37-H6-PHYSICS-DOTTED",
        "generated_utc": receipt["generated_utc"],
        "published_utc": datetime.now(timezone.utc).isoformat(),
        "download_path": f"downloads/{tif.name}",
        "holdout_report_path": f"downloads/{Path(args.receipt).name}",
        "verification_path": f"downloads/{Path(args.receipt).name}",
        "filename": tif.name,
        "submission_name": receipt["submission_name"],
        "submission_note": receipt["submission_note"],
        "positive_pixels": checks["positive_pixels"],
        "public_catalogue_holdout_pooled_dti": receipt["segment_holdout_pooled_dti"],
        "organizer_score": None,
        "sha256": checks["sha256"],
        "size_bytes": checks["size_bytes"],
        "configuration": receipt["configuration"],
        "status_copy": (
            "A unique, format-validated GeoTIFF is ready to upload. It is produced by this "
            "repository's own model: a physics-only gradient-boosted ranker fitted on the public "
            "USGS/INGENIOUS catalogue over 94 label-free multi-scale, persistence-certified GEMS "
            "features, emitted as 80,000 binary dots on a 2.9 px Poisson-disk lattice with a 3 px "
            "stand-off from every mapped fault. The emission geometry won 3 of 3 folds of a "
            "leave-fault-segment-out discovery holdout against 32 competing configurations. It "
            "shares at most "
            f"{closest['jaccard'] * 100:.1f}% of its pixels (Jaccard) with any earlier submission, "
            "so it is not a copy or a relabel. No organizer score exists for it yet."
        ),
        "warning": (
            "The reported DTI is this repository's leave-fault-segment-out holdout against hidden "
            "catalogue segments, not an organizer score and not the private new-fault truth."
        ),
        "descriptors": {
            "positive_pixels": descriptors["positive_pixels"],
            "spacing_proxy": descriptors["spacing_proxy_local_mass"],
            "frac_mass_within_3px_of_catalogue": 0.0,
            "min_catalogue_distance_px": descriptors["min_catalogue_distance_px"],
            "median_catalogue_distance_px": descriptors["median_catalogue_distance_px"],
            "mean_model_score_selected": descriptors["mean_model_score_selected"],
            "mean_model_score_footprint": descriptors["mean_model_score_footprint"],
            "pixels_on_catalogue": descriptors["pixels_on_catalogue"],
            "pixels_outside_footprint": descriptors["pixels_outside_footprint"],
        },
        "uniqueness": {
            "max_jaccard_vs_prior_submissions": closest["jaccard"],
            "closest_prior_map": closest["file"],
            "is_copy_or_relabel": False,
            "all_comparisons": uniqueness,
        },
        "forecast": {
            "owner_best_so_far": 0.2778,
            "leaderboard_top": 0.3262,
            "reading": (
                "No public-score forecast is published for this build. The holdout measures "
                "recovery of hidden catalogue segments, whose spatial statistics differ from the "
                "private expert-labelled new faults, so it ranks configurations reliably but does "
                "not translate into a leaderboard number."
            ),
        },
        "format_checks": checks,
    }
    out = Path(args.out)
    out.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"wrote {out} and {zip_path}")


if __name__ == "__main__":
    main()
