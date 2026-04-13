---
title: "Can We Predict 2014 Resale Prices Using Only Three Visible Fields?"
kicker: "Section 2 / Question A"
description: "A constrained pricing study using only town, flat type, and flat age to estimate 2014 HDB resale prices."
section: "section2"
slug: "question-a"
order: 1
---

# Can We Predict 2014 Resale Prices Using Only Three Visible Fields?

## Business Context

This question studies an intentionally constrained pricing problem: estimate HDB resale prices using only the three fields that are immediately visible in a coarse listing or summary table:

- `town`
- `flat_type`
- `flat_age`

In a production valuation system, we would also want floor area, storey level, flat model, remaining lease, and finer location information. The point of this exercise is therefore not to build the strongest possible model. It is to measure how much pricing signal remains when nearly all structural detail is removed.

## Scope and Constraints

The evaluation uses a forward-looking test design rather than a random split:

- **Training set:** transactions before 2014
- **Test set:** transactions within 2014

This design matters because housing markets drift over time. A random split would mix earlier and later market conditions together and overstate performance. A temporal holdout is closer to the actual operating question: if we only knew the past, how well could we price the next year?

The official feature set is exactly:

$$
X_i = \{\text{town}_i,\; \text{flat\_type}_i,\; \text{flat\_age}_i\}
$$

Where:

- $\text{town}_i$ identifies the planning area of transaction $i$.
- $\text{flat\_type}_i$ captures broad unit size category such as 3-room or 4-room.
- $\text{flat\_age}_i$ measures the age of the flat at transaction time.

## Step 1: Establish the Information Ceiling

Before fitting any model, we first need to understand how much variation these three visible fields leave unexplained. The chart below groups transactions with the same visible attributes and shows the price spread that still remains inside each group.

<iframe src="/outputs/section2/charts/S2QaF1_controlled_variation.html" title="Price dispersion under same visible features" data-caption="Fig 1 — Price range within groups that share the same town, flat type, and flat age. X-axis: grouped feature combinations; y-axis: resale price (SGD). Wide spread inside a group shows the irreducible uncertainty left by the three-field constraint."></iframe>

This figure is important because it defines the difficulty of the task. If prices remain tightly clustered within each group, then a simple model would be enough. Instead, the within-group spread is still wide, which tells us that omitted features such as floor area, storey, exact building, and amenity access continue to matter materially.

In other words, the chart tells us that even a very strong model will face a genuine information ceiling under this feature restriction.

## Step 2: Compare Candidate Models

Given that the remaining signal is limited, the next question is whether nonlinear machine-learning models can still extract more information than a simple linear baseline. Three regressors were compared:

- **Linear Regression:** a transparent baseline that assumes additive linear effects.
- **Random Forest:** a tree ensemble that captures nonlinear interactions without heavy tuning.
- **XGBoost:** a boosted-tree model that typically performs well on structured tabular data.

<iframe src="/outputs/section2/charts/S2QaF2_model_tradeoff.html" title="Model tradeoff comparison" data-caption="Fig 2 — Performance comparison of Linear Regression, Random Forest, and XGBoost on the 2014 holdout set. X-axis: model type; y-axis: error metrics and R-squared. Lower RMSE/MAPE and higher R-squared indicate better predictive accuracy."></iframe>

We include this chart because model choice is itself part of the answer. The objective is not simply to show that prediction is possible, but to identify which model class works best when only three visible fields are available.

The holdout comparison shows:

| **Model** | **RMSE** | **MAPE** | **R²** | **Interpretation** |
|---|---:|---:|---:|---|
| Linear Regression | SGD 55,463 | 8.51% | 0.797 | Strong baseline, but too rigid to capture nonlinear market structure. |
| Random Forest | SGD 53,894 | 8.87% | 0.809 | Improves fit, but produces the highest percentage error. |
| XGBoost | SGD 51,425 | 8.44% | 0.826 | Best overall balance of error reduction and explanatory power. |

XGBoost is selected because it achieves the lowest RMSE, the lowest MAPE, and the highest R² on the forward holdout set.

## Step 3: Show What the Selected Model Gets Right and Wrong

Once the best model is chosen, the next chart examines prediction quality at the transaction level.

<iframe src="/outputs/section2/charts/S2QaF3_actual_vs_predicted.html" title="Actual vs predicted resale prices" data-caption="Fig 3 — Actual versus predicted resale prices for the 2014 holdout set. X-axis: predicted price (SGD); y-axis: actual price (SGD). Points close to the diagonal are well predicted; wider scatter shows residual error created by missing structural details."></iframe>

This figure is necessary because summary metrics alone do not show *how* the model fails. The scatter makes two things visible:

- most transactions still lie near the 45-degree line, so the model captures broad pricing structure reasonably well;
- the remaining misses are not random noise alone, but the predictable consequence of omitting critical building-level information.

Two units can share the same town, type, and age and still differ meaningfully in floor area, storey, renovation quality, or micro-location. The model has no way to distinguish them, so some residual error is unavoidable.

## Step 4: Test Whether More History Helps

The final design choice is the training window. Should the model use all historical data, or only a more recent period?

<iframe src="/outputs/section2/charts/S2QaF4_training_window_sensitivity.html" title="Training window sensitivity" data-caption="Fig 4 — Holdout performance as the training window changes. X-axis: historical window length; y-axis: validation metrics. The 3-year recent window performs best, implying that recency matters more than sheer volume of historical data."></iframe>

This chart matters because a housing model is not trained in a stationary environment. Older data increases sample size, but it also introduces stale market structure. The evidence here shows that the best result comes from a **recent 3-year window**, which balances recency against sample sufficiency.

That result is intuitive: a 3-year window is close enough to 2014 to reflect contemporary pricing relationships, but long enough to train a stable model.

## Interpretation

The main conclusion is that **directionally useful price prediction is possible even under a severe feature constraint**, but the constraint imposes a hard ceiling on precision. The selected XGBoost model performs meaningfully better than the simpler alternatives, yet it still inherits the uncertainty created by the missing structural fields.

This means the model is appropriate for:

- rough screening,
- first-pass pricing support,
- and broad budget guidance.

It is not appropriate for:

- valuation-grade underwriting,
- negotiation based on fine price differences,
- or any task where omitted structural detail is likely to dominate.

## Recommended Strategy

1. **Operational Use:** Deploy XGBoost as the preferred constrained model when only `town`, `flat_type`, and `flat_age` are available.
2. **Window Design:** Train on a recent 3-year history rather than the full archive, because recency improves forecast realism.
3. **Communication:** Present the output as a directional estimate with known information loss, not as a final valuation.

## Latest Rerun Notes

The latest rerun keeps the official constrained result unchanged:

- **Best model:** XGBoost
- **RMSE:** SGD 51,425
- **MAE:** SGD 37,408
- **MAPE:** 8.44%
- **R²:** 0.826

The supplementary diagnostic rerun also confirms that once richer structural information is introduced, performance improves dramatically. That gap reinforces the central lesson of this question: most of the remaining error is not model failure, but missing-information failure.
