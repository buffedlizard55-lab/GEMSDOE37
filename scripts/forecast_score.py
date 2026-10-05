#!/usr/bin/env python3
"""Three independent forecasts of the public DTI for the built submission.

None of them is a guarantee.  They are reported together precisely because
they disagree, and the spread is the honest uncertainty.
"""
from __future__ import annotations

import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / "data" / "prepared"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verification", type=Path, default=PREPARED / "submission_verification.json")
    args = parser.parse_args()

    ver = json.loads(args.verification.read_text(encoding="utf-8"))
    desc = ver["descriptors"]
    model = json.loads((PREPARED / "public_score_model.json").read_text(encoding="utf-8"))
    maps = model["maps"]
    k = desc["positive_pixels"]
    ps = desc["mean_pstruct_of_selected"]
    sp = desc["spacing_proxy"]

    # 1. Descriptor model over all 31 scored maps (LOO R^2 0.554).
    b = model["best_subset"]["beta"]
    f1 = float(np.exp(b[0] + b[1] * ps + b[2] * sp))
    in_range = (
        min(m["mean_pstruct"] for m in maps) <= ps <= max(m["mean_pstruct"] for m in maps)
        and min(m["spacing_proxy"] for m in maps) <= sp <= max(m["spacing_proxy"] for m in maps)
    )

    # 2. Budget power law fitted on the 12 perfectly dotted maps only.
    dotted = [m for m in maps if m["spacing_proxy"] < 1.05]
    X = np.column_stack([np.ones(len(dotted)), [m["log_mass"] for m in dotted]])
    y = np.log([m["public_dti"] for m in dotted])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    f2 = float(np.exp(beta[0] + beta[1] * np.log(k)))
    masses = [m["mass"] for m in dotted]

    # 3. Physical recall model, deliberately pessimistic: it assumes our ranking
    #    recovers truth no faster than the best previously submitted family,
    #    whose kernel-weighted recall curve R(k) = a*k^b is identified from its
    #    own two clean budget points (44,090 -> 0.2600 and 121,131 -> 0.1922).
    n_truth = 14000.0

    def recall_from_dti(dti, budget):
        u = budget / n_truth
        return dti * (0.8 + 0.2 * u) / (1.0 - 0.2 * dti)

    r1, k1 = recall_from_dti(0.2600, 44090.0), 44090.0
    r2, k2 = recall_from_dti(0.1922, 121131.0), 121131.0
    exponent = np.log(r2 / r1) / np.log(k2 / k1)
    scale = r1 / k1 ** exponent
    recall = scale * k ** exponent
    f3 = float(recall / (0.8 + 0.2 * recall + 0.2 * k / n_truth))

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file": ver["file"],
        "inputs": {"positive_pixels": k, "mean_pstruct": ps, "spacing_proxy": sp},
        "forecasts": {
            "descriptor_model_31_maps": {
                "value": f1,
                "loo_r2": model["best_subset"]["loo_r2"],
                "features": model["best_subset"]["features"],
                "predictors_inside_observed_range": bool(in_range),
            },
            "budget_power_law_12_dotted_maps": {
                "value": f2,
                "fit": {"intercept": float(beta[0]), "log_mass_coefficient": float(beta[1])},
                "observed_mass_range": [min(masses), max(masses)],
                "extrapolating_below_observed_range": bool(k < min(masses)),
            },
            "physical_recall_model_pessimistic": {
                "value": f3,
                "assumed_truth_pixels": n_truth,
                "recall_curve": {"scale": float(scale), "exponent": float(exponent)},
                "assumption": "our ranking is no better than the best previously submitted family",
            },
        },
        "current_owner_best_public_dti": 0.2778,
        "leaderboard_top_public_dti": 0.3262,
        "honest_reading": (
            "The pessimistic physical model, which gives our ranking no credit at all, already "
            "puts this build at roughly the level of the current owner best. The two "
            "observational models are more optimistic but extrapolate below the observed budget "
            "range. Treat anything above 0.30 as unverified upside, not a prediction."
        ),
    }
    (PREPARED / "score_forecast.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["forecasts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
