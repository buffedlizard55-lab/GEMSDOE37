# Session 4 results (2026-10-05): instrument inversion and the CSP build

All numbers were produced in this checkout by the named scripts. None of them is an
organizer score. Receipts are under `docs/downloads/` and `data/work/`.

## 1. The decisive negative result: both local screens fail against the live ladder

Re-scoring the eight owner-reported, already-submitted maps whose public DTI is known:

| Map | public DTI | catalogue-fold screen | SGMC off-catalogue screen |
|---|---|---|---|
| `h33-2-b2` | 0.2778 | 0.004 | 0.094 |
| `h27-4-solo-d28` | 0.2708 | 0.029 | 0.094 |
| `h25-dotted-d28` | 0.2600 | 0.093 | 0.093 |
| `h27-gapclosure` | 0.2449 | 0.088 | 0.100 |
| `h19-5` | 0.1922 | 0.066 | 0.098 |
| `h28-dotted-ridge` | 0.1839 | 0.189 | 0.088 |
| `ens12` | 0.1563 | 0.083 | 0.100 |
| `h25-ctx-ridge` | 0.1280 | 0.142 | 0.080 |

Spearman(fold screen, live) = **−0.667**; Spearman(SGMC screen, live) = **+0.143**. The fold
screen rewards exactly what the contest punishes, because its truth is the published catalogue
while the contest's truth is the geometry the catalogue does not contain. Any selection loop
that maximises it walks backwards. Derivation, tables and the replacement gate:
[`instrument_validity.md`](instrument_validity.md).

## 2. What the ladder does respond to (n = 8, geometry only)

```
live ≈ 0.81841 − 0.06129·ln(positive pixels) + 0.00378·mean distance to catalogue (px)
R² 0.992   leave-one-out R² 0.978   max LOO error 0.014
```

| Map | dots | mean distance to catalogue (px) | live |
|---|---|---|---|
| `h33-2-b2` | 37,654 | 29.0 | 0.2778 |
| `h27-4-solo-d28` | 40,199 | 27.3 | 0.2708 |
| `h25-dotted-d28` | 44,090 | 25.0 | 0.2600 |
| `h27-gapclosure` | 61,328 | 24.5 | 0.2449 |
| `ens12` | 172,974 | 21.1 | 0.1563 |
| `h25-ctx-ridge` | 174,232 | 12.1 | 0.1280 |

Both directions are monotone and consistent with the owner's own controlled pruning
(0.2708 → 0.2778 when 6,436 near-catalogue pixels were deleted with kernel recall unchanged).
The safe conclusion is *fewer, further-out dots are rewarded*, not a causal law.

## 3. The CSP build

**Field.** A 4-fold quadrant-blocked out-of-fold ensemble (40 px guard, 200 k negatives, 220
iterations) over **234 label-free features**: for each of the 19 competition bands, four
scale-normalised gradient-magnitude scales, a Hessian line-ness response, and a multi-scale
persistence-survival channel; plus the 12-band public 1 m LiDAR fault-scarp stack and the
8 GeoDAWN radiometric/extension bands. No catalogue-distance, fault-density, tip or
continuation feature is admitted — those were measured to push a model into retracing the map
it was trained on.

**Emission.** Top-37,000 cells by belief under a hard 6 px (600 m) catalogue stand-off, thinned
to a 3 px Poisson-disk spacing → 37,000 dots, `spacing_proxy` 1.000 (no touching pixels),
0.0 % of mass within 300 m of any catalogued pixel, mean distance to catalogue 28.8 px,
mean distance to off-catalogue SGMC structure 28.0 px.

**Screens (falsification only).**

| Screen | CSP | Matched-budget random |
|---|---|---|
| catalogue fold (mean of 4 quadrant folds, catalogue ablation) | 0.151 | ≈0.065 floor (H5 protocol) |
| SGMC prevalence (5 component-preserving draws, 14.3–14.5 k px) | 0.061 | — |
| persistence stability of selected pixels (honest, unflattering) | ≥2 of the four scales survived at 6.3 % (dem), 6.7 % (mag), 9.9 % (grav) of selected pixels, against 5.9 / 5.3 / 5.4 % of the footprint — enrichment only 1.06× / 1.27× / 1.83× | — |

**Uniqueness.** Maximum Jaccard 0.0159 against the 15 prior artifacts recovered in the
workspace (12 sibling TIFs + this repo's three earlier builds); closest is `h19-5`. The
selection is not derived from any of them.

**Forecasts (geometry only, the ranking field gets no credit).** 0.278 (closest-geometry
precedent), 0.282 (8-map ladder regression), 0.282 (budget power law). Owner best 0.2778;
leaderboard top at last manual check 0.3262.

## 4. Why this is the honest best play this session

1. Every local instrument that could rank *fields* was measured to be invalid or flat against
   the live board, so shipping a field chosen by one of them would be faith, not evidence.
2. The only live signal available is geometry, and the CSP is engineered to match the best
   scored geometry exactly (same order of dot count, mean stand-off within 0.2 px) while
   replacing the ranking field with a strictly richer, multi-physics, label-free one.
3. The candidate is falsifiable and its failure modes are published: if the ranking field is
   worse than the ridge field it replaces, the geometry match should still hold the score
   near 0.278; if it is better, the ladder model is the floor and the upside is unmodelled.

## 5. Remaining work and limitations

* **Unmeasurable locally:** whether the CSP field beats the ridge field on the hidden truth.
  Only an organizer score can answer that; the file is a candidate for one weekly slot.
* **H6–H9 untested:** the register's remaining hypotheses (gravity/magnetic mismatch,
  drainage inversion, geothermal re-weighting, Quaternary conditioning) were impossible to
  rank honestly with invalid instruments. They need a new validation channel first — for
  example a three-slot live probe family on the DrivenData board (one anchor, one variant,
  one null), which is the only instrument that has ever agreed with the leaderboard.
* **Egress:** only GitHub and PyPI are reachable from this sandbox. 3DEP 10 m DEM (H7's
  optional upgrade) would need a repo GitHub-Actions runner.
* **Quantisation:** the external products are uint8 on the 100 m grid; their fine-scale claim
  is weakened by resampling from 2 m / airborne survey resolution.
