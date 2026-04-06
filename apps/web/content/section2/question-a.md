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

This study addresses a specific, constrained objective: estimating 2014 HDB resale prices using only three visible attributes: **town**, **flat type**, and **flat age**.

While a comprehensive valuation would typically incorporate variables such as floor area, storey level, and precise geographic coordinates, this analysis intentionally restricts the feature set. The goal is to determine the predictive ceiling of these foundational variables and quantify the level of uncertainty that persists when more granular data is unavailable.

## Constraints and Requirements

To ensure the model's practical utility, the analysis utilizes a forward-looking temporal split:

- **Training Set:** Transactions occurring prior to 2014.
- **Testing Set:** Transactions occurring within 2014.
    

This methodology is superior to a random train-test split for real estate applications, as it accounts for shifts in market conditions and policy changes over time.

## EDA: Explanatory Power of the Input Features

<iframe src="/outputs/section2/charts/S2QaF1_controlled_variation.html" title="Price dispersion under same visible features"></iframe>

Exploratory Data Analysis (EDA) reveals significant price dispersion even among transactions sharing identical visible attributes. This variation suggests that "hidden" factors—such as interior condition or proximity to specific amenities—continue to exert substantial influence on market value.

## Candidate Models

The study evaluated three distinct modeling approaches to identify the most effective predictive architecture:

- Linear Regression
    
- Random Forest
    
- XGBoost
    

<iframe src="/outputs/section2/charts/S2QaF2_model_tradeoff.html" title="Model tradeoff comparison"></iframe>

## Model Comparison and Selection

Three models were implemented to satisfy the requirement for a comparative technical analysis:

1. **Linear Regression:** Serves as the statistical baseline. It assesses whether the relationship between the features and price is primarily linear and provides a high degree of interpretability.
    
    Documentation: [LinearRegression (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html)
    
2. **Random Forest Regressor:** A bagging-based ensemble method. It is utilized to capture non-parametric, nonlinear relationships and feature interactions without extensive hyperparameter tuning.
    
    Documentation: [RandomForestRegressor (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
    
3. **XGBoost Regressor:** A gradient-boosted decision tree framework. It is designed to iteratively minimize residual errors and typically yields high accuracy for tabular data.
    
    Documentation: [XGBRegressor (XGBoost Python API)](https://xgboost.readthedocs.io/en/stable/python/python_api.html?highlight=XGBRegressor)
    

### Performance on 2014 Holdout Set

|**Model**|**RMSE**|**MAPE**|**R²**|**Evaluation Summary**|
|---|---|---|---|---|
|**Linear Regression**|SGD 55,463|8.51%|0.797|Efficient baseline; fails to account for nonlinear complexities.|
|**Random Forest**|SGD 53,894|8.87%|0.809|Captures nonlinearity but exhibits higher MAPE and lower efficiency.|
|**XGBoost**|**SGD 51,425**|**8.44%**|**0.826**|**Optimal performance across all metrics with strong runtime efficiency.**|

**Selected Model:** XGBoost. It achieved the lowest error rates (RMSE and MAPE) and the highest explanatory power (R²) while effectively modeling the nonlinear interactions inherent in the data.

## Impact of Training Window Selection

<iframe src="/outputs/section2/charts/S2QaF4_training_window_sensitivity.html" title="Training window sensitivity"></iframe>

The analysis indicates that the selection of the training period is critical. Models trained on all available historical data performed significantly worse than those using a more focused temporal window. A **3-year recent window** was identified as the optimal balance, providing sufficient volume for stable training while remaining representative of 2014 market dynamics.

## Interpretation of Results

<iframe src="/outputs/section2/charts/S2QaF3_actual_vs_predicted.html" title="Actual vs predicted resale prices"></iframe>

The model demonstrates strong predictive performance given the data constraints. However, the residual error represents the "limit of information"; the model cannot distinguish between properties that appear identical based only on town, type, and age. This uncertainty is an expected outcome of the restricted feature set.

## Recommended Implementation

For constrained prediction tasks of this nature, the **XGBoost** model paired with a **recent-window training strategy** is recommended.

**Key Findings:**

- HDB resale prices can be estimated with reasonable accuracy using minimal inputs.
    
- A persistent error margin exists due to the exclusion of detailed property attributes.
    
- The model is appropriate for directional pricing analysis and high-level support, rather than precision valuation-grade underwriting.
