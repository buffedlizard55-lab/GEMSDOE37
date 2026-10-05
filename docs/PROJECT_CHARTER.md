# GEMSDOE37 project charter (standing prompt)

**Read this charter and [`README.md`](../README.md) at the start of each project session.** This document preserves the user’s requirements, the official scoring correction, and current evidence limits. Do not silently promote owner/user reports into organizer facts.

## Objective and values

Develop a scientifically defensible, reproducible system for the U.S. Department of Energy / National Laboratory of the Rockies **Geologic Enhanced Mapping System (GEMS) Prize Challenge**, DrivenData competition 306. The challenge concerns faults in the GeoDAWN study area and their relevance to geothermal resources. Long-term goal: improve the probability of a strong final result—not merely produce a plausible-looking map or optimize one public score.

- **Maximize P(Win):** choose only experiments with a defensible chance of improving the best comparable spatial holdout; do not spend scarce weekly submissions on untested guesses.
- **Own the Outcome:** own research, code, source verification, data provenance, testing, delivery, and correction. Report blockers and failures rather than hiding them.

## Highest-priority deliverable

When the gates below pass, produce a **new, independently generated, competition-format single-band GeoTIFF** from this repository's method and a recorded input manifest. Make the eligible download, unique filename, submission name/note, validation receipt, evidence status, and concise upload steps prominent on the site.

Never call a template, zero baseline, synthetic fixture, unvalidated candidate, or copied prior entry a ready-to-submit prediction. Renaming prior pixels does not make a unique scientific submission. If there is no eligible candidate, the site must state **not submission-ready** and keep download disabled.

## Scientific and validation requirements

1. Before new implementation, register **3–5 distinct, testable geological hypotheses**. Each must identify layers, physical signature/transform, why it could add geometry absent from USGS/INGENIOUS, difference from inspected prior work, expected DTI direction or a clearly justified inability to forecast numerically, cost, and free official source/availability if external data is needed. Link evidence and disclose the novelty boundary.
2. Validate the leading candidate on spatially separated blocks at a matched pixel budget **against the current local holdout-best baseline** before using a weekly submission slot. A compatible, hash-pinned local current-best report is currently not registered; the gate must fail closed until it exists.
3. Treat public catalogue holdouts only as **catalogue pseudo-holdouts**. They test recovery of withheld mapped faults, not discovery of expert-only hidden geometry. Do not claim they validate new faults, private performance, or final-round results.
4. Keep the official scoring mask exact. DrivenData staff say only the provided known-fault pixels are excluded; there is **no catalogue-distance buffer**. Nearby unmasked predictions are scored normally, and new/corrected/continued/splayed truth may occur within 300 m of a known trace. The 300 m boundary guard in this repository is a validation-design choice, not an organizer rule.
5. Match official aggregation: the public score pools evaluation pixels into a single Tversky calculation; the private score uses the same aggregation; final re-evaluation covers the full GeoDAWN area. Pool TP/FP/FN across non-overlapping holdout blocks before reporting one DTI; mean fold DTI is descriptive only.
6. Give special consideration to H0 persistence, but explain it precisely. A persistence bar describes the birth/death of a connected component in the superlevel sets of a fixed scalar field. It does **not** prove line geometry, geology, fault identity, or geothermal potential. The classical stability theorem is conditional on a stated function-norm perturbation bound; the current epsilon is a preregistered assumption, not an empirically measured error bound. Greedy matching of peaks across Gaussian scales is heuristic, not a formal multiparameter-persistence theorem. The current code has no explicit elongation/line-continuity test.
7. Write a TIFF only from identified inputs and validate the exact competition example grid: dimensions, CRS, transform and resolution; single-band float32; finite `[0,1]` values for every stored cell; no finite negative sentinel or nodata tag under the current conservative local policy. Outside-footprint encoding has not been verified against an authenticated sample or portal. Do not claim the format is accepted until a generated candidate is reopened and the organizer portal accepts it.
8. Keep a source-linked site and executive upload guide. Cite current organizer instructions and disclose date/evidence status. The official leaderboard is dynamic; only link to it unless written permission or an authorized API permits an automated feed.
9. Keep all external data free/official where possible; verify actual availability, overlap with the exact target footprint, checksums, CRS, quality, license, and provenance before calling a source viable. Competition access remains login-gated here; user-supplied mirrors are not authenticated copies.
10. Complete three passes for substantial work: **(1)** implement and test; **(2)** review edge cases, assumptions, source claims, and failures; **(3)** reconcile the final change against this charter. Keep the evidence in `research/review_log.md`.

## Leaderboard and source-access policy

The user asked for the current board and an easy source-linked review. A one-time review on 2026-10-05 found that the leader was above the task's stated 0.3195; the official page does not expose filenames, so it cannot attribute a row to H33. The public board changes. DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) prohibit robots/spiders and automated monitoring/copying, and also prohibit manual monitoring/copying without prior written consent. Therefore the old scheduled scraper/workflow is removed. The site links directly to the [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) and does not cache score rows. An authorized API or written permission would be required to resume an automated feed.

The official data tab redirects to participant login in this environment. Do not seek or store credentials. User-provided Dropbox URLs may be inspected only with explicit mirror provenance and hashes; never call them authenticated organizer data without a checksum/metadata match.

## Rules, AI disclosure, and participant responsibility

The [official NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) describes up to three weekly submissions, a single final selection used across both prize rounds, and required AI-use disclosure. Recheck the current rules before upload. This repository cannot certify the registered competitor's eligibility or author their legal attestation. Any final competition narrative must truthfully describe AI-assisted research/coding and be checked by the participant.

## Core manual-review sources

- [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem, DTI, submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/)
- [Exact known-fault mask clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)
- [Definition of new fault](https://community.drivendata.org/t/where-do-you-draw-the-line/11536/2)
- [Pooled score aggregation clarification](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)
- [Official data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official rules PDF, NLR report 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS compilation, GDR 1391](https://gdr.openei.org/submissions/1391)
- [Persistence diagram stability theorem, Cohen-Steiner et al. (2007)](https://doi.org/10.1007/s00454-006-1276-5)

## Current dated status

- One-time official-board review: the user's stated 0.3195 was not the highest visible score. See official page directly for current values; GEMSDOE37 does not mirror rows.
- H33-2-B2's 0.2778 filename/score association is user-reported and unverified. The owner-side report describes a 0.2747 projection and unscored proxy. Exact official masking means the B=2 neighbourhood deletion is not an organizer rule.
- The four hypotheses are recorded in [`research/hypotheses.md`](../research/hypotheses.md); only H1 has implementation code, and it has not run on competition data. H2–H4 are conditional and unimplemented.
- No authenticated competition raster, local current-holdout-best report, completed spatial holdout, validated TIFF, portal receipt, or GEMSDOE37 organizer score exists. Do not claim readiness or improvement.
- Python dependencies were installed in an ignored local `.venv`; the synthetic suite passed **37 tests** on 2026-10-05 UTC. The GitHub Actions workflow is added but has not yet run. No official-raster experiment or portal acceptance was tested.
