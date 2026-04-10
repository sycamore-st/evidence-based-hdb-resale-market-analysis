---
title: "Are Newer HDB Flats Becoming Smaller In Meaningful Ways?"
kicker: "Section 3 / Question B"
description: "A longitudinal floor-area analysis combining descriptive trends and controlled models by flat type."
section: "section3"
slug: "question-b"
order: 2
---

# Are Newer HDB Flats Becoming Smaller In Meaningful Ways?

## Business Context

A prevalent narrative within the Singapore property market suggests that newer HDB flats are progressively decreasing in size. From a policy and business perspective, it is critical to determine whether this perceived reduction constitutes a broad structural trend or if it is a segment-specific pattern primarily driven by shifts in flat-type composition over the decades.

## Scope and Constraints

Relying solely on raw averages is insufficient, as the aggregate floor area is highly sensitive to the evolving mix of flat types and towns over time. Consequently, this analysis employs a dual-track methodology:

- **Exploratory Data Analysis (EDA):** To identify visible longitudinal trend patterns across different cohorts.
- **Controlled Regression Modeling:** To isolate the net effect of the completion year on floor area, independent of confounding variables.

## Step 1: Descriptive Longitudinal Analysis

<iframe src="/outputs/section3/charts/S3QbF1_floor_area_over_time.html" title="Average floor area over time"></iframe>

<iframe src="/outputs/section3/charts/S3QbF1a_floor_area_over_time.html" title="Common flat types floor area trend"></iframe>

<iframe src="/outputs/section3/charts/S3QbF1b_floor_area_over_time.html" title="Sparse flat types floor area trend"></iframe>

The initial visual evidence suggests that floor area movements are non-uniform across the housing portfolio. This variance necessitates segment-level modeling rather than a singular, pooled market narrative.

## Step 2: Analysis of Descriptive Slopes by Segment

<iframe src="/outputs/section3/charts/S3QbF2_floor_area_slope_by_type.html" title="Average annual floor-area change by flat type"></iframe>

Data from the segment-level slope analysis (`S3QbF2_floor_area_slope_by_type.csv`) reveals the following annual changes:

- **EXECUTIVE:** -1.214 sqm/year
- **5 ROOM:** -0.388 sqm/year
- **4 ROOM:** -0.095 sqm/year
- **3 ROOM:** -0.009 sqm/year

These metrics indicate a more pronounced decline in larger housing formats, whereas smaller flat types have remained comparatively stable over the observed period.

## Step 3: Controlled Baseline Model

The baseline econometric specification is defined as follows:

$$
\text{floor\_area\_sqm}_i
=
\alpha
+ \beta\,\text{completion\_year}_i
+ C(\text{flat\_type}_i)
+ C(\text{town}_i)
+ \varepsilon_i
$$

**Model Coefficients:**

- **Completion-Year Coefficient ($\beta$):** -0.0390
- **95% Confidence Interval:** [-0.0406, -0.0374]
- **p-value:** $\approx 0$

**Interpretation:** After controlling for flat type and town, newer housing cohorts are associated with a statistically significant but modest reduction in average floor area.

## Step 4: Interaction Model (Completion Year $\times$ Flat Type)

To account for nonlinearities and divergence between market segments, an interaction model was implemented:

$$
\text{floor\_area\_sqm}_i
=
\alpha
+ C(\text{completion\_year}_i) * C(\text{flat\_type}_i)
+ C(\text{town}_i)
+ \varepsilon_i
$$

<iframe src="/outputs/section3/charts/S3QbF4a_adjusted_year_trend_by_type.html" title="Adjusted completion-year trend by flat type (group A)"></iframe>

<iframe src="/outputs/section3/charts/S3QbF4b_adjusted_year_trend_by_type.html" title="Adjusted completion-year trend by flat type (group B)"></iframe>

The adjusted price paths confirm that the temporal trend varies significantly by flat type. This heterogeneity underscores why a singular linear slope is insufficient for an accurate business interpretation.

## Interpretation

The empirical evidence does not support the generalized claim that all newer HDB flats are shrinking at a uniform rate. Instead, the pattern is highly segmented: while larger flat categories have undergone meaningful contraction, smaller categories have exhibited minimal change in square footage. This suggests a targeted recalibration of unit design rather than an across-the-board reduction in living standards.

## Recommended Strategy

1. **Metric-Driven Communication:** Utilize type-specific space benchmarks (e.g., floor area and price-per-sqm per flat type) in market reporting and policy discussions.
2. **Granular Benchmarking:** Avoid relying exclusively on overall market averages, as they obscure the divergent trends observed between different flat formats.
