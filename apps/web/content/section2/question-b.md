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

The task is to assess whether one specific HDB resale transaction is reasonably priced, underpriced, or overpriced relative to what we would expect from similar transactions.

Subject transaction profile:

- town: Yishun
- flat type: 4 Room
- flat model: New Generation
- floor area: 91 sqm
- storey range: 10 to 12
- transaction month: 2017-11
- actual price: `SGD 550,800`

## Constraints And Requirement

This is a valuation decision problem, not a causal inference exercise. The decision uses three evidence lenses:

- model-based expected price
- comparable-sales context
- local empirical outlier checks

## EDA: Local Market Positioning

<iframe src="/outputs/section2/charts/S2QbF1_distribution_contexts.html" title="Distribution context around subject transaction"></iframe>

In the local cohort around the subject flat (same town and type, with area/age filters), the empirical 95% band is about `SGD 291,000` to `SGD 425,000` (`n=209`), while the realized transaction is `SGD 550,800`.

## Solution

The expected-price model uses richer structural features than Question A, including flat type, town, flat model, floor area, age and remaining lease, storey bounds, and optional location amenities when available.

Evaluation is done with a temporal holdout split (earlier months for training, later months for testing), which is more realistic than a random split for drifting housing markets.

<iframe src="/outputs/section2/charts/S2QbF4_model_accuracy.html" title="Question B model accuracy comparison"></iframe>

## Results

Key outputs:

- selected model: `XGBoost`
- holdout RMSE: about `SGD 31,871`
- holdout MAPE: about `3.87%`
- holdout R^2: about `0.979`
- model expected price for subject: about `SGD 339,332`
- model-based 95% interval: about `SGD 277,037` to `SGD 401,627`
- actual transaction: `SGD 550,800`

Deviation from expected price is about `SGD 211,468` (`+62.3%`). The subject transaction sits outside the model interval and above the local empirical 97.5th percentile.

## Interpretation

All major evidence points in the same direction:

- model expectation flags the transaction as materially above expected value
- local-distribution diagnostics flag it as an outlier (`modified z-score ~ 5.69`)
- direct comparable-sales support is limited in this run (`0` retained comparables), so confidence should be framed as moderate

## Recommended Decision

Classify this transaction as likely overpriced and treat it as a high-priority exception for manual review or negotiation challenge, with confidence labeled `Moderate` due to weak comparable coverage.
