#!/usr/bin/env bash
# Fetch one historical GEMSDOE32 raster for evaluation only. It is never copied to
# docs/downloads or offered as a GEMSDOE37 submission. The SHA is pinned to the
# owner's public audit receipt; it is not proof that DrivenData awarded its claimed score.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${ROOT}/data/reference"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
mkdir -p "${DEST_DIR}"

REPO="https://github.com/buffedlizard55-lab/GEMSDOE32.git"
FILE="docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
EXPECTED_SHA="c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
TARGET="${DEST_DIR}/prior-h33-h33-2-b2-evaluation-only.tif"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to fetch the historical evaluation-only baseline" >&2
  exit 2
fi
git clone --quiet --depth 1 "${REPO}" "${TMP_DIR}/GEMSDOE32"
source_file="${TMP_DIR}/GEMSDOE32/${FILE}"
if [[ ! -f "${source_file}" ]]; then
  echo "Expected educational reference TIFF is absent from the public source repository" >&2
  exit 3
fi
actual_sha="$(sha256sum "${source_file}" | awk '{print $1}')"
if [[ "${actual_sha}" != "${EXPECTED_SHA}" ]]; then
  echo "Historical baseline hash mismatch: expected ${EXPECTED_SHA}, got ${actual_sha}" >&2
  exit 4
fi
cp "${source_file}" "${TARGET}"
cat > "${DEST_DIR}/baseline-receipt.json" <<EOF
{
  "role": "evaluation-only historical reference; not a GEMSDOE37 output",
  "source_repository": "${REPO}",
  "source_path": "${FILE}",
  "sha256": "${actual_sha}",
  "owner_reported_score_association": "0.2778 in the user's task list; not independently established by the public leaderboard",
  "generated_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
printf 'Fetched evaluation-only reference to %s (sha256 %s).\n' "${TARGET}" "${actual_sha}"
echo "Do not copy this raster to the GEMSDOE37 download site or submit it as a new result."
