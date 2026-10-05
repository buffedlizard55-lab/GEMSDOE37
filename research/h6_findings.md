# H6 session findings — 2026-10-05 UTC

Everything below is a measured output of a script in this repository. Receipts are
linked. Nothing here is an organizer score.

## 0. Inputs actually used, and their provenance

| File | SHA-256 | Source path used here |
|---|---|---|
| `training_features.tif` (19 bands) | `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5` | reassembled from `buffedlizard55-lab/GEMSDOE` `data/bridge/*.part-00{0..4}` |
| `labels.tif` (existing faults) | `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` | `data/bridge/existing_faults.tif` |
| `example_submission.tif` (grid template) | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` | `data/bridge/example_submission.tif` |

All three hashes match the pins recorded in that repository's
`data/bridge/manifest.json`, which in turn records the user-supplied Dropbox
mirrors of the DrivenData data tab. **This sandbox has no network route to
dropbox.com or to raw.githubusercontent.com** (verified: `curl` exit 35 / HTTP
`000`); only `github.com` is reachable, which is why the bridge was used.

Verified grid, read from the files themselves:
EPSG:32611, 3292 x 3730 cells, 100 m, 19 float32 bands,
footprint = 5,167,373 finite template cells of 12,279,160,
catalogue = 60,988 pixels with value 1 (label `-1` is exactly the outside-footprint set).

### Irregularities flagged for review

1. **The mirrored `example_submission.tif` is not a zero raster.** The official
   problem description says the sample "predicts total fault absence", but this
   file contains the 60,988 known-fault pixels at 1.0 (bit-identical to
   `labels.tif == 1`) and NaN outside the footprint. It is used here only as a
   grid/CRS/transform template, never as a prediction.
2. **Six catalogue pixels lie outside the template footprint** (60,988 labelled
   vs 60,982 inside the footprint). They are dropped from training.
3. Provenance is mirror-bridged, not freshly downloaded from an authenticated
   DrivenData session. Hashes are pinned; the chain of custody is not official.

## 1. The metric, re-derived (not assumed)

From the official definition
(`https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/`),
with `alpha = 0.2`, `beta = 0.8`, `k(d) = max(1 - d/300m, 0)`:

`FN_w = sum_g [1 - max_x p(x) k(d)] = |G| - TP_w` exactly, so

```
DTI = TP_w / (0.8 |G| + 0.2 TP_w + 0.2 FP_w)
```

Two consequences we actually use:

* **Binary emission is optimal for a fixed support.** Scaling every value by
  `c > 1` maps `(T, F) -> (cT, cF)` and `DTI -> cT / (0.8|G| + 0.2c(T+F))`,
  which is strictly increasing in `c`. So the best value to emit at a chosen
  pixel is `1.0`, never a soft probability. The builder emits binary.
* **An extra pixel pays when `dT > (0.2 DTI / (1 - 0.2 DTI)) dF`** — about
  0.06 units of newly covered truth per emitted pixel at DTI ≈ 0.28. The bar is
  low, which is why dotted emissions with spacing just under the 3-pixel kernel
  support (maximum new coverage per pixel) dominate solid lines.

Our local implementation `gemsdoe37/metric.py` follows this formula term by term.

## 2. Anatomy of the 0.2778 map (read from the file, not from prose)

`gemsdoe32-h33-h33-2-b2-...-zeros.tif`, fetched from `buffedlizard55-lab/GEMSDOE32`:

* 37,654 positive cells, values strictly in `{0, 1}` — binary, as the algebra above predicts;
* local-mass descriptor **1.000** — perfectly dotted, no two emitted cells touch;
* minimum distance to a catalogue pixel **2.236 px**, median **19.6 px** — the B=2 stand-off.

So its score comes from emission *geometry*, not from a strong detector: the same
dotting and stand-off rules sit under the 0.2600 / 0.2708 / 0.2778 family. That
is the lever this session attacks — the ranking itself.

## 3. What was actually run

### 3.1 Feature stack (`scripts/h6_build_features.py`)

94 label-free columns over the 5,167,373 footprint cells: 19 rank-normalised raw
bands; gradient-magnitude and Hessian ridge strength at sigma = 1, 2, 4, 8 px for
seven bands spanning five independent physics families (topography, magnetics,
gravity, electrical/basement, geodetic strain); a **scales-survived** count per
family (how many of the four smoothing levels keep the cell in the upper decile);
a persistence-weighted family consensus; the **H0 superlevel-set persistence**
(`gemsdoe37/persistence.py`, elder-rule union-find) of that consensus; and four
cross-family corroboration columns. No catalogue-derived column is included.

### 3.2 Quadrant holdout — `research/receipts/h6_holdout.json`

Pooled DTI over four spatial quadrants, catalogue hidden in the scored quadrant,
budget 160,000, spacing 2.9 px:

| Arm | Pooled DTI |
|---|---:|
| supervised physics GBM | **0.2486** |
| label-free persistence consensus (the family used by earlier repos) | 0.1530 |
| uniform random placement | 0.1957 |

At a 20,000 budget the gap is widest: 0.0947 (GBM) vs 0.0464 (label-free) vs
0.0418 (random). **The label-free persistence surface is not better than random
placement** — reproducing, with a cleaner protocol, the finding already recorded
in `research/score_analysis.md`. Persistence earns its place as one feature
family out of 94 and as a stability certificate, not as a detector.

### 3.3 Leave-fault-segment-out holdout — `research/receipts/h6_segment_holdout.json`

The protocol change that matters. The catalogue is cut into **3,199** 8-connected
segments; one third of the segments are hidden per fold; the model sees only the
rest; the hidden segments are the scoring truth. This mimics the actual task —
unmapped faults inside a region whose other faults are public.

Measured spatial statistics of the hidden faults (3 folds, consistent):

* 7.3–7.9 % of hidden fault pixels lie within 3 px of a visible fault (footprint base rate 5.8–6.0 %);
* 26.8–29.6 % within 6 px (base rate 11.4–11.8 %);
* ~75–78 % within 20 px; median distance ~9.5–10.4 px (≈1 km).

So unmapped faults are only ~2.4x enriched in the near-catalogue halo and
overwhelmingly sit about a kilometre away. That is the quantitative reason a
catalogue stand-off helps and a catalogue-hugging prediction fails.

| Arm (spacing 2.9 px, budget 80,000) | Pooled DTI |
|---|---:|
| physics-only GBM | **0.1973** |
| physics + catalogue geometry | 0.0688 |
| catalogue geometry only | 0.0688 |

The second and third arms are *bit-identical*, and that is not a bug: the
training positives are exactly the visible catalogue, so `distance-to-catalogue
== 0` separates the training set perfectly and the booster learns that single
rule, discarding all 94 physics columns. **Any model trained on catalogue labels
with catalogue-relative geometry features degenerates into redrawing the
catalogue.** This is the clean explanation for the harmful "cat" arm reported in
earlier sessions.

### 3.4 Emission-geometry sweep — `research/receipts/h6_sweep.json`, `h6_sweep_standoff.json`

33 configurations over cached per-fold score rasters. Monotone and unambiguous:

* stand-off **3 px > 2 px > 0 px** at every budget and spacing, and 3 px > 4 px > 6 px;
* spacing **2.9 px > 3.5 px** at every budget and stand-off;
* budget optimum at **80,000** (60k–100k is a flat plateau; 120k+ decays).

Best configuration **b80000_s2.9_o3.0 → pooled DTI 0.21383**, and it is the top
configuration in **3 of 3 folds** individually (0.2176 / 0.2132 / 0.2107). That
clears the preregistered promotion rule (beat the incumbent pooled, no fold
regression) against the untuned physics baseline at 0.1973.

### 3.5 Comparator caveat — `research/receipts/h6_reference_maps.json`

Scoring the historical 0.2778 raster on this holdout gives ~0.005, and the
earlier H5 26k raster gives exactly 0.000. **Neither number means anything**: both
maps were built with a stand-off measured against the *full* catalogue, so by
construction every one of their dots is ≥2.24 px (H33) or ≥3.16 px (H5) from the
hidden segments, and at 3.16 px = 316 m the triangular kernel is already zero.
The holdout therefore cannot rank historical maps, only configurations built
inside it. This is recorded so no one reads those numbers as a win.

## 4. The published candidate

`docs/downloads/gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c.tif`

* physics-only HistGradientBoosting ranker, 94 features, fitted on all 60,982
  in-footprint catalogue pixels plus 600,000 sampled negatives ≥3 px away;
* 3 px stand-off from every mapped fault; 2.9 px score-ordered Poisson-disk dotting;
* 80,000 binary dots, local-mass descriptor 1.000, zero dots on the catalogue,
  zero dots outside the footprint, median dot-to-catalogue distance 8.06 px;
* reopened from disk and checked: single-band float32, exact template shape, CRS,
  transform, resolution and bounds, no nodata tag, **all 12,279,160 cells finite
  and inside [0,1]** (this is what fixes the portal's
  "Predicted values must be in range [0, 1]" rejection);
* SHA-256 `ce749a992baec603460dfeddd068758855cb8b12978268e6ef94f6e23ffd9ee7`;
* maximum Jaccard overlap with any earlier submission raster available to this
  sandbox: **3.5 %** (H5 26k), 1.7 % against the 0.2778 map. It is a new map.

## 5. Honest limits

1. The holdout truth is hidden *catalogue* segments, not the private expert
   new-fault set. It ranks configurations; it does not forecast a leaderboard number.
2. The budget optimum depends on the unknown size of the private truth set
   through the `0.2 n / |G|` term. 80,000 is the optimum for a truth set of
   ~20,000 pixels; a much smaller private set would favour a smaller budget.
3. No organizer score exists for this file.
4. Provenance of the input bytes is mirror-bridged (see §0).
