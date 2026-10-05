#!/usr/bin/env python3
"""Fetch and parse the public DrivenData leaderboard into a dated JSON snapshot.

No participant login is used. If the page blocks unauthenticated access or its
markup changes, the script fails without replacing the last good snapshot.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD_URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
OUTPUT = ROOT / "docs" / "data" / "leaderboard.json"


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[dict[str, Any]]]] = []
        self._table: list[list[dict[str, Any]]] | None = None
        self._row: list[dict[str, Any]] | None = None
        self._cell: dict[str, Any] | None = None
        self._anchor_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "table":
            if self._table is None:
                self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = {"text": [], "anchors": []}
        elif tag == "a" and self._cell is not None:
            href = attrs_map.get("href") or ""
            self._cell["anchors"].append({"href": href, "text": []})
            self._anchor_depth = len(self._cell["anchors"])
        elif tag == "br" and self._cell is not None:
            self._cell["text"].append("\n")
            if self._anchor_depth and self._cell["anchors"]:
                self._cell["anchors"][-1]["text"].append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"].append(data)
            if self._anchor_depth and self._cell["anchors"]:
                self._cell["anchors"][-1]["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._anchor_depth = 0
        elif tag in {"td", "th"} and self._cell is not None and self._row is not None:
            raw_text = "".join(self._cell["text"])
            self._cell["value"] = " ".join(raw_text.split())
            self._cell["first_line"] = next(
                (line.strip() for line in raw_text.splitlines() if line.strip()), ""
            )
            for anchor in self._cell["anchors"]:
                anchor["value"] = " ".join("".join(anchor["text"]).split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def parse_leaderboard_html(html: str) -> list[dict[str, Any]]:
    """Extract ranked public participants, accepting common table layouts."""
    parser = _TableParser()
    parser.feed(html)
    candidates: list[dict[str, Any]] = []
    for table in parser.tables:
        for cells in table:
            texts = [str(cell.get("value", "")).strip() for cell in cells]
            score_indices = [
                index
                for index, value in enumerate(texts)
                if re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", value)
            ]
            rank_matches = [re.search(r"(?:^|\s)#?(\d{1,4})(?:\s|$)", value) for value in texts]
            rank_index = next((i for i, match in enumerate(rank_matches) if match), None)
            if not score_indices or rank_index is None:
                continue
            score_index = score_indices[-1]
            name_candidates: list[str] = []
            for index, cell in enumerate(cells):
                if index in {rank_index, score_index}:
                    continue
                anchors = cell.get("anchors", [])
                name_candidates.extend(
                    str(anchor.get("value", "")).strip()
                    for anchor in anchors
                    if str(anchor.get("value", "")).strip()
                )
            if not name_candidates:
                for index, value in enumerate(texts):
                    if index not in {rank_index, score_index} and value:
                        first_line = str(cells[index].get("first_line") or value).strip()
                        if first_line:
                            name_candidates.append(first_line)
            rank_match = rank_matches[rank_index]
            if not rank_match or not name_candidates:
                continue
            try:
                rank = int(rank_match.group(1))
                score = float(texts[score_index])
            except (TypeError, ValueError):
                continue
            if rank < 1 or not 0.0 <= score <= 1.0:
                continue
            candidates.append({"rank": rank, "participant": name_candidates[0], "score": score})
    if not candidates:
        raise ValueError("no ranked score rows parsed; leaderboard HTML may have changed or require login")
    # Remove duplicate rows caused by nested/duplicated markup, preserving best rank.
    deduplicated: dict[tuple[int, str], dict[str, Any]] = {}
    for row in candidates:
        deduplicated[(row["rank"], row["participant"])] = row
    return sorted(deduplicated.values(), key=lambda row: (row["rank"], row["participant"]))


def fetch_html(url: str = LEADERBOARD_URL, *, timeout: int = 30) -> str:
    request = Request(
        url,
        headers={"User-Agent": "GEMSDOE37-public-leaderboard-refresh/1.0", "Accept": "text/html"},
    )
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if response.status != 200:
            raise RuntimeError(f"official leaderboard returned HTTP {response.status}")
        if "html" not in content_type.lower():
            raise RuntimeError(f"official leaderboard returned non-HTML content type {content_type!r}")
        return response.read().decode("utf-8", errors="replace")


def make_snapshot(html: str, captured_utc: str | None = None) -> dict[str, Any]:
    rows = parse_leaderboard_html(html)
    return {
        "source": LEADERBOARD_URL,
        "captured_utc": captured_utc or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "refresh_method": "scripts/refresh_leaderboard.py; scheduled repository workflow proposes changes for review",
        "snapshot_only": True,
        "rows": rows[:50],
        "note": (
            "Dated snapshot parsed from the public DrivenData leaderboard. The board can change; "
            "verify the official page before interpreting a result. Public rank is not the hidden-label score."
        ),
    }


def refresh() -> dict[str, Any]:
    html = fetch_html()
    snapshot = make_snapshot(html)
    if OUTPUT.is_file():
        try:
            previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = None
        if previous and previous.get("rows") == snapshot["rows"]:
            # Avoid a timestamp-only commit every six hours. The feed timestamp
            # denotes the last changed snapshot, and the scheduled job keeps
            # checking the live page without rewriting identical rows.
            return previous
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Replace only after a complete, non-empty parse, preserving the prior feed on errors.
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    return snapshot


def main() -> int:
    try:
        snapshot = refresh()
    except (OSError, URLError, RuntimeError, ValueError) as exc:
        print(f"LEADERBOARD REFRESH BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"captured_utc": snapshot["captured_utc"], "rows": snapshot["rows"][:5]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
