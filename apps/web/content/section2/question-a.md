---
title: "Question A: Predicting 2014 HDB Resale Prices"
kicker: "Section 2 / Question A"
description: "A blog-style case note on predicting 2014 HDB resale prices using only flat type, flat age, and town, with three candidate models and a final model choice."
section: "section2"
slug: "question-a"
order: 1
---

# Section 2 Question A Case Note

## 1. Business Question

The case asks a deliberately constrained prediction question:

> Predict a resale flat transaction price in 2014 using only `flat_type`, `flat_age`, and `town`. Propose and implement at least three models, select the best model, and explain the choice.

The analysis code lives in [section2_question_a.py](/src/analysis/section2/section2_question_a.py), and the official feature set is defined in [S2_config.py](/src/analysis/section2/S2_config.py) as:

- `flat_type`
- `flat_age`
- `town`

This is important. In real valuation work, we would almost always want `floor_area_sqm`, storey information, flat model, and ideally some location variables. Question A intentionally removes most of that information, so the exercise is really about how far we can get with a compact feature set and how we should communicate the resulting uncertainty.

## 2. Data Setup And Evaluation Design

The script does not use a random train-test split. Instead, it uses a **temporal holdout**, which is the right design for a forecasting-style pricing problem.

- training data: transactions before 2014
- holdout data: transactions in 2014
- selected main training window: `recent_3y`, which means 2011 to 2013
- holdout size: `15,870` transactions
- training size under the selected window: `61,534` transactions

Why this matters:

- housing prices drift over time
- a random split can leak future market conditions into the training sample
- a temporal split gives a more realistic estimate of how the model would have performed when predicting 2014 transactions using only earlier data

The script also predicts on the log of resale price and converts predictions back to SGD for reporting. That helps stabilize the learning problem while keeping the final outputs easy to interpret.

## 3. EDA: What The Three Visible Features Can And Cannot Explain

Before fitting models, it helps to ask a simple question: if we hold `town`, `flat_type`, and `flat_age` roughly constant, how much price variation still remains?

![Question A controlled variation](/outputs/section2/charts/S2QaF1_controlled_variation.svg)

The answer is: quite a lot.

For example, among some of the largest 2014 groups saved in the output:

- `YISHUN | 4 ROOM | age 25-29` has `494` transactions, with an interquartile range of about `SGD 54.7K`
- `SENGKANG | 5 ROOM | age 10-14` has `271` transactions, with an interquartile range of `SGD 50.0K`
- `TAMPINES | 4 ROOM | age 25-29` has `246` transactions, with an interquartile range of about `SGD 54.3K`

That residual spread is the first big insight of Question A:

> flats that look identical on the three visible case features still sell at meaningfully different prices.

The likely reasons are omitted variables such as floor area, floor level, flat model, exact block-level location, renovation quality, and local transaction timing.

The saved diagnostic summaries support that story.

Two patterns stand out:

- median floor area rises sharply across flat types, from `67 sqm` for `3 ROOM` to `94 sqm` for `4 ROOM` and `120 sqm` for `5 ROOM`
- `floor_area_sqm` has a strong positive correlation with resale price in the saved diagnostic sample at about `0.725`

So even before modeling, we already know the official feature set is useful but incomplete.

## 4. Model Candidates

The script fits three candidate models for the official task:

1. `LinearRegression`
2. `RandomForestRegressor`
3. `XGBRegressor`

![Question A model tradeoff](/outputs/section2/charts/S2QaF2_model_tradeoff.svg)

### 4.1 Holdout Results On The Official Three-Feature Task

| Model | MAE | RMSE | MAPE | R² | Total runtime |
| --- | ---: | ---: | ---: | ---: | ---: |
| XGBoost | SGD 37,408 | SGD 51,425 | 8.44% | 0.826 | 0.53s |
| Linear Regression | SGD 39,279 | SGD 55,463 | 8.51% | 0.797 | 0.11s |
| Random Forest | SGD 39,201 | SGD 53,894 | 8.87% | 0.809 | 3.70s |

All three models are viable baseline predictors, but XGBoost is the best overall performer:

- lowest RMSE
- lowest MAE
- lowest MAPE
- highest R²
- runtime that is still comfortably small

### 4.2 Why Linear Regression Is Not Quite Enough

Linear Regression is surprisingly competitive here. Its MAPE of `8.51%` is only slightly worse than XGBoost's `8.44%`, which suggests that a large share of the signal is broad and monotonic:

- larger flat types tend to be more expensive
- older flats tend to be cheaper
- town captures substantial location-level price differences

But the relationship is unlikely to be purely linear. The value of age can vary by town, and the price gaps between flat types are not constant everywhere. XGBoost is better able to learn those interactions and non-linear thresholds without hand-crafting them.

### 4.3 Why Random Forest Did Not Win

Random Forest improves on linear regression in RMSE, but it is still worse than XGBoost on every accuracy metric shown in the saved output, while also taking much longer to fit.

For this case, that makes it the awkward middle option:

- less interpretable than linear regression
- slower than XGBoost
- less accurate than XGBoost

## 5. Final Model Choice

The selected model is **XGBoost**.

The reasons are straightforward:

1. it delivers the best holdout accuracy on the official task
2. it captures non-linear interactions between `town`, `flat_type`, and `flat_age`
3. it remains fast enough that the extra complexity is easy to justify
4. the gain is not just in one metric; it is consistent across MAE, RMSE, MAPE, and R²

If this were a teaching or deployment setting where maximum interpretability mattered more than the last bit of accuracy, linear regression would still be a defensible benchmark. But for the case question as written, XGBoost is the strongest answer.

## 6. Why The 2011 To 2013 Training Window Was Chosen

The script also stress-tests the training window for the winning model.

![Question A training window sensitivity](/outputs/section2/charts/S2QaF4_training_window_sensitivity.svg)

The saved results are revealing:

| Training window | Train years | RMSE | MAPE | R² |
| --- | --- | ---: | ---: | ---: |
| Full history | 1990-2013 | SGD 145,331 | 22.31% | -0.392 |
| Recent 5 years | 2009-2013 | SGD 68,761 | 9.91% | 0.688 |
| Recent 3 years | 2011-2013 | SGD 51,425 | 8.44% | 0.826 |
| Recent 1 year | 2013 only | SGD 54,961 | 10.20% | 0.801 |

This is one of the strongest findings in the whole exercise.

Using **all available history** is much worse than using only recent data. That likely reflects market regime change:

- older transactions come from very different price levels and policy environments
- the relationship between age, town, flat type, and price shifts over time
- with only three features, the model has limited ability to correct for those structural changes

The `recent_3y` window is the sweet spot:

- recent enough to reflect the 2014 market
- large enough to retain a healthy training sample
- better than a very short one-year window, which loses too much data

## 7. Diagnostic Check: What Happens When Hidden Features Matter

The script goes further than the official case requirement and runs a diagnostic version of the model with extra features:

- `year`
- `floor_area_sqm`
- `min_floor_level`
- `max_floor_level`

This is not the official final model, but it is useful for understanding what the official model is missing.

With those richer observed features available, the diagnostic XGBoost model reaches:

- RMSE: `SGD 47,224`
- MAPE: `9.05%`
- R²: `0.853`

That confirms the hidden variables really do contain additional pricing information.

But once those hidden fields have to be **imputed** rather than observed, performance collapses. In the saved baseline imputation backtest, the diagnostic XGBoost model falls to:

- RMSE: `SGD 130,510`
- MAPE: `25.22%`
- R²: `-0.123`

That is a very useful reporting lesson:

> a richer model is not automatically a better practical model if the required inputs are unavailable at prediction time.

This is one reason the official three-feature model is the right final answer for Question A. It is aligned with the information the case actually allows us to use.

## 8. Interpreting The Actual-Vs-Predicted Output

![Question A actual versus predicted](/outputs/section2/charts/S2QaF3_actual_vs_predicted.svg)

One subtle pattern in the saved prediction output is that many transactions receive the same prediction when they share the same visible attributes. For example, multiple `ANG MO KIO`, `3 ROOM`, mid-30s-age flats in January 2014 are assigned very similar predicted prices.

That is not a bug. It is a direct consequence of the feature constraint:

- the model cannot distinguish flats that differ only in omitted variables
- so part of the remaining error is irreducible under the case rules

This is why the case should be framed as **predicting from coarse descriptors**, not as a fully specified property valuation model.

## 9. Final Answer

Three models were proposed and implemented:

1. Linear Regression
2. Random Forest
3. XGBoost

The best model is **XGBoost trained on 2011 to 2013 transactions and evaluated on 2014 holdout transactions**.

The choice is justified because it:

- achieved the best official holdout performance at `RMSE = SGD 51,425` and `MAPE = 8.44%`
- handled non-linear effects and interactions better than linear regression
- outperformed random forest while running faster
- matched the information constraints of the case, unlike richer diagnostic models that depend on hidden features

In business terms, the conclusion is:

> Using only `flat_type`, `flat_age`, and `town`, we can build a reasonably accurate 2014 resale price predictor, but a noticeable share of price variation remains unexplained because important property details are intentionally excluded. XGBoost is the best balance of predictive accuracy and practical usability under those constraints.

## 10. Caveats

- This is a predictive model, not a causal model.
- Accuracy is good for a three-feature setup, but it is not a substitute for a full valuation model.
- Full-history training performs badly, so temporal alignment matters a lot.
- The analysis strongly suggests omitted-variable risk, especially from floor area and storey level.
- If the use case were actual pricing or underwriting, the feature set should be expanded before deployment.
