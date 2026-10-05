"""Build, validate and publish the unique GEMSDOE37 candidate ("CSP").

CSP = **Concealed-Structure Persistence**. What makes it different from every
artifact on the sibling sites:

1. The belief field is a 4-fold **quadrant-blocked out-of-fold ensemble** over 234
   label-free structural features built from all 19 competition bands plus the
   public 1 m LiDAR scarp product (12 bands) and the GeoDAWN radiometric and
   extension products (4 + 4 bands). No prior submission raster is an input.
2. The emission budget and spacing come from the metric arithmetic
   (``research/metric_algebra.md``), not from a hand-tuned budget.
3. The dot set is thinned to a Poisson-disk spacing of 3 px and stands 600 m off
   every catalogued fault pixel, matching the geometry of the best publicly
   scored map while replacing its ranking field.

The blocked screens are published *with* their measured failure to rank the live
board (``research/instrument_validity.md``): the catalogue-fold screen
anti-correlates with the public ladder (Spearman -0.67 over eight scored maps),
so nothing here is offered as a prediction of a public score.

Usage:
    python scripts/build_csp_candidate.py --budget 37000 --stand-off 6.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gemsdoe37.belief import emit_thresholded, emission_probability_threshold, quadrant_blocks  # noqa: E402
from gemsdoe37.dti import dti_components  # noqa: E402
from gemsdoe37.submission import sha256_file, write_submission_geotiff  # noqa: E402

DATA = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
DOWNLOADS = ROOT / "docs" / "downloads"


def load_labels() -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(DATA / "labels.tif") as src:
        raw = src.read(1)
    return raw == 1, raw >= 0


def component_subsample(mask: np.ndarray, target_px: int, rng: np.random.Generator) -> np.ndarray:
    """Draw whole connected components until roughly ``target_px`` is reached."""
    labels, count = ndi.label(mask, structure=np.ones((3, 3), int))
    sizes = ndi.sum(mask, labels, index=np.arange(1, count + 1)).astype(int)
    chosen, total = [], 0
    for component in rng.permutation(count):
        if total + sizes[component] >= target_px:
            continue
        chosen.append(component + 1)
        total += int(sizes[component])
        if total >= 0.95 * target_px:
            break
    return np.isin(labels, chosen)


def prevalence_truths(sgmc_off: np.ndarray, *, target_px: int = 15_000,
                      draws: int = 5, seed: int = 11):
    """Component-preserving subsamples whose mass matches the ladder inversion."""
    rng = np.random.default_rng(seed)
    return [component_subsample(sgmc_off, target_px, rng) for _ in range(draws)]


def score(selected: np.ndarray, truth: np.ndarray, valid: np.ndarray,
          exclude: np.ndarray) -> dict:
    domain = valid & ~exclude
    result = dti_components(selected.astype(np.float32), truth & domain, valid_mask=domain)
    kernel = ndi.distance_transform_edt(~(truth & domain)) <= 3.0
    result["dots"] = int(selected.sum())
    result["sharp_fraction"] = float((selected & kernel).sum() / max(int(selected.sum()), 1))
    return result


def validate(belief: np.ndarray, positives: np.ndarray, valid: np.ndarray, *,
             budget: int, suppression: float, stand_off: float) -> dict:
    """Run both blocked screens on a field that never saw the scored truth."""
    in_footprint = int(valid.sum())
    report: dict = {"fold": [], "prevalence": [], "instruments": {}}
    for name, block in quadrant_blocks(positives.shape, guard_px=40).items():
        inner = ndi.binary_erosion(block, iterations=40)
        truth = positives & inner
        if truth.sum() == 0:
            continue
        fold_budget = max(1, int(round(budget * (block & valid).sum() / in_footprint)))
        selection = emit_thresholded(
            belief, block & valid, threshold=0.0, suppression_px=suppression,
            exclusion=positives & ~truth, exclusion_px=stand_off, max_dots=fold_budget)
        row = score(selection, truth, valid, positives & ~truth)
        row["fold"] = name
        row["budget_in_block"] = fold_budget
        report["fold"].append(row)
    sgmc_path = WORK / "sgmc_offcatalogue.npy"
    if sgmc_path.exists():
        sgmc = np.load(sgmc_path)
        whole = emit_thresholded(belief, valid, threshold=0.0, suppression_px=suppression,
                                 exclusion=positives, exclusion_px=stand_off, max_dots=budget)
        for index, truth in enumerate(prevalence_truths(sgmc)):
            row = score(whole, truth, valid, positives)
            row["draw"] = index
            row["truth_px"] = int(truth.sum())
            report["prevalence"].append(row)
    report["instruments"] = {
        "fold_dti_mean": float(np.mean([r["dti"] for r in report["fold"]])) if report["fold"] else None,
        "fold_sharp_mean": float(np.mean([r["sharp_fraction"] for r in report["fold"]])) if report["fold"] else None,
        "prevalence_dti_mean": float(np.mean([r["dti"] for r in report["prevalence"]])) if report["prevalence"] else None,
        "prevalence_sharp_mean": float(np.mean([r["sharp_fraction"] for r in report["prevalence"]])) if report["prevalence"] else None,
    }
    return report


def jaccard_vs_priors(selected: np.ndarray, directories: list[Path]) -> dict:
    seen = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.tif")):
            try:
                with rasterio.open(path) as src:
                    other = np.nan_to_num(src.read(1), nan=0.0) > 0
            except Exception:
                continue
            if other.shape != selected.shape or not other.any():
                continue
            union = int((selected | other).sum())
            seen.append({"file": path.name,
                         "jaccard": int((selected & other).sum()) / union if union else 0.0})
    seen.sort(key=lambda row: -row["jaccard"])
    return {"closest": seen[:5], "max_jaccard": seen[0]["jaccard"] if seen else None,
            "n_compared": len(seen)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=37_000)
    parser.add_argument("--suppression", type=float, default=3.0)
    parser.add_argument("--stand-off", type=float, default=6.0,
                        help="catalogue stand-off in pixels (100 m each)")
    parser.add_argument("--accuracy-target", type=float, default=0.35,
                        help="DTI used only to print the break-even precision")
    parser.add_argument("--stamp", default=time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    parser.add_argument("--prior-maps", nargs="*", default=["/tmp/work/maps"])
    args = parser.parse_args()

    positives, valid = load_labels()
    belief = np.load(WORK / "belief_oof.npy")

    selection = emit_thresholded(belief, valid, threshold=0.0,
                                 suppression_px=args.suppression,
                                 exclusion=positives, exclusion_px=args.stand_off,
                                 max_dots=args.budget)
    dots = int(selection.sum())
    print(f"budget={args.budget} dots={dots}", flush=True)

    validation = validate(belief, positives, valid, budget=args.budget,
                          suppression=args.suppression, stand_off=args.stand_off)
    print(json.dumps(validation["instruments"], indent=2), flush=True)

    digest_source = hashlib.sha256(np.packbits(selection).tobytes()).hexdigest()[:12]
    stem = f"gemsdoe37-csp-concealed-persistence-{args.stamp}-{digest_source}"
    target = DOWNLOADS / f"{stem}.tif"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite {target}")
    checks = write_submission_geotiff(target, selection.astype(np.float32),
                                      DATA / "sample_submission.tif",
                                      expected_budget=dots)
    digest = sha256_file(target)

    distance = ndi.distance_transform_edt(~positives)
    sgmc_off = np.load(WORK / "sgmc_offcatalogue.npy")
    distance_sgmc = ndi.distance_transform_edt(~sgmc_off)
    descriptors = {
        "dots": dots,
        "budget": args.budget,
        "suppression_px": args.suppression,
        "catalogue_standoff_px": args.stand_off,
        "frac_within_3px_of_catalogue": float((distance[selection] <= 3).mean()),
        "median_distance_to_catalogue_px": float(np.median(distance[selection])),
        "mean_distance_to_sgmc_offcatalogue_px": float(distance_sgmc[selection].mean()),
        "belief_mean": float(belief[selection].mean()),
        "break_even_precision_at_target": emission_probability_threshold(args.accuracy_target),
        "value_range": [0.0, 1.0],
    }
    uniqueness = jaccard_vs_priors(selection, [Path(p) for p in args.prior_maps])
    note = (f"GEMSDOE37 CSP: 4-fold blocked OOF belief over 234 label-free features "
            f"(19 competition bands + LiDAR scarp + GeoDAWN radiometric/extension); "
            f"{dots} dots, {args.suppression:g} px spacing, {args.stand_off*100:.0f} m catalogue "
            f"stand-off; blocked fold DTI {validation['instruments']['fold_dti_mean']:.3f}, "
            f"UNSCORED")
    note = note[:200]
    (DOWNLOADS / f"{stem}.note.txt").write_text(note + "\n")

    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidate": "GEMSDOE37-CSP",
        "submission_name": stem,
        "note": note,
        "note_length": len(note),
        "configuration": {"budget": args.budget, "suppression_px": args.suppression,
                          "catalogue_standoff_px": args.stand_off,
                          "field": "data/work/belief_oof.npy (4-fold quadrant-blocked OOF ensemble)",
                          "emission_rule": "metric-algebra budget + Poisson-disk thinning + catalogue stand-off"},
        "format_checks": checks,
        "sha256": digest,
        "descriptors": descriptors,
        "validation": validation,
        "uniqueness": uniqueness,
        "honest_caveats": [
            "No organizer score exists for this file.",
            "The blocked catalogue-fold screen anti-correlates with the public ladder "
            "(Spearman -0.667 over eight owner-reported scored maps), so it is a screen "
            "and never a forecast; see research/instrument_validity.md.",
            "The hidden truth is an expert-mapped fault set we cannot see; every number "
            "here is a local measurement on open data.",
        ],
    }
    (WORK / f"{stem}-validation.json").write_text(json.dumps(report, indent=2))
    np.save(WORK / "csp_selection.npy", selection)

    with zipfile.ZipFile(DOWNLOADS / f"{stem}.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(target, arcname=target.name)
    print(json.dumps({"file": target.name, "sha256": digest, "dots": dots,
                      "note": note, "max_jaccard": uniqueness["max_jaccard"],
                      "closest": uniqueness["closest"][:3]}, indent=2))


if __name__ == "__main__":
    main()
