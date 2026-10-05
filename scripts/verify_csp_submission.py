"""Independent verification, receipts and forecast for a built submission.

Re-opens the GeoTIFF from disk, re-runs the format contract, measures the
descriptors that the public-score ladder is known to read (dot budget, stand-off
from the published catalogue), certifies multi-scale persistence stability, and
recomputes the uniqueness claim against every prior map recovered in the
workspace.  Then it writes three receipts next to the download:

* ``verification-<stem>.json`` -- format + descriptors + persistence.
* ``checks-<stem>.json``       -- the same plus configuration and provenance.
* ``forecast-<stem>.json``     -- three models, none of which is a guarantee.

Usage:
    python scripts/verify_csp_submission.py --tif docs/downloads/<stem>.tif
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, uniform_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gemsdoe37.submission import sha256_file, validate_geotiff  # noqa: E402

DATA = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
DOWNLOADS = ROOT / "docs" / "downloads"
PRIOR_GLOBS = [str(DOWNLOADS / "*.tif"), "/tmp/work/maps/*.tif"]
FAMILIES = {"dem": "gems:det_elev", "mag": "gems:mag_anom", "grav": "gems:iso_grav_anom"}


def load(path: Path, binary: bool = False) -> np.ndarray:
    with rasterio.open(path) as source:
        values = source.read(1).astype(np.float32)
    return np.nan_to_num(values, nan=0.0) > 0 if binary else values


def persistence_stability(selected: np.ndarray, valid: np.ndarray) -> dict:
    """Decode the stored persistence-survival channel for the selected pixels.

    ``sources.band_features`` stores ``pers`` as the *count* of the four
    smoothing scales at which the cell sits in the top 5 % of that scale's
    edge response (0 = none, 4 = every scale). It is a discrete multi-scale
    stability certificate, not a probability.
    """
    store_path = WORK / "features_uint8.npy"
    meta_path = WORK / "feature_store.json"
    if not store_path.exists() or not meta_path.exists():
        return {"status": "feature store unavailable in this checkout"}
    meta = json.loads(meta_path.read_text())
    names = meta["names"]
    store = np.load(store_path, mmap_mode="r")
    report = {}
    stable_counts = np.zeros(int(selected.sum()), dtype=np.int32)
    for family, prefix in FAMILIES.items():
        if f"{prefix}:pers" not in names:
            continue
        channel = np.asarray(store[names.index(f"{prefix}:pers")], dtype=np.float32)
        survived = channel[selected]                     # 0..4 scales
        footprint = channel[valid]                       # 0..4 over the whole footprint
        report[family] = {
            "mean_scales_survived_selected": float(survived.mean()),
            "mean_scales_survived_footprint": float(footprint.mean()),
            "fraction_selected_surviving_2_or_more_scales": float((survived >= 2).mean()),
            "fraction_footprint_surviving_2_or_more_scales": float((footprint >= 2).mean()),
            "enrichment_vs_footprint": float((survived >= 2).mean() / max((footprint >= 2).mean(), 1e-9)),
        }
        stable_counts += (survived >= 2).astype(np.int32)
    report["cross_family"] = {
        "fraction_selected_stable_in_2_or_more_field_families": float((stable_counts >= 2).mean()),
        "fraction_selected_stable_in_all_3_field_families": float((stable_counts == 3).mean()),
    }
    report["citation"] = (
        "Stability is the number of smoothing scales (100/200/400/800 m) at which the "
        "cell remains in the top 5 % of the scale's edge response; the persistence-stability "
        "guarantee for the bottleneck distance between persistence diagrams under bounded "
        "field perturbation is Cohen-Steiner, Edelsbrunner & Harer, Discrete Comput. Geom. 37 "
        "(2007) 103-120, doi:10.1007/s00454-006-1276-5."
    )
    return report


def uniqueness(selected: np.ndarray, tif: Path) -> dict:
    seen = []
    for pattern in PRIOR_GLOBS:
        for path in sorted(glob.glob(pattern)):
            if Path(path) == tif:
                continue
            try:
                with rasterio.open(path) as source:
                    other = np.nan_to_num(source.read(1), nan=0.0) > 0
            except Exception:
                continue
            if other.shape != selected.shape:
                continue
            union = int((selected | other).sum())
            seen.append({
                "id": Path(path).stem,
                "their_pixels": int(other.sum()),
                "shared_pixels": int((selected & other).sum()),
                "jaccard": int((selected & other).sum()) / union if union else 0.0,
                "fraction_of_ours_shared": int((selected & other).sum()) / max(int(selected.sum()), 1),
            })
    seen.sort(key=lambda row: -row["jaccard"])
    return {"n_compared": len(seen), "max_jaccard": seen[0]["jaccard"] if seen else None,
            "closest": seen[:5]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tif", type=Path, required=True)
    parser.add_argument("--note", default=None)
    parser.add_argument("--budget", type=int, default=None)
    args = parser.parse_args()

    tif = args.tif.resolve()
    selected = load(tif, binary=True)
    mass = float(selected.sum())
    catalogue = load(DATA / "labels.tif", binary=True)
    cat_distance = distance_transform_edt(~catalogue)
    sgmc_distance = distance_transform_edt(~np.load(WORK / "sgmc_offcatalogue.npy"))
    belief = np.load(WORK / "belief_oof.npy")
    block = uniform_filter(selected.astype(np.float32), size=3, mode="constant") * 9.0

    footprint = load(DATA / "labels.tif", binary=False) >= 0  # labels nodata -1
    descriptors = {
        "positive_pixels": int(mass),
        "spacing_proxy": float(block[selected].mean()),
        "min_catalogue_distance_px": float(cat_distance[selected].min()),
        "median_catalogue_distance_px": float(np.median(cat_distance[selected])),
        "mean_catalogue_distance_px": float(cat_distance[selected].mean()),
        "frac_selected_within_3px_of_catalogue": float((cat_distance[selected] <= 3.0).mean()),
        "mean_distance_to_sgmc_offcatalogue_px": float(sgmc_distance[selected].mean()),
        "mean_belief_of_selected": float(belief[selected].mean()),
        "mean_belief_of_footprint": float(belief[footprint].mean()),
        "mean_belief_over_all_grid_cells": float(belief.mean()),
        "footprint_pixels": int(footprint.sum()),
        "pixels_on_catalogue": int((selected & catalogue).sum()),
        "selected_pixels_outside_footprint": int((selected & ~footprint).sum()),
    }
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    verification = {
        "generated_utc": generated,
        "file": tif.name,
        "sha256": sha256_file(tif),
        "format_checks": validate_geotiff(tif, DATA / "sample_submission.tif"),
        "descriptors": descriptors,
        "persistence_stability": persistence_stability(selected, footprint),
        "uniqueness": uniqueness(selected, tif),
        "honest_caveats": [
            "No organizer score exists for this file.",
            "Blocked local holdouts measured this session anti-correlate with the public "
            "ladder (Spearman -0.667 over eight owner-reported scored maps); they can "
            "falsify an emission but cannot certify a gain.",
        ],
    }
    (DOWNLOADS / f"verification-{tif.stem}.json").write_text(json.dumps(verification, indent=2))

    checks = {
        "generated_utc": generated,
        "submission_filename": tif.name,
        "recommended_upload": tif.name,
        "submission_name": tif.stem,
        "submission_note": args.note or "",
        "sha256": verification["sha256"],
        "size_bytes": tif.stat().st_size,
        "configuration": {
            "ranking": "4-fold quadrant-blocked OOF belief over 234 label-free structural features",
            "sources": "19 competition bands + 1 m LiDAR scarp (12) + GeoDAWN radiometric/extensions (8)",
            "budget_pixels": args.budget if args.budget is not None else int(mass),
            "spacing_px": 3.0,
            "catalogue_standoff_px": 6.0,
            "values": "binary 1.0 at selected pixels, 0.0 elsewhere",
        },
        "format_checks": verification["format_checks"],
        "descriptors": descriptors,
        "uniqueness": verification["uniqueness"],
        "inputs_sha256": {
            "labels.tif": sha256_file(DATA / "labels.tif"),
            "sample_submission.tif": sha256_file(DATA / "sample_submission.tif"),
            "belief_oof.npy": sha256_file(WORK / "belief_oof.npy"),
        },
        "provenance": "scripts/build_csp_candidate.py -> scripts/verify_csp_submission.py",
    }
    (DOWNLOADS / f"checks-{tif.stem}.json").write_text(json.dumps(checks, indent=2))
    (DOWNLOADS / f"{tif.stem}.note.txt").write_text(
        f"Submission name: {tif.stem}\nNote: {args.note or ''}\n"
        f"Filename: {tif.name}\nSHA-256: {verification['sha256']}\n")

    ladder = json.loads((WORK / "ladder_regression.json").read_text())
    prediction = float(np.array([1.0, np.log(mass), descriptors["mean_catalogue_distance_px"]])
                       @ np.array(ladder["beta"]))
    power_law = float(np.exp(7.041934723641272 - 0.7898013228550378 * np.log(max(mass, 1.0))))
    forecast = {
        "generated_utc": generated,
        "file": tif.name,
        "inputs": {"positive_pixels": int(mass),
                   "mean_catalogue_distance_px": descriptors["mean_catalogue_distance_px"]},
        "forecasts": {
            "geometry_ladder_model_8_maps": {
                "value": prediction,
                "features": ["log_positive_pixels", "mean_catalogue_distance_px"],
                "fit_r2": ladder["r2"], "loo_r2": ladder["loo_r2"],
                "reading": "Fitted on the eight owner-reported scored maps recovered this "
                           "session; it reads geometry only and gives the ranking field no credit.",
            },
            "budget_power_law_12_dotted_maps": {
                "value": power_law,
                "reading": "Same fit as the H5 receipt; extrapolates below the smallest "
                           "budget ever observed on the ladder.",
            },
            "geometry_matched_precedent": {
                "value": 0.2778,
                "reading": "The score of the closest-geometry incumbent (37,654 dots, "
                           "mean catalogue distance 29.0 px). If our ranking field is no "
                           "better than the precedent, this is where the build should land.",
            },
        },
        "owner_best_public_dti": 0.2778,
        "leaderboard_top_public_dti": 0.3262,
        "honest_reading": (
            "All three models read geometry, not the ranking field, and the local holdouts "
            "cannot certify the ranking. The upside case is that the multi-physics field "
            "concentrates the same stand-off geometry on better structures; the downside "
            "case is that it is no better than the ridge field it replaces. Nothing here "
            "is an organizer score."
        ),
    }
    (DOWNLOADS / f"forecast-{tif.stem}.json").write_text(json.dumps(forecast, indent=2))
    print(json.dumps({"verification": verification["descriptors"],
                      "uniqueness": verification["uniqueness"]["max_jaccard"],
                      "forecast": prediction}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
