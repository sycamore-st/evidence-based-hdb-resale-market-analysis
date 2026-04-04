# Section 3 Question D Case Note

## 1. Business Question

The business question for Section 3 Question D is:

> There have been comments online that people are buying flats in towns further from the city so that the cost savings can be used for a car. Are resale prices in HDB estates in areas further away from the city, specifically Sengkang and Punggol, impacted by COE prices for cars?

The implemented analytical version is:

> Are Sengkang and Punggol resale prices more sensitive to COE movements than prices in central HDB towns?

That distinction matters.

The question is not whether all HDB prices co-move with COE. It is whether the far-out towns are unusually COE-sensitive relative to central towns.

That still leaves the sign economically ambiguous:

- if higher COE mainly makes car ownership less affordable, far-town demand could weaken, implying a **negative** extra far-town sensitivity
- if buyers substitute into cheaper far-town flats to preserve a housing-plus-car budget, far-town demand could strengthen relative to central towns, implying a **positive** extra far-town sensitivity

So the test is fundamentally about **differential sensitivity**, while a positive sign should be interpreted specifically as support for a housing-car substitution mechanism.

The analysis code for this question lives in [section3_question_d.py](/src/analysis/section3/section3_question_d.py).

## 2. EDA

### 2.1 Raw indexed co-movement

Outputs:

- [S3QdF1_indexed_coe_and_resale_trends.svg](/outputs/section3/charts/S3QdF1_indexed_coe_and_resale_trends.svg)
- [S3QdF1_indexed_coe_and_resale_trends.csv](/outputs/section3/results/S3QdF1_indexed_coe_and_resale_trends.csv)

Preview:

![Qd F1](/outputs/section3/charts/S3QdF1_indexed_coe_and_resale_trends.svg)

This chart is only an intuition chart.

The raw indexed series are constructed very simply:

- first, for each town-month pair, the code computes the **monthly median resale price**
- then, for `CENTRAL AREA`, `SENGKANG`, and `PUNGGOL`, each town's monthly median-price series is **rebased to 100 at its first observed month**
- separately, the monthly **average COE premium** is computed and also **rebased to 100 at its first observed month**

So for any town or for COE, the raw index is:

$$
\text{RawIndex}_{t}
=
100 \times \frac{\text{Level}_{t}}{\text{Level}_{t_0}}
$$

where $\text{Level}_{t}$ is either:

- the town's monthly median resale price, or
- the monthly average COE premium

and $t_0$ is the first month in that series.

That means this figure is not using a hedonic model, not quality adjustment, and not a repeat-sales method. It is just a common-base visual normalization that puts all series on the same `100` starting scale so their broad co-movement can be compared.

It shows that COE, Central Area, Sengkang, and Punggol all move over time in broadly similar directions. That is enough to make the online claim plausible, but not enough to prove anything, because broad macro conditions can move all series together.

### 2.2 Adjusted housing indices versus COE

Outputs:

- [S3QdF1b_adjusted_indexed_coe_and_resale_trends.svg](/outputs/section3/charts/S3QdF1b_adjusted_indexed_coe_and_resale_trends.svg)
- [S3QdF1b_adjusted_indexed_coe_and_resale_trends.csv](/outputs/section3/results/S3QdF1b_adjusted_indexed_coe_and_resale_trends.csv)

Preview:

![Qd F1b](/outputs/section3/charts/S3QdF1b_adjusted_indexed_coe_and_resale_trends.svg)

This chart improves on the raw index by first estimating quality-adjusted housing indices for:

- central towns
- Sengkang/Punggol

using a hedonic model that controls for:

- flat age
- floor area
- flat type
- town composition

This makes the visual comparison more meaningful than raw medians.

More precisely, the code runs two separate hedonic regressions:

- one on the pooled central-town sample
- one on the pooled Sengkang/Punggol sample

Each regression is:

$$
\log(\text{ResalePrice}_{i,t}) = \alpha
\;+\; \lambda_t
\;+\; \beta_1 \cdot \text{FlatAge}_{i,t}
\;+\; \beta_2 \cdot \text{FloorArea}_{i,t}
\;+\; \alpha_{\text{FlatType}_i}
\;+\; \delta_{\text{Town}_i}
\;+\; \varepsilon_{i,t}
$$

with:

- month fixed effects $\lambda_t$ at the `year_month` level
- flat-level controls for age and floor area
- flat-type fixed effects
- town fixed effects inside each pooled group

The estimated month effects are then exponentiated and rebased so that the first observed month equals `100`. So these are not raw medians and not cumulative growth rates computed mechanically from transaction averages; they are model-based month effects after holding observed flat composition roughly constant.

That matters for interpretation:

- if the adjusted far-town index rises faster than the adjusted central index, that is evidence of relative appreciation after correcting for shifting mix
- if both adjusted indices simply co-move with COE, that is still only descriptive evidence, not the final test of differential COE sensitivity

### 2.3 Far-town minus central-town spread

Outputs:

- [S3QdF2_far_vs_central_price_spread.svg](/outputs/section3/charts/S3QdF2_far_vs_central_price_spread.svg)
- [S3QdF2_far_vs_central_price_spread.csv](/outputs/section3/results/S3QdF2_far_vs_central_price_spread.csv)
- [S3QdF2b_adjusted_far_vs_central_index_spread.svg](/outputs/section3/charts/S3QdF2b_adjusted_far_vs_central_index_spread.svg)
- [S3QdF2b_adjusted_far_vs_central_index_spread.csv](/outputs/section3/results/S3QdF2b_adjusted_far_vs_central_index_spread.csv)

Preview:

![Qd F2](/outputs/section3/charts/S3QdF2_far_vs_central_price_spread.svg)

Adjusted-index preview:

![Qd F2b](/outputs/section3/charts/S3QdF2b_adjusted_far_vs_central_index_spread.svg)

This is the more relevant descriptive chart.

It asks:

$$
\text{far-town price spread} = \text{Sengkang/Punggol average price} - \text{central-town average price}
$$

So the chart is about relative performance, not just common upward drift.

In plain English, the spread tells us whether Sengkang/Punggol are getting cheaper or more expensive **relative to** the central control towns:

- if the spread is **negative**, the far towns are still cheaper than the central towns
- if the spread becomes **less negative** over time, the far towns are catching up
- if the spread becomes **more negative**, the far towns are falling further behind
- if the spread tends to rise when COE rises, that is directionally consistent with the idea that the far towns strengthen relative to central towns when the value of a cheaper flat-plus-car bundle becomes more relevant

But the same relative-performance logic should also be applied to the indices, not only to the dollar-price spread.

In other words, once we construct the adjusted indices, the relevant descriptive question becomes:

$$
\text{far-town adjusted spread index}
=
\text{Adjusted Index}_{\text{Sengkang/Punggol},t}
\;-\;
\text{Adjusted Index}_{\text{Central},t}
$$

or equivalently the gap between the two indexed series over time.

That indexed comparison is often more interpretable than the raw dollar spread because:

- the raw spread mixes level differences with appreciation dynamics
- the indexed spread isolates relative growth from a common base of `100`
- it aligns better with the interaction-regression question, which is about relative sensitivity rather than absolute price levels

So the raw price-spread chart is useful, but the adjusted-index gap is conceptually closer to the management question.

### 2.4 Raw scatter of COE versus spread

Outputs:

- [S3QdF3_coe_vs_price_spread.svg](/outputs/section3/charts/S3QdF3_coe_vs_price_spread.svg)
- [S3QdF3_coe_vs_price_spread.csv](/outputs/section3/results/S3QdF3_coe_vs_price_spread.csv)

Preview:

![Qd F3](/outputs/section3/charts/S3QdF3_coe_vs_price_spread.svg)

This chart is a raw monthly relationship.

It is useful visually, but it is not the main model. The main model is the controlled interaction regression below.

### 2.5 Coefficient explainer charts

Outputs:

- [S3QdF4_coe_regression_coefficients.svg](/outputs/section3/charts/S3QdF4_coe_regression_coefficients.svg)
- [S3QdF4_coe_regression_coefficients.csv](/outputs/section3/results/S3QdF4_coe_regression_coefficients.csv)
- [S3QdF5_adjusted_index_regression_coefficients.svg](/outputs/section3/charts/S3QdF5_adjusted_index_regression_coefficients.svg)
- [S3QdF5_adjusted_index_regression_coefficients.csv](/outputs/section3/results/S3QdF5_adjusted_index_regression_coefficients.csv)

Preview:

![Qd F4](/outputs/section3/charts/S3QdF4_coe_regression_coefficients.svg)

Adjusted-index preview:

![Qd F5](/outputs/section3/charts/S3QdF5_adjusted_index_regression_coefficients.svg)

These are the key communication charts because they explain what each regression coefficient means in plain English for:

- the raw town-month price model
- the adjusted-index model

## 3. Modeling

The Question D story is best told with three linked modeling steps:

1. a raw town-month price interaction model
2. a hedonic model that builds adjusted monthly housing indices
3. a second-stage adjusted town-month regression that tests whether Sengkang/Punggol are more COE-sensitive than central towns after composition adjustment

The raw-price model is included as a benchmark. The adjusted-index model is the preferred version because it better controls for changes in the mix of transacted flats.

### 3.1 Model 1: Raw town-month price interaction

#### Purpose

This is the direct benchmark model.

It asks whether monthly median resale prices in Sengkang/Punggol react more strongly to COE than monthly median prices in the central control towns, after absorbing:

- town fixed effects
- month fixed effects

This version is easy to explain, but it still mixes together changing flat composition across towns and time.

#### Equation

Let:

- $t$ index months
- $j$ index towns
- $\text{FarTown}_j = 1$ for Sengkang or Punggol
- $\log(\text{COE}_t)^\ast$ be centered log COE

Then:

$$
\log(\text{MedianPrice}_{j,t})
=
\alpha
\;+\;\beta_1 \cdot \log(\text{COE}_t)^\ast
\;+\;\beta_2 \cdot \text{FarTown}_j
\;+\;\beta_3 \cdot \left(\log(\text{COE}_t)^\ast \times \text{FarTown}_j\right)
\;+\;\delta_j
\;+\;\lambda_t
\;+\;\varepsilon_{j,t}
$$

This is implemented as:

$$
\log(\text{median\_price})
\sim
\text{log\_coe\_centered} * \text{far\_town} + C(\text{town}) + C(\text{year\_month})
$$

#### Result

From the saved output:

- central-town raw-price COE elasticity: about `0.255`
- extra far-town raw-price sensitivity: about `0.0316`
- p-value on extra raw-price sensitivity: about `0.061`
- implied total far-town raw-price elasticity: about `0.287`

So the raw model is directionally supportive, but only marginally significant at the 10% level.

#### Saved summary

- [S3Qd_raw_price_interaction_summary.txt](/outputs/section3/results/S3Qd_raw_price_interaction_summary.txt)
- [S3Qd_raw_price_interaction_coefficients.csv](/outputs/section3/results/S3Qd_raw_price_interaction_coefficients.csv)

### 3.2 Model 2: Hedonic monthly housing index

#### Purpose

This model is not the final causal test.

Its job is to produce cleaner housing price paths for:

- central towns
- Sengkang/Punggol

so the visual comparison against COE is not distorted by changing flat mix.

Implementation detail:

- the model is estimated separately for `Central adjusted housing index` and `Sengkang/Punggol adjusted housing index`
- for each group, month fixed effects are extracted from the fitted hedonic regression
- those month effects are transformed back from log points and rebased to an index with first month `= 100`

So this is a standard time-dummy hedonic index construction, not a repeat-sales index and not a simple median-price index.

#### Equation

For each housing group:

$$
\log(\text{ResalePrice}_{i,t}) = \alpha
\;+\; \lambda_t
\;+\; \beta_1 \cdot \text{FlatAge}_{i,t}
\;+\; \beta_2 \cdot \text{FloorArea}_{i,t}
\;+\; \alpha_{\text{FlatType}_i}
\;+\; \delta_{\text{Town}_i}
\;+\; \varepsilon_{i,t}
$$

where:

- $\lambda_t$ are year-month effects
- the estimated month effects are converted into an index

Practical interpretation:

- $\beta_1$ and $\beta_2$ absorb changing age and size composition
- $\alpha_{\text{FlatType}_i}$ absorbs changing flat-type mix
- $\delta_{\text{Town}_i}$ absorbs persistent cross-town level differences within the pooled group
- the remaining month effects trace the adjusted price path for that group

#### Expected result

If the online claim is plausible, the far-town adjusted index should directionally move with COE.

But the stronger diagnostic is not simple co-movement. The stronger diagnostic is whether:

- the far-town adjusted index outperforms the central adjusted index when COE is high, or
- the far-town minus central adjusted-index gap widens with COE

That is why the spread framing should be carried from raw prices into the indexed charts as well.

#### Saved summaries

- [S3Qd_central_adjusted_housing_index_hedonic_summary.txt](/outputs/section3/results/S3Qd_central_adjusted_housing_index_hedonic_summary.txt)
- [S3Qd_sengkang_punggol_adjusted_housing_index_hedonic_summary.txt](/outputs/section3/results/S3Qd_sengkang_punggol_adjusted_housing_index_hedonic_summary.txt)

### 3.3 Model 3: Adjusted town-month COE interaction regression

#### Purpose

This is the preferred test of the online claim.

It asks whether the **hedonic-adjusted** Sengkang/Punggol housing index reacts more strongly to COE than the **hedonic-adjusted** central-town housing index.

This is a deliberate change from a raw town-month median-price regression. The first-stage hedonic model already adjusts for:

- floor area
- flat age
- flat type
- town composition within each pooled group

So the second stage can focus on the relationship between:

- adjusted housing price paths
- COE movements
- the far-town versus central-town gap

#### Equation

Let:

- $g$ index housing groups, where $g \in \{\text{Central}, \text{FarTown}\}$
- $\text{FarTown}_g = 1$ for the Sengkang/Punggol adjusted index
- $\log(\text{COE}_t)^\ast$ be centered log COE
- $\text{AdjPrice}_{g,t}$ be the hedonic-adjusted housing index from Model 1

Then:

$$
\log(\text{AdjPrice}_{g,t})
=
\alpha
\;+\;\beta_1 \cdot \log(\text{COE}_t)^\ast
\;+\;\beta_2 \cdot \text{FarTown}_g
\;+\;\beta_3 \cdot \left(\log(\text{COE}_t)^\ast \times \text{FarTown}_g\right)
\;+\;\varepsilon_{g,t}
$$

This is implemented as:

$$
\log(\text{adjusted\_index})
\sim
\text{log\_coe\_centered} * \text{far\_town}
$$

Why there is no floor-area term here:

- size is already adjusted for in the first-stage hedonic model
- the second stage is run on the adjusted group-month index, not on individual flats
- adding flat-level size directly at the second stage would not match the level of aggregation

#### Coefficient interpretation

The key coefficients are:

1. `log_coe_centered`

- baseline COE elasticity for the **central adjusted housing index**

2. `far_town`

- average level difference of the **far-town adjusted index** at average COE

3. `log_coe_centered:far_town`

- extra COE sensitivity of the **far-town adjusted index** relative to the **central adjusted index**

That third coefficient is the main test of the online story.

#### Expected sign

The key point is that the sign of $\beta_3$ is not mechanically fixed by the prompt alone.

- If higher COE mainly discourages car ownership, we could see $\beta_3 < 0$ because far-town demand softens.
- If buyers respond by substituting into cheaper far-town flats to preserve a housing-plus-car bundle, we would expect $\beta_3 > 0$.

So in this case a **positive** $\beta_3$ should be interpreted as evidence in favor of the substitution story, not as something that was guaranteed ex ante by the wording of the question.

#### Result

From the saved output:

- central adjusted-index COE elasticity: about `0.290`
- extra far-town sensitivity: about `0.0736`
- p-value on extra sensitivity: about `0.007`
- implied total far-town elasticity: about `0.364`

So the result is:

- positive in direction
- economically meaningful
- statistically stronger than the raw median-price version

That is still suggestive rather than definitive, but it is a cleaner result because it works off the quality-adjusted housing indices rather than raw town-month medians.

#### Saved summary

- [S3Qd_main_interaction_summary.txt](/outputs/section3/results/S3Qd_main_interaction_summary.txt)
- [S3Qd_main_interaction_coefficients.csv](/outputs/section3/results/S3Qd_main_interaction_coefficients.csv)

#### Full copied summaries

- [section3_question_d_model_summaries.md](/docs/section3_question_d_model_summaries.md)

## 4. Answer

The most defensible answer to Question D is:

Sengkang and Punggol do appear more COE-sensitive than central towns in both the raw town-month price model and the adjusted town-month index model. Because the estimated interaction is positive, the evidence is directionally consistent with a housing-car substitution story in which buyers lean toward cheaper far-out flats when COE rises.

The comparison between the two models matters. The raw town-month price regression finds only a modest extra far-town sensitivity of about `0.0316` with a p-value around `0.061`, while the adjusted-index version finds a larger extra sensitivity of about `0.0736` with a p-value around `0.007`.

Because the adjusted version uses quality-adjusted housing indices, it is a cleaner test than a raw town-month price regression. But it should still not be presented as strong evidence that households explicitly used housing savings to buy cars.

The right conclusion is:

$$
\text{The pattern is suggestive of a positive housing-car substitution mechanism, but it remains correlational rather than conclusive.}
$$
