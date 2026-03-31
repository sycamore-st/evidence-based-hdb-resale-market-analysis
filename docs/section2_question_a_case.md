# Section 2 Question A Case Note

## 1. Business Question

The business question for Section 2 Question A is:

> If we are only allowed to use the visible fields in the case prompt, how accurately can we predict the resale price of the target flat?

The implemented version of that question is narrower and more realistic:

> Using only `flat_type`, `flat_age`, and `town`, can we produce a reasonable price estimate for the target transaction, and how much uncertainty is introduced by the hidden variables we are not allowed to use directly?

That matters because the target flat is only partially observed at prediction time. The code intentionally separates:

- the **official model**, which only uses the allowed fields
- the **diagnostic model**, which checks how much better we could do if hidden fields such as floor area and storey were available
- the **imputation study**, which measures how much error comes back when those hidden fields are replaced with group proxies

The analysis code for this question lives in [section2_question_a.py](/src/analysis/section2/section2_question_a.py).

## 2. EDA

The EDA for Question A is designed to explain why the simplified prediction problem is hard before showing model results.

### 2.1 Controlled variation among comparable groups

Outputs:

- [S2QaF1_controlled_variation.svg](/outputs/section2/charts/S2QaF1_controlled_variation.svg)
- [S2Qa_controlled_variation_summary.csv](/outputs/section2/results/S2Qa_controlled_variation_summary.csv)

Preview:

![S2QaF1](/outputs/section2/charts/S2QaF1_controlled_variation.svg)

This chart groups transactions by the three official fields plus an age bucket and shows that resale prices still vary materially within those cells.

Interpretation:

- even after fixing town, flat type, and broad age bucket, price variation remains large
- that residual variation is exactly why a three-field model cannot be perfectly precise
- the missing information is not noise-free; it contains real pricing signal

### 2.2 Floor-area distribution by flat type

Outputs:

- [S2QaF6_floor_area_by_flat_type.svg](/outputs/section2/charts/S2QaF6_floor_area_by_flat_type.svg)
- [S2Qa_floor_area_by_flat_type_summary.csv](/outputs/section2/results/S2Qa_floor_area_by_flat_type_summary.csv)

Preview:

![S2QaF6](/outputs/section2/charts/S2QaF6_floor_area_by_flat_type.svg)

This chart shows why hidden size information matters. Even within a flat type, floor area still spans a meaningful range.

Interpretation:

- `4 ROOM` flats are not all the same size
- when size is hidden, the model has to average over a wide latent distribution
- that mechanically widens the uncertainty around the final price estimate

### 2.3 Correlation of imputed features

Outputs:

- [S2QaF5_imputation_feature_correlation.svg](/outputs/section2/charts/S2QaF5_imputation_feature_correlation.svg)
- [S2Qa_imputation_feature_correlation.csv](/outputs/section2/results/S2Qa_imputation_feature_correlation.csv)

Preview:

![S2QaF5](/outputs/section2/charts/S2QaF5_imputation_feature_correlation.svg)

This chart explains the imputation design. The hidden fields are not arbitrary; they have structured relationships with the visible fields and with price.

Interpretation:

- hidden features are partly predictable from the visible fields
- but they are not perfectly recoverable
- so imputation can narrow uncertainty, but not eliminate it

## 3. Solution

Question A is solved in three layers.

### 3.1 Official prediction model

The official model is trained using only:

- `flat_type`
- `flat_age`
- `town`

Candidate models:

- Linear Regression
- Random Forest
- XGBoost

Train-test split method:

- the workflow first runs a training-window sensitivity check using earlier years for training and `2014` as the common holdout year
- the main model comparison then uses the selected `recent_3y` window, so training is restricted to transactions up to `2013-12-31` within the most recent three-year window and evaluation is done on `2014`
- the same temporal split is used for the extended model benchmark, so both the official and extended comparisons are aligned on the same out-of-time holdout

The best official model in the saved run is `xgboost`.

Saved model comparison:

- [S2Qa_model_comparison.csv](/outputs/section2/results/S2Qa_model_comparison.csv)

Key official holdout results:

- XGBoost RMSE: about `51,425`
- XGBoost MAPE: about `8.44%`
- XGBoost MAE: about `37,408`
- XGBoost R²: about `0.826`

Supporting chart:

- [S2QaF2_model_tradeoff.svg](/outputs/section2/charts/S2QaF2_model_tradeoff.svg)
- [S2QaF3_actual_vs_predicted.svg](/outputs/section2/charts/S2QaF3_actual_vs_predicted.svg)

### 3.2 Diagnostic model with observed hidden fields

This is not the official answer. It is a diagnostic benchmark.

It adds hidden-but-useful fields such as:

- `floor_area_sqm`
- `min_floor_level`
- `max_floor_level`
- transaction year context

Saved comparison:

- [S2Qa_observed_model_comparison.csv](/outputs/section2/results/S2Qa_observed_model_comparison.csv)

Key diagnostic result:

- XGBoost RMSE improves from about `51.4k` to about `47.2k`
- that is about `8.2%` lower RMSE
- but MAPE worsens from about `8.44%` to about `9.05%`
- that is about `0.61` percentage points worse, or roughly `7.2%` worse in relative terms
- MAE also moves slightly worse, from about `37.4k` to about `38.2k`

Interpretation:

- the hidden fields are genuinely informative
- they improve absolute dollar fit
- but they do not improve percentage accuracy in this rerun, and the MAE result is also slightly weaker
- so the official three-field model remains the cleaner benchmark if MAPE is the primary decision metric

### 3.3 Imputation and uncertainty study

The code then hides those extra fields again and replaces them with group-based proxies such as:

- baseline: median size plus the most common floor band
- group `p25`
- group `p75`
- group most frequent value
- null stress test

This is the realistic proxy-enhanced benchmark:

- train the richer model on rows where the hidden fields are observed
- evaluate it on `2014` holdout rows where the hidden fields are replaced by imputed values

So this section is the right place to judge whether proxy recovery actually helps at prediction time.

Saved outputs:

- [S2Qa_imputed_model_comparison.csv](/outputs/section2/results/S2Qa_imputed_model_comparison.csv)
- [S2Qa_imputation_reference.csv](/outputs/section2/results/S2Qa_imputation_reference.csv)
- [S2Qa_imputation_range_backtest_summary.csv](/outputs/section2/results/S2Qa_imputation_range_backtest_summary.csv)
- [S2QaF10_imputation_tradeoff.svg](/outputs/section2/charts/S2QaF10_imputation_tradeoff.svg)

The imputation study still matters, but it should now be read mainly as an uncertainty exercise rather than a guaranteed accuracy improvement over the official model.

The baseline proxy is still group-based rather than global:

- `floor_area_sqm` uses the group median
- `min_floor_level` and `max_floor_level` use the most common floor band in the group
- the reference group is selected hierarchically from combinations of `town`, `flat_type`, and `flat_age_bucket`

The null-imputation cases perform much worse, which confirms that sensible proxy recovery matters.

In the currently saved imputation output, the best imputed combination is:

- Linear Regression with `most_frequent` imputation
- MAPE: about `14.66%`
- RMSE: about `101.5k`

That is still materially worse than the official three-field XGBoost benchmark, which means proxy-filled hidden features do not currently improve the practical prediction task.

The range backtest is especially important:

- coverage rate: about `50.46%`
- average width: about `167.5k`
- median width: about `163.5k`

Supporting chart:

- [S2QaF10_imputation_tradeoff.svg](/outputs/section2/charts/S2QaF10_imputation_tradeoff.svg)
- [S2QaF9_range_backtest.svg](/outputs/section2/charts/S2QaF9_range_backtest.svg)

The imputation tradeoff chart shows that imputed hidden features are noisy enough to overturn the ranking seen in the observed diagnostic benchmark: simple models can become more stable than XGBoost once proxy quality deteriorates.

The range study shows that a narrow p25-to-p75 interval should not be interpreted as a calibrated 95% confidence band. It is better read as a practical diagnostic band around the midpoint.

### 3.4 Training-window sensitivity

The workflow also checks whether the answer changes materially when training only on more recent data windows.

Outputs:

- [S2QaF4_training_window_sensitivity.svg](/outputs/section2/charts/S2QaF4_training_window_sensitivity.svg)
- [S2Qa_training_window_sensitivity.csv](/outputs/section2/results/S2Qa_training_window_sensitivity.csv)

This is a robustness check on temporal stability rather than a different business answer.

## 4. Interpretation

The most defensible interpretation of Question A is:

- a three-field model can still produce a reasonably strong first-pass estimate
- XGBoost remains the best official model in this rerun
- observed hidden features improve RMSE, so they help the model reduce large dollar misses
- but they worsen MAPE and slightly worsen MAE, so they do not improve the proportional accuracy of the estimate
- once those hidden fields are replaced by imputed proxies, the proxy-enhanced benchmark is clearly worse than the official model
- the safest business framing is still a point estimate plus an uncertainty range, not a claim of precise valuation

So the business conclusion is:

> Yes, the target flat’s price can be estimated reasonably well using only the allowed fields. True hidden structural features help RMSE, but proxy-filled versions of those features do not improve the practical holdout benchmark. The right communication is still a midpoint plus an uncertainty range, not a single overconfident number.
