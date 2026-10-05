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
## Revision 6 — 2026-10-05 (after fold evaluation; disclosed as such)

This revision is made **after** fold scores were observed, and is disclosed as a protocol
change rather than presented as a prior registration. It is recorded because continuing to
use the previous gate would have been knowingly wrong.

**What was learned.** All 31 previously submitted rasters whose public DTI this project holds
were re-scored on the four-fold catalogue-ablation holdout
(`scripts/score_reference_maps.py`, receipt `research/receipts/reference_holdout.json`). The rank
correlation between holdout DTI and public DTI is **−0.271** over all 31 maps and **−0.103**
over the 28 maps whose construction did not leak the held-out folds. Adding holdout DTI to a
regression of `log(public DTI)` on `log(mass)` leaves the leave-one-out R² unchanged at 0.169.
The holdout carries no usable information about the competition objective, and what little
signal it has points the wrong way: its truth is withheld *mapped* catalogue geometry, so it
rewards maps that concentrate near the catalogue, which the public scores punish.

**What changed.**

- The promotion gate "beat the registered current holdout best at matched budget on the
  catalogue-ablation holdout" is **retired**. It is replaced by a gate against the 31-map
  public-score calibration (`scripts/explain_public_scores.py`, receipt
  `research/receipts/public_score_model.json`): a build may be published only if its measured
  descriptors place it at or above the best recorded public score under the pessimistic
  physical recall model, with all predictors inside the observed range of the calibration set.
- The catalogue-ablation holdout is retained for a narrower, defensible purpose: **comparing
  ranking families against a matched-budget random floor**. It separated the arms cleanly and
  by large margins (0.1840 / 0.1670 / 0.0646 / 0.0529 / 0.0432), and its random arm reproduced
  the independently derived analytic floor, so it is sound as a relative instrument even though
  its absolute level does not transfer.
- Catalogue-geometry features (distance to catalogue, fault density at 2/5/10 km, distance to
  nearest fault tip, along-strike continuation score) are **removed from the shipped ranking**.
  Measured: they drop pooled holdout DTI from 0.1670 to 0.0529, i.e. below the random floor.
- Standalone H0 persistence is **withdrawn as a detector**. Measured: 0.0432 pooled, below the
  random floor of 0.0646. It is retained as three label-free features among 63 and as a
  reported stability measure, which is the only claim the evidence supports.
- Budget and stand-off for the shipped build were selected from the public-score calibration
  and the inverted metric, not from the holdout: stand-off 3.0 px, spacing 2.9 px,
  budget 26,000 px.

**What did not change.** The metric implementation, the exact known-fault pixel mask with no
proximity buffer, pooled TP/FP/FN aggregation, binary emission, the fold geometry, and the
GeoTIFF format contract are all unchanged. The shipped ranking is the same `offcat` arm that
won the holdout; only its geometry parameters were re-chosen.

**Honest status.** Because the one internal protocol capable of validating *ranking quality*
has been shown to be invalid, the shipped build's ranking is unvalidated. The budget and
geometry are validated against real public scores; the ranking is not. This is stated on the
site and in `research/results_h5.md` §7 rather than being hidden behind a passing gate.
