# Section 3 Question A Case Note

## 1. Business Question

The business question for Section 3 Question A is:

> Is Yishun actually one of the cheaper HDB resale towns once we control for flat characteristics, or does it only look cheap because it transacts a different mix of flats?

In plain language, the case is trying to separate two stories:

- **Composition story**: Yishun looks cheap only because it has older flats, smaller flats, or a different flat-type mix.
- **Location-value story**: even after controlling for those differences, Yishun is still priced below comparable towns.

The analysis code for this question lives in [section3_question_a.py](/src/analysis/section3/section3_question_a.py).

## 2. EDA

The EDA in this question is not meant to prove the answer by itself. Its job is to make the comparison logic intuitive before moving into regression.

### 2.1 Candidate cheap towns by common flat type

This chart compares price-per-sqm distributions for the most common flat types in the recent sample.

![S3QaF1](/outputs/section3/charts/S3QaF1_yishun_candidate_towns_boxplot.svg)

Chart output:
- [S3QaF1_yishun_candidate_towns_boxplot.svg](/outputs/section3/charts/S3QaF1_yishun_candidate_towns_boxplot.svg)
- [S3QaF1_yishun_candidate_towns_boxplot.csv](/outputs/section3/results/S3QaF1_yishun_candidate_towns_boxplot.csv)

What it shows:
- Yishun sits in the lower-priced cluster for the major flat types.
- But this is still descriptive, not controlled.
- A town can look cheap here either because of genuine price discounting or because its transactions have a different composition.

### 2.2 Price versus space by town

This chart reframes the question from “absolute cheapness” to “value for money.”

![S3QaF3](/outputs/section3/charts/S3QaF3_yishun_price_vs_space.svg)

Chart output:
- [S3QaF3_yishun_price_vs_space.svg](/outputs/section3/charts/S3QaF3_yishun_price_vs_space.svg)
- [S3QaF3_yishun_price_vs_space.csv](/outputs/section3/results/S3QaF3_yishun_price_vs_space.csv)

What it shows:
- Buyers may experience Yishun as attractive not only because of total price, but because of the amount of space they get for the price.
- This supports the “value town” framing in the repo narrative.

### 2.3 Why EDA is not enough

EDA alone cannot answer the question cleanly because:

- different towns transact different flat types
- different towns have different age profiles
- the overall resale market moves materially over time

So the controlled answer needs regression with time controls and location controls.

## 3. Modeling

This question uses two related models:

1. a baseline fixed-effects-style hedonic regression
2. a heterogeneous-effects model with town-by-flat-type interactions

### 3.1 Model 1: Baseline Fixed-Effects Hedonic Regression

#### Method

This is implemented as OLS with:

- **town fixed effects** via `C(town, Treatment(...))`
- **month fixed effects** via `C(year_month)`
- controls for **flat type**
- a continuous control for **flat age**

This is a standard “dummy-variable fixed effects” setup: we absorb persistent town-level differences and common month-level price shocks, then ask whether Yishun still has a negative coefficient after those controls.

Method / library references:

- Fixed-effects intuition: [Panel analysis - fixed effects models](https://en.wikipedia.org/wiki/Panel_analysis)
- Statsmodels OLS fit: [statsmodels.regression.linear_model.OLS.fit](https://www.statsmodels.org/v0.12.2/generated/statsmodels.regression.linear_model.OLS.fit.html)
- Patsy treatment coding for categorical variables: [patsy Treatment coding](https://patsy.readthedocs.io/en/v0.1.0/API-reference.html#patsy.Treatment)
- HC3 robust standard errors: [statsmodels OLSResults.HC3_se](https://www.statsmodels.org/v0.12.2/generated/statsmodels.regression.linear_model.OLSResults.HC3_se.html)

#### Equation

Let:

- $i$ index transactions
- $t$ index transaction month
- $\text{Town}_i$ be the town of transaction $i$
- $\text{Type}_i$ be the flat type
- $\text{Age}_i$ be flat age
- $\lambda_t$ be month fixed effects
- $\alpha_j$ be town fixed effects

Then the baseline model is:

$$
\log(\text{PricePerSqm}_{i,t})
=
\beta_0
\;+\;
\alpha_{\text{Town}_i}
\;+\;
\gamma_{\text{Type}_i}
\;+\;
\delta \cdot \text{Age}_{i,t}
\;+\;
\lambda_t
\;+\;
\varepsilon_{i,t}
$$

In code, this corresponds to:

$$
\log(\text{price\_per\_sqm})
\sim
C(\text{town}) + C(\text{flat\_type}) + \text{flat\_age} + C(\text{year\_month})
$$

#### How to interpret the coefficient

The key coefficient is the Yishun town effect:

$$
\alpha_{\text{YISHUN}}
$$

Because the dependent variable is log price-per-sqm, the town coefficient is approximately a percentage discount or premium relative to the omitted reference town, holding other controls fixed.

In this run:

- reference town: `ANG MO KIO`
- reference flat type: `4 ROOM`
- Yishun coefficient: `-0.2373`
- implied percentage effect: about `-21.1%`
- 95% CI: about `[-21.4%, -20.9%]`

Interpretation:

- after controlling for flat type, flat age, and month fixed effects, Yishun resale price-per-sqm is about **21% lower** than the reference town
- the sign is strongly negative and statistically decisive

#### What we expected to see

If Yishun really is a cheaper-value town, we expected:

- a **negative** Yishun coefficient
- statistical significance
- the discount to survive after time controls and flat controls

That is exactly what the model shows.

#### Supporting chart

![S3QaF2](/outputs/section3/charts/S3QaF2_yishun_simple_regression_coefficients.svg)

Chart output:
- [S3QaF2_yishun_simple_regression_coefficients.svg](/outputs/section3/charts/S3QaF2_yishun_simple_regression_coefficients.svg)
- [S3QaF2_yishun_simple_regression_coefficients.csv](/outputs/section3/results/S3QaF2_yishun_simple_regression_coefficients.csv)

#### Full model summary

Saved output is reproduced inline below.

```text
                              OLS Regression Results                             
=================================================================================
Dep. Variable:     np.log(price_per_sqm)   R-squared:                       0.829
Model:                               OLS   Adj. R-squared:                  0.829
Method:                    Least Squares   F-statistic:                     7564.
Date:                   Sun, 29 Mar 2026   Prob (F-statistic):               0.00
Time:                           10:35:39   Log-Likelihood:             1.5762e+05
No. Observations:                 206696   AIC:                        -3.150e+05
Df Residuals:                     206565   BIC:                        -3.136e+05
Df Model:                            130                                         
Covariance Type:                     HC3                                         
===================================================================================================================================
                                                                      coef    std err          z      P>|z|      [0.025      0.975]
-----------------------------------------------------------------------------------------------------------------------------------
Intercept                                                           8.7939      0.004   2075.500      0.000       8.786       8.802
C(town, Treatment(reference='ANG MO KIO'))[T.BEDOK]                -0.0294      0.002    -18.787      0.000      -0.032      -0.026
C(town, Treatment(reference='ANG MO KIO'))[T.BISHAN]                0.1590      0.002     66.595      0.000       0.154       0.164
C(town, Treatment(reference='ANG MO KIO'))[T.BUKIT BATOK]          -0.1972      0.002   -120.878      0.000      -0.200      -0.194
C(town, Treatment(reference='ANG MO KIO'))[T.BUKIT MERAH]           0.1758      0.002     82.965      0.000       0.172       0.180
C(town, Treatment(reference='ANG MO KIO'))[T.BUKIT PANJANG]        -0.2538      0.002   -133.632      0.000      -0.258      -0.250
C(town, Treatment(reference='ANG MO KIO'))[T.BUKIT TIMAH]           0.2969      0.005     61.027      0.000       0.287       0.306
C(town, Treatment(reference='ANG MO KIO'))[T.CENTRAL AREA]          0.3335      0.005     68.065      0.000       0.324       0.343
C(town, Treatment(reference='ANG MO KIO'))[T.CHOA CHU KANG]        -0.3480      0.002   -211.580      0.000      -0.351      -0.345
C(town, Treatment(reference='ANG MO KIO'))[T.CLEMENTI]              0.0751      0.002     30.825      0.000       0.070       0.080
C(town, Treatment(reference='ANG MO KIO'))[T.GEYLANG]               0.0650      0.002     29.814      0.000       0.061       0.069
C(town, Treatment(reference='ANG MO KIO'))[T.HOUGANG]              -0.1573      0.002    -91.494      0.000      -0.161      -0.154
C(town, Treatment(reference='ANG MO KIO'))[T.JURONG EAST]          -0.1581      0.002    -74.443      0.000      -0.162      -0.154
C(town, Treatment(reference='ANG MO KIO'))[T.JURONG WEST]          -0.2816      0.002   -169.875      0.000      -0.285      -0.278
C(town, Treatment(reference='ANG MO KIO'))[T.KALLANG/WHAMPOA]       0.1184      0.002     54.993      0.000       0.114       0.123
C(town, Treatment(reference='ANG MO KIO'))[T.MARINE PARADE]         0.2727      0.004     66.634      0.000       0.265       0.281
C(town, Treatment(reference='ANG MO KIO'))[T.PASIR RIS]            -0.1996      0.002   -112.583      0.000      -0.203      -0.196
C(town, Treatment(reference='ANG MO KIO'))[T.PUNGGOL]              -0.2428      0.002   -150.405      0.000      -0.246      -0.240
C(town, Treatment(reference='ANG MO KIO'))[T.QUEENSTOWN]            0.2100      0.002     94.524      0.000       0.206       0.214
C(town, Treatment(reference='ANG MO KIO'))[T.SEMBAWANG]            -0.3393      0.002   -189.621      0.000      -0.343      -0.336
C(town, Treatment(reference='ANG MO KIO'))[T.SENGKANG]             -0.2626      0.002   -161.968      0.000      -0.266      -0.259
C(town, Treatment(reference='ANG MO KIO'))[T.SERANGOON]             0.0078      0.003      2.626      0.009       0.002       0.014
C(town, Treatment(reference='ANG MO KIO'))[T.TAMPINES]             -0.0996      0.002    -63.682      0.000      -0.103      -0.097
C(town, Treatment(reference='ANG MO KIO'))[T.TOA PAYOH]             0.0870      0.002     39.905      0.000       0.083       0.091
C(town, Treatment(reference='ANG MO KIO'))[T.WOODLANDS]            -0.3258      0.002   -210.108      0.000      -0.329      -0.323
C(town, Treatment(reference='ANG MO KIO'))[T.YISHUN]               -0.2373      0.002   -145.540      0.000      -0.241      -0.234
C(flat_type, Treatment(reference='4 ROOM'))[T.1 ROOM]               0.2103      0.008     26.220      0.000       0.195       0.226
C(flat_type, Treatment(reference='4 ROOM'))[T.2 ROOM]               0.0852      0.002     49.401      0.000       0.082       0.089
C(flat_type, Treatment(reference='4 ROOM'))[T.3 ROOM]               0.0356      0.001     52.474      0.000       0.034       0.037
C(flat_type, Treatment(reference='4 ROOM'))[T.5 ROOM]              -0.0069      0.001    -10.823      0.000      -0.008      -0.006
C(flat_type, Treatment(reference='4 ROOM'))[T.EXECUTIVE]            0.0594      0.001     62.628      0.000       0.058       0.061
C(flat_type, Treatment(reference='4 ROOM'))[T.MULTI-GENERATION]     0.1745      0.011     16.141      0.000       0.153       0.196
... month fixed effects omitted here for brevity in the note ...
flat_age                                                           -0.0115    2.3e-05   -501.506      0.000      -0.012      -0.011
==============================================================================
Omnibus:                     3901.247   Durbin-Watson:                   1.093
Prob(Omnibus):                  0.000   Jarque-Bera (JB):             5373.597
Skew:                           0.236   Prob(JB):                         0.00
Kurtosis:                       3.634   Cond. No.                     3.99e+03
==============================================================================
Notes:
[1] Standard Errors are heteroscedasticity robust (HC3)
```

### 3.2 Model 2: Town-by-Flat-Type Interaction Model

#### Why a second model is needed

The baseline model tells us whether Yishun is cheaper on average after controls.

But it does **not** tell us whether the discount is similar across flat types.

This matters because the business interpretation changes:

- if the discount appears across 3-room, 4-room, and 5-room flats, the “value town” story is broad
- if the discount exists only in one flat type, the story is more narrow and segment-specific

#### Equation

The interaction model adds town-by-flat-type interactions:

$$
\log(\text{PricePerSqm}_{i,t})
=
\beta_0
\;+\;
\alpha_{\text{Town}_i}
\;+\;
\gamma_{\text{Type}_i}
\;+\;
\theta_{\text{Town}_i,\text{Type}_i}
\;+\;
\delta \cdot \text{Age}_{i,t}
\;+\;
\lambda_t
\;+\;
\varepsilon_{i,t}
$$

In code:

$$
\log(\text{price\_per\_sqm})
\sim
C(\text{town}) * C(\text{flat\_type}) + \text{flat\_age} + C(\text{year\_month})
$$

#### How to interpret the coefficients

For Yishun:

- the **main Yishun coefficient** is the effect for the reference flat type (`4 ROOM`)
- each **Yishun × flat type** interaction adjusts that baseline for another flat type

So:

$$
\text{Effect of Yishun for 4-room} = \alpha_{\text{YISHUN}}
$$

$$
\text{Effect of Yishun for 5-room} = \alpha_{\text{YISHUN}} + \theta_{\text{YISHUN},5\text{ ROOM}}
$$

$$
\text{Effect of Yishun for 3-room} = \alpha_{\text{YISHUN}} + \theta_{\text{YISHUN},3\text{ ROOM}}
$$

#### What we expected to see

If Yishun is broadly a value town, we expected:

- negative effects for the major flat types
- not necessarily equal magnitudes, but a consistent direction

#### What we actually see

Estimated Yishun discount by flat type:

- 4-room: about `-26.2%`
- 5-room: about `-30.1%`
- 3-room: about `-11.5%`

That means the discount is broad, but strongest for larger flats.

This is consistent with a practical buyer story:

- Yishun may not be the absolute cheapest town in every raw comparison
- but it offers especially strong value in the larger, family-oriented segments

#### Supporting chart

![S3QaF4](/outputs/section3/charts/S3QaF4_yishun_interaction_effects_by_flat_type.svg)

Chart output:
- [S3QaF4_yishun_interaction_effects_by_flat_type.svg](/outputs/section3/charts/S3QaF4_yishun_interaction_effects_by_flat_type.svg)
- [S3QaF4_yishun_interaction_effects_by_flat_type.csv](/outputs/section3/results/S3QaF4_yishun_interaction_effects_by_flat_type.csv)

#### Full model summary

Saved output is reproduced inline below.

```text
                              OLS Regression Results                             
=================================================================================
Dep. Variable:     np.log(price_per_sqm)   R-squared:                       0.848
Model:                               OLS   Adj. R-squared:                  0.848
Method:                    Least Squares   F-statistic:                     5959.
Date:                   Sun, 29 Mar 2026   Prob (F-statistic):               0.00
Time:                           10:35:40   Log-Likelihood:             1.5173e+05
No. Observations:                 187477   AIC:                        -3.031e+05
Df Residuals:                     187300   BIC:                        -3.013e+05
Df Model:                            176                                         
Covariance Type:                     HC3                                         
=======================================================================================================================================================================================
                                                                                                                          coef    std err          z      P>|z|      [0.025      0.975]
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Intercept                                                                                                               8.8254      0.005   1885.287      0.000       8.816       8.835
C(town, Treatment(reference='ANG MO KIO'))[T.YISHUN]                                                                   -0.3038      0.003   -110.180      0.000      -0.309      -0.298
C(flat_type, Treatment(reference='4 ROOM'))[T.3 ROOM]                                                                  -0.0608      0.003    -22.973      0.000      -0.066      -0.056
C(flat_type, Treatment(reference='4 ROOM'))[T.5 ROOM]                                                                   0.0541      0.004     13.455      0.000       0.046       0.062
...
C(town, Treatment(reference='ANG MO KIO'))[T.YISHUN]:C(flat_type, Treatment(reference='4 ROOM'))[T.3 ROOM]              0.1820      0.003     52.881      0.000       0.175       0.189
C(town, Treatment(reference='ANG MO KIO'))[T.YISHUN]:C(flat_type, Treatment(reference='4 ROOM'))[T.5 ROOM]             -0.0540      0.005    -11.430      0.000      -0.063      -0.045
flat_age                                                                                                               -0.0112   2.41e-05   -465.667      0.000      -0.011      -0.011
==============================================================================
Omnibus:                     5711.161   Durbin-Watson:                   1.130
Prob(Omnibus):                  0.000   Jarque-Bera (JB):            10128.068
Skew:                           0.258   Prob(JB):                         0.00
Kurtosis:                       4.015   Cond. No.                     4.04e+03
==============================================================================
Notes:
[1] Standard Errors are heteroscedasticity robust (HC3)
```

### 3.3 All-town comparison

This chart places Yishun into the full town ranking after controls.

![S3QaF5](/outputs/section3/charts/S3QaF5_yishun_all_town_dummy_coefficients.svg)

Chart output:
- [S3QaF5_yishun_all_town_dummy_coefficients.svg](/outputs/section3/charts/S3QaF5_yishun_all_town_dummy_coefficients.svg)
- [S3QaF5_yishun_all_town_dummy_coefficients.csv](/outputs/section3/results/S3QaF5_yishun_all_town_dummy_coefficients.csv)

Why this matters:
- it confirms that the Yishun result is not just “negative relative to one reference town”
- it places Yishun within the broader adjusted town landscape

## 4. Answer to the Question

The safest answer is:

**Yes. Yishun still looks meaningfully cheaper after controls, so it is more accurate to describe it as a genuine value town rather than a town that only looks cheap because of mix effects.**

More specifically:

- the baseline fixed-effects model estimates Yishun at about **21% lower price-per-sqm** than the reference town after controlling for flat type, flat age, and month effects
- the interaction model shows the discount is not confined to one segment
- the discount is strongest in **4-room and 5-room flats**, and smaller but still present in **3-room flats**

So the final business interpretation is:

- Yishun is **not merely composition-cheap**
- Yishun is **structurally value-priced** in the recent resale market
- the strongest practical value proposition appears in the larger flat segments

## 5. Output Index

Charts cited in this note:

- [S3QaF1_yishun_candidate_towns_boxplot.svg](/outputs/section3/charts/S3QaF1_yishun_candidate_towns_boxplot.svg)
- [S3QaF2_yishun_simple_regression_coefficients.svg](/outputs/section3/charts/S3QaF2_yishun_simple_regression_coefficients.svg)
- [S3QaF3_yishun_price_vs_space.svg](/outputs/section3/charts/S3QaF3_yishun_price_vs_space.svg)
- [S3QaF4_yishun_interaction_effects_by_flat_type.svg](/outputs/section3/charts/S3QaF4_yishun_interaction_effects_by_flat_type.svg)
- [S3QaF5_yishun_all_town_dummy_coefficients.svg](/outputs/section3/charts/S3QaF5_yishun_all_town_dummy_coefficients.svg)

Model summary artifacts:

- [S3Qa_model_key_numbers.json](/outputs/section3/results/S3Qa_model_key_numbers.json)
