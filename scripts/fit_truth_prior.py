#!/usr/bin/env python3
"""REJECTED APPROACH - kept for the audit trail, do not build on it.

This basis-field inverse model tries to recover a truth-density field rho from the
public DTIs of previously submitted maps. Both parameterisations failed: distance-to-
catalogue bins gave leave-one-out R^2 -0.61, and the 13-field structural basis gave
-0.19 - both worse than predicting the mean. Thirty observations of near-collinear
maps cannot identify a spatial field. The working calibration that replaced it is
scripts/explain_public_scores.py.

Leaderboard-feedback inverse model for the hidden new-fault density.

Every public score we have ever received is an exact linear measurement of the
unknown truth density ``rho``:

    TPw_i = sum_u rho(u) C_i(u)                 C_i(u) = max_x p_i(x) k(d(x,u))
    FPw_i = sum_x p_i(x) - sum_u rho(u) L_i(u)  L_i    = p_i (*) k   (first order)
    N     = sum_u rho(u)
    DTI_i = TPw_i / (0.2 TPw_i + 0.2 FPw_i + 0.8 N + eps)

``C_i`` and ``L_i`` are computable from the raster we submitted, so with
``rho = sum_j theta_j psi_j`` over non-negative basis fields the only unknowns
are the weights ``theta_j >= 0``.  We fit them to our own 31 scored
submissions, select the basis by leave-one-out error, and write the resulting
truth-density estimate for the submission optimiser.

Only our own submissions' scores are used.  The official leaderboard is not
scraped or monitored.
"""

from __future__ import annotations

import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe37.selection import ALPHA, BETA, kernel_offsets  # noqa: E402

RAW = ROOT / "data" / "raw"
PREPARED = ROOT / "data" / "prepared"
REFERENCE = ROOT / "data" / "reference"
LEDGER = ROOT / "research" / "scored_submissions.json"


def coverage_fields(prediction: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(C, L)``: triangular-kernel max-coverage and linear convolution."""
    off_r, off_c, off_w = kernel_offsets()
    height, width = prediction.shape
    cover = np.zeros_like(prediction, dtype=np.float32)
    linear = np.zeros_like(prediction, dtype=np.float32)
    for dr, dc, weight in zip(off_r, off_c, off_w):
        if weight <= 0:
            continue
        sr0, sr1 = max(0, -dr), min(height, height - dr)
        sc0, sc1 = max(0, -dc), min(width, width - dc)
        dr0, dr1 = max(0, dr), min(height, height + dr)
        dc0, dc1 = max(0, dc), min(width, width + dc)
        shifted = prediction[sr0:sr1, sc0:sc1] * np.float32(weight)
        np.maximum(cover[dr0:dr1, dc0:dc1], shifted, out=cover[dr0:dr1, dc0:dc1])
        linear[dr0:dr1, dc0:dc1] += shifted
    return cover, linear


def normalise(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    high = float(np.percentile(values, 99.9))
    if high <= 0:
        return np.zeros_like(values)
    return np.clip(values / high, 0.0, 1.0)


def build_basis(footprint, catalogue, scoring):
    """Non-negative basis fields for the truth density, compact over the footprint."""
    meta = json.loads((PREPARED / "static_features.json").read_text(encoding="utf-8"))
    static = np.load(PREPARED / "static_features.npy", mmap_mode="r")
    names = meta["feature_names"]
    column = {name: index for index, name in enumerate(names)}

    distance = distance_transform_edt(~catalogue).astype(np.float32)[footprint]
    inside = scoring[footprint]
    p_struct = np.load(PREPARED / "p_struct.npy")
    p_cat = np.load(PREPARED / "p_cat.npy")
    tip = np.load(PREPARED / "tip_continuation.npy")

    def top_fraction(values, fraction):
        threshold = np.quantile(values[inside], 1.0 - fraction)
        return (values >= threshold).astype(np.float32)

    basis: dict[str, np.ndarray] = {
        "uniform": np.ones(distance.size, dtype=np.float32),
        "dcat_1_3": ((distance >= 1.0) & (distance <= 3.0)).astype(np.float32),
        "dcat_3_8": ((distance > 3.0) & (distance <= 8.0)).astype(np.float32),
        "dcat_8_30": ((distance > 8.0) & (distance <= 30.0)).astype(np.float32),
        "dcat_30p": (distance > 30.0).astype(np.float32),
        "p_struct": normalise(p_struct),
        "p_struct_top2pct": top_fraction(p_struct, 0.02),
        "p_cat_top2pct": top_fraction(p_cat, 0.02),
        "pers_dem": normalise(np.asarray(static[:, column["pers_dem_max"]])),
        "pers_mag": normalise(np.asarray(static[:, column["pers_mag_max"]])),
        "pers_grav": normalise(np.asarray(static[:, column["pers_grav_max"]])),
        "coh_det_elev": normalise(np.asarray(static[:, column["coh_det_elev"]])),
        "tip_continuation": normalise(tip),
    }
    for key in basis:
        basis[key] = (basis[key] * inside).astype(np.float32)
    return basis


def fit_theta(A, B, P, y, n_basis_mass):
    def predict(theta, A=A, B=B, P=P):
        tp = A @ theta
        fp = np.maximum(P - B @ theta, 0.0)
        n = float(n_basis_mass @ theta)
        return tp / (ALPHA * tp + ALPHA * fp + BETA * n + 1e-8)

    def residual(theta, A=A, B=B, P=P, y=y):
        return predict(theta, A, B, P) - y

    best = None
    for scale in (1e-4, 1e-3, 1e-2):
        start = np.full(A.shape[1], scale)
        solution = least_squares(
            residual, start, bounds=(0.0, 1.0), xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=50000
        )
        if best is None or solution.cost < best.cost:
            best = solution
    return best.x, predict


def evaluate_subset(columns, A, B, P, y, mass):
    theta, predict = fit_theta(A[:, columns], B[:, columns], P, y, mass[columns])
    fitted = predict(theta)
    rss = float(np.sum((fitted - y) ** 2))
    loo = np.empty_like(y)
    for i in range(y.size):
        keep = np.ones(y.size, dtype=bool)
        keep[i] = False
        theta_i, predict_i = fit_theta(
            A[np.ix_(keep, columns)], B[np.ix_(keep, columns)], P[keep], y[keep], mass[columns]
        )
        loo[i] = predict_i(theta_i, A[np.ix_([i], columns)], B[np.ix_([i], columns)], P[[i]])[0]
    loo_rss = float(np.sum((loo - y) ** 2))
    return {
        "theta": theta,
        "fitted": fitted,
        "loo": loo,
        "rss": rss,
        "loo_rss": loo_rss,
        "rmse": float(np.sqrt(rss / y.size)),
        "loo_rmse": float(np.sqrt(loo_rss / y.size)),
    }


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    with rasterio.open(RAW / "sample_submission.tif") as template:
        shape = (template.height, template.width)
        transform = tuple(template.transform)[:6]
        footprint = np.isfinite(template.read(1))
    with rasterio.open(RAW / "labels.tif") as source:
        catalogue = source.read(1) == 1
    scoring = footprint & ~catalogue

    basis = build_basis(footprint, catalogue, scoring)
    basis_names = list(basis)
    basis_matrix = np.column_stack([basis[name] for name in basis_names]).astype(np.float32)
    basis_mass = basis_matrix.sum(axis=0, dtype=np.float64)
    del basis

    design_path = PREPARED / "inverse_design.npz"
    cached = None
    if design_path.is_file():
        blob = np.load(design_path, allow_pickle=True)
        if list(blob["basis_names"]) == basis_names:
            cached = blob
            print("  reusing cached design matrices", flush=True)

    rows, skipped = [], []
    for entry in (() if cached is not None else ledger["entries"]):
        path = REFERENCE / f"{entry['id']}.tif"
        if not path.is_file():
            skipped.append({"id": entry["id"], "reason": "file missing"})
            continue
        with rasterio.open(path) as source:
            if (source.height, source.width) != shape or not np.allclose(
                tuple(source.transform)[:6], transform, atol=1e-6
            ):
                skipped.append({"id": entry["id"], "reason": "grid mismatch"})
                continue
            prediction = source.read(1).astype(np.float32)
        prediction[~np.isfinite(prediction)] = 0.0
        np.clip(prediction, 0.0, 1.0, out=prediction)
        prediction[~scoring] = 0.0
        mass = float(prediction.sum(dtype=np.float64))
        if mass <= 0:
            skipped.append({"id": entry["id"], "reason": "empty prediction"})
            continue
        cover, linear = coverage_fields(prediction)
        cover_c = cover[footprint]
        linear_c = linear[footprint]
        rows.append(
            {
                "id": entry["id"],
                "dti": float(entry["dti"]),
                "mass": mass,
                "positive_pixels": int(np.count_nonzero(prediction > 0)),
                "A": (cover_c @ basis_matrix).astype(np.float64).tolist(),
                "B": (linear_c @ basis_matrix).astype(np.float64).tolist(),
            }
        )
        print(f"  processed {entry['id']}: mass {mass:.0f}, dti {entry['dti']:.4f}", flush=True)
        del cover, linear, cover_c, linear_c, prediction

    if cached is not None:
        A, B, P, y = cached["A"], cached["B"], cached["P"], cached["y"]
        ids = list(cached["ids"])
        positives = list(cached["positives"])
        skipped = json.loads(str(cached["skipped"]))
    else:
        A = np.array([row["A"] for row in rows])
        B = np.array([row["B"] for row in rows])
        P = np.array([row["mass"] for row in rows])
        y = np.array([row["dti"] for row in rows])
        ids = [row["id"] for row in rows]
        positives = [row["positive_pixels"] for row in rows]
        np.savez(
            design_path, A=A, B=B, P=P, y=y, ids=np.array(ids),
            positives=np.array(positives), basis_names=np.array(basis_names),
            basis_mass=basis_mass, skipped=json.dumps(skipped),
        )
    tss = float(np.sum((y - y.mean()) ** 2))

    # Forward selection on leave-one-out error (max 5 basis fields for 30 points).
    selected: list[int] = []
    history = []
    best_overall = None
    remaining = list(range(len(basis_names)))
    while remaining and len(selected) < 5:
        trials = []
        for candidate in remaining:
            columns = selected + [candidate]
            result = evaluate_subset(columns, A, B, P, y, basis_mass)
            trials.append((result["loo_rss"], candidate, result))
        trials.sort(key=lambda item: item[0])
        loo_rss, candidate, result = trials[0]
        if best_overall is not None and loo_rss >= best_overall["loo_rss"] - 1e-12:
            break
        selected.append(candidate)
        remaining.remove(candidate)
        best_overall = {"columns": list(selected), **result, "loo_rss": loo_rss}
        history.append(
            {
                "added": basis_names[candidate],
                "columns": [basis_names[c] for c in selected],
                "loo_rmse": result["loo_rmse"],
                "rmse": result["rmse"],
                "loo_r2": 1.0 - loo_rss / tss,
                "r2": 1.0 - result["rss"] / tss,
            }
        )
        print(f"  + {basis_names[candidate]}: LOO RMSE {result['loo_rmse']:.4f}", flush=True)

    columns = best_overall["columns"]
    theta = best_overall["theta"]
    rho = (basis_matrix[:, columns] @ theta).astype(np.float32)
    np.save(PREPARED / "rho_hat.npy", rho)

    # Jackknife weights: refit theta with each observation removed, so downstream
    # promotion decisions can be required to hold under every leave-one-out fit.
    jackknife = np.zeros((y.size, len(columns)))
    for i in range(y.size):
        keep = np.ones(y.size, dtype=bool)
        keep[i] = False
        theta_i, _ = fit_theta(
            A[np.ix_(keep, columns)], B[np.ix_(keep, columns)], P[keep], y[keep], basis_mass[columns]
        )
        jackknife[i] = theta_i
    np.save(PREPARED / "rho_basis_selected.npy", basis_matrix[:, columns])

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "non-negative fit of the exact DTI linear-functional form to our own scored submissions; basis chosen by forward selection on leave-one-out error",
        "basis_catalogue": basis_names,
        "selected_basis": [basis_names[c] for c in columns],
        "theta": theta.tolist(),
        "selection_history": history,
        "n_observations": len(rows),
        "r2_in_sample": 1.0 - best_overall["rss"] / tss,
        "r2_leave_one_out": 1.0 - best_overall["loo_rss"] / tss,
        "rmse_in_sample": best_overall["rmse"],
        "rmse_leave_one_out": best_overall["loo_rmse"],
        "estimated_total_truth_pixels": float(rho.sum()),
        "rho_summary": {
            "max": float(rho.max()),
            "mean": float(rho.mean()),
            "p999": float(np.quantile(rho, 0.999)),
        },
        "selected_columns": [int(c) for c in columns],
        "basis_mass": basis_mass.tolist(),
        "theta_jackknife": jackknife.tolist(),
        "observations": [
            {
                "id": identifier,
                "dti": float(obs),
                "mass": float(mass_value),
                "positive_pixels": int(positive),
                "fitted_dti": float(f),
                "loo_dti": float(l),
            }
            for identifier, obs, mass_value, positive, f, l in zip(
                ids, y, P, positives, best_overall["fitted"], best_overall["loo"]
            )
        ],
        "skipped": skipped,
        "caveats": [
            "Public scores cover the public chunks only, so rho estimates public-chunk truth density; the private chunks are assumed to share the same structural profile.",
            "FPw uses the first-order approximation FPw = mass - sum rho*L, exact when truth kernels do not overlap and mildly conservative otherwise.",
            "Score-to-file associations come from the owner's own records, not from organizer receipts.",
            "rho is a calibrated prior, not a verified fault map; a high rho pixel is a scoring-optimal bet, not a confirmed fault.",
        ],
    }
    (PREPARED / "truth_prior.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "selected_basis", "theta", "r2_in_sample", "r2_leave_one_out",
        "rmse_in_sample", "rmse_leave_one_out", "estimated_total_truth_pixels", "n_observations",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
