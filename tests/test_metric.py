import pytest
import numpy as np

from gemsdoe37.metric import distance_weighted_tversky, marginal_credit_bar


def test_exact_hit_has_unit_dti():
    truth = np.zeros((5, 5), dtype=bool)
    truth[2, 2] = True
    prediction = truth.astype(np.float32)
    result = distance_weighted_tversky(prediction, truth)
    assert result["tp"] == pytest.approx(1.0)
    assert result["fp"] == pytest.approx(0.0)
    assert result["fn"] == pytest.approx(0.0)
    assert result["dti"] == pytest.approx(1.0, abs=1e-7)


def test_one_pixel_two_hundred_metres_away_uses_triangular_kernel():
    truth = np.zeros((5, 7), dtype=bool)
    truth[2, 2] = True
    prediction = np.zeros_like(truth, dtype=np.float32)
    prediction[2, 4] = 1.0
    result = distance_weighted_tversky(prediction, truth)
    assert result["tp"] == pytest.approx(1.0 / 3.0)
    assert result["fn"] == pytest.approx(2.0 / 3.0)
    assert result["fp"] == pytest.approx(2.0 / 3.0)
    assert result["dti"] == pytest.approx(1.0 / 3.0, abs=1e-7)


def test_prediction_beyond_three_hundred_metres_has_no_tp_credit():
    truth = np.zeros((5, 7), dtype=bool)
    truth[2, 1] = True
    prediction = np.zeros_like(truth, dtype=np.float32)
    prediction[2, 4] = 1.0
    result = distance_weighted_tversky(prediction, truth)
    assert result["tp"] == 0.0
    assert result["fn"] == 1.0
    assert result["fp"] == 1.0
    assert result["dti"] == 0.0


def test_invalid_cells_are_excluded_from_metric():
    truth = np.zeros((3, 3), dtype=bool)
    truth[1, 1] = True
    prediction = np.zeros((3, 3), dtype=np.float32)
    prediction[0, 0] = 1.0
    valid = np.ones((3, 3), dtype=bool)
    valid[0, 0] = False
    result = distance_weighted_tversky(prediction, truth, valid_mask=valid)
    assert result["fp"] == pytest.approx(0.0)
    assert result["dti"] == pytest.approx(0.0)


def test_exact_known_fault_pixels_are_excluded_without_a_proximity_buffer():
    truth = np.zeros((5, 7), dtype=bool)
    truth[2, 2] = True
    known = np.zeros_like(truth)
    known[2, 4] = True
    prediction = np.zeros_like(truth, dtype=np.float32)
    prediction[2, 4] = 1.0  # on the exact known mask: ignored
    prediction[2, 3] = 1.0  # adjacent to it: still scored normally

    result = distance_weighted_tversky(
        prediction,
        truth,
        exclusion_mask=known,
        radius_m=300.0,
        pixel_size_m=100.0,
    )
    assert result["tp"] == pytest.approx(2.0 / 3.0)
    assert result["fp"] == pytest.approx(1.0 / 3.0)
    assert result["fn"] == pytest.approx(1.0 / 3.0)
    assert result["dti"] == pytest.approx(2.0 / 3.0)


def test_truth_and_prediction_on_exact_excluded_pixels_do_not_score():
    truth = np.zeros((3, 3), dtype=bool)
    truth[1, 1] = True
    prediction = truth.astype(np.float32)
    known = truth.copy()
    result = distance_weighted_tversky(prediction, truth, exclusion_mask=known)
    assert result == {"tp": 0.0, "fp": 0.0, "fn": 0.0, "dti": 0.0}


def test_exclusion_mask_shape_is_checked():
    with pytest.raises(ValueError, match="exclusion_mask shape"):
        distance_weighted_tversky(
            np.zeros((2, 2)), np.zeros((2, 2)), exclusion_mask=np.zeros((2, 1))
        )


def test_values_are_checked_and_marginal_rule_is_explicitly_conditional():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        distance_weighted_tversky(np.array([[1.1]]), np.array([[True]]))
    assert marginal_credit_bar(0.25) == pytest.approx(0.05)


def test_published_worked_example_rounds_to_sixty_percent():
    # The official page reports TPw=3.00, FPw=1.89, FNw=2.00 and rounds the
    # resulting alpha=.2, beta=.8 Tversky score to 0.60.
    score = 3.0 / (3.0 + 0.2 * 1.89 + 0.8 * 2.0)
    assert score == pytest.approx(0.6026516673)
    assert round(score, 2) == 0.60
