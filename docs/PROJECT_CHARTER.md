# GEMSDOE37 project charter (standing prompt)

**Read this document at the start of every project session.** It is the durable working brief distilled from the original user request; the source URLs and user-supplied score ledger are kept in the linked research documents. Do not silently treat owner-site claims as official facts.

## Objective

Build a distinct and scientifically defensible system for the U.S. Department of Energy / National Laboratory of the Rockies **Geologic Enhanced Mapping System (GEMS) Prize Challenge**, DrivenData competition 306. The competition asks for a map of geological-fault predictions over the GeoDAWN study area, relevant to geothermal resource discovery. The long-term goal is to maximize the chance of a strong final prize-round result, not merely to produce a visually plausible raster or optimize a single leaderboard snapshot.

## Highest-priority deliverable

Produce a **new, independently generated, competition-format single-band GeoTIFF** with values in `[0,1]`, and make an eligible file easy to download from the very beginning of the site. The home page must display the unique filename, a short note for DrivenData's optional comment field, validation receipt, evidence status, and a prominent download link. Add a separate executive-summary/how-to-submit page that explains the portal steps exactly.

Never describe a template, zero baseline, synthetic fixture, unvalidated candidate, or copied prior entry as a ready-to-submit prediction. A previous raster may only be used for education or as a clearly identified evaluation baseline; it must not be delivered as GEMSDOE37's generated candidate. A filename change does not make copied pixels a unique scientific submission.

## Scientific and validation requirements

1. Read the current competition overview, problem description, rules, metric, and source-data documentation before modeling. Record URLs and access dates and link them for manual audit.
2. Keep a clear distinction between official fact, measured local result, user/team-reported result, model projection, and hypothesis. Flag disagreements and broken or inaccessible sources.
3. Before implementation, formulate **3–5 genuinely distinct, testable geological hypotheses**. Each must name the specific input layer(s), physical signal/transform, reason it can locate a fault missing from the USGS/INGENIOUS catalogue, difference from prior work, expected DTI effect, cost, and external data/license/availability if applicable.
4. Rank hypotheses by expected improvement and implementation cost. Validate the leading idea on spatially blocked holdouts against the current holdout-best baseline at matched prediction budget **before** spending a weekly submission slot. Do not call a catalogue-only proxy holdout proof of discovery of unmapped faults.
5. Give special consideration to topological persistence of curvature/ridge-response surfaces from DEM and potential-field layers. Report the filtration, component/ridge birth and death values, persistence lifetime, smoothing scales observed, cross-scale tracking rule, and a clearly stated perturbation bound. Persistence stability is a theorem about diagrams of specified functions; it is not proof that a feature is a geological fault. A heuristic track over Gaussian smoothing scales must not be mislabeled as a formal multiparameter persistence guarantee.
6. Analyze the distance-weighted Tversky objective: maximize distance-weighted truth coverage while controlling unnecessary prediction mass. Compare changes by paired spatial folds and record per-fold results, budget, code version, and input hashes. Do not infer that a public score or prior high score will generalize to private or expert-expanded labels.
7. Generate a TIFF only from identified, verified inputs. Reopen and independently validate CRS, shape, transform, pixel size, one band, float32, no invalid in-footprint cells, and `[0,1]` values. Keep a receipt and content hash. Resolve the historical portal error `Predicted values must be in range [0, 1]` by testing actual stored values and nodata handling, not by guessing.
8. Keep a current feed of the official public leaderboard and important verified source updates so that users do not need to manually check each source. Label each snapshot with retrieval time and source; a stale snapshot must never appear live.

## Data-access and provenance rules

The official DrivenData data tab requires an authenticated participant account. This session has no DrivenData login and the data page was observed redirecting to login. Do not seek, store, or ask for passwords, tokens, or account credentials. The user supplied public Dropbox mirror URLs for an example submission, existing-fault raster, feature raster, a PDF, and DEM-link documentation. Those mirrors are **not an official authenticated download**; before use, record exact file hashes and raster metadata, label their provenance, and do not claim organizer provenance without a comparison to official data/checksums. Competition inputs, DEM tiles, model checkpoints, and other large datasets belong outside Git.

External data is allowed by the competition only subject to the official rules and applicable licenses. Prefer free official sources (e.g. USGS, DOE/NLR, the Geothermal Data Repository). Name any additional data source and verify its actual availability and license before calling a hypothesis viable. Do not use a source that cannot be obtained and validated in this environment without clearly marking the experiment blocked.

## Site and handoff

Create a clean, responsive, accessible GitHub Pages site. Put the submission action first; follow it with a brief, a precise explanation of the method, validation status, source links, irregularities, and a concise leaderboard/research feed. Provide the exact DrivenData upload workflow and note text. Maintain a limitations / next-steps list and be explicit when the data, source access, CPU/GPU, or eligibility rules block a claim.

The official rules say generative-AI use is permitted but requires disclosure in the narrative and place responsibility for accuracy and authorship on the competitor. Any final competition narrative must disclose how AI-assisted research/coding was used and must be checked by the registered competitor. Do not certify a competitor's eligibility on their behalf.

## Required values and review loop

> **Maximize P(Win)**: “In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win).”
>
> **Own the Outcome**: “We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve.”

For each substantial change, do three passes: **(1)** implement and test; **(2)** review for defects, edge cases, source errors, and unsupported assumptions; **(3)** re-check the full charter and improve remaining issues. Record the checks and any unresolved blocker. Work autonomously; do not ask for manual data entry when the public source can be checked automatically. Never invent a fact to make the deliverable look complete.

## Current dated facts and caveats

- Official problem description: DTI with `alpha=0.2`, `beta=0.8`, a 300 m triangular distance kernel; submission is a single-band float32 raster on the 100 m EPSG:32611 training grid with predictions in `[0,1]`.
- Official rules PDF: competition allows up to three prediction submissions per week; a single selected submission is used across the two award rounds; generative-AI use must be described in the submission narrative.
- Official public leaderboard snapshot fetched 2026-10-05 UTC: top listed score **0.3262**, ahead of the user-stated 0.3195. The user's historical GEMSDOE site ledger lists an H33 file at 0.2778, and the current official leaderboard includes a participant at 0.2778, but the public leaderboard does not expose the submission filename; the exact file-score attribution remains unverified.
- This repository initially contained only a minimal README, with no data, pipeline, holdout set, tests, TIFF, or website. No valid GEMSDOE37 prediction or holdout improvement can be assumed from prior sibling repositories.

## Manual-review sources

- [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About and scientific context](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Data tab (account required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official rules PDF, NLR report 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS compilation, Geothermal Data Repository](https://gdr.openei.org/submissions/1391)
- [Stability of Persistence Diagrams, Cohen-Steiner, Edelsbrunner & Harer (2007)](https://doi.org/10.1007/s00454-006-1276-5)
