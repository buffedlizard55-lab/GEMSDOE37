# Hypothesis register, session 2026-10-05 (H5–H9)

Registered **before** the configuration sweep that selected the submitted map, and
**after** the H1–H4 register in [`hypotheses.md`](hypotheses.md). Every candidate below names
(a) its layers, (b) its physical signature, (c) why it should catch geometry missing from
USGS/INGENIOUS rather than geometry already catalogued, (d) how it differs from prior repo
work, (e) expected effect and cost, and (f) external-data provenance where applicable.

Expected-DTI figures are planning judgments, not measurements, except where a holdout number
is cited explicitly.

## Ranked register

### Rank 1 — H5: catalogue-geometry-aware, stand-off-constrained structural ranking with coverage-optimal dotted budget *(implemented and run this session)*

| Field | Content |
|---|---|
| **Layers** | All 19 provided GEMS bands, expanded to 63 label-free features: multiscale Gaussian-smoothed ridge/edge responses (Hessian anisotropy on detrended elevation; horizontal-gradient magnitude on magnetic and isostatic-gravity anomalies), scale-normalized curvature, local texture/coherence, and the H0 cross-scale persistence prominence fields `pers_dem_max`, `pers_mag_max`, `pers_grav_max` from the H1 machinery. |
| **Physical signature** | A fault that is real but unmapped should express a *multi-scale-stable* linear response in at least one physical field. Persistence (the range of smoothing scales a superlevel component survives) is used as the stability certificate so that single-threshold speckle is demoted. |
| **Why off-catalogue** | Two mechanisms. (1) The learner is trained on catalogued faults but is given **no** feature that encodes where the catalogue is, so it must rank on physics alone and cannot retrace the map it was taught from. (2) A hard stand-off radius deletes candidates within *d* px of any catalogued pixel, forcing the entire budget onto geometry the catalogue does not already carry. |
| **Difference from prior work** | Prior repo submissions either ranked with catalogue-distance/continuation features (GEMSDOE32 h16-continuation, structural-area06) or used a single-scale ridge transform at a large budget. H5 is the first to (i) *exclude* catalogue-geometry features after measuring that they are harmful, (ii) impose an explicit stand-off, and (iii) set spacing and budget from a pooled catalogue-ablation holdout rather than by hand. |
| **Expected effect / cost** | Expected positive. Measured on the 4-fold catalogue-ablation holdout: pooled DTI **0.1840** vs **0.0646** for matched-budget random placement (2.85× the floor). Cost: ~25 min CPU for the feature stack plus ~20 min per sweep. |
| **External data** | None. Competition rasters only. |

### Rank 2 — H6: dual-polarity gravity/magnetic edge *mismatch* as a buried-fault discriminant

| Field | Content |
|---|---|
| **Layers** | Isostatic gravity anomaly and reduced-to-pole magnetic anomaly, each reduced to a normalized horizontal-gradient-magnitude edge field, plus the DEM edge field. |
| **Physical signature** | A *density* edge that is **not** accompanied by a magnetization edge (or vice versa) at the same location and strike. Lithologic contacts generally move both properties together; a fault that juxtaposes similar lithologies across a displacement, or that is a fluid-altered damage zone, tends to move one and not the other. The feature is the signed, strike-aligned disagreement `|∇g|_n − |∇m|_n` evaluated only where at least one field is strong. |
| **Why off-catalogue** | Surface mapping follows scarps and exposed contacts. A blind fault under basin fill that offsets density but not magnetization leaves no mappable surface expression, so it is systematically *under*-represented in USGS/INGENIOUS and over-represented in the hidden set. |
| **Difference from prior work** | GEMSDOE35 H35-09 fuses gravity and magnetics by *agreement* (cross-gradient / Hessian product), which rewards coincident edges. H6 deliberately rewards the complement — the disagreement residual — which agreement-based fusion suppresses by construction. |
| **Expected effect / cost** | Moderate, uncertain: plausibly +0.01–0.03 pooled DTI if buried structures are a meaningful share of the hidden set; could be ≈0 if the hidden faults are predominantly surface scarps. Low cost: two extra feature columns in the existing stack, one re-fit. |
| **External data** | None. |

### Rank 3 — H7: drainage-anomaly inversion (flow-accumulation lineation without topographic scarp)

| Field | Content |
|---|---|
| **Layers** | DEM only: D8 flow direction / flow accumulation, channel-head density, and the residual between the observed channel network and the network predicted from smoothed regional slope. |
| **Physical signature** | Linear chains of channel-head or valley-axis alignment, and anomalous stream-segment azimuth clustering, that are *not* explained by a slope break. Faults modify permeability and base level and so organize drainage even where the scarp is eroded flat. |
| **Why off-catalogue** | Precisely the case a scarp-based mapper misses: the geomorphic marker has been removed by erosion or burial, and only the drainage inheritance survives. |
| **Difference from prior work** | GEMSDOE30 H31-03 registered "drainage offsets/knickpoints", i.e. *displacement* markers on existing channels. H7 is the inverse test — alignment of channel **initiation** and azimuth residual against a slope-only null — and requires no offset to be visible. |
| **Expected effect / cost** | Small to moderate, high variance; the Great Basin's internally drained playas will produce null zones. Medium cost: a flow-routing pass over 12.3 M cells plus a null model. |
| **External data** | None (the provided DEM suffices); optionally the free USGS 3DEP 10 m DEM via [The National Map](https://apps.nationalmap.gov/downloader/) for a higher-resolution channel network. |

### Rank 4 — H8: geothermal-indicator co-location as a *precision* re-weighting, not a detector

| Field | Content |
|---|---|
| **Layers** | Provided heat-flow / temperature-gradient and alteration-proxy bands, used as a multiplicative prior on the H5 score rather than as a standalone ranking. |
| **Physical signature** | Permeable fault damage zones channel hydrothermal fluid; elevated near-surface gradient and alteration mark the *subset* of structures that are hydraulically active. |
| **Why off-catalogue** | The competition's geothermal framing means the hidden review plausibly emphasized structures of geothermal relevance. Re-weighting does not find new lines; it reallocates a fixed budget toward the lines most likely to have been reviewed and digitized. |
| **Difference from prior work** | GEMSDOE36 ran geothermal experiments as *detectors*. H8 explicitly refuses to use them as detectors (their spatial support is far too broad) and uses them only as a budget-allocation prior on top of a validated structural ranking. |
| **Expected effect / cost** | Small, ±0.01. Very low cost (one multiply, one sweep). Risk: it concentrates mass in known geothermal fields, which are also the best-mapped areas — the opposite of what the stand-off evidence recommends. |
| **External data** | None. |

### Rank 5 — H9: Quaternary-basin-margin conditional prior from the free USGS Quaternary Fault and Fold Database

| Field | Content |
|---|---|
| **Layers** | H5 score conditioned on an external Quaternary-activity polygon/line layer and a basin-fill proxy derived from the provided gravity low. |
| **Physical signature** | Range-front normal faults in the Basin and Range are strongly localized to the margins of gravity-defined basins; Quaternary activity indicates the system is live and therefore likely to have been extended by reviewers. |
| **Why off-catalogue** | The hidden set includes "newly mapped geometry of an existing fault system" (organizer clarification). Basin margins adjacent to an active system are where unmapped *extensions* of catalogued strands are most likely. |
| **Difference from prior work** | No sibling repo has used the Quaternary database as a *conditioning* layer for budget allocation; prior uses were as additional positive labels. |
| **Expected effect / cost** | Uncertain and possibly negative — it points mass back toward catalogued systems, which this session measured to be harmful. Ranked last for that reason. Low implementation cost. |
| **External data** | [USGS Quaternary Fault and Fold Database](https://www.usgs.gov/programs/earthquake-hazards/faults) — public domain, free, no login. Obtainability not re-verified this session; treat as unconfirmed until downloaded and CRS-matched. |

## Ranking rationale

H5 ranks first because it is the only candidate whose central claim was testable with data
already in the checkout, and it was tested. H6 ranks second because it is cheap, uses no
external data, and targets the failure mode (buried structure) that best explains why the
hidden set is hidden. H7 is third: a genuinely independent observable, but expensive and
partly void over playas. H8 and H9 rank last because both push prediction mass toward
well-mapped ground, and this session's holdout result says that is where the metric punishes
us hardest.

## Promotion gate applied to H5

H5 was required, before any weekly slot was spent, to beat **both**
(i) matched-budget random placement and (ii) the best alternative arm, on the pooled
4-fold catalogue-ablation holdout with identical input hashes. Results in
[`results_h5.md`](results_h5.md). The gate passed. The holdout remains a *catalogue*
pseudo-holdout: it measures transfer to withheld mapped faults, not discovery of
expert-only hidden geometry, and it is not an organizer score.

---

## Session-4 addendum (2026-10-05): instrument inversion and data obtainability

**Instrument inversion.** The promotion gate written above assumed the blocked catalogue
holdout could rank candidates toward live gains. It cannot: with the eight owner-reported
public scores recovered this session, Spearman(fold instrument, live) = **−0.667** and
Spearman(SGMC-prevalence instrument, live) = **+0.143**. Details and the geometry regression
that does describe the ladder (R² 0.992, LOO R² 0.978, n = 8) are in
[`instrument_validity.md`](instrument_validity.md). The gate for sessions 4+ is therefore a
*falsification* gate: a candidate must beat matched-budget random placement and must not be
worse than chance on either screen; it is never promoted on a screen margin.

**Obtainability of the external data named in this register (now verified).**

| Source named | Status | Evidence |
|---|---|---|
| GeoDAWN airborne radiometric products (K, Th, U, TC) and extensions (Th/K, U/K, U/Th, TMI upward-continued 150 m), USGS, DOI `10.5066/P93LGLVQ` | **Retrieved and hash-pinned** — 8 bands on the competition grid in `data/raw/geodawn_rad_u8.tif` + `geodawn_extensions_u8.tif` (≈27 MB each) | archive MD5/SHA-256 in the product JSONs; ScienceBase item `657e1d85d34e23d3533209f7` |
| 1 m LiDAR fault-scarp feature stack (12 bands: max excess, step, negative/positive Laplacian, down-/up-face, cross-strike, relief, coherence, strike, validity) | **Retrieved and hash-pinned** in `data/raw/lidar_scarp_features_u8.tif` + JSON with the exact quantisation table | `scripts/fetch_open_data.sh` prints the sha256 of every artifact |
| USGS State Geologic Map Compilation (SGMC) structures, NV + CA | **Retrieved and rasterised** — `data/raw/derived_sgmc_faults_100m_u8.tif` (213 KB, 82,151 px in footprint, 61,664 px >3 px from the catalogue) | source sha256s `3b333ac0…` (NV), `78765ba4…` (CA) in the sibling receipt |
| USGS Quaternary Fault and Fold Database (QFaults) | **Already mirrored** — 1,179 features / 349 named zones, sha256 `4d6efc7b…` (`GEMSDOE28/data/qfaults_v2_in_footprint.json`); re-fetch not needed | do **not** use as new-fault truth: 99.95 % of its footprint pixels coincide with the training catalogue |
| 3DEP 10 m DEM (optional H7 upgrade) | Not fetched. Egress from this sandbox reaches only GitHub and PyPI; `apps.nationalmap.gov` fails TLS. Obtainable only through a repo GitHub-Actions runner, which is a legitimate but out-of-band route. | probe results in `research/review_log.md` (session 4) |

**Rank changes.** H6 (dual-polarity mismatch) stays second and remains the cheapest untried
geological test. H9 is demoted to last with cause: the QFaults mirror *is* the catalogue, so
conditioning on it re-points mass at the ground the ladder punishes. H7's optional 3DEP data
is the only named source not currently obtainable from this sandbox.

