# Section 3 Question B Case Note

## 1. Business Question

The business question for Section 3 Question B is:

> Are newer HDB flats getting smaller?

In business terms, this is not just a descriptive curiosity. It affects how we talk about housing affordability:

- if newer flats are materially smaller, then buyers may face a hidden affordability trade-off where nominal prices do not tell the full story
- if the pattern is concentrated in only some flat types, then the story is more nuanced than a blanket “all new flats are shrinking”
- if the apparent decline is just composition, then the concern is overstated

So the analytical task is to separate three possibilities:

1. a raw average-size decline driven by newer flats actually being smaller
2. a compositional shift driven by different flat-type mix over time
3. a nonlinear design pattern where some flat types shrink and others do not

The analysis code for this question lives in [section3_question_b.py](/src/analysis/section3/section3_question_b.py).

## 2. EDA

The EDA here is important because stakeholders understand “sqm over time” much faster than they understand regression coefficients. The EDA does not prove the answer on its own, but it establishes what must be explained by the models.

### 2.1 Average floor area by completion year

![S3QbF1](/outputs/section3/charts/S3QbF1_floor_area_over_time.svg)

Chart outputs:
- [S3QbF1_floor_area_over_time.svg](/outputs/section3/charts/S3QbF1_floor_area_over_time.svg)
- [S3QbF1_floor_area_over_time.csv](/outputs/section3/results/S3QbF1_floor_area_over_time.csv)

What it shows:

- the overall average does not collapse steadily year after year
- the apparent trend differs by flat type
- larger flat types matter most for the business interpretation, because they contribute most to the “families are getting less space” narrative

### 2.2 Split view: common versus sparse flat types

![S3QbF1a](/outputs/section3/charts/S3QbF1a_floor_area_over_time.svg)

Chart outputs:
- [S3QbF1a_floor_area_over_time.svg](/outputs/section3/charts/S3QbF1a_floor_area_over_time.svg)
- [S3QbF1a_floor_area_over_time.csv](/outputs/section3/results/S3QbF1a_floor_area_over_time.csv)

![S3QbF1b](/outputs/section3/charts/S3QbF1b_floor_area_over_time.svg)

Chart outputs:
- [S3QbF1b_floor_area_over_time.svg](/outputs/section3/charts/S3QbF1b_floor_area_over_time.svg)
- [S3QbF1b_floor_area_over_time.csv](/outputs/section3/results/S3QbF1b_floor_area_over_time.csv)

Why the split matters:

- `3 ROOM`, `4 ROOM`, and `5 ROOM` are the common flat types and carry most of the practical market story
- `1 ROOM`, `2 ROOM`, and `EXECUTIVE` are sparse or niche and have noisier year-by-year patterns
- separating them avoids over-reading volatility from thin cells

### 2.3 Simple slope summary by flat type

Chart outputs:
- [S3QbF2_floor_area_slope_by_type.csv](/outputs/section3/results/S3QbF2_floor_area_slope_by_type.csv)

The raw slope file shows:

- `EXECUTIVE`: about `-1.21 sqm` per completion year
- `5 ROOM`: about `-0.39 sqm` per completion year
- `4 ROOM`: about `-0.10 sqm` per completion year
- `3 ROOM`: near flat at about `-0.01 sqm` per year
- `1 ROOM` and `2 ROOM`: not declining in the same way

This already suggests that the shrinkage story is not uniform across all flat types.

### 2.4 Focus on the post-2008 period

Chart outputs:
- [S3QbF3_floor_area_post_2008.csv](/outputs/section3/results/S3QbF3_floor_area_post_2008.csv)
- [S3QbF3a_floor_area_post_2008.csv](/outputs/section3/results/S3QbF3a_floor_area_post_2008.csv)
- [S3QbF3b_floor_area_post_2008.csv](/outputs/section3/results/S3QbF3b_floor_area_post_2008.csv)

This view matters because most of the current affordability discussion is about recent supply, not 1970s design history.

From the saved data:

- `4 ROOM` averages are around `93-95 sqm` in the early 2010s and are lower in many later years
- `5 ROOM` averages are around `116 sqm` in 2012 and closer to `113.5 sqm` by 2020
- `3 ROOM` stays relatively stable around `67-69 sqm`

That is consistent with a recent decline in larger flat types, but not a broad-based decline in every category.

### 2.5 Adjusted completion-year profile by flat type

Chart outputs:
- [S3QbF4_adjusted_year_trend_by_type.csv](/outputs/section3/results/S3QbF4_adjusted_year_trend_by_type.csv)
- [S3QbF4a_adjusted_year_trend_by_type.csv](/outputs/section3/results/S3QbF4a_adjusted_year_trend_by_type.csv)
- [S3QbF4b_adjusted_year_trend_by_type.csv](/outputs/section3/results/S3QbF4b_adjusted_year_trend_by_type.csv)

This is the bridge between EDA and modeling:

- it compares years within flat type
- it controls for town composition
- it makes clear that the completion-year effect is not well-described by one straight line for all flat types

## 3. Modeling

This question is best explained with two models:

1. a simple controlled trend model to answer “is there a broad size decline at all?”
2. a richer interaction model to answer “does the completion-year pattern differ by flat type?”

### 3.1 Model 1: Controlled Trend Model

#### Method and intuition

This is a fixed-effects-style dummy-variable regression implemented with `statsmodels` formula OLS:

- town controls absorb persistent cross-town differences in average unit size
- flat-type controls absorb the structural size gap between `3 ROOM`, `4 ROOM`, `5 ROOM`, etc.
- the completion-year term captures whether newer-completion cohorts are systematically larger or smaller after those controls

Method / library references:

- Statsmodels formula API examples: [statsmodels formula examples](https://www.statsmodels.org/stable/example_formulas.html)
- Statsmodels OLS formula API: [statsmodels.formula.api.ols](https://www.statsmodels.org/stable/generated/statsmodels.formula.api.ols.html)
- Patsy treatment coding for categorical regressors: [patsy Treatment coding](https://patsy.readthedocs.io/en/latest/builtins-reference.html#patsy.builtins.Treatment)

Important implementation note:

- the saved summary artifact for Model 1 is the linear completion-year specification below
- the current codebase is moving toward categorical completion-year effects for the richer model, because the year pattern is plausibly nonlinear
- for documentation fidelity, this note describes Model 1 using the saved artifact that currently exists in [S3Qb_model_controlled_completion_year_summary.txt](/outputs/section3/results/S3Qb_model_controlled_completion_year_summary.txt)

#### Equation

Let:

- $i$ index transactions
- $\text{Area}_i$ be `floor_area_sqm`
- $\text{Year}_i$ be completion year
- $\alpha_{\text{Type}_i}$ be flat-type fixed effects
- $\delta_{\text{Town}_i}$ be town fixed effects

Then Model 1 is:

$$
\text{Area}_i
=
\beta_0
\;+\;
\beta_1 \cdot \text{Year}_i
\;+\;
\alpha_{\text{Type}_i}
\;+\;
\delta_{\text{Town}_i}
\;+\;
\varepsilon_i
$$

In code terms, the saved model summary corresponds to:

$$
\text{floor\_area\_sqm}
\sim
\text{completion\_year}
\;+\;
C(\text{flat\_type})
\;+\;
C(\text{town})
$$

#### How to interpret the coefficients

The key coefficient is:

$$
\beta_1
$$

It measures the average difference in floor area, in square metres, associated with a one-year increase in completion year, after controlling for flat type and town.

From the saved model output:

- `completion_year` coefficient: about `-0.0388`
- 95% CI: about `[-0.0404, -0.0372]`
- p-value: effectively `0`

Interpretation:

- holding flat type and town constant, a flat completed one year later is associated with about `0.039 sqm` less floor area on average
- over 10 years, that is about `0.39 sqm`
- the sign is negative and statistically decisive, but the magnitude is small when averaged across all flat types

#### What we expected to see

If the “new flats are getting smaller” story were broadly true, we would expect:

- a negative completion-year coefficient
- a precise estimate
- the decline to survive flat-type and town controls

That is what Model 1 shows at the average market level.

#### Why we do not log floor area here

The business question is about physical size, not proportional size.

So we keep the dependent variable in levels:

$$
\text{floor\_area\_sqm}
$$

rather than:

$$
\log(\text{floor\_area\_sqm})
$$

This makes the coefficient directly interpretable in square metres lost or gained. That is the more natural business unit for this question.

#### Full model summary

Saved output:
- [S3Qb_model_controlled_completion_year_summary.txt](/outputs/section3/results/S3Qb_model_controlled_completion_year_summary.txt)
- [S3Qb_model_controlled_completion_year_coefficients.csv](/outputs/section3/results/S3Qb_model_controlled_completion_year_coefficients.csv)

### 3.2 Model 2: Completion-Year-by-Flat-Type Interaction Model

#### Why a second model is needed

Model 1 is intentionally simple, but it imposes one common average trend across the entire market.

That is probably too restrictive because:

- `3 ROOM` flats may have a different design history from `5 ROOM`
- shrinkage may be concentrated after certain policy or design periods
- the raw charts already suggest nonlinearity

So the second model relaxes both assumptions:

- completion year enters as a categorical variable rather than a straight line
- the year pattern is allowed to differ by flat type

#### Method and intuition

This model is estimated as weighted least squares on year-by-flat-type-by-town cells:

- the dependent variable is still average floor area in sqm
- each cell is weighted by its transaction count
- `C(completion_year)` avoids assuming that the year effect is linear
- `C(completion_year) * C(flat_type)` allows the completion-year profile to differ by flat type
- `C(town)` controls for persistent town-level size differences

Method / library references:

- Statsmodels WLS formula API: [statsmodels.formula.api.wls](https://www.statsmodels.org/stable/generated/statsmodels.formula.api.wls.html)
- Statsmodels formula examples: [statsmodels formula examples](https://www.statsmodels.org/stable/example_formulas.html)
- Patsy treatment coding for categorical regressors: [patsy Treatment coding](https://patsy.readthedocs.io/en/latest/builtins-reference.html#patsy.builtins.Treatment)

#### Equation

Let:

- $y$ index completion year
- $f$ index flat type
- $t$ index town
- $w_{yft}$ be the number of transactions in the cell

Then Model 2 is:

$$
\text{Area}_{yft}
=
\beta_0
\;+\;
\lambda_y
\;+\;
\alpha_f
\;+\;
\theta_{y,f}
\;+\;
\delta_t
\;+\;
\varepsilon_{yft}
$$

estimated with weights:

$$
w_{yft} = \text{transactions}_{yft}
$$

In code terms:

$$
\text{floor\_area\_sqm}
\sim
C(\text{completion\_year})
*
C(\text{flat\_type}, \text{Treatment(reference='4 ROOM')})
\;+\;
C(\text{town})
$$

#### How to interpret the coefficients

This model has three coefficient blocks that matter:

1. `C(completion_year)[T.y]`
   - the year effect for the reference flat type
   - here the reference flat type is `4 ROOM`

2. `C(flat_type)[T.f]`
   - the level difference between flat type `f` and the reference flat type in the omitted base year

3. `C(completion_year)[T.y] : C(flat_type)[T.f]`
   - how flat type `f` deviates from the `4 ROOM` completion-year profile in year `y`

The interpretation is therefore relative, not absolute:

- a negative interaction term means that flat type `f` is smaller than the `4 ROOM` baseline would imply in that year
- a positive interaction term means it is larger than the `4 ROOM` baseline would imply in that year

This is why the charts derived from the model, especially `F4`, are easier to explain than the raw coefficient table.

#### What we expected to see

If shrinkage is mainly a larger-flat phenomenon, we would expect:

- downward relative profiles for `4 ROOM`, `5 ROOM`, and `EXECUTIVE`
- a flatter profile for `3 ROOM`
- noisy estimates for `1 ROOM` and `2 ROOM` because those cells are sparse

That is broadly what the EDA and adjusted-profile charts suggest.

#### Why categorical completion-year effects are preferable here

The year pattern is unlikely to be truly linear. HDB design standards changed in episodes, not in a perfectly smooth line.

So:

$$
C(\text{completion\_year})
$$

is preferable to:

$$
\text{completion\_year}
$$

for the interaction model, because it allows:

- jumps
- reversals
- plateaus
- flat-type-specific design breaks

This is the correct specification when the business question is about changing design eras rather than one steady secular slope.

#### Full model summary

Saved output:
- [S3Qb_model_completion_year_dummy_interaction_summary.txt](/outputs/section3/results/S3Qb_model_completion_year_dummy_interaction_summary.txt)
- [S3Qb_model_completion_year_dummy_interaction_coefficients.csv](/outputs/section3/results/S3Qb_model_completion_year_dummy_interaction_coefficients.csv)

## 4. Answer To The Business Question

The best answer is:

> Yes, there is evidence that newer HDB flats are getting smaller, but the effect is not uniform across all flat types. The strongest decline appears in larger formats such as `4 ROOM`, `5 ROOM`, and `EXECUTIVE`, while `3 ROOM` is relatively stable and the smallest categories are too sparse or idiosyncratic to support a broad shrinking narrative.

More precisely:

- the raw averages show that larger flat types are generally smaller in more recent completion cohorts
- the simple controlled model finds a statistically significant negative average completion-year effect
- the richer interaction model shows that the year pattern is nonlinear and differs by flat type, which is exactly why the “all new flats are shrinking” claim should be qualified

So the final business framing should be:

- **true directionally**
- **strongest for larger flat types**
- **not a universal statement about every HDB format**
- **best explained as a design-era change, not just one smooth linear decline**
