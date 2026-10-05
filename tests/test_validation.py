import json

import numpy as np
import pytest

from scripts.validate_candidate import (
    load_registered_current_best,
    score_one_fold,
    summarize_folds,
    validation_protocol_sha256,
)


def _minimal_prereg():
    return {
        "evaluation": {
            "truth": "test truth",
            "spatial_blocks": ["NW", "NE", "SW", "SE"],
            "guard_distance_m": 300,
            "known_fault_mask_rule": "exact pixels only",
            "metric": {
                "alpha": 0.2,
                "beta": 0.8,
                "pixel_size_m": 100.0,
                "radius_m": 300.0,
                "denominator_epsilon": 1e-8,
            },
            "matched_positive_pixel_budget": 1,
            "top_budget_rule": "top-k",
            "normalization_fit_scope": "train quadrants only",
            "promotion_gate": {"minimum_pooled_dti_gain": 0.005, "minimum_positive_folds": 3},
            "current_holdout_best": None,
        }
    }


def test_fold_scorer_excludes_exact_mask_pixel_but_scores_adjacent_pixel():
    prereg = _minimal_prereg()
    labels = np.zeros((5, 7), dtype=bool)
    labels[2, 2] = True
    footprint = np.ones_like(labels)
    block = np.ones_like(labels)
    known = np.zeros_like(labels)
    known[2, 4] = True
    prediction = np.zeros_like(labels)
    prediction[2, 4] = True  # exact known pixel: excluded
    prediction[2, 3] = True  # adjacent unmasked pixel: scored

    result = score_one_fold(prediction, labels, footprint, block, known, prereg)
    assert result["tp"] == pytest.approx(2.0 / 3.0)
    assert result["fp"] == pytest.approx(1.0 / 3.0)
    assert result["fn"] == pytest.approx(1.0 / 3.0)
    assert result["dti"] == pytest.approx(2.0 / 3.0)


def test_fold_summary_pools_components_instead_of_averaging_fold_scores():
    folds = {
        "NW": {"tp": 1.0, "fp": 0.0, "fn": 9.0, "dti": 0.5, "truth_pixels": 10},
        "NE": {"tp": 9.0, "fp": 0.0, "fn": 1.0, "dti": 0.9, "truth_pixels": 10},
        "SW": {"tp": 1.0, "fp": 0.0, "fn": 9.0, "dti": 0.5, "truth_pixels": 10},
        "SE": {"tp": 9.0, "fp": 0.0, "fn": 1.0, "dti": 0.9, "truth_pixels": 10},
    }
    spec = {"alpha": 0.2, "beta": 0.8, "denominator_epsilon": 1e-8}
    summary = summarize_folds(folds, spec)
    expected = 20.0 / (20.0 + 0.8 * 20.0 + 1e-8)
    assert summary["pooled_dti"] == pytest.approx(expected)
    assert summary["mean_fold_dti_descriptive_only"] == pytest.approx(0.7)
    assert summary["pooled_dti"] != pytest.approx(summary["mean_fold_dti_descriptive_only"])


def test_protocol_hash_is_deterministic_and_current_best_is_explicitly_missing():
    prereg = _minimal_prereg()
    digest = validation_protocol_sha256(prereg, 37654)
    assert digest == validation_protocol_sha256(prereg, 37654)
    changed = json.loads(json.dumps(prereg))
    changed["evaluation"]["guard_distance_m"] += 100
    assert digest != validation_protocol_sha256(changed, 37654)
    summary, reason = load_registered_current_best(
        prereg,
        budget=37654,
        input_hashes={"features": "a" * 64},
        protocol_sha256=digest,
    )
    assert summary is None
    assert "No local current holdout-best" in reason


def test_registered_current_best_report_must_match_hash_inputs_and_protocol(tmp_path, monkeypatch):
    import scripts.validate_candidate as validation

    prereg = _minimal_prereg()
    inputs = {"features": "a" * 64}
    digest = validation_protocol_sha256(prereg, 37654)
    report = {
        "candidate_id": "BASELINE-1",
        "input_hashes_sha256": inputs,
        "validation_protocol_sha256": digest,
        "budget_positive_pixels": 37654,
        "summaries": {
            "topological_candidate": {
                "pooled_dti": 0.2,
                "per_fold_dti": {name: 0.2 for name in ("NW", "NE", "SW", "SE")},
            }
        },
    }
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    report_hash = validation.sha256_file(path)
    monkeypatch.setattr(validation, "ROOT", tmp_path)
    prereg["evaluation"]["current_holdout_best"] = {
        "candidate_id": "BASELINE-1",
        "report_path": "baseline.json",
        "report_sha256": report_hash,
    }
    summary, reason = load_registered_current_best(
        prereg,
        budget=37654,
        input_hashes=inputs,
        protocol_sha256=digest,
    )
    assert reason is None
    assert summary["pooled_dti"] == 0.2
    with pytest.raises(ValueError, match="different raw input hashes"):
        load_registered_current_best(
            prereg,
            budget=37654,
            input_hashes={"features": "b" * 64},
            protocol_sha256=digest,
        )
    with pytest.raises(ValueError, match="different scoring/split protocol"):
        load_registered_current_best(
            prereg,
            budget=37654,
            input_hashes=inputs,
            protocol_sha256="0" * 64,
        )
    with pytest.raises(ValueError, match="different positive-pixel budget"):
        load_registered_current_best(
            prereg,
            budget=37655,
            input_hashes=inputs,
            protocol_sha256=digest,
        )

    prereg["evaluation"]["current_holdout_best"]["report_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="missing or changed"):
        load_registered_current_best(
            prereg,
            budget=37654,
            input_hashes=inputs,
            protocol_sha256=digest,
        )
