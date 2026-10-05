import gzip
import json
from types import SimpleNamespace

from gemsdoe37.topology import PersistenceBar, PersistenceTrack, ScaleObservation
from scripts import build_candidate


def test_track_sidecar_is_hash_pinned_complete_and_reproducible(tmp_path, monkeypatch):
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    monkeypatch.setattr(build_candidate, "ROOT", tmp_path)
    monkeypatch.setattr(build_candidate, "PREPARED", prepared)
    observations = (
        ScaleObservation(100.0, PersistenceBar(4, 5, 0.7, 0.2, 0.5)),
        ScaleObservation(200.0, PersistenceBar(4, 6, 0.6, 0.2, 0.4)),
    )
    track = PersistenceTrack(
        observations=observations,
        min_persistence=0.4,
        epsilon=0.01,
        stability_margin=0.38,
        sigma_span_m=100.0,
    )
    result = SimpleNamespace(accepted_tracks=(track,))

    first = build_candidate.write_track_detail(result, "NW", "dem_curvature")
    path = tmp_path / first["path"]
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        record = json.loads(stream.readline())
    assert first["track_count"] == 1
    assert first["bar_observation_count"] == 2
    assert record["observations"][0] == {
        "sigma_m": 100.0,
        "row": 4,
        "column": 5,
        "birth": 0.7,
        "death": 0.2,
        "persistence": 0.5,
    }
    second = build_candidate.write_track_detail(result, "NW", "dem_curvature")
    assert second["sha256"] == first["sha256"]
