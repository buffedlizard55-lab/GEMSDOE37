import numpy as np
import pytest

from gemsdoe37.holdout import spatial_quadrant_masks, spatial_quadrant_region_masks, top_budget_binary


def test_quadrants_are_disjoint_and_guarded():
    masks = spatial_quadrant_masks((20, 22), guard_px=2)
    assert set(masks) == {"NW", "NE", "SW", "SE"}
    total = np.zeros((20, 22), dtype=np.uint8)
    for mask in masks.values():
        total += mask
    assert total.max() == 1
    assert not np.any(total[:, 9:13])
    assert not np.any(total[8:12, :])
    assert not np.any(total[:2, :])


def test_full_quadrant_regions_partition_grid_for_fold_normalization():
    regions = spatial_quadrant_region_masks((11, 13))
    total = np.zeros((11, 13), dtype=np.uint8)
    for region in regions.values():
        total += region
    assert np.all(total == 1)
    assert sum(int(region.sum()) for region in regions.values()) == 11 * 13


def test_top_budget_uses_deterministic_tie_breaks():
    score = np.array([[0.4, 0.9], [0.9, 0.0]], dtype=np.float32)
    mask = np.ones_like(score, dtype=bool)
    selected = top_budget_binary(score, mask, budget=2)
    assert selected.sum() == 2
    assert selected[0, 1] and selected[1, 0]


def test_top_budget_fails_when_the_ranking_has_too_few_candidates():
    score = np.array([[0.0, 0.5], [0.0, 0.0]], dtype=np.float32)
    with pytest.raises(ValueError, match="below requested budget"):
        top_budget_binary(score, np.ones_like(score, dtype=bool), budget=2)
