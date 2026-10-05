import numpy as np
import pytest

from gemsdoe37.ridge import persistent_layer_score


def test_persistent_score_exposes_full_scale_track_observations():
    values = np.zeros((25, 25), dtype=np.float32)
    valid = np.ones(values.shape, dtype=bool)
    response = np.full(values.shape, 0.1, dtype=np.float32)
    response[12, 12] = 0.9
    response[12, 17] = 0.7
    response[12, 13:17] = 0.2

    def fixed_response(field, mask, **kwargs):
        return response.copy(), mask.copy()

    result = persistent_layer_score(
        values,
        valid,
        layer_name="synthetic-test-only",
        transform=fixed_response,
        sigma_px_values=(1.0, 2.0, 4.0),
        pixel_size_m=100.0,
        min_persistence=0.05,
        epsilon=0.01,
        min_scale_count=2,
        max_peak_distance_px=2.0,
    )
    assert result.accepted_tracks
    track = next(track for track in result.accepted_tracks if track.scale_count == 3)
    assert track.sigma_values_m == (100.0, 200.0, 400.0)
    assert track.min_persistence == 0.5
    assert track.stability_margin == 0.48
    for item in track.observations:
        assert item.bar.birth == pytest.approx(0.7)
        assert item.bar.death == pytest.approx(0.2)
        assert item.bar.persistence == pytest.approx(0.5)
