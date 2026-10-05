import numpy as np
import pytest

from gemsdoe37.features import (
    dem_curvature_ridge,
    identify_layers,
    masked_gaussian,
    potential_field_edge,
    robust_standardize,
)


def test_layer_selection_uses_tags_and_not_fixed_indices():
    descriptions = [
        "surface conductivity",
        "Total Magnetic Intensity",
        "isostatic gravity anomaly",
        "detrended elevation",
    ]
    selected = identify_layers(descriptions)
    assert selected.dem_index == 3
    assert selected.magnetic_index == 1
    assert selected.gravity_index == 2


def test_layer_selection_rejects_derived_slope_and_gradient_tags():
    descriptions = [
        "DEM slope",
        "digital elevation model",
        "total magnetic intensity horizontal gradient",
        "total magnetic intensity",
        "isostatic gravity anomaly horizontal gradient",
        "isostatic gravity anomaly",
    ]
    selected = identify_layers(descriptions)
    assert (selected.dem_index, selected.magnetic_index, selected.gravity_index) == (1, 3, 5)


def test_layer_selection_refuses_ambiguous_missing_bands():
    with pytest.raises(ValueError, match="could not identify"):
        identify_layers(["band 1", "band 2", "band 3"])


def test_masked_gaussian_does_not_turn_nodata_into_zero_signal():
    field = np.ones((25, 25), dtype=np.float32)
    mask = np.ones((25, 25), dtype=bool)
    mask[:, :3] = False
    field[:, :3] = np.nan
    smooth, support = masked_gaussian(field, mask, sigma_px=1.0)
    assert np.allclose(smooth[support], 1.0, atol=1e-5)
    assert not np.any(support[:, 0])


def test_normalization_and_transforms_return_bounded_values():
    y, x = np.mgrid[-12:13, -12:13]
    field = (x**2 - y**2).astype(np.float32)
    mask = np.ones(field.shape, dtype=bool)
    normalized, valid = robust_standardize(field, mask)
    assert normalized.min() >= 0 and normalized.max() <= 1
    dem_score, dem_support = dem_curvature_ridge(field, mask, sigma_px=1.0)
    mag_score, mag_support = potential_field_edge(field, mask, sigma_px=1.0)
    assert dem_score.shape == field.shape
    assert mag_score.shape == field.shape
    assert np.all(np.isfinite(dem_score))
    assert np.all(np.isfinite(mag_score))
    assert np.all((dem_score >= 0) & (dem_score <= 1))
    assert np.all((mag_score >= 0) & (mag_score <= 1))
    assert np.any(dem_support) and np.any(mag_support) and np.any(valid)


def test_normalization_fit_ignores_held_out_values():
    field = np.arange(40 * 40, dtype=np.float32).reshape(40, 40)
    valid = np.ones(field.shape, dtype=bool)
    fit = np.zeros(field.shape, dtype=bool)
    fit[:20] = True
    altered = field.copy()
    altered[~fit] += 1_000_000.0
    original_score, _ = robust_standardize(field, valid, fit_mask=fit)
    altered_score, _ = robust_standardize(altered, valid, fit_mask=fit)
    assert np.allclose(original_score[fit], altered_score[fit])
    assert np.allclose(original_score[~fit], altered_score[~fit])
    dem, _ = dem_curvature_ridge(altered, valid, sigma_px=1.0, fit_mask=fit)
    edge, _ = potential_field_edge(altered, valid, sigma_px=1.0, fit_mask=fit)
    assert np.all(np.isfinite(dem))
    assert np.all(np.isfinite(edge))
