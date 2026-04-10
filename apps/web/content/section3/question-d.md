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

A common market hypothesis suggests that homebuyers may optimize their budgets by trading off residential location against car ownership costs. If this trade-off holds, property values in outer towns should exhibit greater sensitivity to Certificate of Entitlement (COE) price fluctuations. The objective of this study is to determine if outer HDB towns react more aggressively to COE "shocks" than central control towns.

## Scope and Constraints

The analysis utilizes a relative-sensitivity research design, categorizing towns based on their proximity to the urban core:

- **Far Towns (Treatment):** `SENGKANG`, `PUNGGOL`.
- **Central Towns (Control):** `CENTRAL AREA`, `TOA PAYOH`, `KALLANG/WHAMPOA`, `QUEENSTOWN`, `BUKIT MERAH`.

The primary metric of interest is the **interaction term**, which quantifies the incremental sensitivity of far towns relative to the central baseline, rather than the simple co-movement of prices.

## Step 1: Exploratory Data Analysis (Relative Market Movement)

<iframe src="/outputs/section3/charts/S3QdF1_indexed_coe_and_resale_trends.html" title="Indexed COE and resale trend"></iframe>

<iframe src="/outputs/section3/charts/S3QdF1b_adjusted_indexed_coe_and_resale_trends.html" title="Adjusted indexed COE and resale trend"></iframe>

<iframe src="/outputs/section3/charts/S3QdF2b_adjusted_far_vs_central_index_spread.html" title="Adjusted far-versus-central spread"></iframe>

Visual inspection of the indexed trends suggests a potential divergence in price reactions during periods of COE volatility. However, these descriptive trends necessitate econometric validation to account for underlying market cycles.

## Step 2: Raw Price Interaction Model

The initial model evaluates the elasticity of median resale prices in relation to COE prices:

$$
\log(\text{MedianPrice}_{j,t})
=
\alpha
+ \beta_1\log(\text{COE}_t)^*
+ \beta_2\text{FarTown}_j
+ \beta_3\left(\log(\text{COE}_t)^* \times \text{FarTown}_j\right)
+ \delta_j + \lambda_t + \varepsilon_{j,t}
$$

**Results from the Raw-Price Specification:**

- **Central-Town Elasticity:** 25.54%
- **Incremental Far-Town Sensitivity ($\beta_3$):** 3.17% ($p = 0.0609$)
- **Total Implied Far-Town Elasticity:** 28.70%

In this specification, the differential effect is directionally positive but fails to meet the standard threshold for statistical significance.

<iframe src="/outputs/section3/charts/S3QdF4_coe_regression_coefficients.html" title="Raw model coefficients"></iframe>

## Step 3: Adjusted-Index Interaction Model

To mitigate distortions caused by shifts in transaction composition (e.g., changes in flat age or type mix), a second model was estimated using adjusted housing indices:

$$
\log(\text{AdjIndex}_{g,t})
=
\alpha
+ \theta_1\log(\text{COE}_t)^*
+ \theta_2\text{FarTown}_g
+ \theta_3\left(\log(\text{COE}_t)^* \times \text{FarTown}_g\right)
+ \varepsilon_{g,t}
$$

**Results from the Adjusted-Index Specification:**

- **Central-Town Elasticity:** 29.04%
- **Incremental Far-Town Sensitivity ($\theta_3$):** **7.33%** ($p = 0.00739$)
- **Total Implied Far-Town Elasticity:** **36.36%**

In the adjusted model, the differential sensitivity of far towns is both positive and statistically significant.

<iframe src="/outputs/section3/charts/S3QdF5_adjusted_index_regression_coefficients.html" title="Adjusted model coefficients"></iframe>

## Interpretation

The empirical evidence supports the hypothesis of **differential sensitivity**: property values in outer towns respond more robustly to COE price movements than those in central locations. This finding is theoretically consistent with a household-level trade-off between housing and transportation budgets. While this reflects an aggregate market relationship, it underscores the heightened vulnerability of outer-town asset values to fluctuations in car ownership costs.

## Recommended Strategy

1. **Scenario Planning:** Incorporate COE price volatility as a high-weight variable when forecasting demand and pricing for outer-town developments.
2. **Monitoring:** Continuously track whether this differential sensitivity persists across different economic cycles or if it is mitigated by improvements in regional public transit infrastructure.
3. **Risk Assessment:** Treat the heightened sensitivity in Sengkang and Punggol as a key factor in regional market risk profiles.
