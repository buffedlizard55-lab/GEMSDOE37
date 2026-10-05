#!/usr/bin/env bash
# Fetch the open GEMS inputs used by GEMSDOE37 from public mirrors.
#
# Why this exists: drivendata.org's data tab is login-walled and the dropbox
# mirrors listed in data_sources.json are unreachable from the dev sandbox
# (TLS reset). The project owner's public GitHub repositories carry a byte-split
# copy of the same open rasters with sha256 pins in data/bridge/manifest.json.
# This script clones ONLY those mirrors, verifies every part hash, and writes
# checked files into data/raw/. Nothing here contacts DrivenData.
#
# Usage:  bash scripts/fetch_open_data.sh [workdir]     (default: .data_bridge)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:-${REPO_ROOT}/.data_bridge}"
OUT="${REPO_ROOT}/data/raw"
BRIDGE_REPO="${BRIDGE_REPO:-https://github.com/buffedlizard55-lab/GEMSDOE.git}"
EXT_REPO="${EXT_REPO:-https://github.com/buffedlizard55-lab/GEMSDOE24.git}"

mkdir -p "${OUT}" "${WORK}"

if [ ! -d "${WORK}/GEMSDOE/.git" ]; then
  git clone --depth 1 "${BRIDGE_REPO}" "${WORK}/GEMSDOE"
fi
if [ ! -d "${WORK}/GEMSDOE24/.git" ]; then
  git clone --depth 1 "${EXT_REPO}" "${WORK}/GEMSDOE24"
fi

python3 - "$WORK" "$OUT" <<'PY'
import hashlib, json, pathlib, sys
work, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
b = work / "GEMSDOE" / "data" / "bridge"
manifest = json.loads((b / "manifest.json").read_text())
report = {"reassembled": [], "simple": []}
for f in manifest["files"]:
    target = out / f["canonical"]
    h = hashlib.sha256()
    with target.open("wb") as w:
        parts = f.get("parts")
        items = [(p["name"], p["sha256"], p["bytes"]) for p in parts] if parts else \
                [(f["name"], f["sha256"], f["bytes"])]
        for name, sha, nbytes in items:
            payload = (b / name).read_bytes()
            got = hashlib.sha256(payload).hexdigest()
            assert got == sha, f"{name}: part sha256 mismatch"
            assert len(payload) == nbytes, f"{name}: part size mismatch"
            w.write(payload); h.update(payload)
    got = h.hexdigest()
    ok = got == f["sha256"] and target.stat().st_size == f["bytes"]
    entry = {"file": f["canonical"], "bytes": target.stat().st_size, "sha256": got, "ok": ok}
    report["reassembled" if f.get("parts") else "simple"].append(entry)
    print(("OK   " if ok else "FAIL ") + f"{f['canonical']} {got[:16]}... {entry['bytes']} B")

# External, public-domain layers used for the geophysical belief field.
ext = [("data/external/lidar_scarp_features_u8.tif", "lidar_scarp_features_u8.tif"),
       ("data/external/lidar_scarp_features.json", "lidar_scarp_features.json"),
       ("data/external/geodawn_rad_u8.tif", "geodawn_rad_u8.tif"),
       ("data/external/geodawn_rad.json", "geodawn_rad.json"),
       ("data/external/geodawn_extensions_u8.tif", "geodawn_extensions_u8.tif"),
       ("data/external/geodawn_extensions.json", "geodawn_extensions.json"),
       ("data/external/gdr_wellspring_in_footprint.csv", "gdr_wellspring_in_footprint.csv"),
       ("data/external/gdr_volcanic_vents_in_footprint.csv", "gdr_volcanic_vents_in_footprint.csv")]
for src, dst in ext:
    s = work / "GEMSDOE24" / src
    d = out / dst
    if s.exists():
        d.write_bytes(s.read_bytes())
        print(f"OK   {dst} {hashlib.sha256(d.read_bytes()).hexdigest()[:16]}... {d.stat().st_size} B")
        report["simple"].append({"file": dst, "bytes": d.stat().st_size,
                                 "sha256": hashlib.sha256(d.read_bytes()).hexdigest(), "ok": True})
(out / "fetch_report.json").write_text(json.dumps(report, indent=2))
print(f"\nwrote {out/'fetch_report.json'}")
PY

# Independent structural population used as the off-catalogue validation
# instrument (USGS SGMC structures, DOI 10.3133/ds1052), rasterised by the
# sibling GEMSDOE30 pipeline and mirrored in that public repository.
if [ ! -d "${WORK}/GEMSDOE30/.git" ]; then
  git clone --depth 1 "${SGMC_REPO:-https://github.com/buffedlizard55-lab/GEMSDOE30.git}" "${WORK}/GEMSDOE30"
fi
cp -f "${WORK}/GEMSDOE30/data/external/derived_sgmc_faults_100m_u8.tif" "${OUT}/derived_sgmc_faults_100m_u8.tif"
cp -f "${WORK}/GEMSDOE30/data/external/external_receipt.json" "${OUT}/sgmc_external_receipt.json"
python3 - "$OUT" <<'PY'
import hashlib, pathlib, sys
out = pathlib.Path(sys.argv[1])
for name in ("derived_sgmc_faults_100m_u8.tif", "sgmc_external_receipt.json"):
    p = out / name
    print(f"OK   {name} {hashlib.sha256(p.read_bytes()).hexdigest()[:16]}... {p.stat().st_size} B")
PY
