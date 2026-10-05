# Ranked geological hypotheses and measured screening status

**Reviewed:** 2026-10-05 UTC. **Data class:** competition-grid rasters reconstructed in this sandbox from a GitHub data bridge built from the user-provided Dropbox mirrors; these bytes are hash-pinned and internally consistent but were **not** freshly downloaded from the authenticated DrivenData data tab here.

## Why the register changed

The repository started with an H1-only persistence experiment over detrended elevation, magnetic intensity, and isostatic gravity. Once the mirror-bridged rasters were available, that H1 path was executed and exposed two concrete facts:

1. the H1 fused persistence surface produced only **25,686** positive full-grid cells, below the fixed 37,654-pixel budget, so it could not even be evaluated under the registered exact-budget holdout without a fallback rule; and
2. simple exact-mask pseudo-holdout screens on the actual competition bands showed that the **geodetic strain fields** were materially stronger than the original DEM/magnetic/gravity-only single-scale control on this proxy.

The updated ranking below reflects those measured screening results. It does **not** turn the public-catalogue pseudo-holdout into organizer truth.

## Prior-work boundary

The sibling repositories already explored many of the obvious families: multiscale DEM scarps, magnetic tilt, strain-rate maps, gravity–magnetic fusion, radiometric ratios, geothermal priors, Anderson/PINN ideas, and dotted/thinned emissions. GEMSDOE37 therefore does **not** claim global novelty for these physical observables. What is new here is the exact combination, the exact-mask pooled holdout protocol, the explicit use of a topological prior as one term in a measured rank-mix, and the repository-local generation of a new TIFF from those ingredients.

## Ranked 2026-10-05 shortlist

| Rank | Hypothesis | Specific layers | Physical signature targeted | Why it may catch faults missing from the catalogue | Difference from prior GEMSDOE37 code | Measured/expected value & cost |
|---:|---|---|---|---|---|---|
| **1** | **H2 — strain-dominated structural rank-mix with a persistence prior** | Band 4 geodetic second invariant, band 7 geodetic shear rate, band 8 geodetic dilatation rate; plus the H1 single-scale DEM/magnetic/gravity prior and the H1 fused persistence prior | Primary term: mean robust-standardized **absolute strain magnitudes**. Secondary term: DEM-curvature + magnetic-edge + gravity-edge control. Tertiary term: multiscale H0 persistence surface. Published score = `2·strain + structural + persistence`. | Blind or poorly mapped active transfer zones can have localized strain-rate concentration even when the surface trace is weak in topography or catalogue geometry. Adding structural/topological corroboration is intended to shrink broad non-structural strain halos. | This is **not** the original H1 detector. It promotes geodetic strain to the primary signal and demotes topology to a prior. | **Measured exact-mask pseudo-holdout:** baseline strain-only pooled DTI **0.02809**; final rank-mix pooled DTI **0.03693**; pooled gain **+0.00884** with **4/4 positive fold gains**. **Cost:** low incremental compute because it reuses H1 control/topology arrays. |
| **2** | **H3 — buried basin-boundary fault hypothesis** | Band 15 depth to basement, band 17 conductivity surface, band 13 isostatic gravity anomaly (or gradient-derived variants) | Edge/discontinuity ranking on conductivity and basement-thickness contrasts, optionally corroborated by gravity contrasts | Basin-bounding or sediment-buried faults can be weak in surface morphology but strong in electrical/gravimetric partitioning across concealed basin margins. | Not implemented in the original repo; uses subsurface-property contrasts rather than only DEM and potential-field texture. | **Measured quick screen (simple single-scale proxy):** pooled DTI about **0.02137**. **Expectation:** geologically plausible but weaker than H2 on this proxy. **Cost:** low, already in the provided stack. |
| **3** | **H4 — conductivity/gravity/magnetic corroboration for concealed contacts** | Band 17 conductivity, band 13 isostatic gravity anomaly, band 14 total magnetic intensity | Multi-physics contact/edge ranking, especially where conductivity and mass/magnetization boundaries coincide | Concealed structural zones can separate alteration, density, and magnetic domains even where strain is muted or the mapped trace is incomplete. | Different emphasis from H1: conductivity enters directly; topology is optional rather than the core detector. | **Measured quick screen:** pooled DTI about **0.02581**. **Cost:** low. Could still be a useful ensemble leg, but it underperformed H2. |
| **4** | **H5 — tilt-plus-gradient structural edges** | Band 6 tilt angle / total curvature, band 3 magnetic horizontal gradient, band 18 gravity horizontal gradient | Edge-detection / lineament ranking on already-derived magnetic and gravity structural transforms | A subtle unmapped contact may already be highlighted in derivative products designed for structural edges. | Unlike H1, this treats the provided derivative bands as first-class inputs rather than recomputing all structure from the rawer bands. | **Measured quick screen:** pooled DTI about **0.01488**. **Cost:** very low, but the signal was weak on this proxy. |
| **5** | **H1 — DEM/magnetic/gravity H0 persistence of stable maxima** | Metadata-identified detrended elevation, total magnetic intensity, isostatic gravity anomaly | Multiscale H0 births/deaths of Hessian-anisotropy and gradient responses, requiring cross-scale survival and multi-layer support | In principle, a stable cross-physics boundary response may highlight a fault-related contact absent from the catalogue. | This is the repository's original implemented persistence detector. | **Measured status:** built successfully, but the fused full-grid score contained only **25,686** positive cells, below the fixed **37,654** budget, so it was not directly scoreable under the exact-budget validator. It remains useful as a tertiary prior inside H2. |

## Measured quick-screen table used for ranking

The following simple exact-mask pseudo-holdout screens were measured on the mirror-bridged competition rasters at the fixed 37,654-pixel budget. They are **not** organizer scores and should not be over-interpreted, but they do provide a real repository-local ordering for implementation decisions.

| Screened proxy | Pooled pseudo-holdout DTI | Notes |
|---|---:|---|
| Geodetic strain only (`abs(second invariant, shear, dilatation)`) | **0.02809** | Strongly concentrated in the SW fold on this proxy. |
| DEM + magnetic + gravity single-scale control | **0.02673** | Original H1 control family. |
| Conductivity + gravity + magnetic | **0.02581** | Best purely concealed-contact proxy among the fast screens run. |
| Buried basin boundary (`depth to basement + conductivity + gravity`) | **0.02137** | Plausible geology, weaker measured proxy. |
| Tilt + magnetic horizontal gradient + gravity horizontal gradient | **0.01488** | Weak on this proxy. |
| Final H2 rank-mix (`2·strain + structural + persistence`) | **0.03693** | The published GEMSDOE37 TIFF comes from this unique rank-mix. |

## Why H2 became the published candidate

H2 is the only measured candidate in this repository that satisfied all three of the repository-local promotion conditions simultaneously against a concrete incumbent:

- pooled gain above the fixed **+0.005** threshold,
- at least **3/4 positive fold gains**, and
- no fold regression worse than **−0.02**.

Against the registered strain-only incumbent, the published H2 candidate achieved:

- **baseline pooled DTI:** 0.02809,
- **candidate pooled DTI:** 0.03693,
- **pooled gain:** +0.00884,
- **per-fold gains:** NW +0.00480, NE +0.00264, SW +0.03363, SE +0.00327.

These values are exact outputs of the repository-local scorer stored in `data/prepared/rankmix_h2/holdout-report.json` and mirrored for public reading at `docs/reports/.../holdout-report.json`.

## Important limitations

1. **The pseudo-holdout truth is still the public catalogue.** It does not validate expert-only hidden new faults.
2. **The source bytes are mirror-bridged, not freshly authenticated from DrivenData in this sandbox.** Hashes are pinned, but provenance remains a real caveat.
3. **H2 is heavily SW-dominated on this proxy.** It improved all four folds over the strain-only incumbent, but most of the pooled gain came from SW.
4. **Topology remains a prior, not a certificate of geology.** In H2 the persistence surface is a tertiary ranking term, not a proof that a pixel is a fault.
5. **No organizer score exists yet for this TIFF.** The download is eligible by the repository's local rules, not by any organizer receipt.
