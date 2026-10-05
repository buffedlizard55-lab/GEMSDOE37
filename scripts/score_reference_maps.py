#!/usr/bin/env python3
"""Score every previously-submitted raster on our catalogue-ablation holdout.

Purpose: calibration, not imitation.  Thirty-one owner-side rasters have public
leaderboard DTIs.  Re-scoring them on the same four-fold holdout we use for
model selection tells us how our internal number maps onto the public number,
and whether a new candidate is predicted to beat the current best
(``h33-2-b2``, public DTI 0.2778).

Caveat recorded in the output: several reference maps were built with the full
catalogue in hand, so their holdout scores are optimistically biased.  A new
map that beats them on this holdout is therefore beating a handicapped field.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.catalogue import make_ablation_folds  # noqa: E402
from gemsdoe37.selection import ALPHA, BETA, PIXEL_SIZE_M, RADIUS_M, kernel_offsets  # noqa: E402
from scripts.run_cv import SEED  # noqa: E402

try:
    from numba import njit
except Exception:  # pragma: no cover
    def njit(*args, **kwargs):
        def wrap(func):
            return func
        return wrap(args[0]) if args and callable(args[0]) else wrap

PREPARED = ROOT / "data" / "prepared"
RAW = ROOT / "data" / "raw"
REFERENCE = ROOT / "data" / "reference"


@njit(cache=True, nogil=True)
def _tp_weighted(prob, truth_rows, truth_cols, off_r, off_c, off_w):  # pragma: no cover
    height, width = prob.shape
    total = 0.0
    for i in range(truth_rows.shape[0]):
        r = truth_rows[i]
        c = truth_cols[i]
        best = 0.0
        for k in range(off_r.shape[0]):
            rr = r + off_r[k]
            cc = c + off_c[k]
            if rr < 0 or rr >= height or cc < 0 or cc >= width:
                continue
            value = prob[rr, cc] * off_w[k]
            if value > best:
                best = value
        total += best
    return total


def score_raster(prob, truth_valid, nearest_kernel, off):
    truth_rows, truth_cols = np.nonzero(truth_valid)
    n_truth = truth_rows.size
    tp = _tp_weighted(prob, truth_rows.astype(np.int64), truth_cols.astype(np.int64), *off)
    fp = float((prob * (1.0 - nearest_kernel)).sum())
    fn = n_truth - tp
    return tp, fp, fn


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--out", type=Path, default=PREPARED / "reference_holdout.json")
    parser.add_argument("--candidate", type=Path, default=None,
                        help="extra raster to score alongside the references")
    args = parser.parse_args()

    footprint = np.load(PREPARED / "footprint.npy")
    with rasterio.open(RAW / "labels.tif") as source:
        faults = source.read(1) == 1
    folds = make_ablation_folds(faults, n_folds=args.folds, seed=SEED)
    off = kernel_offsets(RADIUS_M, PIXEL_SIZE_M)

    ledger = json.loads((ROOT / "research" / "scored_submissions.json").read_text(encoding="utf-8"))
    entries = [e for e in ledger["entries"] if (REFERENCE / f"{e['id']}.tif").is_file()]
    maps: list[tuple[str, float | None, Path]] = [
        (e["id"], e.get("dti", e.get("public_dti")), REFERENCE / f"{e['id']}.tif") for e in entries
    ]
    if args.candidate is not None:
        maps.append((f"CANDIDATE::{args.candidate.name}", None, args.candidate))

    from scipy.ndimage import distance_transform_edt

    fold_context = []
    for fold in range(args.folds):
        hidden = folds.hidden_mask(fold)
        visible = folds.visible_mask(fold)
        truth_valid = hidden & footprint & ~visible
        nearest = distance_transform_edt(~truth_valid, sampling=PIXEL_SIZE_M)
        nearest_kernel = np.clip(1.0 - nearest / RADIUS_M, 0.0, 1.0)
        fold_context.append((visible, truth_valid, nearest_kernel))
        print(f"fold {fold}: truth {int(truth_valid.sum())}", flush=True)

    results = []
    for identifier, public_dti, path in maps:
        with rasterio.open(path) as source:
            prob = source.read(1).astype(np.float32)
        prob = np.nan_to_num(prob, nan=0.0, posinf=0.0, neginf=0.0)
        prob = np.clip(prob, 0.0, 1.0)
        prob[~footprint] = 0.0
        mass = float(prob.sum())
        tp = fp = fn = 0.0
        for visible, truth_valid, nearest_kernel in fold_context:
            masked = prob.copy()
            masked[visible] = 0.0  # the organizer masks known-fault pixels
            a, b, c = score_raster(masked, truth_valid, nearest_kernel, off)
            tp += a
            fp += b
            fn += c
        dti = tp / (tp + ALPHA * fp + BETA * fn + 1e-8)
        results.append({
            "id": identifier,
            "public_dti": public_dti,
            "holdout_dti": dti,
            "mass": mass,
            "tp": tp, "fp": fp, "fn": fn,
        })
        print(f"  {identifier:46s} holdout {dti:.4f}  public {public_dti}", flush=True)

    paired = [r for r in results if r["public_dti"] is not None and r["holdout_dti"] > 0]
    calibration = None
    if len(paired) >= 5:
        x = np.log(np.array([r["holdout_dti"] for r in paired]))
        y = np.log(np.array([r["public_dti"] for r in paired]))
        slope, intercept = np.polyfit(x, y, 1)
        pred = slope * x + intercept
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        rank = float(np.corrcoef(
            np.argsort(np.argsort(x)).astype(float), np.argsort(np.argsort(y)).astype(float)
        )[0, 1])
        calibration = {
            "model": "log(public_dti) = slope * log(holdout_dti) + intercept",
            "slope": float(slope),
            "intercept": float(intercept),
            "r2_log": 1.0 - ss_res / ss_tot if ss_tot > 0 else None,
            "spearman": rank,
            "n": len(paired),
        }
        for r in results:
            if r["holdout_dti"] > 0:
                r["predicted_public_dti"] = float(np.exp(slope * np.log(r["holdout_dti"]) + intercept))

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_folds": args.folds,
        "caveat": (
            "Reference rasters were built with the full public catalogue available, so their "
            "holdout scores are optimistically biased relative to a model trained only on the "
            "visible folds. Treat the calibration as indicative, not exact."
        ),
        "calibration": calibration,
        "results": sorted(results, key=lambda r: -r["holdout_dti"]),
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(calibration, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
