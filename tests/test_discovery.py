"""Tests for the H6 discovery primitives and the published candidate."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gemsdoe37.discovery import (
    catalogue_standoff,
    gradient_magnitude,
    greedy_spaced_selection,
    local_mass,
    nonmax_suppress,
    rank_normalize,
    ridge_strength,
    scales_survived,
)
from gemsdoe37.metric import distance_weighted_tversky

ROOT = Path(__file__).resolve().parents[1]


def test_gradient_magnitude_detects_a_step_edge():
    field = np.zeros((21, 21), dtype=np.float32)
    field[:, 10:] = 1.0
    response = gradient_magnitude(field, 1.0)
    assert response[10, 10] > response[10, 2]
    assert response.dtype == np.float32


def test_ridge_strength_is_non_negative_and_peaks_on_a_ridge():
    field = np.zeros((31, 31), dtype=np.float32)
    field[:, 15] = 1.0
    response = ridge_strength(field, 1.0)
    assert (response >= 0).all()
    assert response[15, 15] > response[15, 5]


def test_rank_normalize_maps_to_unit_interval_and_preserves_order():
    values = np.array([[3.0, 1.0], [2.0, 4.0]], dtype=np.float32)
    valid = np.ones_like(values, dtype=bool)
    ranked = rank_normalize(values, valid)
    assert ranked.min() == 0.0 and ranked.max() == 1.0
    assert ranked[0, 1] < ranked[1, 0] < ranked[0, 0] < ranked[1, 1]


def test_rank_normalize_zeroes_invalid_cells():
    values = np.array([[5.0, 9.0]], dtype=np.float32)
    valid = np.array([[True, False]])
    assert rank_normalize(values, valid)[0, 1] == 0.0


def test_scales_survived_counts_only_persistent_cells():
    valid = np.ones((10, 10), dtype=bool)
    persistent = np.zeros((10, 10), dtype=np.float32)
    persistent[5, 5] = 1.0
    transient = np.zeros((10, 10), dtype=np.float32)
    transient[1, 1] = 1.0
    counts = scales_survived([persistent, persistent, transient], valid, quantile=0.99)
    assert counts[5, 5] == 2.0
    assert counts[1, 1] == 1.0


def test_nonmax_suppress_keeps_one_cell_per_plateau_peak():
    score = np.zeros((7, 7), dtype=np.float32)
    score[3, 3] = 1.0
    score[3, 4] = 0.9
    valid = np.ones_like(score, dtype=bool)
    keep = nonmax_suppress(score, valid, size=3)
    assert keep[3, 3]
    assert not keep[3, 4]


def test_greedy_spaced_selection_respects_budget_and_spacing():
    rng = np.random.default_rng(0)
    score = rng.random((60, 60)).astype(np.float32)
    allowed = np.ones_like(score, dtype=bool)
    selection = greedy_spaced_selection(score, allowed, budget=50, spacing_px=3.0)
    assert selection.sum() == 50
    rows, cols = np.nonzero(selection)
    points = np.stack([rows, cols], axis=1).astype(float)
    distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    np.fill_diagonal(distances, np.inf)
    assert distances.min() >= 3.0


def test_greedy_spaced_selection_takes_the_highest_scores_first():
    score = np.zeros((30, 30), dtype=np.float32)
    score[0, 0] = 1.0
    score[20, 20] = 0.5
    score[10, 10] = 0.9
    allowed = np.ones_like(score, dtype=bool)
    selection = greedy_spaced_selection(score, allowed, budget=2, spacing_px=2.0)
    assert selection[0, 0] and selection[10, 10] and not selection[20, 20]


def test_greedy_spaced_selection_never_leaves_the_allowed_mask():
    score = np.ones((20, 20), dtype=np.float32)
    allowed = np.zeros_like(score, dtype=bool)
    allowed[5:8, 5:8] = True
    selection = greedy_spaced_selection(score, allowed, budget=100, spacing_px=1.5)
    assert selection.sum() > 0
    assert not (selection & ~allowed).any()


def test_catalogue_standoff_excludes_the_buffer():
    known = np.zeros((11, 11), dtype=bool)
    known[5, 5] = True
    allowed = catalogue_standoff(known, 3.0)
    assert not allowed[5, 5]
    assert not allowed[5, 7]
    assert allowed[5, 8]


def test_local_mass_is_one_for_isolated_cells_and_larger_when_clumped():
    dotted = np.zeros((20, 20), dtype=bool)
    dotted[::4, ::4] = True
    clumped = np.zeros((20, 20), dtype=bool)
    clumped[5:9, 5:9] = True
    assert local_mass(dotted) == pytest.approx(1.0)
    assert local_mass(clumped) > 2.0


def test_metric_reproduces_the_published_worked_example_identity():
    """FN_w = |G| - TP_w, so DTI = TP/(0.8|G| + 0.2TP + 0.2FP)."""
    truth = np.zeros((21, 21), dtype=bool)
    truth[8:13, 10] = True
    prediction = np.zeros((21, 21), dtype=np.float64)
    prediction[10, 12] = 1.0
    parts = distance_weighted_tversky(prediction, truth)
    count = int(truth.sum())
    assert parts["fn"] == pytest.approx(count - parts["tp"], abs=1e-9)
    expected = parts["tp"] / (0.8 * count + 0.2 * parts["tp"] + 0.2 * parts["fp"])
    assert parts["dti"] == pytest.approx(expected, rel=1e-6)


def test_binary_emission_dominates_a_scaled_down_prediction():
    truth = np.zeros((31, 31), dtype=bool)
    truth[15, 10:20] = True
    support = np.zeros((31, 31), dtype=np.float64)
    support[15, 12] = 1.0
    support[15, 17] = 1.0
    full = distance_weighted_tversky(support, truth)["dti"]
    half = distance_weighted_tversky(support * 0.5, truth)["dti"]
    assert full > half


def test_published_candidate_record_is_internally_consistent():
    record = json.loads((ROOT / "docs/data/current_submission.json").read_text())
    tif = ROOT / "docs" / record["download_path"]
    assert tif.exists(), "the advertised download must exist"
    checks = record["format_checks"]
    assert checks["range_0_1_all_cells"] and checks["all_cells_finite"]
    assert checks["nodata_tag_absent"] and checks["dtype_float32"] and checks["single_band"]
    assert checks["positive_pixels"] == record["positive_pixels"] == 80_000
    assert record["uniqueness"]["max_jaccard_vs_prior_submissions"] < 0.5
    assert record["organizer_score"] is None


def test_published_candidate_raster_matches_its_receipt():
    rasterio = pytest.importorskip("rasterio")
    record = json.loads((ROOT / "docs/data/current_submission.json").read_text())
    with rasterio.open(ROOT / "docs" / record["download_path"]) as src:
        assert src.count == 1
        assert src.dtypes == ("float32",)
        assert src.crs.to_epsg() == 32611
        assert (src.height, src.width) == (3730, 3292)
        assert src.nodata is None
        array = src.read(1)
    assert np.isfinite(array).all()
    assert array.min() >= 0.0 and array.max() <= 1.0
    assert set(np.unique(array).tolist()) == {0.0, 1.0}
    assert int((array > 0).sum()) == record["positive_pixels"]
