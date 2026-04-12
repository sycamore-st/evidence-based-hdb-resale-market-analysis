---
title: "Do Outer HDB Towns React More To COE Shocks Than Central Towns?"
kicker: "Section 3 / Question D"
description: "A differential-sensitivity study comparing COE exposure in Sengkang/Punggol versus central control towns."
section: "section3"
slug: "question-d"
order: 4
---

# Do Outer HDB Towns React More To COE Shocks Than Central Towns?

## Business Context

A common housing-market hypothesis is that households trade off **where they live** against **how much it costs to own a car**. If that trade-off is real, then outer-rim towns should be more exposed to Certificate of Entitlement (COE) shocks than central towns, because households in peripheral locations may depend more heavily on private transport.

This study evaluates whether HDB prices in outer towns react more strongly to COE movements than prices in central control towns.

## Scope and Constraints

The design is deliberately relative. We are not asking whether COE matters for all HDB prices in the same way. We are asking whether the **far-town response exceeds the central-town response**.

The town groups are:

- **Far Towns (Treatment):** `SENGKANG`, `PUNGGOL`
- **Central Towns (Control):** `CENTRAL AREA`, `TOA PAYOH`, `KALLANG/WHAMPOA`, `QUEENSTOWN`, `BUKIT MERAH`

The key estimand is therefore the **interaction term**, not the raw co-movement between prices and COE.

## Step 1: Inspect the Raw Time-Series Pattern

Before fitting a regression, we first check whether the broad price paths are even consistent with the hypothesis. The chart below places the indexed housing series beside the indexed COE series.

<iframe src="/outputs/section3/charts/S3QdF1_indexed_coe_and_resale_trends.html" title="Indexed COE and resale trend" data-caption="Fig 1 — Indexed COE premium and HDB resale price trends for far and central towns. X-axis: month; y-axis: indexed value (start = 100). This chart is used to see whether the outer-town housing series visually moves more with COE cycles than the central series."></iframe>

This figure is included because the regression result should not arrive as a surprise. If the outer-town and central-town series looked indistinguishable here, there would be little reason to expect a meaningful interaction effect later.

The visual pattern suggests that the far-town housing series does react more strongly during periods of elevated COE pressure. That is only descriptive evidence, but it provides the first justification for testing a differential-sensitivity model.

## Step 2: Focus on the Relative Gap

The next chart tightens the question by looking directly at the **far-minus-central spread** after composition adjustment.

<iframe src="/outputs/section3/charts/S3QdF2b_adjusted_far_vs_central_index_spread.html" title="Adjusted far-versus-central spread" data-caption="Fig 2 — Adjusted price spread between far and central towns over time. X-axis: month; y-axis: spread in adjusted index points. If the spread widens during high-COE periods, the relative-sensitivity hypothesis becomes more plausible."></iframe>

This chart is necessary because the hypothesis is relative, not absolute. We do not merely want to know whether both groups move with COE. We want to know whether the *gap* between them widens in the expected direction when car ownership becomes more expensive.

The spread chart shows that the adjusted gap does expand during higher-COE episodes, which is exactly the pattern the interaction model is designed to formalize.

## Step 3: Check the Pattern Using Adjusted Housing Indices

Raw price movements can be distorted by changing transaction mix. If one group happens to sell older flats or smaller flats in a given period, the raw series may move for compositional reasons rather than because of true market sensitivity.

That is why the next chart uses adjusted housing indices.

<iframe src="/outputs/section3/charts/S3QdF1b_adjusted_indexed_coe_and_resale_trends.html" title="Adjusted indexed COE and resale trend" data-caption="Fig 3 — Composition-adjusted indexed trends for the far-town and central-town groups. X-axis: month; y-axis: adjusted housing index (start = 100). This verifies whether the outer-town sensitivity pattern survives after controlling for changing transaction composition."></iframe>

This figure matters because it asks whether the story still holds once the comparison is cleaned up. The persistence of the pattern in the adjusted index suggests that the outer-town sensitivity signal is not just a by-product of changes in flat mix.

The adjusted index is built in two steps. First, we estimate a **hedonic regression** separately for the far-town group and the central-town group, regressing transaction prices on flat age, floor area, flat type, and month fixed effects. This strips out composition effects and produces a month-by-month fitted price level for a like-for-like representative unit within each group. Second, we exponentiate those month effects and rebase the resulting series to 100 at the starting month. The result is a hedonic housing index: a time series intended to reflect price movement rather than changes in what happened to transact.

## Step 4: Estimate the Raw-Price Interaction Model

The first formal model is estimated on median resale prices:

$$
\begin{aligned}
\log(\text{MedianPrice}_{j,t})
=\;& \alpha
+ \beta_1\log(\text{COE}_t)^*
+ \beta_2\text{FarTown}_j \\
&+ \beta_3\left(\log(\text{COE}_t)^* \times \text{FarTown}_j\right) \\
&+ \delta_j
+ \lambda_t
+ \varepsilon_{j,t}
\end{aligned}
$$

Where:

- $\text{MedianPrice}_{j,t}$ is the median resale price for town group $j$ in period $t$.
- $\log(\text{COE}_t)^*$ is the logged COE price measure.
- $\text{FarTown}_j$ equals 1 for Sengkang/Punggol and 0 for the central control group.
- $\beta_3$ is the interaction term of interest: the extra COE sensitivity of far towns relative to central towns.
- $\delta_j$ and $\lambda_t$ absorb group and time effects.

The most important coefficient is $\beta_3$. Economically, it asks: when COE rises by 1%, do far-town prices move more than central-town prices, after netting out the average central-town response? A positive $\beta_3$ supports the housing-versus-car substitution story; a zero coefficient would imply no meaningful differential exposure; a negative coefficient would suggest that higher car costs are more of a drag than a substitution catalyst for outer towns. The baseline COE term, $\beta_1$, should be read as the elasticity for the central control group, while the total far-town elasticity is $\beta_1 + \beta_3$.

<iframe src="/outputs/section3/charts/S3QdF4_coe_regression_coefficients.html" title="Raw model coefficients" data-caption="Fig 4 — Coefficient plot for the raw-price interaction model. It separates the baseline central-town COE elasticity, the incremental far-town sensitivity, and the implied total far-town elasticity. The purpose is to make the interaction term economically interpretable."></iframe>

**Raw-price results**

- **Central-town elasticity:** 25.54%
- **Incremental far-town sensitivity ($\beta_3$):** 3.17% ($p = 0.0609$)
- **Total implied far-town elasticity:** 28.70%

This chart is included because the interaction coefficient is difficult to interpret in isolation. The coefficient view makes clear that the far-town differential is positive, but only borderline significant in the raw-price specification.

## Step 5: Re-estimate on Adjusted Housing Indices

To reduce the influence of changing transaction composition, the analysis is repeated using adjusted housing indices:

$$
\begin{aligned}
\log(\text{AdjIndex}_{g,t})
=\;& \alpha
+ \theta_1\log(\text{COE}_t)^*
+ \theta_2\text{FarTown}_g \\
&+ \theta_3\left(\log(\text{COE}_t)^* \times \text{FarTown}_g\right)
+ \varepsilon_{g,t}
\end{aligned}
$$

Where:

- $\text{AdjIndex}_{g,t}$ is the composition-adjusted housing index for group $g$ in period $t$.
- $\theta_3$ is the parameter of interest, measuring incremental far-town sensitivity after adjustment.
- The remaining terms retain the same interpretation as in the raw-price model.

This adjusted specification is the preferred one because the dependent variable has already been purged of shifts in flat age, floor area, and flat-type mix. That changes the interpretation in a useful way: $\theta_3$ is no longer "extra sensitivity of whatever happened to transact in far towns." It is the extra COE sensitivity of the **far-town hedonic index** relative to the central hedonic index. In other words, it is a cleaner estimate of differential market response rather than differential sample composition.

<iframe src="/outputs/section3/charts/S3QdF5_adjusted_index_regression_coefficients.html" title="Adjusted model coefficients" data-caption="Fig 5 — Coefficient plot for the adjusted-index model. This is the most policy-relevant figure because it shows whether the far-town sensitivity remains after filtering out composition effects."></iframe>

**Adjusted-index results**

- **Central-town elasticity:** 29.04%
- **Incremental far-town sensitivity ($\theta_3$):** **7.33%** ($p = 0.00739$)
- **Total implied far-town elasticity:** **36.36%**

This is the strongest chart on the page. Once the analysis moves to adjusted housing indices, the extra far-town COE exposure becomes both economically larger and statistically much clearer.

## Interpretation

The evidence supports the hypothesis of **differential sensitivity**: outer-town HDB prices respond more strongly to COE shocks than central-town prices.

The logic of the page is cumulative:

- the descriptive time-series suggests the pattern,
- the spread chart shows that the relative gap widens,
- the adjusted index confirms the signal survives composition cleanup,
- and the adjusted interaction model shows that the differential effect is statistically credible.

This is consistent with a household trade-off between housing location and transport cost. In practical terms, outer-town valuations appear more exposed to fluctuations in the cost of car ownership.

## Recommended Strategy

1. **Forecasting and pricing:** treat COE volatility as a higher-weight driver when modeling outer-town demand and pricing.
2. **Infrastructure monitoring:** track whether improved public-transport connectivity weakens this outer-town sensitivity over time.
3. **Risk management:** incorporate the stronger COE exposure of Sengkang and Punggol into regional market-risk assessments.
