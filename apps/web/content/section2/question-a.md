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

The business ask is practical and constrained: estimate 2014 HDB resale prices using only three visible attributes:

- town
- flat type
- flat age

This is intentionally restrictive. In real valuation work, we would also include floor area, storey level, and finer location details. Here, the goal is to understand what is possible under limited information, and how much uncertainty remains.

## Constraints And Requirements

The analysis is evaluated in a forward-looking setup:

- train on pre-2014 transactions
- test on 2014 transactions

This design mirrors real usage better than random splitting because resale market conditions shift over time.

## EDA: What The Three Inputs Can Explain

<iframe src="/outputs/section2/charts/S2QaF1_controlled_variation.html" title="Price dispersion under same visible features"></iframe>

Even when transactions share the same visible fields, price ranges remain wide. This means hidden attributes still drive substantial variation.

## Candidate Models

Three models were compared:

- linear regression
- random forest
- XGBoost

<iframe src="/outputs/section2/charts/S2QaF2_model_tradeoff.html" title="Model tradeoff comparison"></iframe>

## What The Results Say

Holdout performance on 2014 transactions:

- XGBoost: RMSE `SGD 51,425`, MAPE `8.44%`, R² `0.826`
- Linear regression: RMSE `SGD 55,463`, MAPE `8.51%`, R² `0.797`
- Random forest: RMSE `SGD 53,894`, MAPE `8.87%`, R² `0.809`

XGBoost is the best overall choice because it consistently outperforms alternatives across all key error metrics while staying computationally efficient.

## Why Training Window Choice Matters

<iframe src="/outputs/section2/charts/S2QaF4_training_window_sensitivity.html" title="Training window sensitivity"></iframe>

Using all historical years performs much worse than using recent years. The best balance is a recent 3-year window, which is both representative of 2014 market conditions and large enough for stable training.

## Interpretation

<iframe src="/outputs/section2/charts/S2QaF3_actual_vs_predicted.html" title="Actual vs predicted resale prices"></iframe>

The model is strong for a three-field setup, but it cannot separate properties that look identical on these visible fields. That residual uncertainty is expected, not a modeling bug.

## Recommended Decision

Use XGBoost with a recent-window training strategy for this constrained prediction task.

Business takeaway:

- pricing can be estimated reasonably well with minimal inputs
- a non-trivial error band remains because key property details are intentionally excluded
- this model is suitable for directional pricing support, not full valuation-grade underwriting
