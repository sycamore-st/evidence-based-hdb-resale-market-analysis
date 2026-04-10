---
title: "Is Yishun Structurally More Affordable After Controls?"
kicker: "Section 3 / Question A"
description: "A controlled town comparison of whether Yishun's discount persists after accounting for flat type, flat age, and market timing."
section: "section3"
slug: "yishun-affordability-analysis"
order: 1
---

# Is Yishun Structurally More Affordable After Controls?

## Business Context

Yishun is frequently characterized as a high-value, lower-priced HDB town. The central objective of this analysis is to determine whether this price differential is structural (intrinsic to the location) or merely a reflection of a specific transaction mix—such as a higher proportion of smaller flat types or older housing stock.

## Scope and Constraints

To rigorously isolate the "location effect" from "composition effects," the analysis employs a hedonic regression framework controlling for the following variables:

- Flat type
- Flat age
- Transaction month (to account for temporal market fluctuations)

Exploratory Data Analysis (EDA) provides directional context, while the regression models provide the statistical basis for final inference.

## Step 1: Descriptive Analysis (Unadjusted Positioning)

<iframe src="/outputs/section3/charts/S3QaF1_yishun_candidate_towns_boxplot.html" title="Yishun versus candidate towns by flat type"></iframe>

<iframe src="/outputs/section3/charts/S3QaF3_yishun_price_vs_space.html" title="Price versus space by town"></iframe>

Descriptive statistics from the preliminary dataset reveal the following for Yishun:

- **Median Resale Price:** SGD 440,000
- **Median Price per SQM:** SGD 4,983.6
- **Median Floor Area:** 92 sqm

While these metrics place Yishun within a lower-price cluster, they do not establish a causal relationship because the distribution of unit ages and types varies significantly across different towns.

## Step 2: Baseline Controlled Model (Fixed Effects)

The baseline econometric specification is defined as follows:

$$
\log(\text{price\_per\_sqm}_i)
=
\alpha
+ C(\text{town}_i)
+ C(\text{flat\_type}_i)
+ \beta\,\text{flat\_age}_i
+ C(\text{year\_month}_i)
+ \varepsilon_i
$$

<iframe src="/outputs/section3/charts/S3QaF2_yishun_simple_regression_coefficients.html" title="Controlled coefficient view"></iframe>

**Key Findings:**

- **Yishun Log Coefficient:** -0.2374
- **Implied Price Effect:** **-21.1%**
- **95% Confidence Interval:** [-21.4%, -20.9%]

The percentage impact is derived via the transformation: $\left(e^{\beta}-1\right)\times 100$.

## Step 3: Heterogeneity Analysis by Flat Type

To determine if the observed discount is uniform or segment-specific, an interaction model was implemented:

$$
\log(\text{price\_per\_sqm}_i)
=
\alpha
+ C(\text{town}_i) * C(\text{flat\_type}_i)
+ \beta\,\text{flat\_age}_i
+ C(\text{year\_month}_i)
+ \varepsilon_i
$$

<iframe src="/outputs/section3/charts/S3QaF4_yishun_interaction_effects_by_flat_type.html" title="Yishun interaction effects by flat type"></iframe>

**Segment-Specific Discounts:**

- **3-Room:** -11.5%
- **4-Room:** -26.2%
- **5-Room:** -30.1%

The results indicate that while the discount is broad-based, it is significantly more pronounced in the larger flat segments.

## Step 4: Comparative Adjusted Town Distribution

<iframe src="/outputs/section3/charts/S3QaF5_yishun_all_town_dummy_coefficients.html" title="All-town adjusted coefficient comparison"></iframe>

The adjusted town distribution confirms that Yishun consistently resides on the lower end of the pricing spectrum even after normalization. Its effect size is comparable to other value-oriented towns, suggesting a consistent structural positioning within the broader market.

## Interpretation

The empirical evidence demonstrates that Yishun's affordability is not merely a statistical artifact of its transaction mix. After controlling for flat type, age, and temporal effects, Yishun remains significantly more affordable on a price-per-square-meter basis. Notably, the value proposition strengthens as flat size increases, with 4-room and 5-room units showing the most substantial discounts relative to the market baseline.

## Recommended Strategy

1. **Market Positioning:** Position Yishun as a structural value segment in both internal planning and external communications.
2. **Segmented Messaging:** Rather than applying a single town-wide discount figure, utilize segment-specific data (especially for larger units) to provide a more accurate representation of the affordability landscape.
