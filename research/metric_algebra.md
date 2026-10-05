# Metric algebra used by the emitter, and the score-ladder inversion

**Session:** 2026-10-05 · **Status:** derived from the official metric equations, then
checked numerically against the metric implementation in `gemsdoe37/dti.py`.

Every equation below is algebra on the published competition metric. The metric itself
is quoted verbatim from the problem description in [`sources.md`](sources.md); nothing
here depends on an organizer score of ours, because we do not have one.

---

## 1. The metric, in the form used here

For a binary truth set $G$ (the scored hidden faults), a prediction field
$p \in [0,1]$, kernel $k(d) = \max(1 - d/R, 0)$ with $R = 300$ m, and
$\alpha = 0.2$, $\beta = 0.8$:

```
T = TP_w = sum_{g in G} max_{x} p(x) k(d(x,g))
F = FP_w = sum_{x: p(x)>0} p(x) (1 - max_{g in G} k(d(x,g)))
FN_w     = G - T                    (binary truth, single best match per truth pixel)
DTI      = T / (alpha T + alpha F + beta G)                                      (1)
```

Line (1) is exact: $T + \alpha F + \beta(G - T) = \alpha(T+F) + \beta G$ because
$\alpha = 1 - \beta$. This form is convenient because $T$, $F$ and $G$ are all additive
over the prediction and over the truth, which makes the marginal rules below exact.

## 2. Binary beats graded (why every shipped file is 0/1)

Scale any support set by $\lambda \in (0,1]$: $T \to \lambda T$, $F \to \lambda F$, while
$G$ is unchanged. Then

```
DTI(lambda) = lambda T / (alpha lambda (T+F) + beta G)
d/dlambda  = beta T G / (alpha lambda (T+F) + beta G)^2  > 0                    (2)
```

so the index is strictly increasing in $\lambda$ and the maximum over $\lambda \in (0,1]$
is at $\lambda = 1$. **A graded probability map is strictly dominated by its own
thresholded support.** Consequence for this repository: emitting float probabilities is
never right; emit indicators.

## 3. Marginal inclusion rule (the emitter's decision rule)

Add one unit prediction whose kernel credit against its nearest truth pixel is $k$. Then
$T$ rises by *at most* $k$ (exactly $k$ when that truth pixel was uncovered or had a
smaller credit) and $F$ rises by exactly $1-k$, because $k$ is that dot's own kernel
distance term. The denominator of (1) therefore rises by exactly
$\alpha (k + 1 - k) = \alpha$, while the numerator rises by $k$, so

```
DTI_new > DTI  <=>  k (alpha (T+F) + beta G) > alpha T
              <=>  k > alpha * DTI                                                (3)
```

Equation (3) is the marginal break-even rule. At the leader's published score
$s = 0.3195$ it requires $k > 0.0639$, i.e. the dot must lie within
$R(1 - 0.0639) = 281$ m of a scored truth pixel.

## 4. Probability form (what the emitter actually implements)

A dot cannot know $k$ in advance, only the belief field's estimate
$p$ that a truth pixel lies within the kernel. Writing $\kappa$ for the mean credit of a
hit (a hit anywhere in the kernel gives $k \in (0,1]$; $\kappa \lesssim 0.5$ for a dot
placed anywhere inside the 3-pixel disc) and taking expectations in (3) with
$\Delta T = p\kappa$, $\Delta F = 1-p$:

```
p kappa (alpha (T+F) + beta G) > alpha T
p > alpha T / (kappa (D - alpha T) + alpha T),   D = alpha(T+F) + beta G = T / DTI
p > alpha / (kappa (1/DTI - alpha) + alpha)                                       (4)
```

Equation (4) is the emission rule. It says something counter-intuitive but important:
**the better the score, the higher the precision bar**, and the bar is set by the current
score, not by a budget.

| target DTI | threshold with $\kappa = 0.5$ |
| ---: | ---: |
| 0.25 | 0.096 |
| 0.30 | 0.113 |
| 0.35 | 0.130 |
| 0.40 | 0.148 |
| 0.50 | 0.186 |

So a candidate set that is 10–19 % precise at the 300 m kernel is worth emitting; a
candidate set that is 5 % precise is not. This is exactly the failure mode measured on
the prior lineage: the shipped 0.2778 file carries **37,654 dots for an estimated truth
mass of order $10^4$ pixels**, i.e. it operates far below the break-even precision,
which is why its own authors found that *deleting* dots (thinning, flank pruning) kept
raising the score.

## 5. Inverting the score ladder for the hidden truth mass

The public ladder of owner-reported scores is a sequence of nested or near-nested
emissions, so it can be inverted for two structural quantities that no single
submission can measure.

Take two emissions that differ by removing $n$ dots, and assume the removed dots were
pure false-positive mass (removed dots far from any truth pixel, each contributing
$\approx 1$ to $F$). From (1), $D_i = \alpha(T_i + F_i) + \beta G = T_i / s_i$, and
removing mass changes only $F$:

```
D_1 - D_2 = alpha (F_1 - F_2) = alpha n     =>     T = alpha n / (1/s_1 - 1/s_2)   (5)
```

Two independent steps on the same family give the same answer, which is the consistency
check that the assumption is not free:

| step | dots removed | $1/s_1 - 1/s_2$ | $T$ from (5) |
| --- | ---: | ---: | ---: |
| 44,090 → 40,199 (0.2600 → 0.2708) | 3,891 | 0.15339 | **5,073** |
| 40,199 → 37,654 (0.2708 → 0.2778) | 2,545 | 0.09276 | **5,489** |

The two estimates agree to 8 %, which supports the model but does **not** prove it; the
d15 → d28 step (60,069 → 44,090 px) gives 16,733 and is reported here as a failure of the
nesting assumption rather than hidden.

Combining $T \approx 5.1\text{–}5.5 \times 10^3$ with (1) at $s = 0.2778$ and the
constraint $F \le$ (number of dots) gives a closed interval for the scored truth mass

```
T + F = T/s - beta G / alpha  with F <= 37654   =>   G in [1.23e4, 2.17e4]        (6)
```

i.e. **roughly 12,000–22,000 scored truth pixels** (1,200–2,200 km of hidden trace at
100 m sampling). A sibling repository reached $N \approx 12,691$ px independently from a
different argument, which is consistent at the bottom of the interval.

Everything that follows from (1)–(6) for strategy:

1. Emission geometry is not the remaining lever — the prior lineage already thinned to
   the point where further thinning starts to remove recall.
2. **Precision is the lever.** With $T \approx 5\times10^3$ and ~3.6×10^4 dots, about
   90–95 % of the emitted mass is false-positive mass at $\alpha = 0.2$.
3. The right question is therefore not "which field ranks highest" but "which cells clear
   the 10–15 % kernel-precision bar of equation (4)".
