---
title: "Is Yishun Truly Cheaper After Controlling For Flat Mix?"
kicker: "Section 3 / Question A"
description: "A controlled town comparison to test whether Yishun remains a value location after adjusting for housing characteristics and time effects."
section: "section3"
slug: "question-a"
order: 1
---

# Is Yishun Truly Cheaper After Controlling For Flat Mix?

## Business Context

Yishun is often viewed as a lower-priced town. The key question is whether that discount is real after controls, or whether it only appears because Yishun transacts a different mix of flats.

## Constraints And Requirement

A fair comparison needs to isolate location effect from composition effects. The model therefore controls for:

- flat type
- flat age
- transaction month

EDA is used to build intuition, not to claim a final answer.

## EDA: Descriptive Signals Before Controls

<iframe src="/outputs/section3/charts/S3QaF1_yishun_candidate_towns_boxplot.html" title="Yishun versus candidate towns by flat type"></iframe>

<iframe src="/outputs/section3/charts/S3QaF3_yishun_price_vs_space.html" title="Price versus space by town"></iframe>

These views show Yishun in the lower-price cluster with favorable space-for-price positioning, but they cannot separate location discount from transaction composition.

## Solution

The implementation in `section3_question_a.py` uses two related regressions:

- baseline fixed-effects-style hedonic model: `log(price_per_sqm) ~ C(town) + C(flat_type) + flat_age + C(year_month)`
- interaction model: `log(price_per_sqm) ~ C(town) * C(flat_type) + flat_age + C(year_month)`

The baseline model answers whether Yishun is still cheaper after controls. The interaction model checks whether that discount is broad across flat types or concentrated in specific segments.

Written out more explicitly, the baseline specification is:

$$ 
\begin{aligned}
\log(\text{price\_per\_sqm}_i)
=\;&\alpha
+ \sum_{t \neq \text{ref town}} \beta_t \mathbf{1}\{\text{town}_i=t\} \\
&+ \sum_{f \neq \text{ref flat type}} \gamma_f \mathbf{1}\{\text{flat type}_i=f\} \\
&+ \delta \,\text{flat\_age}_i
+ \sum_m \lambda_m \mathbf{1}\{\text{year\_month}_i=m\}
+ \varepsilon_i
\end{aligned}
$$

For the reported Yishun effect, the key coefficient is the town dummy for Yishun relative to the reference town, which in this run is `ANG MO KIO`.

The interaction specification adds town-by-flat-type terms:

$$ 
\begin{aligned}
\log(\text{price\_per\_sqm}_i)
=\;&\alpha
+ \sum_{t \neq \text{ref town}} \beta_t \mathbf{1}\{\text{town}_i=t\} \\
&+ \sum_{f \neq \text{ref flat type}} \gamma_f \mathbf{1}\{\text{flat type}_i=f\} \\
&+ \sum_{t \neq \text{ref town}} \sum_{f \neq \text{ref flat type}}
\theta_{tf}\,\mathbf{1}\{\text{town}_i=t\}\mathbf{1}\{\text{flat type}_i=f\} \\
&+ \delta \,\text{flat\_age}_i
+ \sum_m \lambda_m \mathbf{1}\{\text{year\_month}_i=m\}
+ \varepsilon_i
\end{aligned}
$$

Because the dependent variable is in logs, the town effect is converted back to a percentage discount using:

$$
\text{effect \%} = \left(e^{\beta}-1\right)\times 100
$$

<iframe src="/outputs/section3/charts/S3QaF2_yishun_simple_regression_coefficients.html" title="Controlled coefficient view"></iframe>

<iframe src="/outputs/section3/charts/S3QaF4_yishun_interaction_effects_by_flat_type.html" title="Yishun interaction effects by flat type"></iframe>

<iframe src="/outputs/section3/charts/S3QaF5_yishun_all_town_dummy_coefficients.html" title="All-town adjusted coefficient comparison"></iframe>

## Results

Baseline controlled finding:

- Yishun coefficient is about `-0.237` (log points)
- implied effect is about `-21.1%` versus reference town (`ANG MO KIO`)
- 95% CI is about `[-21.4%, -20.9%]`

Interaction model finding (by flat type):

- 4-room: about `-26.2%`
- 5-room: about `-30.1%`
- 3-room: about `-11.5%`

The discount is broad-based but strongest in larger flats.

## Interpretation

The evidence supports a structural value-town story, not only a composition story:

- Yishun remains materially cheaper after controlling for flat type, flat age, and month effects
- the discount is visible across major flat types, not limited to one segment
- larger flat segments show the strongest value signal in this run

## Recommended Decision

Frame Yishun as a genuine value location in market communication, and segment the message by flat type because the discount magnitude differs across 3-room, 4-room, and 5-room units.
