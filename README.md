# GEMSDOE37 — GEMS Prize research and submission system

> **Every work session begins by reading this README and [`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md).** The charter preserves the standing goals, values, source constraints, and review requirements.

## Standing brief (preserved from the user's request)

> Review the repository and continue the project toward a scientifically defensible, **unique** GEMS competition GeoTIFF submission. Explain the reported H33 result and the current official leaderboard without conflating owner-reported artifacts with organizer scores. Before implementation, register and rank 3–5 distinct geological hypotheses; validate the leading candidate against the current spatial-holdout best at matched budget before using a weekly submission slot. Keep topological persistence and its limits scientifically precise. Maintain the source-linked research/site, make an eligible download and exact submission instructions prominent, and ensure values meet `[0,1]`. Also preserve the full prompt in this README, complete three implementation/review/reconciliation passes, work autonomously, flag irregularities, and open a PR and merge to `main` only after verification.
>
> Additional standing constraints: never copy/relabel a previous submission or publish a placeholder as ready; verify source claims and link them for review; for each hypothesis name layers, physical signature, why it may identify faults absent from USGS/INGENIOUS, distinction from prior work, expected DTI direction, implementation cost, and any free official data source plus verified availability; keep the site download, unique submission name/note, and executive upload guide prominent; preserve the core values **“Maximize P(Win)”** and **“Own the Outcome.”**

## Mission and values

Build an auditable, reproducible system to test geological fault hypotheses over the GeoDAWN region and generate a competition-format GeoTIFF only when inputs, holdout, baseline, and format gates pass. The current checkout has a deterministic H0-persistence candidate implementation, but no authenticated competition data or measured result.

- **Maximize P(Win):** use a scarce weekly slot only for a candidate that beats a compatible, matched-budget current holdout best. Do not submit exploratory ideas as lottery tickets.
- **Own the Outcome:** report failures and irregularities; distinguish official facts, measured results, owner/user claims, and hypotheses.

## Non-negotiable research and submission rules

1. **Unique pixels, not a new filename.** Generate any future TIFF from this repository's method and recorded input manifest. Prior artifacts are educational evidence only; never copy their prediction pixels into GEMSDOE37.
2. **No invented results.** Label every score by evidence class and date. A public score without a linked organizer receipt does not authenticate a named file. Never call a proxy or owner projection an organizer score.
3. **Preregister 3–5 distinct hypotheses.** State layers, physical signatures, novelty boundary, expected DTI direction (numeric only if supported), cost, source, and coverage status before implementing new arms. See [`research/hypotheses.md`](research/hypotheses.md).
4. **Holdout before slot.** Compare H1 against the same-budget single-scale control and a separately registered, hash-pinned local current holdout-best report on identical inputs/protocol. The current-best report is not registered, so the promotion gate fails closed. The catalogue pseudo-holdout is not expert-only truth.
5. **Official mask and aggregation.** Only exact supplied known-fault pixels are masked; no proximity buffer applies. New truth may occur within 300 m of a known trace. The public/private DTI is pooled over all evaluation pixels, so cross-fold summaries pool TP/FP/FN rather than averaging fold scores. See official links in [`research/sources.md`](research/sources.md).
6. **Topological precision.** H0 persistence records connected-component births/deaths in superlevel sets of fixed scalar response fields. In this code it tracks maxima and paints small peak neighborhoods; it has no explicit elongation/line-continuity test. The classical diagram stability theorem is conditional on a function-norm bound and does not establish geology; greedy cross-scale peak matching is heuristic, not multiparameter persistence.
7. **Safe GeoTIFF.** Reopen and validate exact template dimensions, CRS, affine transform and resolution; require one-band float32 and finite `[0,1]` values for every stored cell, with no nodata tag. This is a conservative local writer policy; outside-footprint encoding has not been verified against an authenticated competition template or portal.
8. **Prominent handoff.** The site puts the candidate download, unique filename/name/note, evidence status, and exact upload guide first. When no candidate passes, the download remains disabled and the page says **not submission-ready**.
9. **Three passes.** Implement/test; review for defects, edge cases, source errors, and assumptions; reconcile against this brief and charter. Keep the pass log in [`research/review_log.md`](research/review_log.md).
10. **No unauthorized leaderboard polling.** The site links directly to the official leaderboard but does not cache its rows or scrape it. DrivenData's Terms of Use prohibit automated monitoring/copying and manual monitoring/copying without written consent. No authorized API or written permission is documented here.

## Current status (2026-10-05 UTC)

- One-time review of the official board found the task's stated 0.3195 was not the highest public entry at that time. The dynamic board is authoritative and does not expose TIFF filenames; see the [official page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) and the evidence limits in [`research/score_analysis.md`](research/score_analysis.md). GEMSDOE37 does not maintain a score-row cache.
- The user-supplied H33-2-B2 association with 0.2778 is **unverified**. The GEMSDOE32 owner report described a 0.2747 projection and an unscored four-fold proxy. The official exact mask does not require a 200 m buffer; nearby predictions are scored normally.
- H1 H0-persistence code is implemented and preregistered but **unrun**. H2–H4 are proposed; external data coverage is conditional. No official raster, spatial-holdout result, registered current-best report, validated TIFF, organizer score, or slot-eligible candidate exists.
- Official data access requires a participant login. User-provided Dropbox mirrors are not authenticated organizer data and were not downloaded here. No credentials were requested or stored.
- Python dependencies were initially absent, then installed in an ignored isolated `.venv` for review. The synthetic suite passes (**37 passed**, 2026-10-05 UTC). GitHub Actions has not yet run; no actual competition raster, GeoTIFF, portal acceptance, or organizer score was produced.

## Site and source links

- [Project charter](docs/PROJECT_CHARTER.md) · [ranked hypotheses](research/hypotheses.md) · [score analysis](research/score_analysis.md)
- [Prior-results ledger](research/prior_results.md) · [source/provenance register](research/sources.md) · [preregistration](research/preregistration.json)
- [Site home](docs/index.html) · [executive upload guide](docs/executive-summary.html) · [leaderboard access policy](docs/leaderboard.html)

## Local workflow (only after authorized inputs are available)

```bash
python -m pip install -e '.[test]'
pytest -q
bash scripts/download_competition_data.sh  # user-provided mirrors only; not organizer authentication
python scripts/prepare_data.py
python scripts/build_candidate.py
python scripts/validate_candidate.py       # score the preregistered spatial proxy
python scripts/validate_candidate.py --publish  # fails closed unless all promotion and format gates pass
```

The `data/` tree and intermediate arrays are ignored by Git. Input hashes establish which local bytes were processed; they do not establish organizer provenance. Do not run a weekly slot from a catalogue-only proxy. The only allowed future download is a newly generated candidate after data authentication, matched holdout comparison, compatible current-best registration, and exact-template validation.
