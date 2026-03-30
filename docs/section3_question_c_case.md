# Section 3 Question C Case Note

## 1. Business Question

The business question for Section 3 Question C is:

> Did Downtown Line Stage 2 increase HDB resale prices for flats closer to the new line?

In the current codebase, that question is implemented more narrowly as:

> Within Bukit Timah corridor towns, did buildings closer to Downtown Line Stage 2 stations appreciate more after opening than buildings farther away?

That scope matters. This is not a whole-island evaluation of the entire Downtown Line network. It is a corridor design focused on:

- `BUKIT PANJANG`
- `CHOA CHU KANG`
- `BUKIT BATOK`
- `BUKIT TIMAH`

The opening event used in the analysis is:

- actual opening date: `2015-12-27`
- monthly post-period proxy: `2015-12-01`
- annual event-study reference year: `2016`

The analysis code for this question lives in [section3_question_c.py](/src/analysis/section3/section3_question_c.py).

## 2. EDA

The EDA for this question is mainly about making the treatment definition visible before the regression.

### 2.1 Near-versus-far treated/control trend

Chart outputs:
- [S3QcF1_dtl2_treated_vs_control.svg](/outputs/section3/charts/S3QcF1_dtl2_treated_vs_control.svg)
- [S3QcF1_dtl2_treated_vs_control.csv](/outputs/section3/results/S3QcF1_dtl2_treated_vs_control.csv)

The treated/control chart compares:

- treated buildings: within `1.0 km` of a DTL2 Stage 2 station
- control buildings: more than `1.5 km` but at most `4.0 km` away

From the saved data:

- in 2012, treated median price was `480,000` versus `433,000` for control
- in 2018, treated median price was `450,000` versus `365,000` for control

That suggests a widening gap, but it does not prove causality because treated buildings were already more expensive before opening.

### 2.2 Event-study visual

Chart outputs:
- [S3QcF2_dtl2_event_study_coefficients.svg](/outputs/section3/charts/S3QcF2_dtl2_event_study_coefficients.svg)
- [S3QcF2_dtl2_event_study_coefficients.csv](/outputs/section3/results/S3QcF2_dtl2_event_study_coefficients.csv)

This is the most important diagnostic chart in the section.

From the saved event-study coefficients:

- `-4`: about `+5.9%`
- `-3`: about `+5.3%`
- `-2`: about `+8.0%`
- `+0`: about `+10.1%`
- `+1`: about `+12.0%`
- `+2`: about `+15.5%`

The post-opening effects are positive and growing, but the pre-opening leads are also already positive and statistically significant. That is a direct warning sign for parallel-trends validity.

### 2.3 Distance-band price gradient

Chart outputs:
- [S3QcF3_dtl2_mrt_proximity_bands.svg](/outputs/section3/charts/S3QcF3_dtl2_mrt_proximity_bands.svg)
- [S3QcF3_dtl2_mrt_proximity_bands.csv](/outputs/section3/results/S3QcF3_dtl2_mrt_proximity_bands.csv)

This chart shows median price per sqm by coarse station-distance bands.

From the saved data:

- pre-2016, `0-500m` was about `4959` SGD/sqm
- post-2016, `0-500m` was about `5155` SGD/sqm
- pre-2016, `2.0-4.0km` was about `4191` SGD/sqm
- post-2016, `2.0-4.0km` was about `3664` SGD/sqm

So the gradient becomes steeper after opening, which is directionally consistent with a station-access premium.

### 2.4 Treatment map

Chart outputs:
- [S3QcF4_dtl2_treatment_map.svg](/outputs/section3/charts/S3QcF4_dtl2_treatment_map.svg)
- [S3QcF4_dtl2_treatment_map.csv](/outputs/section3/results/S3QcF4_dtl2_treatment_map.csv)

This is not a result chart. Its role is to make the treatment assignment defensible:

- Stage 2 stations are the Bukit Panjang to Rochor segment
- each treated building lies within a `1 km` circle of a Stage 2 station
- control buildings are in the same broad corridor but outside that near-station radius

## 3. Modeling

The core Question C story should be told with two models:

1. a difference-in-differences model
2. an event-study model that checks whether the DiD assumption is credible

I also include the new `250/500/750/1000m` band experiment as a robustness section, not as the main causal model.

### 3.1 Model 1: Difference-in-Differences

#### Method and intuition

The baseline design is:

- treated buildings: within `1.0 km` of a Stage 2 station
- controls: between `1.5 km` and `4.0 km`
- same corridor towns only
- compare pre- versus post-opening

This is a standard difference-in-differences setup:

- `treated` captures whether a building is near the line
- `post` captures whether the transaction happened after the line opened
- `treated:post` is the incremental post-opening effect for near-line buildings

Method / library references:

- Statsmodels formula API examples: [statsmodels formula examples](https://www.statsmodels.org/stable/example_formulas.html)
- Statsmodels OLS formula API: [statsmodels.formula.api.ols](https://www.statsmodels.org/stable/generated/statsmodels.formula.api.ols.html)
- Difference-in-differences overview: [Difference in differences](https://en.wikipedia.org/wiki/Difference_in_differences)
- Patsy treatment coding: [patsy Treatment coding](https://patsy.readthedocs.io/en/latest/builtins-reference.html#patsy.builtins.Treatment)

#### Equation

Let:

- $i$ index transactions
- $\text{Near}_i$ indicate whether transaction $i$ is within `1 km` of a Stage 2 station
- $\text{Post}_i$ indicate whether transaction $i$ is in the post-opening period
- $\alpha_{\text{Type}_i}$ be flat-type fixed effects
- $\delta_{\text{Town}_i}$ be town fixed effects
- $\lambda_t$ be transaction-year fixed effects

Then the main model is:

$$
\log(\text{Price}_i)
=
\beta_0
\;+\;
\beta_1 \cdot \text{Near}_i
\;+\;
\beta_2 \cdot \text{Post}_i
\;+\;
\beta_3 \cdot (\text{Near}_i \times \text{Post}_i)
\;+\;
\alpha_{\text{Type}_i}
\;+\;
\delta_{\text{Town}_i}
\;+\;
\lambda_t
\;+\;
\gamma_1 \cdot \text{FlatAge}_i
\;+\;
\gamma_2 \cdot \text{FloorArea}_i
\;+\;
\varepsilon_i
$$

In code terms:

$$
\log(\text{price})
\sim
\text{treated} * \text{post}
\;+\;
\text{flat\_age}
\;+\;
\text{floor\_area\_sqm}
\;+\;
C(\text{flat\_type})
\;+\;
C(\text{town})
\;+\;
C(\text{transaction\_year})
$$

#### How to interpret the coefficients

The key coefficient is:

$$
\beta_3
$$

which is the `treated:post` interaction.

It measures the additional post-opening log-price change for near-station buildings relative to farther corridor buildings.

From the saved model output:

- `treated:post` coefficient: `0.0521`
- 95% CI: about `[0.044, 0.060]`
- implied percentage effect: about `+5.35%`
- p-value: effectively `0`

Interpretation:

- after the DTL2 opening, buildings within `1 km` of Stage 2 stations were priced about `5.4%` higher relative to the farther corridor control group, after controls

#### What we expected to see

If DTL2 genuinely created a local accessibility premium, we expected:

- `treated:post > 0`
- statistical significance
- a sensible magnitude in the low- to mid-single digits

The model delivers that pattern.

#### Full model summary

Saved output:
- [S3Qc_model_did_summary.txt](/outputs/section3/results/S3Qc_model_did_summary.txt)
- [S3Qc_model_did_coefficients.csv](/outputs/section3/results/S3Qc_model_did_coefficients.csv)

Full markdown copy:
- [section3_question_c_model_summaries.md](/docs/section3_question_c_model_summaries.md)

### 3.2 Model 2: Event Study

#### Why the second model is necessary

A DiD estimate is only credible if treated and control units were not already on diverging paths before treatment.

So the event-study model is not optional here. It is the key validity check.

#### Equation

The event-study replaces the single `treated:post` term with lead and lag indicators for treated buildings.

Let $k$ denote event time relative to the first full post-opening year (`2016` here). Then:

$$
\log(\text{Price}_i)
=
\beta_0
\;+\;
\sum_{k \in \{-4,-3,-2,0,1,2\}} \theta_k \cdot 1\{\text{Near}_i \text{ and event time } = k\}
\;+\;
\alpha_{\text{Type}_i}
\;+\;
\delta_{\text{Town}_i}
\;+\;
\lambda_t
\;+\;
\gamma_1 \cdot \text{FlatAge}_i
\;+\;
\gamma_2 \cdot \text{FloorArea}_i
\;+\;
\varepsilon_i
$$

In code terms:

$$
\log(\text{price})
\sim
\text{flat\_age}
\;+\;
\text{floor\_area\_sqm}
\;+\;
C(\text{flat\_type})
\;+\;
C(\text{town})
\;+\;
C(\text{transaction\_year})
\;+\;
\sum_k \text{treated\_event}_k
$$

#### How to interpret the coefficients

Each event coefficient says:

- how much more expensive near-station buildings were at that event time
- relative to the omitted baseline year
- after the same controls used in the DiD model

What matters most is the pattern:

- lead coefficients (`-4`, `-3`, `-2`) should be near zero if parallel trends are credible
- lag coefficients (`0`, `1`, `2`) should turn positive only after opening if the causal story is clean

#### What we actually see

From the saved output:

- `-4`: `+5.9%`
- `-3`: `+5.3%`
- `-2`: `+8.0%`
- `+0`: `+10.1%`
- `+1`: `+12.0%`
- `+2`: `+15.5%`

And the joint pre-trend p-value is:

$$
2.39 \times 10^{-52}
$$

That is overwhelmingly significant.

Interpretation:

- the post-opening effects are positive
- but treated buildings were already on a different path before opening
- so the event study weakens the causal interpretation of the DiD result

#### Full model summary

Saved output:
- [S3Qc_model_event_study_summary.txt](/outputs/section3/results/S3Qc_model_event_study_summary.txt)
- [S3Qc_model_event_study_coefficients.csv](/outputs/section3/results/S3Qc_model_event_study_coefficients.csv)

Full markdown copy:
- [section3_question_c_model_summaries.md](/docs/section3_question_c_model_summaries.md)

## 4. Robustness: 250m / 500m / 750m / 1000m Band Experiment

This is the new experiment added to the code.

Instead of treating all buildings within `1 km` as one group, the model now splits the near-station zone into:

- `0-250m`
- `250-500m`
- `500-750m`
- `750m-1.0km`

with:

- `1.5-4.0km control`

as the omitted reference group.

#### Equation

Let $\text{Band}_i$ be the distance band. The experimental model is:

$$
\log(\text{Price}_i)
=
\beta_0
\;+\;
C(\text{Band}_i)
\;+\;
\beta_1 \cdot \text{Post}_i
\;+\;
\beta_2 \cdot \bigl(C(\text{Band}_i) \times \text{Post}_i\bigr)
\;+\;
\alpha_{\text{Type}_i}
\;+\;
\delta_{\text{Town}_i}
\;+\;
\lambda_t
\;+\;
\gamma_1 \cdot \text{FlatAge}_i
\;+\;
\gamma_2 \cdot \text{FloorArea}_i
\;+\;
\varepsilon_i
$$

#### What it finds

Saved outputs:
- [S3Qc_model_distance_band_experiment_coefficients.csv](/outputs/section3/results/S3Qc_model_distance_band_experiment_coefficients.csv)
- [S3Qc_distance_band_experiment_effects.csv](/outputs/section3/results/S3Qc_distance_band_experiment_effects.csv)

The incremental post-opening effects versus the `1.5-4.0km` control are:

- `0-250m`: about `+15.2%`
- `250-500m`: about `+9.1%`
- `500-750m`: about `+4.1%`
- `750m-1.0km`: about `+2.8%`

This is the strongest evidence in the section that the DTL2 effect behaves like an accessibility gradient:

- the closer the building is to the new line, the larger the estimated uplift

That does not solve the pre-trend problem, but it does strengthen the economic interpretation of the pattern.

## 5. Answer To The Business Question

The best answer is:

> Yes, flats closer to DTL2 Stage 2 stations in the Bukit Timah corridor appear to have gained value relative to farther corridor buildings after opening, and the new `250/500/750/1000m` experiment shows a clear distance-decay pattern. However, the event-study pre-trends are strongly significant, so the evidence should be presented as suggestive rather than as a clean causal estimate.

So the final presentation line should be:

- **positive relative uplift in the baseline DiD**
- **stronger uplift the closer the flat is to the station**
- **but pre-trends fail, so causal language must be qualified**

That is a stronger and more honest conclusion than saying simply:

- “DTL2 definitely caused prices to rise”

or:

- “there is no effect”

The right framing is:

- **economically consistent with a rail-access premium**
- **statistically non-clean as a DiD because treated flats were already different before opening**
