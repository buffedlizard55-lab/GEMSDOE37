# Score autopsy and strategy for improvement

**Status:** research synthesis; not a claim of a new score. Checked against the official competition pages and the public site materials on **2026-10-05 UTC**.

## 1. Correct the leaderboard premise

The user-provided history identifies `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` as a 0.2778 result and treats 0.3195 as the current leader. The official public leaderboard fetched for this work instead displayed:

| Official public rank | Participant | DW-Tversky | Relevance |
|---:|---|---:|---|
| 1 | nchuzhoy | **0.3262** | Current visible leader at snapshot time |
| 2 | kinghorton42 | 0.3222 | Second |
| 3 | DARD | 0.3195 | The user-stated 0.3195 value is present, but is not the highest in this snapshot |
| 13 | extradr19 | 0.2778 | Same numerical score as the user-reported H33 result, but the public table does not expose artifact filenames |

Source: [official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). Scores can change; this is a dated snapshot, not a live score promise.

**Attribution irregularity:** the user's message associates a named H33 TIFF with 0.2778. The current [GEMSDOE32 owner site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) described H33-2-B2 as a primary candidate with a **projected** 0.2747 and explicitly said no organizer score existed for artifacts in that repository at the time that page was published. The public leaderboard displays a participant at 0.2778 but not the submitted filename. Therefore we cannot independently prove that the H33 TIFF is the artifact that received 0.2778. Treat the association as **user-reported**, not official.

## 2. What the metric rewards

The official problem description defines a distance-weighted Tversky index. With ground truth pixels `G`, prediction field `p(x) in [0,1]`, `R=300 m`, and triangular kernel

`k(d) = max(1 - d/R, 0)`,

it defines

- `TP_w = sum_g max_x p(x) k(d(x,g))` over prediction pixels within the support,
- `FP_w = sum_x p(x) [1 - max_g k(d(x,g))]`, and
- `FN_w = sum_g [1 - max_x p(x) k(d(x,g))]`.

The score is `TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + epsilon)`. Thus a prediction close to an as-yet-unmatched truth line contributes more than a prediction farther away; a prediction more than 300 m away contributes no distance-weighted true-positive credit but can still add false-positive mass. The official weights deliberately penalize missed faults more than false positives, but they do **not** make arbitrary dense output optimal because every unsupported positive adds `FP_w`.

For a narrow, marginal addition that raises one truth pixel's current maximum and adds its corresponding FP mass, and with `alpha + beta = 1`, the score-improving condition simplifies to `k > alpha * current_DTI`. At `alpha=0.2`, this is `k > 0.2 * DTI`. This is a useful **conditional marginal rule**, not a universal threshold: the full metric must be used when pixels compete for the same truth maximum, affect multiple truth pixels, or are clipped by an existing prediction.

The practical objective is to improve the spatial distribution and credit-per-emitted-mass of candidate fault pixels—not merely to increase an uncalibrated probability, choose a single favorable gradient threshold, or emit the thickest possible ridge. This explains why sparse thinning, high-precision ranking, and a distance-aware budget can outperform a high-volume surface. It does not identify which geological detector is best.

Source: [official problem/metric/submission description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

## 3. What can and cannot be inferred about the 0.2778 report

If the file-score association supplied by the user is correct, a plausible mechanism is that H33-2-B2 removed low-value candidate dots near the existing catalogue from a previously successful sparse detector. That can reduce `FP_w` while sacrificing only small amounts of `TP_w`, which can raise DTI under the asymmetric metric. The GEMSDOE32 page says H33-2-B2 was a **removal-only** operation on a user-reported 0.2708 base, and its independent site receipt reports 37,654 emitted pixels and four-fold owner-side proxy calculations. Those are owner-site measurements, not organizer-verified results.

What we **cannot** claim from the available evidence:

- that H33-2-B2 caused the official 0.2778 leaderboard result;
- that the reported 4-fold holdout predicts the private expert labels;
- that the 0.2778 result is the current competition high score;
- that removing pixels near the catalogue is universally beneficial; or
- that high persistence in a scalar field proves a subsurface fault.

The linked previous site itself cautions that its visible-catalogue holdout cannot reward a genuinely new fault. This is scientifically appropriate. Use such holdouts as a proxy/ablation, not as ground-truth discovery validation.

## 4. Why a persistence-based method is a reasonable experiment

A conventional response such as Hessian curvature, gradient magnitude, or a tilt/edge transform gives a score at a chosen smoothing scale and threshold. It is vulnerable to threshold-specific artifacts and to changes caused by smoothing. A one-parameter superlevel persistence diagram instead records births and deaths of connected components as the response threshold sweeps through its full range. For a fixed transformed raster, the persistence lifetime is `birth - death` in response units. The stability theorem of Cohen-Steiner, Edelsbrunner, and Harer bounds the bottleneck distance between persistence diagrams by the sup-norm perturbation of the underlying scalar functions. Therefore, if a bar has lifetime greater than `2 epsilon`, it cannot be matched to the diagonal under a perturbation bounded by `epsilon`.

Important limits:

1. The theorem applies to the specified scalar response field and filtration. It does not certify a geological interpretation.
2. A spatial match of bars between separately smoothed rasters is an empirical cross-scale tracker. A rigorous guarantee for a two-parameter filtration would require an explicitly defined multiparameter persistence framework; this project will not present adjacent-scale matching as that theorem.
3. A numerical perturbation bound must be stated and justified. If sensor/model uncertainty is not known, the output is conditional on a sensitivity parameter, not a measured confidence interval.
4. `H0` bars track connected components of superlevel sets. To interpret them as candidate ridges, require elongated/line-like geometry, persistence across scales, cross-layer agreement, and spatial holdout evidence; do not equate every persistent peak with a fault.

Source: [Cohen-Steiner et al. (2007), *Stability of Persistence Diagrams*](https://doi.org/10.1007/s00454-006-1276-5); bibliographic record and stability statement also available from [ISTA Research Explorer](https://research-explorer.ista.ac.at/record/3972).

## 5. Path to a result above the current leader

The visible gap from a correctly attributed 0.2778 artifact to the 2026-10-05 official public leader at 0.3262 is 0.0484 DTI. That gap is not evidence that any one new transform can close it. First reproduce the reported baseline on the same grid and metric, then run a preregistered spatially blocked comparison at matched positive-pixel budget. Require a positive paired improvement with no catastrophic fold and a minimum practical margin selected before seeing the holdout. Keep a second, independent proxy such as newer official fault traces or expert verification separate from the catalogue-only validation.

The best novel test in this repository is the registered **multiscale topological ridge-persistence** experiment in [`hypotheses.md`](hypotheses.md). It is not yet validated because this checkout initially contained no rasters, no baseline holdout data, and no working pipeline. Until that changes, the slot status is **BLOCKED / NOT ELIGIBLE**. This is a deliberate win-probability decision, not a completed score improvement.
