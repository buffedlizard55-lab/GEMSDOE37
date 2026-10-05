# Ranked candidate hypotheses — registered 2026-10-05 UTC (H6 session)

Registered **before** the raster work that promoted H6-A. Each entry names the
layers, the physical signature, why it should catch a fault the USGS/INGENIOUS
catalogue is missing rather than one it already contains, how it differs from
anything implemented in this repository or its siblings, and the expected
DTI effect against implementation cost.

Validation rule in force: a candidate may not consume a weekly submission slot
unless it beats the current holdout best on the **leave-fault-segment-out**
protocol (`scripts/h6_sweep.py`), pooled and in a majority of folds.
Current holdout best: **0.21383** (`b80000_s2.9_o3.0`, H6-A).

| Rank | Hypothesis | Layers | Signature targeted | Why it finds *uncatalogued* faults | New versus existing code | Expected gain / cost | Status |
|---:|---|---|---|---|---|---|---|
| **1** | **H6-A — supervised multi-physics ranker over persistence-certified scale space, dotted and stood off** | all 19 bands + sigma = 1,2,4,8 gradient/Hessian-ridge responses for topography, TMI, RTP, isostatic gravity, conductivity, depth-to-basement, geodetic 2nd invariant + H0 persistence per family | joint, learned combination of scarp curvature, potential-field edges, conductivity contrast and strain concentration, each required to survive a multi-scale filtration | trained **only** on label-free physics: it cannot reproduce catalogue geometry, and a 3 px stand-off deletes everything that merely re-draws a mapped trace, so all emitted mass is off-catalogue | every earlier GEMSDOE ranking was an unsupervised hand-weighted transform (persistence, tilt, strain rank-mix). This is the first *learned* physics ranker here, and the first validated on hidden fault **segments** | measured **0.1973 → 0.21383** pooled on the new holdout, 3/3 folds; ~25 min CPU | **PROMOTED — published** |
| 2 | H6-B — radiometric alteration halo | GeoDAWN K / eTh / eU grids (external) joined to the 19-band stack | K-enrichment and Th/K depletion ratios mark hydrothermal argillic/sericitic alteration above an upflow zone | alteration is a *fluid-pathway* signature: it marks permeable structures whether or not anyone has mapped the trace, and the competition stack ships **no** radiometric band although GeoDAWN flew one | the sibling repo `5GEMSDOE` carried a `radiometric_u8` bridge but never validated it under a segment holdout or inside a learned ranker | plausible +0.01–0.03; cost: one external download + reprojection to EPSG:32611 @100 m | ready — data verified obtainable (see below), **not downloadable from this sandbox** |
| 3 | H6-C — anisotropic lineament continuity (structure-tensor coherence) | det_elev, tmi_hg, iso_grav_anom_hg | coherence/orientation of the local structure tensor, then a directional (steerable) path-continuity filter along the dominant Walker Lane strike bands | a genuine fault is *linear over kilometres*; a single-scale ridge pixel is not. Continuity rewards unmapped segments that line up, which is exactly where experts add new traces | the repo has NMS and gap-closure heuristics but no structure-tensor orientation field or steerable path integral | plausible +0.005–0.015; cost: low, pure in-stack | queued |
| 4 | H6-D — budget/size-robust emission under an unknown truth size | none (post-processing) | choose the dot budget by maximising `c(n)/(0.8 + 0.2c(n) + 0.2 n/G)` over a *distribution* of plausible private truth sizes G instead of a point estimate | does not find new faults, but protects the score: the published 80,000 optimum is exact only for G ≈ 20,000 | prior repos tuned budget by public-score curve fitting on 31 maps; this is a decision-theoretic choice under explicit uncertainty | ±0.01–0.02 of pure score risk; cost: trivial once `c(n)` is tabulated | queued |
| 5 | H6-E — Quaternary-scarp morphology from 1 m lidar | USGS 3DEP 1 m DEM tiles (`1m_DEM_links.csv`, competition-provided) | sub-100 m scarp slope-break and knickpoint density aggregated to the 100 m grid | the provided 100 m detrended elevation cannot resolve a 2–10 m Basin-and-Range scarp; the signal that experts use visually is literally absent from the competition stack | sibling repo `7GEMSDOE` tried a "lidarscarp" ridge (0.1461) but at 100 m and unsupervised, not as a 1 m-derived feature inside a learned ranker | highest ceiling of the five (this is the expert's own evidence), but highest cost: hundreds of tiles, large I/O | blocked here — needs the authenticated data tab for the link CSV and bulk egress |

## External-source obtainability checks (run 2026-10-05)

| Needed for | Source | Official URL | Checked |
|---|---|---|---|
| H6-B | GeoDAWN airborne magnetic **and radiometric** survey, incl. GeoTIFFs of the geophysical grids | `https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7` (DOI `10.5066/P93LGLVQ`) | page fetched and read; the item text states GeoTIFF images of geophysical grids are included; public, no login |
| H6-B fallback | USGS national aeroradiometric grids (K, Th, U), conterminous US | `https://mrdata.usgs.gov/radiometric/` | listed with direct TIFF downloads (K 41 MB, Th 42 MB, U 41 MB) |
| H6-E | 1 m DEM link list | DrivenData data tab `1m_DEM_links.csv` | **not obtainable**: the data tab requires a participant login, and this sandbox has no egress to it |

**Egress limitation, flagged:** from this sandbox only `github.com` resolves and
connects (`curl` to `dropbox.com` and `raw.githubusercontent.com` returns exit 35 /
HTTP 000). H6-B and H6-E therefore cannot be executed here even though their
sources are free, official and verified to exist. They must run on an
unrestricted machine, or via a GitHub-hosted runner that fetches the data and
commits a hash-pinned bridge, which is the mechanism already used for the
competition rasters.
