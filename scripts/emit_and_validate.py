"""Validate candidate emissions on blocked holdouts and write the submission GeoTIFF.

The emitter follows ``research/metric_algebra.md``: a dot is worth emitting iff
its probability of landing within the 300 m kernel of a hidden fault clears
``emission_probability_threshold``. Because that rule fixes the *precision* of
the dot set rather than its size, the budget is an output of the method.

Validation is run against two held-out targets that the model never sees:

* ``catalogue_fold`` — the out-of-fold catalogue faults (the analogue of the
  hidden truth: mapped faults withheld from training).
* ``sgmc_offcatalogue`` — USGS State Geologic Map Compilation structures
  (DOI 10.3133/ds1052) that are further than 300 m from any catalogue pixel.
  These are an independent structural population, and the sibling repository
  GEMSDOE32 measured this instrument as the best ranker of live scores
  (Spearman +0.54 over 12 scored artifacts) among the proxies available here.

Usage:
    python scripts/emit_and_validate.py sweep      # parameter screen, writes JSON
    python scripts/emit_and_validate.py submit     # writes the shipped GeoTIFF
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gemsdoe37.belief import emit_thresholded, emission_probability_threshold, quadrant_blocks  # noqa: E402
from gemsdoe37.dti import dti_components  # noqa: E402

DATA = ROOT / "data" / "raw"
WORK = ROOT / "data" / "work"
DOWNLOADS = ROOT / "docs" / "downloads"


def load_labels() -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(DATA / "labels.tif") as src:
        raw = src.read(1)
    return raw == 1, raw >= 0


def grid_profile() -> dict:
    with rasterio.open(DATA / "sample_submission.tif") as src:
        return {"transform": list(src.transform)[:6], "crs": src.crs.to_string(),
                "height": src.height, "width": src.width}


def load_sgmc_offcatalogue(labels: np.ndarray) -> np.ndarray | None:
    """SGMC structures >300 m from the catalogue, rasterised on the data grid.

    The raster is produced by the sibling repository's documented pipeline
    (USGS SGMC NV/CA ``*_structure.shp``, DOI 10.3133/ds1052) and is not part of
    this repository's inputs; when it is absent the validation simply reports
    only the catalogue instrument.
    """
    candidate = WORK / "sgmc_offcatalogue.npy"
    if candidate.exists():
        return np.load(candidate)
    return None


def training_catalogue_exclusion(positives: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Catalogue pixels that are NOT part of the held-out truth of this fold.

    The fold instrument must charge the same kind of stand-off the competition
    does -- away from the *known* catalogue -- without deleting the held-out
    faults it is trying to score.
    """
    return positives & ~truth


def oof_fold_truth(positives: np.ndarray, block: np.ndarray) -> np.ndarray:
    """Truth for one fold: catalogue pixels inside the block, shrunk away from edges."""
    inner = ndi.binary_erosion(block, iterations=40)
    return positives & inner


def evaluate(selected: np.ndarray, truth: np.ndarray, valid: np.ndarray,
             *, exclude: np.ndarray) -> dict:
    """Score a dot set against ``truth`` with ``exclude`` removed from the domain.

    For the fold instrument ``exclude`` is the *training* catalogue (the held-out
    fault pixels stay in the scored domain). For the SGMC instrument ``exclude``
    is the whole catalogue, mirroring the organizer's removal of known faults.
    """
    prediction = selected.astype(np.float32)
    domain = valid & ~exclude
    components = dti_components(prediction, truth & domain, valid_mask=domain)
    components["dots"] = int(selected.sum())
    components["precision_at_kernel"] = float(
        (selected & (ndi.distance_transform_edt(~truth) <= 3.0)).sum() / max(selected.sum(), 1))
    return components


def sweep() -> dict:
    positives, valid = load_labels()
    belief = np.load(WORK / "belief_oof.npy")
    blocks = quadrant_blocks(positives.shape, guard_px=40)
    sgmc = load_sgmc_offcatalogue(positives)
    results = []
    for dti_target in (0.25, 0.30, 0.35, 0.40, 0.50, 0.60):
        threshold = emission_probability_threshold(dti_target)
        for suppression in (2.8, 3.5):
            for stand_off in (3.0,):
                dot_union = np.zeros_like(positives)
                fold_rows = []
                for name, block in blocks.items():
                    truth = oof_fold_truth(positives, block)
                    if truth.sum() == 0:
                        continue
                    exclusion = training_catalogue_exclusion(positives, truth)
                    selected = emit_thresholded(
                        belief, block & valid, threshold=threshold,
                        suppression_px=suppression, exclusion=exclusion,
                        exclusion_px=stand_off)
                    dot_union |= selected
                    row = evaluate(selected, truth, valid, exclude=positives & ~truth)
                    row.update({"fold": name, "instrument": "catalogue_fold"})
                    fold_rows.append(row)
                if sgmc is not None:
                    selected = emit_thresholded(
                        belief, valid, threshold=threshold, suppression_px=suppression,
                        exclusion=positives, exclusion_px=stand_off)
                    row = evaluate(selected, sgmc, valid, exclude=positives)
                    row.update({"fold": "all", "instrument": "sgmc_offcatalogue"})
                    fold_rows.append(row)
                results.append({
                    "dti_target": dti_target, "threshold": float(threshold),
                    "suppression_px": suppression, "stand_off_px": stand_off,
                    "dots": int(dot_union.sum()),
                    "catalogue_fold_dti": float(np.mean([r["dti"] for r in fold_rows
                                                         if r["instrument"] == "catalogue_fold"])),
                    "catalogue_fold_precision": float(np.mean(
                        [r["precision_at_kernel"] for r in fold_rows
                         if r["instrument"] == "catalogue_fold"])),
                    "sgmc_dti": float(np.mean([r["dti"] for r in fold_rows
                                               if r["instrument"] == "sgmc_offcatalogue"]))
                    if sgmc is not None else None,
                    "rows": fold_rows,
                })
                print(f"target={dti_target} thr={threshold:.3f} sup={suppression} off={stand_off} "
                      f"dots={dot_union.sum():6d} "
                      f"foldDTI={results[-1]['catalogue_fold_dti']:.4f} "
                      f"foldP={results[-1]['catalogue_fold_precision']:.3f} "
                      f"sgmcDTI={results[-1]['sgmc_dti']}", flush=True)
    report = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "sweep": results}
    (WORK / "emission_sweep.json").write_text(json.dumps(report, indent=2))
    return report


def _submit(args: argparse.Namespace) -> dict:
    from gemsdoe37.submission import write_submission_geotiff

    positives, valid = load_labels()
    belief = np.load(WORK / "belief_full.npy")
    threshold = emission_probability_threshold(args.dti_target)
    selected = emit_thresholded(
        belief, valid, threshold=threshold, suppression_px=args.suppression,
        exclusion=positives, exclusion_px=args.stand_off)
    print(f"selected {int(selected.sum())} dots at threshold {threshold:.4f}")
    name = args.name
    target = DOWNLOADS / f"{name}.tif"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite {target}")
    checks = write_submission_geotiff(target, selected.astype(np.float32),
                                      DATA / "sample_submission.tif",
                                      expected_budget=int(selected.sum()))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {"file": str(target.relative_to(ROOT)), "sha256": digest,
            "checks": checks, "threshold": float(threshold),
            "dots": int(selected.sum())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sweep", "submit", "screen"])
    parser.add_argument("--dti-target", type=float, default=0.35)
    parser.add_argument("--suppression", type=float, default=2.8)
    parser.add_argument("--stand-off", type=float, default=3.0)
    parser.add_argument("--name", default="gemsdoe37-csp")
    args = parser.parse_args()
    if args.mode in {"sweep", "screen"}:
        report = sweep()
        print(json.dumps({"n_configs": len(report["sweep"])}, indent=2))
    else:
        print(json.dumps(_submit(args), indent=2, default=str))


if __name__ == "__main__":
    main()
