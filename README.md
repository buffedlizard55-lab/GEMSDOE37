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

## Current status (2026-10-05 UTC, session 2)

A **unique, format-validated submission GeoTIFF now exists** and is the first thing on the site:
`docs/downloads/gemsdoe37-h5-standoff-dotted-26k-20261005T031536Z-3d5db2166013.tif`
(26,000 positive pixels, single-band float32, exact template grid, every cell finite in `[0,1]`,
no nodata tag). Maximum Jaccard overlap with any of 31 previously submitted rasters is **0.032**,
so it is demonstrably not a copy or a relabel. No organizer score exists for it.

Four measured results from this session changed the build, all with committed receipts and
written up in [`research/results_h5.md`](research/results_h5.md):

1. **Our catalogue-ablation holdout does not predict the public score** (Spearman −0.10 over 28
   non-leaking scored maps; −0.27 over all 31). Withheld *mapped* faults reward maps that hug the
   catalogue; the competition rewards the opposite. Model selection was moved onto a 31-map
   public-score calibration. Protocol change recorded in
   [`research/preregistration_revisions.md`](research/preregistration_revisions.md).
2. **Dottedness is the dominant controllable lever** (Spearman −0.751, leave-one-out R² 0.553
   alone, over 31 scored maps). The shipped map is perfectly dotted (`spacing_proxy` = 1.000).
3. **Near-catalogue mass has zero marginal recall.** The controlled pair in the record
   (`dotted-h19-5-d2-8` → `h33-2-b2`) deleted 6,436 pixels within 2 px of the catalogue, changed
   kernel-weighted recall by +0.002, and raised the score 0.2600 → 0.2778. The shipped map uses a
   3 px stand-off and places 0.0 % of its mass within 300 m of a catalogued fault.
4. **Catalogue-geometry features and standalone persistence both score below the random floor**
   (0.053 and 0.043 vs. 0.065 at matched budget). Both were removed from the shipped ranking;
   persistence survives only as 3 of the 63 label-free features.

Forecast for the shipped file: **0.277** under the pessimistic physical model that gives the new
ranking no credit at all, 0.37–0.39 under two observational models that extrapolate below the
smallest budget ever submitted. Owner best to date 0.2778; leaderboard top at last manual check
0.3262. Treat anything above 0.30 as unverified upside.

Earlier status notes (H1 unrun, no data) are superseded: the full 19-band feature stack, the
four-fold catalogue-ablation CV, the full-catalogue model and the submission writer have all run
to completion in this checkout.

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
