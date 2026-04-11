# Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?

## Business Context

From the perspectives of urban planning and public policy, it is important to quantify the extent to which transport infrastructure improvements are capitalized into residential property values. This study evaluates whether the commencement of **Downtown Line Stage 2 (DTL2)** is associated with an appreciation in HDB resale prices for units located in the immediate vicinity of the new stations.

## Theoretical Framework: Difference-in-Differences

This inquiry uses a **Difference-in-Differences (DiD)** research design. The DiD framework is well suited to this study because the DTL2 opening occurred at a discrete point in time, allowing resale units with different levels of exposure to the infrastructure change to be observed across both **pre-opening** and **post-opening** periods.

The methodology isolates the transport-opening effect by comparing two temporal shifts:

- The price trajectory of homes located near the new stations (**Treated Group**).
- The price trajectory of comparable homes situated outside the immediate catchment area (**Control Group**).

By differencing these two changes, the model separates localized infrastructure premiums from broader market movements affecting the overall HDB resale market.

<iframe src="/outputs/section3/charts/S3QcF0_did_framework.html" title="Difference-in-differences framework for DTL2"></iframe>

## Identification Requirements and Model Credibility

The validity of the DiD estimator rests on the **parallel-trends assumption**: absent the DTL2 intervention, treated and control units would have followed statistically similar price trajectories. For the resulting inference to remain credible, the study requires:

- **Distinct cohort definition:** Clearly demarcated treated and control groups based on station proximity, together with explicit pre-treatment and post-treatment periods.
- **Minimal anticipation effects:** Limited speculative pricing or localized redevelopment that could raise treated prices before the line officially opened.
- **Geospatial integrity:** Limited spillover effects through which the treated corridor materially influences prices within the control zone.
- **Pre-opening diagnostics:** Trend plots and event-study coefficients that do not exhibit systematic divergence before the intervention.

## Scope and Constraints

This analysis adopts a localized corridor-based design, focusing on the Bukit corridor towns: `BUKIT PANJANG`, `CHOA CHU KANG`, `BUKIT BATOK`, and `BUKIT TIMAH`.

**Experimental Design**

- **Treated Group:** Units located within **1.0 km** of DTL2 stations.
- **Control Group:** Units located between **1.5 km and 4.0 km** from DTL2 stations.

**Temporal Parameters**

- **Opening Date:** December 27, 2015.
- **Post-Period Proxy:** Beginning December 1, 2015, at monthly granularity.
- **Event-Study Reference:** 2016.

## Step 1: Descriptive Analysis (Price Path Divergence)

<iframe src="/outputs/section3/charts/S3QcF1_dtl2_treated_vs_control.html" title="DTL2 treated versus control trend"></iframe>

An initial comparison of median resale prices indicates a widening valuation gap between the two cohorts:

- **2012 (Pre-opening):** Treated (**SGD 480k**) versus Control (**SGD 433k**).
- **2018 (Post-opening):** Treated (**SGD 450k**) versus Control (**SGD 365k**).

Although the post-opening price gap is larger, these descriptive patterns alone are not sufficient to establish a causal relationship without formal econometric controls.

## Step 2: Distance Gradient Analysis

<iframe src="/outputs/section3/charts/S3QcF3_dtl2_mrt_proximity_bands.html" title="Price gradient by station distance"></iframe>

Median resale price per square meter (sqm) by distance band indicates a steeper proximity gradient after the line opened:

- **0–500m:** Pre-opening (**4,959 SGD/sqm**) to Post-opening (**5,155 SGD/sqm**).
- **2.0–4.0km:** Pre-opening (**4,191 SGD/sqm**) to Post-opening (**3,664 SGD/sqm**).

<iframe src="/outputs/section3/charts/S3QcF4_dtl2_treatment_map.html" title="DTL2 treatment assignment map"></iframe>

## Step 3: Baseline Difference-in-Differences Specification

The causal effect is estimated using the following log-linear DiD specification:

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

The coefficient of interest, $\beta_3$ (`treated:post`), captures the incremental change in valuation for near-station units relative to the control group after the opening of DTL2.

## Step 4: Event-Study Diagnostics (Parallel-Trends Validation)

The event-study diagnostic refines the DiD design by replacing the single post-treatment interaction with a sequence of relative-time indicators:

$$
\log(\text{Price}_i)
=
\alpha_{\text{Type}_i}
+ \delta_{\text{Town}_i}
+ \lambda_{\text{Year}_i}
+ \sum_{k \neq -1} \beta_k
\Bigl(
\text{Treated}_i
\times
1[\text{event time}=k]
\Bigr)
+ \gamma_1\text{FlatAge}_i
+ \gamma_2\text{FloorArea}_i
+ \varepsilon_i
$$

In this specification, each $\beta_k$ measures the treated-control gap at relative time $k$ compared with the omitted reference period ($k=-1$). Credible identification requires the pre-treatment coefficients to remain close to zero; statistically meaningful leads would indicate that the two groups were already diverging before the intervention.

<iframe src="/outputs/section3/charts/S3QcF2_dtl2_event_study_coefficients.html" title="DTL2 event-study coefficients"></iframe>

The event-study coefficients indicate the following percentage impacts over time:

- **Pre-opening leads:** $t-4$ (+5.9%), $t-3$ (+5.3%), $t-2$ (+8.0%).
- **Post-opening lags:** $t+0$ (+10.1%), $t+1$ (+12.0%), $t+2$ (+15.5%).

The positive pre-opening coefficients are an important result. They suggest that the treated and control groups were already diverging before the line became operational, potentially because of anticipation effects, localized redevelopment, or both.

## Step 5: Findings and Statistical Significance

- **Primary DiD Coefficient:** **0.0521** (95% CI: `[0.0439, 0.0603]`, $p \approx 0$).
- **Implied Price Uplift:** Approximately **+5.35%**, after log-to-percent conversion.
- **Pre-trend Check:** A separate trend model confirms a statistically significant pre-trend (**0.00736**, $p = 0.00125$).

## Interpretation

The evidence is directionally consistent with a **DTL2 proximity premium** within the Bukit corridor. However, the presence of positive pre-opening leads requires a cautious interpretation. The results are therefore better described as **quasi-causal** evidence of a strong association rather than definitive causal proof, because the strict parallel-trends condition required for a clean DiD design is not fully satisfied.

## Recommended Strategy

1. **Reporting:** Present the findings as robust corridor-level evidence of an accessibility premium, while remaining explicit about the pre-trend evidence and model assumptions.
2. **Terminology:** Use conservative language in professional reporting, describing the result as "suggestive of capitalization" rather than "definitive island-wide causality."
3. **Future methodological refinement:** Strengthen identification in future iterations by incorporating additional controls for concurrent localized developments or rezoning activity so the transport effect can be isolated more cleanly.
