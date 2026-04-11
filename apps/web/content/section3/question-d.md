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

A prevalent market hypothesis suggests that homebuyers optimize their total expenditure by trading off residential location against car ownership costs. If this trade-off holds, property values in outer-rim towns should exhibit heightened sensitivity to Certificate of Entitlement (COE) price fluctuations. This study evaluates whether outer HDB towns respond more aggressively to COE "shocks" than central control towns.

## Scope and Constraints

The analysis utilizes a relative-sensitivity research design, categorizing towns by their proximity to the urban core:

- **Far Towns (Treatment):** `SENGKANG`, `PUNGGOL`.
- **Central Towns (Control):** `CENTRAL AREA`, `TOA PAYOH`, `KALLANG/WHAMPOA`, `QUEENSTOWN`, `BUKIT MERAH`.

The primary metric of interest is the **interaction term**, which isolates the incremental sensitivity of far towns relative to the central baseline, rather than the simple co-movement of prices.

## Step 1: Descriptive Time-Series Analysis

Prior to estimating the interaction model, we inspected the broad co-movement between COE and resale prices across both cohorts. This initial visualization establishes the market intuition: **do outer-town prices visually diverge in response to COE cycles?**

<iframe src="/outputs/section3/charts/S3QdF1_indexed_coe_and_resale_trends.html" title="Indexed COE and resale trend"></iframe>

The visual evidence suggests that outer-town series respond more sharply during periods of elevated COE pressure. While this establishes a descriptive foundation, it is not sufficient for causal inference as it may still capture broader macro housing cycles or shifts in transaction mix.

## Step 2: Evaluation of the Adjusted Price Spread

The second stage of analysis narrows the focus to the **far-versus-central spread** after composition adjustment. The core hypothesis is relative: does the valuation gap between outer and central towns widen as car ownership becomes more expensive?

<iframe src="/outputs/section3/charts/S3QdF2b_adjusted_far_vs_central_index_spread.html" title="Adjusted far-versus-central spread"></iframe>

This chart identifies our primary target for regression. If the adjusted spread expands during high-COE periods, it validates the descriptive pattern that the interaction term will later formalize.

## Step 3: Verification via Adjusted Housing Indices

To mitigate distortions from the transaction mix, such as changes in flat age or floor area, we examined the market narrative using adjusted housing indices rather than raw price data.

<iframe src="/outputs/section3/charts/S3QdF1b_adjusted_indexed_coe_and_resale_trends.html" title="Adjusted indexed COE and resale trend"></iframe>

The persistence of the far-town sensitivity pattern in the adjusted index increases confidence that the observed trend reflects market sensitivity rather than sample-composition noise.

## Step 4: Baseline Interaction Model (Raw Prices)

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

In this raw-price setup, the differential effect is directionally positive but remains borderline in terms of statistical significance.

<iframe src="/outputs/section3/charts/S3QdF4_coe_regression_coefficients.html" title="Raw model coefficients"></iframe>

## Step 5: Refined Interaction Model (Adjusted Indices)

To isolate the effect from shifts in transaction composition, a second model was estimated using adjusted housing indices:

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

In the adjusted specification, the differential sensitivity of far towns is both positive and statistically significant.

<iframe src="/outputs/section3/charts/S3QdF5_adjusted_index_regression_coefficients.html" title="Adjusted model coefficients"></iframe>

## Interpretation

The empirical evidence supports the hypothesis of **differential sensitivity**: property values in outer towns respond more robustly to COE price movements than those in central locations. While the raw data provides the directional signal, the relationship becomes materially stronger once composition adjustments are applied.

This finding aligns with the theory of a household-level trade-off between housing location and transportation costs. Outer-town valuations appear structurally more exposed to fluctuations in the cost of car ownership.

## Recommended Strategy

1. **Forecasting & Pricing:** Incorporate COE volatility as a high-weight variable when modeling demand and pricing scenarios for outer-rim developments.
2. **Infrastructure Monitoring:** Evaluate whether this differential sensitivity is mitigated by major transit infrastructure improvements, such as new MRT line openings, over time.
3. **Risk Management:** Categorize the heightened sensitivity in Sengkang and Punggol as a significant factor in regional market risk profiles during periods of car ownership inflation.
