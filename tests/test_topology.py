import numpy as np
import pytest

from gemsdoe37.topology import PersistenceBar, h0_superlevel_persistence, match_adjacent_scale_bars


def test_h0_superlevel_reports_birth_death_and_peak():
    field = np.array([[0.0, 5.0, 1.0, 4.0, 0.0]], dtype=np.float32)
    bars = h0_superlevel_persistence(field, connectivity=4, min_persistence=0.1)
    assert len(bars) == 1
    assert bars[0] == PersistenceBar(row=0, col=3, birth=4.0, death=1.0, persistence=3.0)


def test_h0_respects_connectivity_choice():
    field = np.array([[4.0, 0.0], [0.0, 3.0]], dtype=np.float32)
    bars8 = h0_superlevel_persistence(field, connectivity=8, min_persistence=0.1)
    bars4 = h0_superlevel_persistence(field, connectivity=4, min_persistence=0.1)
    # Eight-connectivity merges the two peaks at the second peak's birth,
    # yielding only a zero-lifetime bar; four-connectivity waits for level 0.
    assert bars8 == []
    assert len(bars4) == 1
    assert bars4[0].persistence == pytest.approx(3.0)


def test_masked_components_do_not_merge_across_nodata():
    field = np.array([[4.0, 0.0, 3.0, 0.0, 2.0]], dtype=np.float32)
    mask = np.array([[True, True, False, True, True]])
    bars = h0_superlevel_persistence(field, mask, connectivity=4, min_persistence=0.1)
    assert bars == []


def test_plateau_ties_do_not_create_positive_lifetime_bars():
    field = np.array([[0.0, 2.0, 2.0, 1.0, 0.0]], dtype=np.float32)
    assert h0_superlevel_persistence(field, connectivity=4, min_persistence=0.01) == []


def test_invalid_inputs_fail_closed():
    with pytest.raises(ValueError, match="2-D"):
        h0_superlevel_persistence(np.ones(5))
    with pytest.raises(ValueError, match="shape"):
        h0_superlevel_persistence(np.ones((2, 2)), np.ones((2, 3), dtype=bool))
    with pytest.raises(ValueError, match="connectivity"):
        h0_superlevel_persistence(np.ones((2, 2)), connectivity=6)


def test_adjacent_scale_tracking_and_conditional_stability_margin():
    bars = {
        100.0: [PersistenceBar(10, 10, 0.6, 0.3, 0.3)],
        200.0: [PersistenceBar(11, 10, 0.5, 0.3, 0.2)],
        400.0: [PersistenceBar(80, 80, 0.8, 0.3, 0.5)],
    }
    tracks = match_adjacent_scale_bars(bars, max_peak_distance_px=2, epsilon=0.05)
    assert len(tracks) == 2
    multi = next(track for track in tracks if track.scale_count == 2)
    assert multi.sigma_values_m == (100.0, 200.0)
    assert multi.sigma_span_m == 100.0
    assert multi.min_persistence == pytest.approx(0.2)
    assert multi.stability_margin == pytest.approx(0.1)
