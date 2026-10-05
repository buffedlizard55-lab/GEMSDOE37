# Data directory policy

Downloaded competition rasters, mirror inputs, derived masks, evaluation-only historical rasters, and outputs belong here but are ignored by Git. See `data_sources.json` and `research/sources.md` for provenance warnings. Do not commit data files.

- `raw/` — user-provided public mirror inputs; not official-authenticated until cross-checked.
- `prepared/` — masks, manifests, feature scores, and holdout receipts.
- `reference/` — prior raster(s) used strictly as educational/evaluation baselines; never offer as a GEMSDOE37 candidate.
