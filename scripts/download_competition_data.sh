#!/usr/bin/env bash
# Download the user-provided public mirrors, not the login-protected DrivenData data tab.
# Keep downloaded competition files out of Git; compare their hashes/metadata to official
# participant data before treating them as canonical competition inputs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/data_sources.json"
OUT_DIR="${ROOT}/data/raw"
mkdir -p "${OUT_DIR}"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Missing source manifest: ${MANIFEST}" >&2
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to download the public mirror files." >&2
  exit 2
fi

while IFS=$'\t' read -r name filename url; do
  [[ -n "${name}" ]] || continue
  target="${OUT_DIR}/${filename}"
  partial="${target}.part"
  echo "Downloading ${name} (${filename}) from the user-provided public mirror..."
  rm -f "${partial}"
  curl --fail --location --retry 3 --retry-delay 2 --retry-all-errors \
    --connect-timeout 30 --max-time 1800 --silent --show-error \
    "${url}" --output "${partial}"
  if [[ ! -s "${partial}" ]]; then
    echo "Downloaded file is empty: ${filename}" >&2
    rm -f "${partial}"
    exit 3
  fi
  magic="$(od -An -N4 -t x1 "${partial}" | tr -d ' \n')"
  case "${magic}" in
    49492a00|4d4d002a|49492b00|4d4d002b) ;;
    *)
      echo "${filename} is not a TIFF/BigTIFF (magic=${magic}); refusing to accept an HTML/login/error page." >&2
      rm -f "${partial}"
      exit 4
      ;;
  esac
  mv "${partial}" "${target}"
  printf '  saved %s bytes to %s\n' "$(wc -c < "${target}" | tr -d ' ')" "${target}"
done < <(
  python - "${MANIFEST}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    manifest = json.load(stream)
for name, item in manifest["files"].items():
    print(f"{name}\t{item['filename']}\t{item['url']}")
PY
)

cat <<'NOTICE'
NOTICE: these files came from the user-provided Dropbox mirrors in the task prompt.
They have not been authenticated against the DrivenData data tab. Run
`python scripts/prepare_data.py` to inspect and cross-check their raster metadata.
Do not use them as official inputs or submit a prediction until provenance and holdout
validation have been reviewed.
NOTICE
