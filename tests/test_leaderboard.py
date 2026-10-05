import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_leaderboard_asset_is_only_a_source_link_not_a_score_cache():
    feed = json.loads((ROOT / "docs/data/leaderboard.json").read_text(encoding="utf-8"))
    assert feed["status"] == "source-link-only"
    assert feed["rows"] == []
    assert feed["automatic_monitoring"] is False
    assert feed["local_score_cache"] is False
    assert feed["source"].startswith("https://www.drivendata.org/")


def test_site_links_to_official_board_without_scraper_code():
    page = (ROOT / "docs/leaderboard.html").read_text(encoding="utf-8")
    script = (ROOT / "docs/assets/site.js").read_text(encoding="utf-8")
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/" in page
    assert "data/leaderboard.json" not in script
    assert "refresh_leaderboard" not in script
    assert "Terms of Use" in page
