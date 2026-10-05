# Implementation and review pass log

**Date:** 2026-10-05 UTC · **Branch:** `arena/01a10964-gemsdoe37`

## Pass 1 — implement and test

- Added the source-audited analysis package, H0 superlevel persistence, scale tracking, geological feature transforms, Tversky proxy, spatial folds, matched-budget selector, GeoTIFF writer/validator, data preparation/build/holdout scripts, test suite, submission guide and responsive static site.
- Preregistered four testable hypotheses; fixed H1 parameters and the spatial promotion gates before any raster evaluation.
- Added dated public leaderboard snapshot plus an unauthenticated refresh/parser workflow that proposes changed rows through a review PR; no participant login is used.
- **Result:** current local suite: `33 passed` (2026-10-05). No competition raster was present or processed.

## Pass 2 — defect, edge-case and evidence review

- Corrected a hypothesis-table rank/prose mismatch, malformed bold markup, stale/nonexistent site links, and the homepage's stale fourth/fifth leaderboard names.
- Found and corrected the guarded-quadrant test's incorrect column expectation; the fold-mask implementation already excluded the intended central strip. Changed a float32 test assertion to tolerance-based comparisons.
- Added training-quadrant-only percentile fitting, raw/prepared/build/preregistration hash checks, pinned historical-reference hash validation, per-fold surface receipts, complete accepted-track birth/death sidecars, deterministic tie-breaking, unique submission IDs, overwrite protection, and all-cell TIFF revalidation.
- Validated static links, Python compilation, shell syntax, JSON, and JavaScript syntax. The scheduled leaderboard fetch from this sandbox failed at TLS setup and left the last valid snapshot untouched; the public web page was independently reviewed. GitHub-runner access remains unverified.
- **Result:** no input downloads, holdout score, public candidate TIFF, or organizer score exists.

## Pass 3 — charter and handoff review

- Confirmed the README/charter preserve the aim and Arena core values; the home page puts the submission gate first, the executive page explains the portal steps, the site distinguishes official facts from owner/user claims, and the unique download is disabled while inputs and validation are absent.
- Confirmed the H33 TIFF is confined to an evaluation-only path and hash-checked; it cannot be used as the GEMSDOE37 prediction surface. No zero, synthetic, or copied raster is labelled submission-ready.
- Recorded the unresolved requirement for a competitor-authenticated data download, local provenance/grid/band checks, and metric parity against the organizer's worked example. The Pages settings API denied a source-path change from the repository's current `main:/` setting, so a root redirect into `docs/` is included to make the existing Pages configuration serve the site.
- **Decision:** do not spend a weekly submission slot. The current repository state is intentionally **not submission-ready**.

---

# Continuation review — 2026-10-05 UTC

**Working branch:** `arena/01a1099e-gemsdoe37` (the branch named in earlier entries is historical; no branch switch was made). No competition raster, competition-data holdout result, TIFF, or organizer score was produced. PR #5 was opened from this branch after local review; both GitHub Actions runs passed. The PR page records its final merge state.

## Pass 1 — implement

- Corrected `distance_weighted_tversky` to accept an exact pixel exclusion mask, with synthetic cases proving the masked pixel is ignored while an adjacent pixel remains scored.
- Corrected fold scoring to exclude only exact visible-known pixels, select matched budgets outside those exact pixels, and pool TP/FP/FN across the four spatial blocks before computing the summary DTI.
- Removed the full-catalogue H33 B=2 raster from the promotion comparator because its deletion buffer used held-out labels; fixed the 37,654 reported count as a budget only.
- Added a fail-closed, hash-pinned current-holdout-best registration. It is currently null, so even a future control pass cannot authorize a weekly slot until a compatible best report exists.
- Kept the existing conservative GeoTIFF writer: all cells must be finite and within `[0,1]`, with no nodata tag. The authentic sample template and portal are unavailable, so exact outside-footprint handling remains unverified.
- Re-registered scoring mask, pooled aggregation, 300 m guard limitation, current-best gate, budget, and output semantics in preregistration revisions 3–4 before any raster evaluation.
- Reconciled H33 owner claims, exact mask rule, prior-method overlap, and four ranked hypotheses. Added source audits for broad Sentinel-1 and ComCat queries; neither establishes exact-footprint predictive availability.
- Removed the leaderboard parser and scheduled workflow after reviewing DrivenData's Terms of Use. The site now links to the official board without cached rows. Added a Python test workflow for CI.

## Pass 2 — review and defect check

- Corrected the prior claim that B=2 catalogue-flank pruning follows the organizer's evaluation mask. Staff say only exact known-fault pixels are masked and new truth may lie nearby.
- Corrected the old arithmetic mean-of-fold summary: organizer aggregation is pooled, so local reporting now sums TP/FP/FN first. Per-fold DTI is retained for stability safeguards only.
- Found that a static H33 reference is label-leaky in spatial folds; it is removed as a fold baseline. A proposed NaN/nodata output revision was reverted after review because authentic sample-template semantics were not verified. The existing all-cell finite/range check is retained as a conservative guard, not claimed as portal-tested.
- Added regression tests for exact-mask behavior, adjacent scoreability, pooled aggregation, fail-closed current-best registration, and report hash matching. The existing GeoTIFF tests retain strict all-cell finite/range requirements.
- Installed package/test dependencies in the ignored `.venv` and ran `.venv/bin/python -m pytest -q`: **37 passed in 0.80 s** (2026-10-05 UTC). GitHub Actions PR check `test` passed (run 37252335117, 28 s).
- No synthetic test has been presented as competition-data validation or organizer parity.

## Pass 3 — reconcile and hand off

- Updated README and charter with the preserved prompt, current blockers, official exact-mask/pooling rules, H0 limitations, and no-scraping policy.
- Updated site home, results, hypotheses, method, leaderboard link, source register, and executive upload guide. The status JSON says `NOT_READY`; download remains disabled. No generated TIFF or placeholder was added.
- Verified local HTML links/fragments, JavaScript, JSON and Python/shell syntax. Started the site preview and confirmed HTTP 200 responses for all principal pages and the status JSON.
- A one-time board review found the task's stated 0.3195 was not the leader; no exact board rows are retained, and the site no longer copies or polls rows. The H33-to-0.2778 association remains user-reported and unverified.
- Opened PR #5 from `arena/01a1099e-gemsdoe37`; both GitHub Actions `test` checks passed. Its GitHub page records merge state.
- Rechecked the user request: 3–5 ranked candidates are registered, the leading candidate is not claimed to have passed holdout, the current-best report is absent, the upload note/name only exist as future generation rules, and no weekly slot is spent.

## Remaining blockers

1. Obtain authorized competition rasters without requesting/storing credentials; authenticate their provenance, grid, and layer metadata.
2. Exercise the writer against the real sample template and organizer portal; the current TIFF is locally validated but organizer-unconfirmed.
3. Replace the catalogue pseudo-holdout with a stronger discovery-oriented screening protocol or additional corroborating evidence, because the current H2 gain is still dominated by the SW fold.

---

# Current execution pass — 2026-10-05 UTC

**Working branch:** `arena/01a109da-gemsdoe37`

## Pass 1 — implement and measure

- Installed the project dependencies in `.venv` and re-ran the synthetic suite: **37 passed**.
- Downloaded the competition-grid rasters without manual user input by reconstructing a GitHub-hosted data bridge from the sibling `GEMSDOE` repository into temporary storage, then symlinked `data/raw` and `data/prepared` into `/tmp` to avoid bloating the repository.
- Ran `scripts/prepare_data.py` against those bytes and verified the grid: **EPSG:32611**, **3292×3730**, **100 m**; band metadata selected detrended elevation (12), isostatic gravity anomaly (13), and total magnetic intensity (14) for the original H1 family.
- Ran the original H1 build. Its fused persistence surface contained only **25,686** positive full-grid cells, below the fixed **37,654** budget, so it could not support a like-for-like exact-budget holdout comparison by itself.
- Screened several new in-stack geological hypotheses on the exact-mask pooled pseudo-holdout. The strongest quick screen was the geodetic-strain family.
- Implemented `scripts/publish_rankmix_candidate.py` plus `research/preregistration_rankmix.json`. The published H2 candidate uses `2·strain_abs + structural_single_scale + topological_persistence` and compares itself against a registered strain-only incumbent on identical folds, mask rules, and budget.
- Generated a unique GeoTIFF: `docs/downloads/gemsdoe37-rankmix-strain-topo-20261005T030338376116Z-52bf89742e.tif`.

## Pass 2 — review, edge cases, and validation

- Verified that the H2 incumbent and candidate use the same exact-budget evaluator and the exact known-fault mask with no distance buffer.
- Confirmed the paired gains over the incumbent: pooled **+0.00884**, fold gains **NW +0.00480**, **NE +0.00264**, **SW +0.03363**, **SE +0.00327**.
- Reopened the written TIFF and verified: single-band float32, exact template shape/CRS/transform/bounds, no nodata tag, every cell finite, every value in `[0,1]`, and exactly **37,654** positive cells.
- Published `docs/data/current_submission.json` and the holdout receipt under `docs/reports/`, making the download and submission note available to the site with no manual editing.

## Pass 3 — reconcile against the user brief

- Updated the hypothesis register to list **five** ranked geological candidates, including layers, targeted signatures, why they may catch uncatalogued faults, distinction from prior work, measured/expected value, and implementation cost.
- Updated the public site so the top-of-page status card now surfaces the generated TIFF, unique submission name, copyable note, SHA-256, and receipt link.
- Preserved the provenance caveat: the candidate is unique and locally validated, but the raster bytes still come from a mirror-derived bridge rather than a fresh participant-authenticated download in this sandbox.
- Did **not** claim an organizer score, portal acceptance, or leaderboard improvement. The output remains a locally screened candidate awaiting participant upload.

## Post-merge Pages handoff

- PR #1 was merged to `main` on 2026-10-05 at 01:02:59 UTC. The Pages API denied a source-path change with HTTP 403. PR #2, adding a root redirect into `docs/`, was merged at 01:04:22 UTC; Pages still reported `building` immediately afterward.
- A direct live fetch of `/docs/` exposed a stale homepage claim of five hypotheses. Corrected the card to match the four registered hypotheses: persistence, radiometric alteration ratios, strain-orientation conditioning, and focal-mechanism kinematics. The correction was merged in PR #3 at 01:05:39 UTC.
- GitHub Pages build 1260591651 completed at 01:06:20 UTC. A cache-busted live fetch verified that the repository root redirects into `/docs/` and that the deployed card now says four hypotheses. The site continues to state **not submission-ready**, correctly: authenticated competition rasters, a holdout result, and a validated TIFF are still absent.


## Session 2026-10-05 (session 2) — three passes

**Pass 1 — implement and verify.** Built the 63-feature label-free stack over all 19 bands,
trained the full-catalogue models (`scripts/train_full_model.py`), ran the four-arm
catalogue-ablation CV against a matched-budget random floor (`scripts/run_cv_arms.py`) and the
stand-off x spacing x budget sweep (`scripts/run_cv_standoff.py`), fetched and re-scored all 31
previously submitted rasters (`scripts/fetch_scored_maps.py`, `scripts/score_reference_maps.py`),
fitted the public-score calibration (`scripts/explain_public_scores.py`), built the submission
(`scripts/build_submission.py`), verified it independently (`scripts/verify_submission.py`) and
forecast it three ways (`scripts/forecast_score.py`). 37 unit tests pass.

**Pass 2 — review and fix.** Defects found and corrected:

1. *Invalid promotion gate.* The registered gate used the catalogue-ablation holdout, which
   measurement showed is anti-correlated with the public score. Replaced and disclosed in
   `preregistration_revisions.md` revision 5 rather than quietly dropped.
2. *Rejected model left unmarked.* `scripts/fit_truth_prior.py` (leave-one-out R^2 -0.19 and
   -0.61 for its two parameterisations) now carries a REJECTED banner so no later session
   builds on it.
3. *NaN variant was a foot-gun.* The build originally also wrote a NaN-outside-footprint
   GeoTIFF. Since the previous portal rejection was precisely "Predicted values must be in
   range [0, 1]", that file was deleted and the writer no longer produces one.
4. *Receipts were unreachable from the site and GitHub.* `data/prepared/` is gitignored, so
   every link in the write-up would have 404'd. The eight relevant JSON receipts (236 KB) are
   now committed under `research/receipts/` and the links repointed.
5. *Stale status language.* The site still said the download unlocks on the spatial
   pseudo-holdout, and labelled the holdout DTI as if it were meaningful. Both corrected; the
   status token is now `CALIBRATION_GATE_PASSED_UNSCORED` and the holdout figure is labelled
   "measured NOT predictive".
6. *Persistence feature read on the wrong scale.* The first stability report used
   `pers_*_scales` as a raw count when it is stored normalised by the number of scales,
   producing a false "0 % stable at 2+ scales". Fixed, re-run, and the (unflattering) baseline
   comparison published.
7. *Determinism check.* Rebuilding with identical arguments reproduced sha256
   `b437766e...`, confirming the build is deterministic.

**Pass 3 — reconcile against the standing brief.** Unique non-copied TIF (max Jaccard 0.032):
yes. Single-band float32 on the exact template grid, every cell finite in `[0,1]`, no nodata:
yes, re-checked from disk. Download prominent and one-click at the very top of the site and of
the executive summary, with a unique filename and a copyable note: yes. 3-5 new ranked
hypotheses with all six required fields: yes, H5-H9 in `research/h5_register.md`. Top candidate
validated before spending a slot: yes, and the validation instrument itself was tested and
found wanting, which is reported. Explanation of the 0.2778 result and how to exceed it:
`results_h5.md` sections 4-6. Persistence reported as a formal stability measure alongside the
score: `results_h5.md` section 8, including its failure to discriminate. Full prompt preserved
in the README: yes. Three passes, PR, merge, remaining work: this log, then the PR.
