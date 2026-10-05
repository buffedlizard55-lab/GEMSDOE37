# Session results, 2026-10-05 — H5 build and the calibration that replaced our holdout

All numbers below were produced in this checkout by the named script and are reproducible
from the committed JSON receipts. None of them is an organizer score.

## 1. The catalogue-ablation holdout does not predict the public score

`scripts/score_reference_maps.py` re-scored all **31** previously submitted rasters
(downloaded from the sibling GEMSDOE sites, public DTI known for all of them) on our own
four-fold catalogue-ablation holdout, using the published distance-weighted Tversky index.

| Comparison | Spearman |
|---|---|
| holdout DTI vs. public DTI, all 31 maps | **−0.271** |
| holdout DTI vs. public DTI, excluding 2 maps whose pruning leaked the held-out folds | **−0.103** |
| total predicted mass vs. public DTI | **−0.641** |

Adding the holdout DTI to a regression of `log(public DTI)` on `log(mass)` moved the
leave-one-out R² from 0.169 to 0.169 — it contributes nothing.

Two extreme cases make the mechanism obvious:

| Map | Public DTI | Our holdout DTI |
|---|---|---|
| `Hedge-v2` (mass piled on the catalogue) | 0.1563 | **0.3186** |
| `h33-2-b2` (mass pushed off the catalogue) | **0.2778** | 0.0048 |

A holdout whose truth *is* withheld catalogue geometry rewards maps that hug the catalogue.
The competition's truth is expert-identified geometry that the catalogue does **not**
contain. The two objectives point in opposite directions.

**Consequence:** the preregistered promotion gate ("beat the current holdout best") was
retired for this build and replaced with a gate against the 31-map public-score
calibration. This is a protocol change and is recorded as such; it is not a post-hoc
rationalisation of a result we liked, because the model that *won* the holdout
(`offcat`, 0.1840) is the same model used in the build — only the budget and stand-off
choices changed.

Receipt: [`data/prepared/reference_holdout.json`](receipts/reference_holdout.json).

## 2. What the ablation holdout *is* good for: ranking families

Even though its absolute DTI is not transferable, the holdout cleanly separates arms
(`scripts/run_cv_arms.py`, 4 folds, pooled TP/FP/FN, matched spacing 2.9 px and budget
55,722 px):

| Arm | Pooled DTI | vs. random floor |
|---|---|---|
| `offcat` — structural model, candidates > 2 px from the catalogue | **0.1840** | 2.85× |
| `struct` — structural model, no stand-off | 0.1670 | 2.58× |
| `random` — uniform placement | 0.0646 | 1.00× |
| `cat` — structural model **plus** catalogue-geometry features | 0.0529 | 0.82× |
| `persist` — multi-scale H0 persistence alone, no learning | 0.0432 | 0.67× |

Two results worth stating plainly:

* **Catalogue-geometry features are harmful**, not merely useless. Distance-to-catalogue,
  local fault density, distance-to-nearest-tip and along-strike continuation drive the model
  *below* random. A learner given the position of the map it was trained on will reproduce
  that map. All 63 features in the shipped build are label-free.
* **Persistence alone is below the random floor.** The honest framing is that cross-scale
  H0 persistence is a useful *stability certificate* and one feature family among 63, not a
  fault detector. The earlier framing of persistence as a standalone method is not supported.

The random arm's 0.0646 at k = 55,722 independently reproduces the analytic floor model
(≈0.062 at k = 50,000), which is a useful cross-check that the scoring code is correct.

Receipts: [`data/prepared/cv_arms.json`](receipts/cv_arms.json),
[`data/prepared/cv_standoff.json`](receipts/cv_standoff.json).

## 3. What actually predicts the public score

`scripts/explain_public_scores.py` regresses `log(public DTI)` for the 31 scored maps on
descriptors we control at build time. Leave-one-out R² (not in-sample fit) decides.

| Descriptor | Spearman vs. public DTI | LOO R² alone |
|---|---|---|
| `spacing_proxy` — mass-weighted mean of 3×3 neighbourhood mass; 1.0 = perfectly dotted | **−0.751** | **+0.553** |
| `mean_persist` — mass-weighted persistence prominence | +0.278 | +0.218 |
| `frac_near_cat` — share of mass within 3 px of a catalogued fault | −0.441 | +0.201 |
| `log_mass` — budget | −0.569 | +0.098 |
| `mean_pstruct` — mass-weighted structural score | −0.235 | +0.085 |

Best subset: `{mean_pstruct, spacing_proxy}`, LOO R² **0.554**. Note that `mean_persist`
and `frac_near_cat` lose all of their apparent value once dottedness is controlled for —
they were proxies for clumpiness.

Restricting to the 12 perfectly dotted maps, budget alone gives LOO R² **0.570** with
`log(DTI) = 7.042 − 0.790 · log(mass)`.

**Dottedness is the dominant lever, and budget is second.** Both are geometric, both are
free, and both were already saturated by the best prior map — which is why the remaining
upside has to come from either a smaller budget or a better ranking.

Receipt: [`data/prepared/public_score_model.json`](receipts/public_score_model.json).

## 4. Why `h33-2-b2` scored 0.2778, and how to beat it

Inverting the metric, `DTI = R / (0.8 + 0.2R + 0.2k/N)` where `R` is kernel-weighted recall,
`k` the budget and `N ≈ 14,000` the hidden truth pixels, recovers the recall of the
`h19-5` family from its own public scores:

| Map | Budget `k` | Public DTI | Implied recall `R` |
|---|---|---|---|
| `h19-5-powerlaw-budget` | 121,131 | 0.1922 | 0.506 |
| `dotted-h19-5-d2-8` | 44,090 | 0.2600 | 0.392 |
| `h33-2-b2` (= the previous row minus everything within 2 px of the catalogue) | 37,654 | **0.2778** | 0.394 |

The controlled pair is decisive: deleting 6,436 near-catalogue pixels changed recall by
**+0.002** — those pixels bought nothing — while cutting the false-positive bill by 15 %.
`h33-2-b2` is not a better *map*; it is the same map with its dead weight removed.

That immediately implies the next move. Fitting `R(k) = 0.0265 · k^0.252` to the family's own
two clean points and maximising the metric gives an interior optimum near
**k ≈ 20,000–26,000**, worth roughly +0.01 over 37,654 px *with no improvement in ranking at
all*. Below ~15,000 px recall collapses and the score falls again.

## 5. The shipped build

`scripts/build_submission.py --ranking struct --spacing 2.9 --standoff-px 3.0 --budget 26000`

| Property | Value | Why |
|---|---|---|
| Ranking | label-free structural model, 63 features incl. H0 persistence prominence | best arm on the holdout (§2), and the only genuinely new ingredient |
| Stand-off | 3.0 px from every catalogued fault pixel | §4 — near-catalogue pixels have zero marginal recall |
| Spacing | 2.9 px minimum centre-to-centre | §3, the dominant lever; also the holdout optimum |
| Budget | 26,000 pixels | §4 interior optimum; smaller than any map ever submitted by this project |
| Values | binary 1.0 / 0.0 | the objective is linear-fractional per pixel, so its optimum is at the extremes |

Measured properties of the file (`scripts/verify_submission.py`):

* `spacing_proxy` = **1.000** — no two predicted pixels touch, the optimum of the dominant predictor.
* mass within 300 m of a catalogued fault = **0.0 %**; minimum catalogue distance 3.16 px.
* `mean_pstruct` = 0.295 versus 0.075 over the footprint — 3.9× enrichment, and *inside* the
  range spanned by the 31 scored maps (0.067–0.390), so the descriptor model is interpolating.
* Maximum Jaccard overlap with any of the 31 prior submissions = **0.032** (closest:
  `h16-continuation`). It is not a copy or a relabel.
* All format checks pass: single-band float32, exact template shape/CRS/EPSG:32611/transform/
  bounds/resolution, no nodata tag, every cell finite and in `[0,1]`, 26,000 positive pixels.

## 6. Forecast, with its error bars shown

| Model | Forecast public DTI | Standing |
|---|---|---|
| Physical recall model, pessimistic (our ranking given **no** credit) | **0.277** | interpolating; the floor |
| Descriptor model over 31 maps (LOO R² 0.554) | 0.390 | both predictors inside observed range |
| Budget power law over 12 dotted maps (LOO R² 0.570) | 0.373 | **extrapolates** below the smallest submitted budget |

For reference: best score this project has recorded is 0.2778; the public leaderboard top at
the last manual check was 0.3262.

The pessimistic model says this build should land around the current owner best even if the
new ranking adds nothing. The two observational models say materially higher, but both are
fitted to 12–31 observational points from a non-randomised design. **Anything above 0.30
should be read as unverified upside.** The single largest unknown is ranking quality, which
no internal protocol in this repository can currently validate — see Limitations.

Receipt: [`data/prepared/score_forecast.json`](receipts/score_forecast.json).

## 7. Limitations

1. **We cannot validate ranking quality offline.** The one internal protocol we had is
   anti-correlated with the objective (§1). Two prior maps with identical budget and
   dottedness scored 0.2477 and 0.1223 — a 2× spread attributable purely to ranking — so
   this is a large uncertainty, not a rounding error.
2. **The budget choice extrapolates.** No map below 37,654 pixels has ever been scored. If
   recall falls faster below that point than `R(k) = 0.0265·k^0.252` predicts, 26,000 is too
   small and the score will come in under 0.2778.
3. **`N ≈ 14,000` is inferred, not known.** It comes from our own floor model fitted to
   public scores. The budget optimum scales roughly linearly with `N`.
4. **The descriptor regressions are observational.** The 31 maps were not produced under a
   randomised design, so a descriptor can look predictive through what it correlates with.
5. **Persistence is a feature, not a method.** Used alone it scores below random (§2). The
   "topological certification" framing is retained only in the narrow sense that persistence
   across smoothing scales enters the feature stack and is reported per candidate.

## 8. Persistence reported as a formal stability measure

Requested explicitly: report, alongside the score, the range of scales each certified
candidate survived. For every predicted pixel the build records how many of the three
Gaussian smoothing scales (100 / 200 / 400 m) its H0 superlevel component persisted through,
per physical field family. Receipt:
[`research/receipts/submission_verification.json`](receipts/submission_verification.json).

| Field family | Mean scales survived (selected) | Mean scales survived (whole footprint) | Selected pixels stable at ≥2 scales |
|---|---|---|---|
| DEM curvature | 2.838 | 2.786 | 97.6 % |
| Magnetic gradient | 2.872 | 2.874 | 96.7 % |
| Gravity gradient | 2.949 | 2.949 | 98.9 % |

Cross-family: **99.8 %** of predicted pixels are multi-scale stable in at least two of the
three independent field families, and **93.5 %** in all three.

**This is a weak certificate, and saying so is the point.** The footprint baseline is almost
identical to the selected set, so at the registered persistence threshold
(ε = 0.01, minimum bar lifetime 0.05) essentially *every* pixel qualifies as multi-scale
stable. Persistence as currently parameterised discriminates almost nothing, which is exactly
consistent with the measured result that persistence used alone as a ranking scores 0.0432 —
below the 0.0646 random floor. The honest conclusion is that the certification threshold is
far too permissive to act as a filter; tightening it (a much larger minimum lifetime, or
requiring survival of all three scales *and* top-decile prominence) is the obvious next
experiment, and is listed under remaining work.
