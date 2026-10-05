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

**Working branch:** `arena/01a1099e-gemsdoe37` (the branch named in earlier entries is historical; no branch switch was made). No competition raster, competition-data holdout result, TIFF, or organizer score was produced. PR #5 was opened from this branch after local review; GitHub Actions passed, and merge is pending.

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
- Opened PR #5 from `arena/01a1099e-gemsdoe37`; its GitHub Actions `test` check passed. Merge remains pending.
- Rechecked the user request: 3–5 ranked candidates are registered, the leading candidate is not claimed to have passed holdout, the current-best report is absent, the upload note/name only exist as future generation rules, and no weekly slot is spent.

## Remaining blockers

1. Obtain authorized competition rasters without requesting/storing credentials; authenticate their provenance, grid, and layer metadata.
2. Establish a same-input, same-protocol current holdout-best report before H1 scoring; then run the registered pooled spatial holdout at matched budget.
3. Exercise the writer against the real sample template and organizer portal; no file is currently eligible for download/upload.
4. Merge PR #5 only after reviewing the passing check and confirming the target branch/merge state.

## Post-merge Pages handoff

- PR #1 was merged to `main` on 2026-10-05 at 01:02:59 UTC. The Pages API denied a source-path change with HTTP 403. PR #2, adding a root redirect into `docs/`, was merged at 01:04:22 UTC; Pages still reported `building` immediately afterward.
- A direct live fetch of `/docs/` exposed a stale homepage claim of five hypotheses. Corrected the card to match the four registered hypotheses: persistence, radiometric alteration ratios, strain-orientation conditioning, and focal-mechanism kinematics. The correction was merged in PR #3 at 01:05:39 UTC.
- GitHub Pages build 1260591651 completed at 01:06:20 UTC. A cache-busted live fetch verified that the repository root redirects into `/docs/` and that the deployed card now says four hypotheses. The site continues to state **not submission-ready**, correctly: authenticated competition rasters, a holdout result, and a validated TIFF are still absent.
