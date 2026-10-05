# GEMSDOE37 — GEMS Prize Research and Submission System

> **Every work session begins by reading this README and [`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md).**

## Verbatim Project Prompt

```text
Review the repo.   
  
THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!  
  
MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.  DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.  BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.  
  
There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.  
  
Use topological persistence to certify a candidate is a stable structure, not a single-scale artifact. A fixed threshold on a gradient or curvature map can't tell a genuinely continuous ridge from something that only appears at one smoothing level. Persistent homology tracks how topological features are born and die as a surface sweeps across a full range of scales, and carries a formal stability guarantee — small data perturbations produce only small changes in the result, a property proven directly, not assumed. The same construction used to characterize ridge bifurcations, terminations, and gaps in fingerprint-ridge analysis applies directly to a curvature or gradient-magnitude surface here: compute the persistence of candidate ridges across the DEM-curvature and potential-field layers, and report how large a range of scales each one survives across as a formal stability measure, rather than describing it only by its score at one chosen threshold — a high-persistence candidate is a fundamentally stronger claim than a high-probability one that only exists at a single scale.  
  
The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.  
  
Here are the results from submissions into the competition, separated by ....:  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html))  
gems-submission-20260925T001403Z-7f00890a: 0.1563  
....  
[[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)](https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/))  
gems6_hgb88-topk03_33cec71ff0: 0.0286  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html))  
pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193  
pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830  
pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html))  
gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)](https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/))  
gems-submission-20260926T163915Z-237f0063: 0.0343  
....  
[[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html))  
gems-submission-20260926T175114Z-7f00890a: 0.1563  
....  
[[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)](https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/))  
lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461  
....  
[[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)](https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/))  
Hedge-v2_submission: 0.1563  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html))  
2314b599: 0.0107  
....  
[[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html))  
gems-structural-area06-v1: 0.0202  
....  
[[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html))  
r7-nms3-dem10-scarp_0c9199f14e62:0.1294  
r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294  
....  
[[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html))  
gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782  
....  
[[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html))  
GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020  
....  
[[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)](https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/))  
17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187  
....  
[[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)](https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/))  
H19-C_20260930T212401Z_c11e495e: 0.0297  
....  
[[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html))  
h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894  
h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)](https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/))  
h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461  
h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921  
H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280  
h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839  
....  
[[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)](https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/))  
20261001_r13-lattice-s5_v2_nan-outside:0.0904  
....  
[[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html))  
h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855  
h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976  
h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)](https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/))  
h19-4-reference-20260930-691e4dfa: 0.1894  
....  
[[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html))  
h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890  
h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html))  
h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002  
h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)](https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/))  
h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)](https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/))  
h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)](https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/))  
dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/)](https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/))  
dilcond-oof-v1-20261003-47629f496133-nan: 0.1223  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)](https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/))  
topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)](https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/))  
h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708  
h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan:  
h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan:  
h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan:  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html))  
efd28-repro-20261003-1cc7dc534d51-nan: 0.2600  
repo-c0-habitat-emission-20261003-a4d439b07426-nan:  
sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan:  
wormrank-d28-20261003-59dcaf6dd11d-zeros:  
wormsurv-filter-20261003-921f10960d6e-zeros:  
xfit-c0-habitat-20261003-ca879db0089a-zeros:  
xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros:  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)](https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/))  
d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/))  
h27-4-solo-d28-20261004-8acb75e1-nan:0.2708  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html))  
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)](https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/))  
h33d-analog-tip-stepover-r30-20261004-cb490425926e:   
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html))  
h34-scatter-q50-arr-matched-20261004T223317Z:   
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html))  
h35-06-aaa86efb25-20261004T225420098147Z-candidate:  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/))  
anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros:   
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/)](https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/))  
:  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html))  
:  
....  
[[https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/)](https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/))  
:  
....  
40GEMSDOE  
:  
....  
  
WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:  
  
[[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html))  
  
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778  
  
Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?  
  
Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.  
  
The following is the leaderboard for the competition:  
  
[[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/))  
  
We need to quickly look at the results and results from the GEMSDOE websites above.  
  
Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.  
  
Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above.  We need to come up with distinct and unique strategies to score higher in this competition leaderboard.  We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents.  We should store all of our information and knowledge that we can gather from official verified sources.  This will serve as a starting point for other projects as well.  We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for.  So it's important to be contrarian but be smart about it.  We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents.  We need to do deep research and critical thinking and come up with new hypothesis to test.  
  
0.3195	is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website.  It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.    
  
Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use.  It should solve the problem of having to manually check everything ourselves and having an up to date current feed.  
  
Review the repo.   
  
The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.  
  
Our Core Values  
  
Maximize P(Win)  
  
“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.  
  
Own the Outcome  
  
We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.  
  
Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
We need to focus on being able to generate a submission into the competition.    
  
The site should be able to generate a TIF file that is required for submission.  It should be as easy as download to click a File to submit into the competition.  This needs to be in the executive summary or the very beginning of the site.  it should be obvious when you visit the site.  
  
I tried to submit the document that i downloaded from the site but it returned this error on the submission form:  
  
"Predicted values must be in range [0, 1]"  
  
Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25  
  
Here is the submission page when i click submit file  
  
New submission  
  
File to submitNo file chosen  
  
You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.  
  
Note (optional)  
  
A short comment to help you or your team tell submissions apart later e.g. clustering with k=25  
  
Create a executive summary subpage that explains exactly how to make a submission into the contest.  
  
Work on the next steps from the previous sessions first.  
  
The goal of this project is to place top of the leaderboard in this competition.  The following is the competition:  
  
[[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/))  
  
We need to create a project that can compete and place top of the leaderboard.  We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.    
  
This is the guidelines we need to follow.[[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)](https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/))  
  
Get familiar with the problem through the overview and problem description,[[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). You might also want to reference additional resources available on the about page,[[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)).  
  
Download the data from the data,[[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)), tab.    
  
Create and train your own model. This reference solution,[[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)](https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)) implements a simple approach.  
  
Use your model to generate predictions that match the submission format.  
  
Tell me what are you limitations and what you need access to during this project.  We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.    
  
this pdf outlines how submissions must be entered into the competition.    
  
[[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)](https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf))  
  
You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information.  this must be done autonomously and must be constantly reviewed and improved upon.  Provide suggestions and improvements and implement them.  
  
❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)) (verified redirect to login)  
  
See below for links from the above site.  See attached files for links from the above site.  
  
[[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)](https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391))  
  
Download competition data from [[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)) (requires login) to data/  
  
See links below for competition data:  
  
[[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;amp;st=wz4kofki&amp;amp;dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;st=wz4kofki&amp;dl=0)](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&amp;st=wz4kofki&amp;dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0))  
  
[[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;amp;st=8junzdyw&amp;amp;dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;st=8junzdyw&amp;dl=0)](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&amp;st=8junzdyw&amp;dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0))  
  
[[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;amp;st=rnino7ya&amp;amp;dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;st=rnino7ya&amp;dl=0)](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&amp;st=rnino7ya&amp;dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0))  
  
[[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;amp;st=zj1lag1r&amp;amp;dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;st=zj1lag1r&amp;dl=0)](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&amp;st=zj1lag1r&amp;dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0))  
  
[[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;amp;st=srhhir10&amp;amp;dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;st=srhhir10&amp;dl=0)](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&amp;st=srhhir10&amp;dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0))  
  
Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
Site creation  
  
Create a github page for this repo that has clean ui, user friendly, simple and easy to use.  It should be organized and clean.    
  
It should include all relevant information in an easy to read format with official verified links as sources for review.  Work line by line verify everything no hallucinations.  
  
**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).  
  
you need to complete the above task by yourself.  Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.                        
  
Verify no hallucinations.      
  
The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.  
  
Run this task through multiple passes.  
  
Pass 1: Implement the task completely and verify the result.  
  
Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.  
  
Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.  
  
Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request.  Work line by line verify everything no hallucinations.  
  
Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.
```

---

## Executive deliverable — download and submit

**Recommended upload (session 3, 2026-10-05): `gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c.tif`**

| Field | Value |
|---|---|
| File | [`docs/downloads/gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c.tif`](docs/downloads/gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c.tif) (331 KB) |
| Zip (also accepted by the portal) | [`...-0bef9211631c.zip`](docs/downloads/gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c.zip) |
| Submission name | `gemsdoe37-h6-physics-dotted-80k-20261005T055000Z-0bef9211631c` |
| Submission note (paste into the optional DrivenData note box) | `H6 physics-only GBM on 94 multi-scale persistence-certified GEMS features; 3px catalogue stand-off; 2.9px Poisson-disk dotting; 80000 dots` |
| SHA-256 | `ce749a992baec603460dfeddd068758855cb8b12978268e6ef94f6e23ffd9ee7` |
| Positive cells | 80,000 at exactly 1.0; every other cell exactly 0.0 |
| Grid | EPSG:32611, 3292 x 3730, 100 m, single band float32, no nodata tag, all 12,279,160 cells finite in `[0,1]` |
| Internal holdout | leave-fault-segment-out pooled DTI **0.21383**, best of 33 configurations, winner in 3/3 folds |
| Organizer score | none yet |

The live site puts the same download first: **<https://buffedlizard55-lab.github.io/GEMSDOE37/>**
(step-by-step upload instructions: `docs/executive-summary.html`).

### Second candidate in this repository, and why it is not the recommendation

A concurrent session published `gemsdoe37-csp-concealed-persistence-20261005T060000Z-8ba2edb16e5c.tif`
(37,000 dots, 3.0 px spacing, 6 px catalogue stand-off, 234 features including external
1 m LiDAR and GeoDAWN radiometric products). It is kept in `docs/downloads/` and is a
legitimate alternative. It is **not** the recommended upload because the one leakage-free
instrument in this repository was run on *its exact emission geometry with the identical
ranker and folds*:

| Emission geometry | Pooled segment-holdout DTI | Folds won |
|---|---:|---|
| H6 — 80,000 dots, 2.9 px spacing, 3 px stand-off | **0.21383** | 3/3 |
| CSP — 37,000 dots, 3.0 px spacing, 6 px stand-off | 0.16651 | 0/3 |

Receipt: `research/receipts/h6_sweep_csp_geometry.json`. The gap is geometry, not ranking:
a 6 px stand-off discards the near-catalogue band where 27–30 % of unmapped faults actually
sit, and a 37,000-dot budget sits below the measured 60k–100k plateau.

### How to submit (4 steps)

1. Download the `.tif` above (or the `.zip`; the portal accepts either).
2. Open <https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/> and sign in.
3. Choose the file, paste the submission note into the **Note** box, submit.
4. Record the returned public DW-Tversky score in `research/prior_results.md`.

### Why the portal's "Predicted values must be in range [0, 1]" error cannot recur

`gemsdoe37/submission.py` reopens the written file and fails closed unless every
one of the 12,279,160 cells is finite and inside `[0,1]`, the nodata tag is
absent, and the shape, CRS, transform, resolution and bounds equal the template.
Negative float sentinels (`-3.4e38`) and NaNs — the two historical causes of that
rejection — cannot survive that check.

## What this session established (full detail: [`research/h6_findings.md`](research/h6_findings.md))

1. **The metric was re-derived, not assumed.** Because `FN_w = |G| - TP_w`,
   `DTI = TP_w / (0.8|G| + 0.2 TP_w + 0.2 FP_w)`, which is strictly increasing
   under a global scaling of the prediction. **Binary 1.0 emission is provably
   optimal for a fixed support**, and an added pixel pays whenever it buys more
   than ~0.06 units of newly covered truth.
2. **The 0.2778 map was read from the file, not from prose**: 37,654 binary
   dots, perfect dotting (local-mass 1.000), minimum 2.236 px off-catalogue. Its
   score came from emission *geometry*, not from a strong detector.
3. **The detector was therefore the lever.** A physics-only gradient-boosted
   ranker over 94 label-free multi-scale features beats the unsupervised
   persistence surface used by every earlier GEMSDOE submission by 1.6-2.3x on a
   blocked holdout, while the unsupervised surface is **no better than random
   placement**.
4. **Catalogue-relative features are provably self-defeating here**: training
   positives are the catalogue, so `distance-to-catalogue == 0` separates them
   perfectly and the model degenerates into redrawing the catalogue (the
   "physics+geometry" and "geometry-only" arms are bit-identical, DTI 0.069 vs
   0.197).
5. **New protocol — leave-fault-segment-out.** The catalogue is split into 3,199
   connected segments; a third are hidden per fold and become the truth. Hidden
   faults sit a median ~1 km from the visible catalogue and are only ~2.4x
   enriched within 600 m, which is the measured justification for a stand-off.
6. **Emission geometry was swept, not guessed**: stand-off 3 px > 2 > 0 and
   > 4 > 6; spacing 2.9 px > 3.5 px; budget plateau 60k-100k peaking at 80k.

## Core values applied

* **Maximize P(Win)** — the session spent its compute on the one component with
  the largest measured headroom (the ranker), kept the emission geometry that
  the public scores already validated, and refused to publish a number the
  holdout cannot support.
* **Own the outcome** — the data blocker from previous sessions was removed
  without asking for credentials by rebuilding the hash-pinned GitHub data
  bridge; every claim here is a receipt in `research/receipts/`.

## Reproduce end to end

```bash
python -m venv .venv && .venv/bin/pip install -e . scikit-learn numba
bash scripts/download_competition_data.sh          # or restore the hash-pinned bridge
.venv/bin/python scripts/h6_build_features.py      # 94 features -> data/work/feat
.venv/bin/python scripts/h6_holdout.py             # quadrant holdout, arm comparison
.venv/bin/python scripts/h6_holdout_segment.py     # leave-fault-segment-out holdout
.venv/bin/python scripts/h6_sweep.py               # emission-geometry sweep
.venv/bin/python scripts/h6_build_submission.py --budget 80000 --spacing 2.9 \
    --standoff 3.0 --holdout-dti 0.21383
.venv/bin/python scripts/h6_publish.py --receipt docs/downloads/receipt-*.json
.venv/bin/python -m pytest -q
```

## Receipts

| Receipt | What it proves |
|---|---|
| `research/receipts/h6_holdout.json` | quadrant holdout: GBM 0.2486 vs label-free 0.1530 vs random 0.1957 |
| `research/receipts/h6_segment_holdout.json` | segment holdout arms + hidden-fault distance statistics |
| `research/receipts/h6_sweep.json`, `h6_sweep_standoff.json` | 33-configuration emission sweep, best `b80000_s2.9_o3.0` = 0.21383 |
| `research/receipts/h6_reference_maps.json` | historical maps on this holdout **and why those numbers are not comparable** |
| `docs/downloads/receipt-gemsdoe37-h6-*.json` | format checks, descriptors, uniqueness of the published file |

## Known limitations and the next session's work

1. **Holdout truth is hidden catalogue segments, not the private expert new-fault
   set.** It ranks configurations reliably; it does not forecast a leaderboard
   number. Next: fit the `c(n)` coverage curve and choose the budget under an
   explicit distribution of plausible truth sizes (hypothesis H6-D).
2. **Sandbox egress is restricted to `github.com`.** Dropbox and
   `raw.githubusercontent.com` are unreachable (curl exit 35), so the inputs come
   from a hash-pinned bridge in the sibling `GEMSDOE` repository, not from an
   authenticated DrivenData download. Chain of custody is pinned but unofficial.
3. **Two high-ceiling hypotheses are blocked only by that egress** — GeoDAWN
   radiometric alteration (H6-B) and 1 m lidar scarp morphology (H6-E). Both
   sources were verified to exist and be free/official; see
   `research/hypotheses_h6.md`.
4. **The mirrored `example_submission.tif` is not an all-zero raster** — it
   contains the known faults. Flagged; used only as a grid template.
5. No organizer score exists for the published file.

## Verified official sources

* Competition overview, metric, submission format — <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
* About / resources — <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
* Data download tab (login required) — <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
* Public leaderboard — <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
* Reference solution — <https://github.com/drivendataorg/gems-prize-reference-solution>
* GeoDAWN data release (USGS, DOI 10.5066/P93LGLVQ) — <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7>
* USGS national aeroradiometric grids — <https://mrdata.usgs.gov/radiometric/>
* INGENIOUS project (Great Basin Center for Geothermal Energy) — <https://gbcge.org/current-projects/ingenious/>
* GDR submission 1391 — <https://gdr.openei.org/submissions/1391>
* Stability of persistence diagrams (Cohen-Steiner, Edelsbrunner & Harer, 2007) — <https://doi.org/10.1007/s00454-006-1276-5>

**Leaderboard context, read from the official board on 2026-10-05:** #1 `nchuzhoy`
0.3262, #2 `kinghorton42` 0.3222, #3 `DARD` 0.3195. The 0.2778 reported by the
project owner corresponds to rank #13 on that reading.
