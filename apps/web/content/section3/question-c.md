---
title: "Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?"
kicker: "Section 3 / Question C"
description: "A difference-in-differences study evaluating whether the DTL2 opening in December 2015 capitalized into HDB resale prices in the Bukit corridor."
section: "section3"
slug: "question-c"
order: 3
---

# Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?

## Business Context

From the perspectives of urban planning and public policy, it is important to quantify the extent to which transport infrastructure improvements are capitalized into residential property values. New MRT lines reduce commute times for nearby residents, which should — in theory — make those locations more attractive and bid up prices. But isolating the transport effect from the general market is not straightforward: prices in the treated area may have been rising anyway, or may have already incorporated expectations before the line opened.

This study evaluates whether the commencement of **Downtown Line Stage 2 (DTL2)** in December 2015 is associated with an appreciation in HDB resale prices for units located in the immediate vicinity of the new stations.

## Theoretical Framework: Difference-in-Differences

This inquiry uses a **Difference-in-Differences (DiD)** research design. The intuition behind DiD is straightforward: rather than comparing near-station and far-station prices at a single point in time (which would confound location quality with transit access), we compare how each group's prices *changed* around the event. If the near-station group rose faster after the opening than the far-station group, and if the two groups were tracking each other before the opening, the excess post-opening gain is attributable to the transit improvement.

Formally, DiD isolates the transport effect by differencing two temporal comparisons:

- The change in prices for homes near the new stations (**Treated Group**), before versus after opening.
- The change in prices for comparable homes farther away (**Control Group**), over the same window.

The conceptual diagram below makes the mechanics explicit.

<iframe src="/outputs/section3/charts/S3QcF0_did_framework.html" title="Difference-in-differences framework for DTL2" data-caption="Fig 0 — Conceptual diagram of the Difference-in-Differences design. The control group (amber) follows a steady pre-trend; the treated group (green) follows a parallel pre-trend, then accelerates after the event. The counterfactual (dotted) shows where the treated group would have been absent the intervention. DiD = ΔB − ΔA: the post-treatment gap minus the pre-treatment gap."></iframe>

The critical element in this diagram is the **counterfactual** (the dotted line): the hypothetical trajectory the treated group would have followed had the line never opened. DiD estimates this counterfactual by borrowing the control group's post-treatment trend. This borrowing is valid only if the **parallel-trends assumption** holds — that is, if the two groups were genuinely moving together before the intervention. We test this assumption explicitly later in the analysis.

## Identification Requirements and Model Credibility

The validity of the DiD estimator rests on the **parallel-trends assumption**: absent the DTL2 intervention, treated and control units would have followed statistically similar price trajectories. For the resulting inference to remain credible, the study requires:

- **Distinct cohort definition:** Clearly demarcated treated and control groups based on station proximity, with explicit pre-treatment and post-treatment periods.
- **Minimal anticipation effects:** Limited speculative pricing that could raise treated prices before the line officially opened.
- **Geospatial integrity:** Limited spillover effects through which the treated corridor materially influences prices within the control zone.
- **Pre-opening diagnostics:** Trend plots and event-study coefficients that do not exhibit systematic divergence before the intervention.

## Scope and Constraints

This analysis adopts a corridor-based design, focusing on the Bukit corridor towns: `BUKIT PANJANG`, `CHOA CHU KANG`, `BUKIT BATOK`, and `BUKIT TIMAH` — the towns most directly served by DTL2 Stage 2.

**Experimental Design**

- **Treated Group:** Units within **1.0 km** of a DTL2 station.
- **Control Group:** Units between **1.5 km and 4.0 km** from a DTL2 station. The gap between 1.0 km and 1.5 km is intentional — it creates a buffer zone that prevents treated units from contaminating the control sample.

**Temporal Parameters**

- **Opening Date:** December 27, 2015.
- **Post-Period:** Transactions from December 1, 2015 onwards (monthly granularity).
- **Event-Study Reference Year:** 2016, the first full calendar year post-opening.

## Step 1: Descriptive Analysis — Do the Price Paths Diverge?

Before fitting any model, we examine whether treated and control groups visually diverge after the opening. This provides both a sanity check on the data and a first look at the parallel-trends assumption.

<iframe src="/outputs/section3/charts/S3QcF1_dtl2_treated_vs_control.html" title="DTL2 treated versus control trend" data-caption="Fig 1 — Annual median resale price for treated (within 1 km) versus control (1.5–4 km) units over time. The vertical dashed line marks December 2015. A widening gap post-2015 is consistent with a transit-driven premium, but does not yet rule out pre-existing divergence."></iframe>

The raw price paths show a widening valuation gap between the two cohorts after the opening:

- **2012 (Pre-opening):** Treated (**SGD 480k**) vs. Control (**SGD 433k**) — a gap of SGD 47k.
- **2018 (Post-opening):** Treated (**SGD 450k**) vs. Control (**SGD 365k**) — a gap of SGD 85k.

The absolute gap nearly doubled. However, this descriptive pattern does not prove a causal effect: both groups fell in nominal terms after 2013 (reflecting market-wide cooling measures), and the control group's steeper decline could reflect factors unrelated to transit. The regression in Step 3 controls for these confounds.

## Step 2: Distance Gradient Analysis

If transit access is genuinely driving a price premium, we would expect the effect to decay with distance from the station — the closest units benefit most, those farther away benefit less. The chart below examines median price-per-sqm by distance band from DTL2 stations, comparing the pre-opening and post-opening periods.

<iframe src="/outputs/section3/charts/S3QcF3_dtl2_mrt_proximity_bands.html" title="Price gradient by station distance" data-caption="Fig 2 — Median price per sqm by distance band from DTL2 stations, split into pre-opening (before Dec 2015) and post-opening (from Dec 2015) periods. A steeper post-opening gradient — falling faster as distance increases — is consistent with a proximity premium being priced in after the line opened."></iframe>

The gradient steepened after the line opened:

- **0–500m band:** Pre-opening **SGD 4,959/sqm** → Post-opening **SGD 5,155/sqm** (+4.0%).
- **2.0–4.0km band:** Pre-opening **SGD 4,191/sqm** → Post-opening **SGD 3,664/sqm** (−12.6%).

The near-station units gained while the far units fell — a pattern consistent with the transit premium hypothesis. The treatment map below shows the geographic layout of treated and control zones across the Bukit corridor.

<iframe src="/outputs/section3/charts/S3QcF4_dtl2_treatment_map.html" title="DTL2 treatment assignment map" data-caption="Fig 3 — Geographic assignment of treated (within 1 km, orange) and control (1.5–4 km, blue) units in the Bukit corridor. DTL2 stations are marked; the 1 km treatment rings are overlaid for reference."></iframe>

## Step 3: Baseline Difference-in-Differences Specification

The causal effect is estimated using a log-linear DiD specification:

$$
\begin{aligned}
\log(\text{Price}_i)
=\;& \beta_0
+ \beta_1\text{Treated}_i
+ \beta_2\text{Post}_i \\
&+ \beta_3(\text{Treated}_i \times \text{Post}_i)
+ \gamma_1\text{FlatAge}_i
+ \gamma_2\text{FloorArea}_i \\
&+ \alpha_{\text{Type}_i}
+ \delta_{\text{Town}_i}
+ \lambda_{\text{Year}_i}
+ \varepsilon_i
\end{aligned}
$$

Breaking down the key terms:

- $\beta_1\text{Treated}_i$ captures the time-invariant level difference between treated and control units — the pre-existing premium for being close to an MRT station, regardless of DTL2.
- $\beta_2\text{Post}_i$ captures the market-wide price change that affected both groups in the post-opening period (the macro trend).
- $\beta_3(\text{Treated}_i \times \text{Post}_i)$ is the **DiD coefficient**: the incremental gain in treated units after the opening, above and beyond both the baseline gap and the market-wide shift. This is the coefficient of interest.
- $\gamma_1$, $\gamma_2$ control for unit characteristics (flat age and floor area) so the treatment estimate is not contaminated by compositional differences between groups.
- $\alpha_{\text{Type}}$, $\delta_{\text{Town}}$, $\lambda_{\text{Year}}$ are fixed effects absorbing flat-type, town-level, and annual market factors.

## Step 4: Event-Study Diagnostics — Testing the Parallel-Trends Assumption

The baseline DiD produces a single estimate of the average treatment effect. An event study goes further by replacing the binary $\text{Post}$ indicator with a sequence of year-relative indicators, estimating the treated-control gap separately for each year around the opening:

$$
\begin{aligned}
\log(\text{Price}_i)
=\;& \alpha_{\text{Type}_i}
+ \delta_{\text{Town}_i}
+ \lambda_{\text{Year}_i} \\
&+ \sum_{k \neq -1} \beta_k
\Bigl(
\text{Treated}_i \times \mathbf{1}[\text{event time}=k]
\Bigr) \\
&+ \gamma_1\text{FlatAge}_i
+ \gamma_2\text{FloorArea}_i
+ \varepsilon_i
\end{aligned}
$$

The year immediately before the opening ($k = -1$) is omitted as the reference period, so all coefficients $\beta_k$ measure the treated-control gap *relative to the year before opening*. Coefficients for pre-opening years ($k < 0$) should be statistically indistinguishable from zero if the parallel-trends assumption holds — there should be no divergence before the intervention. Coefficients for post-opening years ($k \geq 0$) reveal whether the treatment effect builds over time.

<iframe src="/outputs/section3/charts/S3QcF2_dtl2_event_study_coefficients.html" title="DTL2 event-study coefficients" data-caption="Fig 4 — Event-study coefficients showing the treated-control price gap in each year relative to the year before DTL2 opened (k = −1). Negative k values are pre-opening leads; positive k values are post-opening lags. Error bars show 95% confidence intervals. Pre-opening leads near zero support parallel trends; positive and growing post-opening lags support a genuine treatment effect."></iframe>

The event-study results reveal a pattern that is directionally encouraging but econometrically troubling:

- **Pre-opening leads:** $t-4$ (+5.9%), $t-3$ (+5.3%), $t-2$ (+8.0%).
- **Post-opening lags:** $t+0$ (+10.1%), $t+1$ (+12.0%), $t+2$ (+15.5%).

The post-opening coefficients grow steadily, consistent with transit capitalization taking time to fully materialize. But the pre-opening leads are positive and non-trivial — treated units were already commanding a higher and apparently growing premium *before* the line opened. This is a red flag: it suggests the two groups were not running parallel before the intervention, which means the DiD estimate may be absorbing a pre-existing divergence rather than measuring purely the DTL2 effect.

## Step 5: Findings and Statistical Significance

- **Primary DiD Coefficient:** **+0.0521** (95% CI: [0.0439, 0.0603], $p \approx 0$).
- **Implied Price Uplift:** Approximately **+5.35%**, after converting from log scale via $(e^{0.0521} - 1) \times 100$.
- **Pre-trend Check:** A separate regression estimated over the pre-opening period finds a statistically significant pre-trend coefficient (**+0.00736**, $p = 0.00125$), confirming that treated units were already diverging from controls before 2015.

At a median treated-group price of SGD 450,000, a 5.35% uplift corresponds to approximately **SGD 24,000 per unit** — a material but not implausibly large effect for transit access in the Singapore context. The problem is that this figure cannot be cleanly attributed to DTL2 alone, given the positive pre-trend.

## Interpretation

The evidence is directionally consistent with a **DTL2 proximity premium** within the Bukit corridor. However, the positive pre-opening event-study coefficients are a serious identification challenge. They suggest that buyers were already discounting the *anticipated* future transit access before the line opened — either bidding up treated prices in expectation of the opening, or because concurrent localized improvements (rezoning, amenity upgrades) affected the two groups differently.

The results are therefore best described as **quasi-causal evidence of a strong accessibility association** rather than a clean causal estimate. The DiD design identifies something real, but the strict parallel-trends condition required to call it *definitively* causal is not fully satisfied in this data.

## Recommended Strategy

1. **Reporting:** Present the +5.35% estimate as a robust corridor-level signal of an accessibility premium, while being transparent about the pre-trend evidence and its implications for causal interpretation.
2. **Terminology:** Use conservative language — "suggestive of capitalization" rather than "definitive causal proof" — particularly in any context where the distinction carries policy or legal weight.
3. **Future Methodological Refinement:** Strengthen identification in future iterations by incorporating additional controls for concurrent localized developments or rezoning activity, or by applying a matching approach that constructs a more comparable control group on pre-opening trend characteristics.
