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
- Recorded the unresolved requirement for a competitor-authenticated data download, local provenance/grid/band checks, metric parity against the organizer's worked example, a passing spatial holdout, and a GitHub Pages source change from the repository's current `main:/` setting to `main:/docs`.
- **Decision:** do not spend a weekly submission slot. The current repository state is intentionally **not submission-ready**.
