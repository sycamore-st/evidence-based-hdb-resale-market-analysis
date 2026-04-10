---
title: "Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?"
kicker: "Section 3 / Question C"
description: "A corridor-level Difference-in-Differences study on whether DTL2 proximity is associated with higher HDB resale prices."
section: "section3"
slug: "question-c"
order: 3
---

# Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?

## Business Context

From the perspectives of urban planning and public policy, it is essential to quantify the extent to which transport infrastructure improvements are capitalized into residential property values. This study evaluates whether the commencement of Downtown Line Stage 2 (DTL2) is associated with an appreciation in HDB resale prices for units located in the immediate vicinity of the new stations.

## Scope and Constraints

The analysis utilizes a corridor-based research design rather than an island-wide claim, focusing specifically on the Bukit corridor towns: `BUKIT PANJANG`, `CHOA CHU KANG`, `BUKIT BATOK`, and `BUKIT TIMAH`.

**Experimental Design:**

- **Treated Group:** Units situated within **1.0 km** of DTL2 stations.
- **Control Group:** Units situated between **1.5 km and 4.0 km** from the stations.

**Temporal Parameters:**

- **Opening Date:** December 27, 2015.
- **Post-Period Proxy:** Commencing December 1, 2015 (monthly granularity).
- **Event-Study Reference:** 2016.

## Step 1: Descriptive Analysis (Price Path Divergence)

<iframe src="/outputs/section3/charts/S3QcF1_dtl2_treated_vs_control.html" title="DTL2 treated versus control trend"></iframe>

Initial comparison of median resale prices reveals a widening gap between the two cohorts:

- **2012 (Pre-opening):** Treated (**SGD 480k**) vs. Control (**SGD 433k**).
- **2018 (Post-opening):** Treated (**SGD 450k**) vs. Control (**SGD 365k**).

While the post-opening price delta is more pronounced, these descriptive statistics are insufficient to establish a causal link without econometric controls.

## Step 2: Distance Gradient Analysis

<iframe src="/outputs/section3/charts/S3QcF3_dtl2_mrt_proximity_bands.html" title="Price gradient by station distance"></iframe>

The median price-per-square-meter (sqm) by distance band indicates a steeper proximity gradient following the line's opening:

- **0-500m:** Pre-opening (**4,959 SGD/sqm**) to Post-opening (**5,155 SGD/sqm**).
- **2.0-4.0km:** Pre-opening (**4,191 SGD/sqm**) to Post-opening (**3,664 SGD/sqm**).

<iframe src="/outputs/section3/charts/S3QcF4_dtl2_treatment_map.html" title="DTL2 treatment assignment map"></iframe>

## Step 3: Baseline Difference-in-Differences (DiD) Framework

The causal effect is estimated using the following DiD specification:

$$
\log(\text{Price}_i)
=
\beta_0
+ \beta_1\text{Treated}_i
+ \beta_2\text{Post}_i
+ \beta_3(\text{Treated}_i \times \text{Post}_i)
+ \gamma_1\text{FlatAge}_i
+ \gamma_2\text{FloorArea}_i
+ \alpha_{\text{Type}_i}
+ \delta_{\text{Town}_i}
+ \lambda_{\text{Year}_i}
+ \varepsilon_i
$$

The coefficient of interest, $\beta_3$ (`treated:post`), captures the incremental change in value for near-station units relative to the control group following the opening of DTL2.

## Step 4: Event-Study Diagnostics (Parallel-Trends Validation)

<iframe src="/outputs/section3/charts/S3QcF2_dtl2_event_study_coefficients.html" title="DTL2 event-study coefficients"></iframe>

Event-study coefficients suggest the following percentage impacts over time:

- **Pre-opening Leads:** $t-4$ (**+5.9%**), $t-3$ (**+5.3%**), $t-2$ (**+8.0%**).
- **Post-opening Lags:** $t+0$ (**+10.1%**), $t+1$ (**+12.0%**), $t+2$ (**+15.5%**).

The positive coefficients in the pre-opening period are critical; they indicate that the treated and control groups were diverging prior to the line's completion, likely due to market anticipation or localized redevelopment.

## Step 5: Findings and Statistical Significance

- **Primary DiD Coefficient:** **0.0521** (95% CI: `[0.0439, 0.0603]`, $p \approx 0$).
- **Implied Price Uplift:** Approximately **+5.35%** (log-to-percent conversion).
- **Pre-trend Check:** A separate trend model confirms a positive, statistically significant pre-trend (**0.00736**, $p = 0.00125$).

## Interpretation

The empirical evidence is directionally consistent with a **DTL2 proximity premium** within the Bukit corridor. However, the presence of positive pre-opening leads necessitates a conservative interpretation. The results should be framed as **quasi-causal**—representing a strong association—rather than a definitive causal effect, as the strict parallel-trends assumption required for pure DiD identification is not fully satisfied.

## Recommended Strategy

1. **Reporting:** Position the findings as robust corridor-level evidence of a proximity premium, while explicitly documenting the underlying assumptions and pre-trend observations.
2. **Terminology:** Utilize conservative language, characterizing the effect as "suggestive of capitalization" rather than "definitive island-wide causality."
3. **Future Iterations:** Enhance model identification by incorporating additional controls for concurrent localized developments or rezoning activities to further isolate the transport infrastructure effect.
