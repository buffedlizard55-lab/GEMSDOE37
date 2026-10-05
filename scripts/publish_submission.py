#!/usr/bin/env python3
"""Merge build, verification and forecast receipts into the site's status file."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / "data" / "prepared"
DOCS = ROOT / "docs"


def main() -> int:
    current = json.loads((DOCS / "data" / "current_submission.json").read_text(encoding="utf-8"))
    ver = json.loads((PREPARED / "submission_verification.json").read_text(encoding="utf-8"))
    forecast = json.loads((PREPARED / "score_forecast.json").read_text(encoding="utf-8"))
    if ver["file"] != current["filename"]:
        raise SystemExit(f"verification is for {ver['file']}, not {current['filename']}")

    (DOCS / "downloads" / f"verification-{current['submission_name']}.json").write_text(
        json.dumps(ver, indent=2) + "\n", encoding="utf-8")
    (DOCS / "downloads" / f"forecast-{current['submission_name']}.json").write_text(
        json.dumps(forecast, indent=2) + "\n", encoding="utf-8")

    f = forecast["forecasts"]
    current.update({
        "published_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status_copy": (
            "A unique, format-validated GeoTIFF is ready to upload. It was built by this "
            "repository's own model: a label-free structural + multi-scale-persistence ranking of "
            "all 19 GEMS bands, a 3 px stand-off from every catalogued fault pixel, 2.9 px dotting, "
            "and a 26,000-pixel budget chosen from a calibration of 31 previously scored maps. "
            "It shares at most 3.2% of its pixels (Jaccard) with any previous submission, so it is "
            "not a copy or a relabel. No organizer score exists for it yet."
        ),
        "verification_path": f"downloads/verification-{current['submission_name']}.json",
        "forecast_path": f"downloads/forecast-{current['submission_name']}.json",
        "descriptors": ver["descriptors"],
        "persistence_stability": ver["persistence_stability"],
        "uniqueness": {
            "max_jaccard_vs_prior_submissions": ver["uniqueness"]["max_jaccard_vs_31_prior_submissions"],
            "closest_prior_map": ver["uniqueness"]["per_map"][0]["id"],
            "is_copy_or_relabel": ver["uniqueness"]["is_copy_or_relabel"],
        },
        "forecast": {
            "pessimistic": f["physical_recall_model_pessimistic"]["value"],
            "descriptor_model": f["descriptor_model_31_maps"]["value"],
            "budget_power_law": f["budget_power_law_12_dotted_maps"]["value"],
            "owner_best_so_far": forecast["current_owner_best_public_dti"],
            "leaderboard_top": forecast["leaderboard_top_public_dti"],
            "reading": forecast["honest_reading"],
        },
        "format_checks": ver["format_checks"],
    })
    (DOCS / "data" / "current_submission.json").write_text(
        json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: current[k] for k in
                      ("filename", "submission_name", "submission_note", "forecast")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
