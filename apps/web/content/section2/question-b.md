# Section 2 Question B Case Note

## 1. Business Question

The business question for Section 2 Question B is:

> Is the target transaction reasonably priced, overpriced, or underpriced relative to what we would expect from similar HDB resale transactions?

The code turns that into a practical valuation exercise for the target flat in [S2_config.py](/src/analysis/section2/S2_config.py):

- town: `YISHUN`
- flat type: `4 ROOM`
- flat model: `NEW GENERATION`
- storey range: `10 TO 12`
- floor area: `91 sqm`
- lease commence year: `1984`
- transaction month: `2017-11`
- actual resale price: `SGD 550,800`

The analysis code for this question lives in [section2_question_b.py](/src/analysis/section2/section2_question_b.py).

## 2. EDA

The EDA for Question B is about valuation context, not causal inference.

### 2.1 Distribution contexts around the subject transaction

Outputs:

- [S2QbF1_distribution_contexts.svg](/outputs/section2/charts/S2QbF1_distribution_contexts.svg)
- [S2Qb_distribution_contexts.csv](/outputs/section2/results/S2Qb_distribution_contexts.csv)

Preview:

![S2QbF1](/outputs/section2/charts/S2QbF1_distribution_contexts.svg)

This chart shows the local transaction environment for similar flats before the subject month and in adjacent periods.

Interpretation:

- it gives a quick sense of whether the subject price is sitting near the middle of the local market or at the edge
- it is descriptive only; it does not control for all property attributes

### 2.2 Local empirical distribution

Outputs:

- [S2QbF3_local_distribution.svg](/outputs/section2/charts/S2QbF3_local_distribution.svg)
- [S2Qb_local_distribution_frame.csv](/outputs/section2/results/S2Qb_local_distribution_frame.csv)

Preview:

![S2QbF3](/outputs/section2/charts/S2QbF3_local_distribution.svg)

This chart focuses on the local empirical price distribution around the subject property.

From the saved result:

- local 2.5th percentile: `SGD 291,000`
- local 97.5th percentile: `SGD 425,000`
- local cohort size: `209`

Interpretation:

- the realized transaction at `SGD 550,800` is well above the local empirical 95% range
- that is already a strong descriptive signal that the transaction is unusually expensive

## 3. Solution

Question B combines three valuation lenses:

1. a machine-learning expected-price model
2. comparable-sales context
3. local empirical outlier checks

### 3.1 Main expected-price model

The main model uses richer property features than Question A, including:

- flat type
- town
- flat model
- floor area
- age and remaining lease
- storey bounds
- optional location amenities when available

Candidate models in the saved run:

- Linear Regression
- XGBoost

Train-test split method:

- the main evaluation in [section2_question_b.py](/Users/claire/PycharmProjects/evidence-based-hdb-resale-market-analysis/src/analysis/section2/section2_question_b.py) uses a temporal holdout created by `make_temporal_split(...)`
- that means the model is trained on earlier transactions and validated on later holdout months, which is more appropriate for a pricing task with time drift
- the file also contains an optional notebook-style random `75/25` split benchmark, but that is secondary and only runs when `run_random_split_validation=True`

Saved comparison:

- [S2Qb_model_comparison.csv](/outputs/section2/results/S2Qb_model_comparison.csv)

Key holdout results:

- XGBoost RMSE: about `31,718`
- XGBoost MAPE: about `4.01%`
- XGBoost R²: about `0.979`

This is a strong forecasting model by the standards of the case.

Supporting charts:

- [S2QbF4_model_accuracy.svg](/outputs/section2/charts/S2QbF4_model_accuracy.svg)
- [S2Qb_actual_vs_predicted.svg](/outputs/section2/charts/S2Qb_actual_vs_predicted.svg)

### 3.2 Expected price for the subject flat

Saved subject summary:

- [S2Qb_assessment_summary.csv](/outputs/section2/results/S2Qb_assessment_summary.csv)
- [S2Qb_subject_summary.csv](/outputs/section2/results/S2Qb_subject_summary.csv)

Main result:

- actual price: `SGD 550,800`
- model expected price: about `SGD 345,182`
- model-based 95% interval: about `SGD 283,016` to `SGD 407,347`

So the subject transaction is far above the model expectation.

### 3.3 Comparable-sales and local-range checks

The code also attempts a comparable-sales overlay and a local empirical check.

In this saved run:

- exact comparable support is weak: `0` high-quality comparables were retained in the final comparable frame
- local empirical evidence is still available and strong
- the local modified z-score is about `5.69`
- the local outlier flag is `True`

That combination matters:

- the comparables lens is limited here
- but the transaction still looks extreme relative to the modeled expectation and local historical distribution

### 3.4 Final assessment logic

Question B does not stop at raw deviation. It converts the evidence stack into a business-facing verdict using:

- model error benchmarks
- interval checks
- percentile position in local transactions
- outlier diagnostics
- strength or weakness of secondary comparable support

The saved verdict in [S2Qb_subject_summary.csv](/outputs/section2/results/S2Qb_subject_summary.csv) is:

> The transaction is above the expected price, with limited secondary comparable support.

Confidence is labeled `Moderate`.

## 4. Interpretation

The most defensible interpretation of Question B is:

- the target transaction looks expensive relative to the learned market expectation
- it also sits above the local empirical 95% range
- the model fit is strong enough that this gap is hard to dismiss as ordinary prediction noise
- but comparable-sales support is weak, so the conclusion should be framed as a strong warning signal rather than an indisputable mispricing proof

So the business answer is:

> The target flat appears materially overpriced relative to the model-based expected price and the local transaction distribution. The evidence is strong enough to flag the deal as unusual, but confidence should remain moderate because direct comparable support is thin.
