# Score autopsy and strategy for improvement

**Status:** evidence-graded research synthesis, not a claim of a new score. Sources checked 2026-10-05 UTC. The board state below is a one-time review; the official leaderboard is dynamic.

## 1. Current official board versus the H33 owner claim

A one-time review on 2026-10-05 found that the highest public-board entry was above the task's stated 0.3195; the official leaderboard is dynamic and its current value must be checked at the [organizer page](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). The board does not identify submitted TIFF filenames or methods, so a score row cannot authenticate a named artifact. This repository does not mirror leaderboard rows or run an automated monitor; see the [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/).

The user-supplied score ledger associates the file `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` with 0.2778. The [GEMSDOE32 owner site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) instead describes H33-2-B2 as a 37,654-pixel removal-only candidate, reports an owner-side four-fold proxy gain of +0.004870 over a reported 0.2708 base, projects 0.2747, and states that the artifacts were not organizer-scored when its page was published. The 0.2778 file-to-score association is therefore **unverified**, not an organizer-confirmed H33 result.

## 2. What the official DTI does

For the organizer's valid evaluation pixels, let `G` be the new-fault truth, `p(x) in [0,1]` the prediction, `R = 300 m`, and

`k(d) = max(1 - d/R, 0)`.

The official description defines distance-weighted components equivalent to

- `TP_w = sum_g max_x p(x) k(d(x,g))`,
- `FN_w = sum_g [1 - max_x p(x) k(d(x,g))]`, and
- `FP_w = sum_x p(x) [1 - max_g k(d(x,g))]`,

with `alpha = 0.2` and `beta = 0.8`, so

`DTI = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)`.

The local proxy adds a deterministic `1e-8` denominator epsilon for numerical safety; its exact scorer implementation remains organizer-controlled. The local code is checked against the published worked example, not a replacement for the official scorer.

DrivenData staff clarified the masking rule: only the **exact provided known-fault pixels** are masked/excluded. There is no distance buffer around those pixels. Predictions on adjacent unmasked pixels are scored normally, and new truth may lie within 300 m of known traces, including corrections, continuations, and splays. See the [scoring clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) and [new-fault definition](https://community.drivendata.org/t/where-do-you-draw-the-line/11536/2).

The official public score pools all public-subset pixels into one calculation; the same single pooled Tversky aggregation is used on private pixels, and final re-evaluation covers the entire GeoDAWN area. Therefore a local cross-fold summary should sum `TP_w`, `FP_w`, and `FN_w` across non-overlapping folds before computing one DTI; the arithmetic mean of fold DTIs is descriptive only. Source: [leaderboard aggregation clarification](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2).

A narrow marginal calculation can simplify to `k > alpha * current_DTI` when an added prediction raises one truth pixel's current maximum by its kernel-weighted amount, adds the corresponding FP mass, and `alpha + beta = 1`. At `alpha=0.2`, this is `k > 0.2 * DTI`. It is **not** a universal per-pixel rule; overlapping truths, existing maxima, and competition between predictions require evaluating the full metric.

## 3. Why H33-2-B2's 200 m pruning cannot be explained by the official mask

The owner site describes H33-2-B2 as removing points within 2 pixels (200 m) of catalogue geometry. Under the official rule:

- Predictions on the **exact** known-fault pixels are excluded and do not contribute to TP/FP/FN.
- Predictions within 100–200 m but **outside** the exact pixel mask remain in the scoring domain. They may help if close to a new/corrected/splayed truth, or hurt if unsupported.
- The new-truth kernel extends to 300 m, and staff explicitly say new geometry may be within that distance.

So a 200 m deletion is not required by the evaluator and is not guaranteed to improve DTI. The earlier explanation that all removed B=2 predictions earned zero TP and only penalty was not supported by the official rules. If the file-score association is accurate, a generic sparse-emission effect is plausible: removing redundant, low-marginal-credit predictions can lower `FP_w` more than it reduces `TP_w`. But the owner-reported proxy, not the organizer score, is the only evidence for that mechanism. No causal attribution to the B=2 rule is established.

The official H33 owner page and user history also disagree in evidence status: owner projection 0.2747 versus user-reported organizer association 0.2778. The public board does not identify TIFF filenames, so it cannot bridge that gap or verify the file-score association.

## 4. What H0 persistence does—and does not—say

For a fixed response raster `f`, a one-parameter H0 superlevel filtration follows connected components of `{x : f(x) >= t}` as threshold `t` decreases. A finite bar has birth/death thresholds and lifetime `birth - death`. The stability result of Cohen-Steiner, Edelsbrunner & Harer (2007) bounds the bottleneck distance between diagrams by the sup-norm perturbation of the underlying functions. Thus a bar of persistence greater than `2 epsilon` cannot be matched to the diagonal under a perturbation bounded by `epsilon`.

Limits matter in GEMSDOE37:

1. The theorem is conditional on a fixed transformed scalar field and a justified `epsilon`. The current `epsilon=0.01` is a registered sensitivity assumption, **not a measured sensor/model error bound**.
2. Matching representative peak coordinates between separately smoothed rasters within 2 pixels is a greedy spatial heuristic. It is not a formal multiparameter persistence result.
3. H0 bars identify connected-component maxima. The current implementation paints a small neighborhood around matched peaks; it contains **no explicit elongation or line-continuity test**. It cannot certify that a candidate is a fault or even a line.
4. The DEM Hessian-anisotropy response is a geomorphic lineament proxy; magnetic/gravity gradient responses can mark lithologic boundaries, acquisition artifacts, or other geology. Cross-layer support is a hypothesis to test, not a geological label.

Source: [Cohen-Steiner et al. (2007), *Stability of Persistence Diagrams*](https://doi.org/10.1007/s00454-006-1276-5); see also the [ISTA research record](https://research-explorer.ista.ac.at/record/3972).

## 5. What is new enough to test next

The current H1 implementation is algorithmically differentiated from inspected multiscale scarp/ridge work only by explicit per-scale H0 birth/death accounting plus heuristic cross-scale peak tracking. H35-06 already tests multiscale DEM curvature/slope breaks; GEMSDOE30 registered 1 m scarp and drainage methods; GEMSDOE35 registered tilt, geodetic, gravity–magnetic, and radiometric arms; GEMSDOE36 explores Anderson/PINN, gravity, and geothermal evidence. Those are not to be relabeled as new. The distinct remaining candidates are raw GeoDAWN flight-line repeatability, Sentinel-1 InSAR deformation, and USGS moment-tensor orientation; all are conditional on source coverage and remain unimplemented in GEMSDOE37. See the [ranked register](hypotheses.md).

The GEMSDOE37 promotion gate now requires a same-budget comparison against the single-scale control **and** a separately registered, hash-pinned local current holdout-best report under identical raw inputs and scoring protocol. The current-best slot is empty. The public-catalogue spatial proxy is not proof of hidden expert-fault discovery, especially for truths close to visible mapped traces.

## 6. Current result and blockers

No authenticated competition raster, complete spatial holdout, measured DTI, current holdout-best report, validated submission TIFF, or organizer score exists in the checkout. The 37,654-pixel H33 count is used only as a fixed matched-budget setting from an owner report; no H33 pixels are reused. Do not infer the candidate has beaten the user-supplied 0.2778 association or any dynamic public-board entry. The [official leaderboard link](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) is the source for any later one-time check; no scheduled polling is run because the [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) prohibit robots/spiders and manual monitoring/copying without prior written consent.
