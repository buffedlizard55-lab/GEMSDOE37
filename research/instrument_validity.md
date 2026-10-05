# Instrument validity: what our local holdouts can and cannot do

Written 2026-10-05 (session 4), after the two local instruments were scored against the
public ladder of eight recovered, owner-reported, already-submitted maps.

**Bottom line.** Neither local instrument predicts the public score. The blocked
catalogue-fold instrument *anti-correlates* with it, and the SGMC-prevalence instrument is
effectively flat. They may be used to **falsify** an emission (a map that scores at chance on
a screen is still at chance) and to compare arms under *identical* protocol; they may not be
used to certify, rank, or forecast a live gain. That is why the shipped candidate's argument
is geometric (dot budget and stand-off), not holdout-based.

## 1. The instruments

| Instrument | Truth domain | Why it exists | Measured Spearman vs live (n = 8) |
|---|---|---|---|
| **Fold** (`data/work/belief_oof.npy` screens) | held-out catalogue fault pixels, quadrant-blocked, 40 px guard, catalogue ablation | tests whether a field transfers to *withheld mapped* faults | **−0.667** |
| **SGMC prevalence** (`data/work/sgmc_offcatalogue.npy`, component-preserving subsample to 15 k px) | USGS State Geologic Map Compilation structure pixels that are >3 px from every training-label pixel | tests whether a field finds off-catalogue *mapped* structure | **+0.143** |
| Geometry ladder (baseline only) | none — reads dot budget and stand-off | measures what the ladder actually responds to | **+0.99 (R², in-sample)** |

Source of the live column: the eight maps whose organizer scores the owner has published
(GEMSDOE24/28/32 sites): `h33-2-b2` 0.2778, `h27-4-solo-d28` 0.2708, `h25-dotted-d28`
0.2600, `h27-gapclosure` 0.2449, `h19-5` 0.1922, `h28-dotted-ridge` 0.1839, `ens12` 0.1563,
`h25-ctx-ridge` 0.1280. Full per-map numbers: `data/work/incumbent_instruments.json`.

## 2. Why the fold instrument inverts

The public truth is expert-identified geometry that the published catalogue does **not**
contain. The fold instrument's truth is the published catalogue itself. A map that hugs the
catalogue therefore wins the screen and loses the contest:

| Map | public DTI | fold instrument |
|---|---|---|
| `h33-2-b2` (deliberately pruned away from the catalogue) | **0.2778** | 0.004 |
| `h25-ctx-ridge` (mass on catalogue-dense ground) | 0.1280 | 0.142 |

Any hypothesis selection loop that maximises the fold instrument is therefore optimising in
the wrong direction. This was measured the hard way: the matched-budget arm that the fold
instrument preferred (0.2400) is not the arm the ladder prefers.

## 3. What the ladder actually rewards (measured, n = 8)

Public DTI against two geometry descriptors, fitted by ordinary least squares:

```
live ≈ 0.81841 − 0.06129·ln(positive pixels) + 0.00378·mean distance to catalogue (px)
n = 8   R² = 0.992   leave-one-out R² = 0.978   max LOO error 0.014
```

| Map | dots | mean distance to catalogue (px) | public DTI |
|---|---|---|---|
| `h33-2-b2` | 37,654 | 29.0 | 0.2778 |
| `h27-4-solo-d28` | 40,199 | 27.3 | 0.2708 |
| `h25-dotted-d28` | 44,090 | 25.0 | 0.2600 |
| `h27-gapclosure` | 61,328 | 24.5 | 0.2449 |
| `h19-5` | 121,131 | 24.8 | 0.1922 |
| `h28-dotted-ridge` | 69,281 | 14.3 | 0.1839 |
| `ens12` | 172,974 | 21.1 | 0.1563 |
| `h25-ctx-ridge` | 174,232 | 12.1 | 0.1280 |

Caveats, stated plainly: eight points, all authored by the same owner, with dot budget and
stand-off partly collinear, so the two coefficients should not be read as independent causal
effects. The safe reading is monotone in both directions — **fewer dots and a larger
stand-off are rewarded**, which is exactly what the owner's own pruning experiment
(`h33-2-b1` → `h33-2-b2`, 0.2708 → 0.2778) found directly.

## 4. Consequences for this session's build

1. The promotion gate is redefined as a **falsification gate**: the candidate must not be
   *worse than chance* on either screen, and must beat matched-budget random placement under
   identical protocol. It cannot be required to beat the fold instrument's best arm.
2. The shipped geometry is matched to the best-scoring precedent (37,654 dots at mean
   stand-off 29.0 px) rather than to any local optimum, because that is the only measured
   live signal available.
3. Every public-facing number is labelled a screen or a geometry forecast, never a predicted
   organizer score.
