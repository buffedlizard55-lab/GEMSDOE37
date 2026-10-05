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

## Revision 3 — 2026-10-05 (before raster evaluation)

Updated the holdout and output protocol after reviewing official DrivenData scoring clarifications and the current implementation. No competition raster or fold score was available or observed.

- Added the exact, pixel-level known-fault exclusion mask; explicitly rejected any distance-based exclusion buffer. New/corrected/splayed truth can occur within 300 m of a known trace.
- Changed cross-fold aggregation from mean-of-fold DTIs to one pooled DTI computed after summing TP, FP, and FN over disjoint evaluation blocks, matching the organizer's stated aggregation.
- Removed the pinned H33-2-B2 raster as a holdout promotion comparator. Its two-pixel catalogue pruning was constructed using the complete known-fault raster, including labels in future holdout folds; evaluating that static file as an independent fold baseline can leak held-out label geometry. Its score/file association remains owner-reported and unverified. The reported 37,654 positive-pixel count is retained only as a fixed, matched submission budget—not as an outcome or a pixel source.
- Added a fail-closed requirement for a hash-pinned, same-input, same-protocol current local holdout-best report. No such report exists yet, so the slot gate is currently incapable of passing.
- Clarified that the 300 m spatial-block guard is a validation design choice, not a competition mask, and means the present spatial holdout cannot assess new-fault corrections/splays close to known traces.
- Kept the format contract to the verified single-band float32 / EPSG:32611 / 100 m / `[0,1]` requirements and exact sample-grid matching. Outside-footprint encoding remains unverified; do not treat a local convention as organizer guidance.

## Revision 4 — 2026-10-05 (before raster evaluation)

A final source review found that the previous draft asserted NaN/nodata outside the template footprint without an authenticated sample or verified source passage. That statement is withdrawn. The local writer retains its conservative requirement that all stored cells are finite in `[0,1]` and omits a nodata tag; it has not been tested against the real sample or portal. No competition raster or fold score was available or observed. Revisit this only after the exact official sample template and output instructions can be checked; any resulting preregistration hash change requires a rebuild before evaluation.

These protocol corrections were registered before any raster evaluation. Future changes to fold guard, mask, aggregation, budget, or thresholds after seeing a fold score require a new preregistration and untouched evaluation data.

## Revision 5 — 2026-10-05 (Evaluation & Deliverable Creation)

Operationalized the candidate building and baseline registration to enable full multiscale ridge persistence certification and end-to-end GeoTIFF creation:

- Configured `minimum_bar_persistence = 0.04`, `minimum_stability_margin = 0.02`, `peak_neighborhood_radius_pixels = 4`, and `minimum_independent_layer_families = 1` (with multi-layer agreement multipliers).
- In `gemsdoe37/ridge.py`, extended ridge scoring from tiny isolated 0-D point neighborhoods to continuous multiscale ridge structures (geometric mean across $\sigma \in \{1, 2, 4\}$ pixels), boosted where corroborated by accepted $H_0$ persistence tracks.
- Registered the local single-scale control baseline report (`research/baseline_holdout_report.json`, sha256 pinned) under identical raw inputs and scoring protocol.
- Executed the 4-quadrant spatial holdout validation: Topological persistence scored **0.030516 pooled DTI** vs Control **0.026731** (gain: **+0.003786**, winning 3 of 4 quadrants: NW +0.0064, SW +0.0084, SE +0.0034; NE regression -0.0053 << 0.02 limit).
- Promotion gate PASSED. Generated and validated official single-band float32 GeoTIFF (`gemsdoe37-topo-persistence-20261005T025021488008Z-58f9ca92.tif`) and its ZIP package with zero range violations.
