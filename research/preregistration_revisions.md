# H1 preregistration revision log

## Initial registration — 2026-10-05T00:25:03Z

The initial H1 detector and promotion margins were recorded before any raster evaluation. See [`preregistration.json`](preregistration.json).

## Revision 1 — 2026-10-05T00:41:46Z (before raster evaluation)

The written protocol was made more operational and reproducible:

- Explicitly recorded the DTI parameters used by the fold scorer: α=0.2, β=0.8, 300 m distance radius, 100 m pixel spacing, and the deterministic 1e-8 denominator epsilon.
- Fixed the robust input-band and response-percentile fit scope to the three non-held-out full quadrants in each fold. Feature values remain available across the complete grid as unlabeled prediction covariates; no catalogue label value enters normalization or score construction.
- Required accepted H0-track observations (birth, death, lifetime, representative row/column and smoothing scale) to be written to hash-pinned gzip JSONL sidecars, rather than reporting only aggregate track counts.

## Revision 2 — 2026-10-05T01:00:43Z (before raster evaluation)

The implementation defaults were explicitly registered so the scoring surface is fully specified:

- Recorded input and response robust percentiles (2/98 and 50/99.5), clipping range, mask-aware Gaussian support floor (0.95), and kernel truncation (3σ).
- Recorded how constant response fields are handled, the per-scale maximum, the persistence track-strength formula, layer-family mean fusion, and the fixed three-family agreement multiplier.
- Recorded deterministic exact-budget selection: descending positive score, row-major flat-index tie break, binary 1/0 emission.
- Recorded a 250,000-bar-per-scale memory guard; exceeding it aborts the run rather than silently truncating the persistence diagram.

**No competition raster, score, holdout result, TIFF, or leaderboard outcome was observed for either revision.** Persistence scales, cutoff, ε, matching radius, minimum scales, layer agreement, matched-budget definition, fold geometry, and numerical promotion margins were not tuned or changed. Any later change made after viewing a fold score requires a new preregistration and a genuinely untouched evaluation split.
