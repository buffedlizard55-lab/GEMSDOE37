import json

import pytest

import scripts.refresh_leaderboard as refresh_leaderboard
from scripts.refresh_leaderboard import make_snapshot, parse_leaderboard_html


def test_parse_public_leaderboard_rows_and_order():
    html = """
    <table>
      <thead><tr><th>Rank</th><th>Participant</th><th>Score</th></tr></thead>
      <tbody>
        <tr><td>#2</td><td><a href='/users/second/'>Second player</a></td><td>0.3222</td></tr>
        <tr><td>#1</td><td><a href='/users/leader/'>Top player</a></td><td>0.3262</td></tr>
      </tbody>
    </table>
    """
    rows = parse_leaderboard_html(html)
    assert rows == [
        {"rank": 1, "participant": "Top player", "score": 0.3262},
        {"rank": 2, "participant": "Second player", "score": 0.3222},
    ]


def test_parser_uses_first_line_for_unlinked_team_participant():
    html = """
    <table><tr><th>Rank</th><th>Members</th><th>Participant</th><th>Score</th></tr>
    <tr><td>#7</td><td><a href='/users/a/'><img src='avatar.png'></a></td>
    <td>Fault Mapping Team<br>3d ago<br>19 submissions</td><td>0.2998</td></tr></table>
    """
    rows = parse_leaderboard_html(html)
    assert rows == [{"rank": 7, "participant": "Fault Mapping Team", "score": 0.2998}]


def test_snapshot_is_dated_and_clearly_labeled_as_snapshot():
    html = "<table><tr><td>#1</td><td>Lead</td><td>0.3000</td></tr></table>"
    snapshot = make_snapshot(html, captured_utc="2026-10-05T12:00:00+00:00")
    assert snapshot["captured_utc"] == "2026-10-05T12:00:00+00:00"
    assert snapshot["snapshot_only"] is True
    assert snapshot["rows"][0]["participant"] == "Lead"


def test_refresh_does_not_create_timestamp_only_updates(tmp_path, monkeypatch):
    html = "<table><tr><td>#1</td><td>Lead</td><td>0.3000</td></tr></table>"
    path = tmp_path / "leaderboard.json"
    previous = make_snapshot(html, captured_utc="2026-10-01T00:00:00+00:00")
    path.write_text(json.dumps(previous), encoding="utf-8")
    monkeypatch.setattr(refresh_leaderboard, "OUTPUT", path)
    monkeypatch.setattr(refresh_leaderboard, "fetch_html", lambda: html)
    result = refresh_leaderboard.refresh()
    assert result["captured_utc"] == previous["captured_utc"]
    assert json.loads(path.read_text(encoding="utf-8")) == previous


def test_parser_fails_closed_when_markup_has_no_scores():
    with pytest.raises(ValueError, match="no ranked score rows parsed"):
        parse_leaderboard_html("<html><p>Login required</p></html>")
