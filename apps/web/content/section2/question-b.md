---
title: "Is This Yishun Transaction Materially Overpriced?"
kicker: "Section 2 / Question B"
description: "A valuation decision note combining expected-price modeling, local distribution context, and outlier signals."
section: "section2"
slug: "question-b"
order: 2
---

# Is This Yishun Transaction Materially Overpriced?

## Business Context

This question moves from broad prediction to **transaction-level valuation**. Rather than forecasting a large batch of prices, the goal is to assess whether one specific resale deal looks fairly priced relative to its local market context and structural attributes.

The subject transaction is:

- **Town:** Yishun
- **Flat type:** 4 Room
- **Flat model:** New Generation
- **Floor area:** 91 sqm
- **Storey range:** 10 to 12
- **Transaction month:** 2017-11
- **Actual price:** SGD 550,800

The business question is not whether the transaction is statistically unusual in the abstract. It is whether the deal is **materially above what we would expect** for a flat with similar observable attributes.

## Scope and Evidence Framework

This is a valuation decision problem, not a causal inference problem. The conclusion combines three evidence lenses:

1. **Model-based expectation:** what a supervised pricing model predicts from structural features.
2. **Local distribution context:** where the observed transaction sits inside the nearby empirical price distribution.
3. **Comparable-sales screen:** whether direct comparables support or contradict the observed price.

The pricing model uses a richer feature set than Question A. The base predictors are:

$$
X_i = \{
\text{flat\_type}_i,\,
\text{town}_i,\,
\text{flat\_model}_i,\,
\text{floor\_area\_sqm}_i,\,
\text{year}_i,\,
\text{age}_i,\,
\text{remaining\_lease\_years}_i,\,
\text{min\_floor\_level}_i,\,
\text{max\_floor\_level}_i
\}
$$

Where:

- `flat_type`, `town`, and `flat_model` capture broad categorical structure.
- `floor_area_sqm` captures unit size directly.
- `year` and `age` capture market timing and depreciation.
- `remaining_lease_years` captures lease tenure remaining.
- `min_floor_level` and `max_floor_level` proxy the storey band.

When available, the model also absorbs optional accessibility variables such as:

- distance to CBD,
- distance to nearest MRT,
- distance to nearest bus stop,
- distance to nearest school,
- bus-stop count within 1 km,
- school count within 1 km.

## Step 1: Locate the Subject Transaction in Its Local Market

Before fitting any model, we first ask a simpler empirical question: among similar Yishun 4-room transactions, where does this deal sit in the local price distribution?

<iframe src="/outputs/section2/charts/S2QbF1_distribution_contexts.html" title="Distribution context around subject transaction" data-caption="Fig 1 — Local price distribution for comparable Yishun 4-room transactions. X-axis: resale price (SGD); y-axis: frequency. The subject transaction (SGD 550,800) is plotted against the empirical local range to show whether it already looks extreme before modeling."></iframe>

This chart is necessary because it grounds the valuation decision in the observed market, not just in model output. A transaction that already sits far outside the local distribution should trigger further scrutiny even before formal prediction is introduced.

In the local cohort around the subject flat, the empirical 95% band is approximately **SGD 291,000 to SGD 425,000** (`n = 209`), while the realized transaction price is **SGD 550,800**. That immediately suggests the deal sits far above what similar transactions typically cleared at.

## Step 2: Build an Expected-Price Model

The next step is to estimate what the subject flat should have sold for, based on its structural features. Model evaluation is done using a **temporal holdout split**, which is more realistic than a random split for a drifting housing market.

The valuation model can be written at a high level as:

$$
\log(\text{Price}_i) = f(X_i) + \varepsilon_i
$$

Where:

- $\text{Price}_i$ is the resale price of transaction $i$.
- $X_i$ is the feature vector described above.
- $f(\cdot)$ is the predictive model.
- $\varepsilon_i$ is the residual error.

Three candidate learners were compared in the analysis pipeline:

- **Linear Regression**
- **XGBoost**
- **CatBoost** (when available in the environment)

<iframe src="/outputs/section2/charts/S2QbF4_model_accuracy.html" title="Question B model accuracy comparison" data-caption="Fig 2 — Holdout accuracy comparison for the valuation task. X-axis: model type; y-axis: holdout metrics such as RMSE, MAPE, and R-squared. The selected model is the one that produces the most accurate out-of-sample valuation signal."></iframe>

This chart is included because the credibility of the pricing conclusion depends on whether the predictive model is strong enough to anchor a transaction-level decision. If the holdout error were too large, the model-based flag would not carry much weight.

## Step 3: Convert Model Output Into a Decision Signal

The selected model is **XGBoost**, which provides the strongest out-of-sample performance for this task.

**Holdout model performance**

- **RMSE:** approximately SGD 31,871
- **MAPE:** approximately 3.87%
- **R²:** approximately 0.979

**Subject transaction valuation outputs**

- **Expected price:** approximately SGD 339,332
- **Model-based 95% interval:** approximately SGD 277,037 to SGD 401,627
- **Actual transaction:** SGD 550,800

That places the realized transaction about **SGD 211,468 above the model expectation**, or roughly **+62.3%** above expected value.

The purpose of this step is to answer a different question from Step 1. The local distribution tells us the transaction is unusual relative to nearby realized deals. The model estimate tells us that even after controlling for the subject flat's observable structure, the price still looks materially too high.

## Step 4: Compare the Evidence Across Lenses

The transaction is now assessed across the full valuation framework:

- **Local market lens:** the deal lies above the empirical local 97.5th percentile.
- **Model lens:** the realized price is far outside the model's prediction interval.
- **Comparables lens:** in this run, no direct comparable transactions survived the final filtering criteria.

That third point matters. A clean set of retained comparables would have provided a strong market-based cross-check. Because the retained comparable count is **zero**, the final classification should be expressed with some caution even though the other two signals are strong.

## Interpretation

The evidence points in the same direction: the subject Yishun transaction appears **materially overpriced** relative to both:

- the local empirical distribution, and
- the expected price implied by its observable features.

The lack of retained comparables does not overturn that conclusion, but it does affect confidence. It means the decision relies more heavily on the model and distribution diagnostics than on a tight direct-comps argument.

## Recommended Decision

Classify the transaction as **likely overpriced** and treat it as a high-priority exception for manual review or negotiation challenge.

The confidence level should be described as **Moderate**, not High, because the comparable-sales support is weak in this specific run.
