#!/usr/bin/env python3
"""Independent verification of the built submission.

Checks three things the build script cannot check about itself:

1. **Uniqueness.**  Jaccard and containment overlap against all 31 previously
   submitted rasters, so "not a copy or relabel" is a measured claim.
2. **Metric-relevant descriptors.**  Dottedness, catalogue proximity and mean
   structural score, placed next to the distribution of the 31 scored maps.
3. **Format.**  Re-opens the file from disk and re-runs the template checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, uniform_filter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.submission import validate_geotiff  # noqa: E402

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"
REFERENCE = ROOT / "data" / "reference"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tif", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=PREPARED / "submission_verification.json")
    args = parser.parse_args()

    footprint = np.load(PREPARED / "footprint.npy")
    with rasterio.open(RAW / "labels.tif") as source:
        catalogue = source.read(1) == 1
    cat_distance = distance_transform_edt(~catalogue).astype(np.float32)
    p_struct = np.zeros(footprint.shape, dtype=np.float32)
    p_struct[footprint] = np.load(PREPARED / "p_struct.npy")

    with rasterio.open(args.tif) as source:
        prob = source.read(1).astype(np.float32)
    ours = prob > 0
    mass = float(prob.sum())
    block = uniform_filter(prob, size=3, mode="constant") * 9.0

    meta = json.loads((PREPARED / "static_features.json").read_text(encoding="utf-8"))
    column = {name: i for i, name in enumerate(meta["feature_names"])}
    static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
    flat_index = np.flatnonzero(footprint.ravel())
    sel_compact = np.flatnonzero(ours.ravel()[flat_index])

    # Persistence as a formal stability measure: for each predicted pixel, the number of
    # Gaussian smoothing scales (of 3) at which its H0 superlevel component survived, and the
    # prominence (birth-death lifetime) of the longest-lived bar, per physical field family.
    persistence = {}
    for family in ("dem", "mag", "grav"):
        scales = np.asarray(static[sel_compact, column[f"pers_{family}_scales"]], dtype=np.float32) * 3.0
        prominence = np.asarray(static[sel_compact, column[f"pers_{family}_max"]], dtype=np.float32)
        all_scales = np.asarray(static[:, column[f"pers_{family}_scales"]], dtype=np.float32) * 3.0
        persistence[family] = {
            "mean_scales_survived_selected": float(scales.mean()),
            "mean_scales_survived_footprint": float(all_scales.mean()),
            "fraction_selected_surviving_2_or_more_scales": float((scales >= 1.999).mean()),
            "fraction_footprint_surviving_2_or_more_scales": float((all_scales >= 1.999).mean()),
            "mean_prominence_selected": float(prominence.mean()),
        }
    multi = np.zeros(sel_compact.size, dtype=np.int32)
    for family in ("dem", "mag", "grav"):
        multi += (np.asarray(static[sel_compact, column[f"pers_{family}_scales"]]) * 3.0 >= 2.0).astype(np.int32)
    persistence["cross_family"] = {
        "fraction_selected_stable_in_2_or_more_field_families": float((multi >= 2).mean()),
        "fraction_selected_stable_in_all_3_field_families": float((multi == 3).mean()),
    }

    descriptors = {
        "positive_pixels": int(ours.sum()),
        "mass": mass,
        "spacing_proxy": float((prob * block).sum() / mass),
        "frac_mass_within_3px_of_catalogue": float(prob[cat_distance <= 3.0].sum() / mass),
        "min_catalogue_distance_px": float(cat_distance[ours].min()),
        "mean_pstruct_of_selected": float((prob * p_struct).sum() / mass),
        "mean_pstruct_of_footprint": float(p_struct[footprint].mean()),
        "pixels_on_catalogue": int((ours & catalogue).sum()),
        "pixels_outside_footprint": int((ours & ~footprint).sum()),
    }

    overlaps = []
    for path in sorted(REFERENCE.glob("*.tif")):
        with rasterio.open(path) as source:
            other = np.nan_to_num(source.read(1).astype(np.float32), nan=0.0) > 0
        inter = int((ours & other).sum())
        union = int((ours | other).sum())
        overlaps.append({
            "id": path.stem,
            "their_pixels": int(other.sum()),
            "shared_pixels": inter,
            "jaccard": inter / union if union else 0.0,
            "fraction_of_ours_shared": inter / max(1, int(ours.sum())),
        })
    overlaps.sort(key=lambda o: -o["jaccard"])

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file": args.tif.name,
        "format_checks": validate_geotiff(args.tif, RAW / "sample_submission.tif"),
        "descriptors": descriptors,
        "persistence_stability": persistence,
        "persistence_note": (
            "Scales survived counts how many of the three Gaussian smoothing scales "
            "(100/200/400 m) the pixel's H0 superlevel component persisted through. It is a "
            "multi-scale stability certificate, not evidence that the structure is a fault: "
            "used alone as a ranking, persistence scored 0.0432 on the catalogue-ablation "
            "holdout, below the 0.0646 matched-budget random floor."
        ),
        "uniqueness": {
            "max_jaccard_vs_31_prior_submissions": overlaps[0]["jaccard"],
            "max_fraction_of_our_pixels_shared": max(o["fraction_of_ours_shared"] for o in overlaps),
            "is_copy_or_relabel": overlaps[0]["jaccard"] > 0.95,
            "per_map": overlaps,
        },
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "descriptors": descriptors,
        "persistence_stability": persistence,
        "max_jaccard": overlaps[0]["jaccard"],
        "closest_prior_map": overlaps[0]["id"],
        "format_ok": all(v for k, v in report["format_checks"].items() if isinstance(v, bool)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
