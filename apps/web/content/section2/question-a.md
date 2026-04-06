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

The task works within a constraint: estimate 2014 HDB resale prices using only three visible attributes: town, flat type, and flat age.

A real valuation would also use floor area, storey level, and finer location data. This analysis is scoped to the three fields above. The aim is to see how well they perform on their own, and to measure how much uncertainty remains without the additional detail.

## Constraints and Requirements

The model is trained and tested in a forward-looking setup:

- Training set: transactions before 2014
- Test set: transactions within 2014

This is more appropriate than a random split for real estate, because market conditions change over time. Testing on a later period reflects how the model would actually be used.

## EDA: Explanatory Power of the Input Features

<iframe src="/outputs/section2/charts/S2QaF1_controlled_variation.html" title="Price dispersion under same visible features"></iframe>

Even among transactions with the same town, flat type, and flat age, prices vary widely. This indicates that unobserved factors — such as interior condition or proximity to specific amenities — still account for a meaningful share of the price difference.

## Candidate Models

Three models were compared:

- Linear Regression
    
- Random Forest
    
- XGBoost
    

<iframe src="/outputs/section2/charts/S2QaF2_model_tradeoff.html" title="Model tradeoff comparison"></iframe>

## Model Comparison and Selection

1. **Linear Regression:** The simplest baseline. Assumes a straight-line relationship between the inputs and price. Easy to interpret, and useful for checking whether a linear model is sufficient.

    Documentation: [LinearRegression (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html)

2. **Random Forest Regressor:** A tree ensemble where each tree is trained on a random subset of the data. Handles nonlinear patterns and interactions between features without much hyperparameter tuning.

    Documentation: [RandomForestRegressor (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)

3. **XGBoost Regressor:** A gradient boosting model that builds trees one at a time, each correcting the errors of the previous. Generally performs well on structured tabular data.

    Documentation: [XGBRegressor (XGBoost Python API)](https://xgboost.readthedocs.io/en/stable/python/python_api.html?highlight=XGBRegressor)
    

### Performance on 2014 Holdout Set

|**Model**|**RMSE**|**MAPE**|**R²**|**Evaluation Summary**|
|---|---|---|---|---|
|**Linear Regression**|SGD 55,463|8.51%|0.797|Interpretable baseline; does not capture nonlinear patterns.|
|**Random Forest**|SGD 53,894|8.87%|0.809|Handles nonlinearity, but has the highest MAPE of the three.|
|**XGBoost**|SGD 51,425|8.44%|0.826|Lowest RMSE, lowest MAPE, and highest R² across all three models.|

Selected model: XGBoost. It produces the lowest RMSE and MAPE, and the highest R², on the 2014 holdout set.

## Impact of Training Window Selection

<iframe src="/outputs/section2/charts/S2QaF4_training_window_sensitivity.html" title="Training window sensitivity"></iframe>

The training period matters. Models trained on all available historical data performed worse than those using a shorter, more recent window. A 3-year recent window works best here — it is close enough to 2014 to reflect current market conditions, and large enough to train on without instability.

## Interpretation of Results

<iframe src="/outputs/section2/charts/S2QaF3_actual_vs_predicted.html" title="Actual vs predicted resale prices"></iframe>

The model produces reasonable estimates given only three inputs. The remaining error comes from what these fields cannot capture — the model has no way to tell apart two properties that look the same on town, type, and age. This is expected when the feature set is this limited.

## Recommended Implementation

Use XGBoost with a recent 3-year training window for this constrained task.

Key takeaways:

- Reasonable price estimates are possible with just three fields.
- A persistent error margin remains because key property details are excluded.
- This model is suited for directional pricing support, not full valuation-grade precision.
