# Prior-submission and score-claim ledger

**Accessed/reviewed:** 2026-10-05 UTC. This ledger separates organizer-visible public scores from owner- or user-reported artifacts. The public leaderboard does not reveal the submitted TIFF filenames or feature pipeline for another participant.

## Official public leaderboard snapshot

| Public rank | Participant | Score | What is actually known |
|---:|---|---:|---|
| 1 | nchuzhoy | 0.3262 | Official public board, visible at retrieval time. Submission method/file unknown. |
| 2 | kinghorton42 | 0.3222 | Official public board. Submission method/file unknown. |
| 3 | DARD | 0.3195 | Official public board. This is the value the original task described as the leader, but it ranked third in this snapshot. Submission method/file unknown. |
| 13 | extradr19 | 0.2778 | Same numeric value as the user-supplied H33 score claim; the leaderboard does not link this participant to that TIFF. |

Source: [official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). Board is dynamic; see the site's dated [snapshot feed](../docs/leaderboard.html).

**Method attribution limit:** no public leaderboard row identifies a TIFF, note, model, or feature method. We cannot explain the methods behind the current top three from that board alone; doing so would be speculation. The official [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) is a public U-Net baseline, not evidence about these participants' submissions.

## Sibling-project reports (not organizer verified)

The [GEMSDOE32 owner site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) and its linked receipts are first-party experiment reports, not organizer score records:

| Artifact or experiment | Owner-reported detail | Evidence class / limitation |
|---|---|---|
| H19-5 dotted raster | The owner site identifies a 44,090-pixel H19-5 file as its own best at 0.2600. It describes the score as an owner claim and attributes gains to sparse dot-thinning / credit-density, but supplies no organizer-verified receipt in the retrieved summary. | Owner-reported score and explanation. Not a high public-leader score; cannot establish the actual portal score. |
| H33-2-B2 “zeros” raster | The owner page describes a removal-only change from a user-reported 0.2708 base: deletes candidate dots within 2 pixels of the catalogue, leaving 37,654 positives. Its owner-side four-fold proxy reports +0.004870 across 4/4 folds, a “safety” factor 2.08, and a projected 0.2747. The page explicitly says no organizer score existed for its artifacts at publication. | Owner-reported proxy and model projection, not a competition score. The user-supplied task list associates the file with 0.2778; the public leaderboard's unrelated-looking `extradr19` row at 0.2778 does not prove that association. |
| H32D / H33 comparisons | The owner site describes a 46,090-pixel H32D multi-physics candidate with selected structural/geophysical additions and provides owner-side Monte Carlo comparisons. | Educational method history only; models depend on owner-inferred hidden-label distributions. No claim of organizer-scored performance is adopted here. |

The pinned H33 raster is fetched only by `scripts/fetch_educational_baseline.sh` for matched-budget evaluation. It is never used as the GEMSDOE37 prediction surface or placed in the site's download folder.

## What the metric suggests—and what it does not

The official DTI uses α=0.2, β=0.8 and a 300 m triangular distance kernel. The metric favors prediction mass that supplies new nearby credit and penalizes unsupported mass; therefore thinning a dense surface can improve a proxy score if it removes redundant false-positive mass while preserving useful coverage. That is a plausible explanation for the sibling project's **reported** sparse-thinning result, not an independently verified causal account of its organizer score.

The official board provides no method details for the actual leading submissions. GEMSDOE37's multiscale persistence experiment is a separate hypothesis; it has not been compared to any of these artifacts on verified challenge data and has no score.
