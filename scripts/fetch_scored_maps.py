#!/usr/bin/env python3
"""Fetch our own previously-submitted prediction rasters listed in
``research/scored_submissions.json`` into ignored ``data/reference/``.

These rasters are used *only* as calibration observations for the
leaderboard-feedback inverse model.  Their pixels are never copied into a
GEMSDOE37 candidate.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "research" / "scored_submissions.json"
OUT = ROOT / "data" / "reference"


def main() -> int:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    by_repo: dict[str, list[dict]] = defaultdict(list)
    for entry in ledger["entries"]:
        target = OUT / f"{entry['id']}.tif"
        if target.exists():
            continue
        by_repo[entry["repo"]].append(entry)

    failures: list[str] = []
    for repo, entries in by_repo.items():
        with tempfile.TemporaryDirectory(dir="/home/user/work") as tmp:
            clone = Path(tmp) / repo
            cmd = [
                "git", "clone", "--quiet", "--depth", "1", "--filter=blob:none",
                "--no-checkout", f"https://github.com/buffedlizard55-lab/{repo}.git", str(clone),
            ]
            if subprocess.run(cmd).returncode != 0:
                failures.extend(e["id"] for e in entries)
                continue
            subprocess.run(["git", "-C", str(clone), "sparse-checkout", "init", "--no-cone"], check=True)
            subprocess.run(
                ["git", "-C", str(clone), "sparse-checkout", "set", *[e["path"] for e in entries]],
                check=True,
            )
            subprocess.run(["git", "-C", str(clone), "checkout"], check=True)
            for entry in entries:
                source = clone / entry["path"]
                if not source.is_file():
                    failures.append(entry["id"])
                    print(f"MISSING {entry['repo']}/{entry['path']}", file=sys.stderr)
                    continue
                (OUT / f"{entry['id']}.tif").write_bytes(source.read_bytes())
                print(f"fetched {entry['id']} ({source.stat().st_size} bytes)", flush=True)

    present = sorted(p.name for p in OUT.glob("*.tif"))
    print(json.dumps({"fetched": len(present), "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
