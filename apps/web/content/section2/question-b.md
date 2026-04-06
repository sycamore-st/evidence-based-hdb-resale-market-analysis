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

We need to evaluate whether a specific resale transaction should be treated as fairly priced or overpriced relative to comparable market behavior.

Subject transaction profile:

- town: Yishun
- flat type: 4 Room
- flat model: New Generation
- floor area: 91 sqm
- storey range: 10 to 12
- transaction month: 2017-11
- actual price: `SGD 550,800`

## Constraints And Decision Framing

The goal is not to prove causality. The goal is valuation judgment under uncertainty, combining:

- model-based expected price
- local market distribution context
- outlier diagnostics

## EDA: Local Market Positioning

> Interactive chart pending export: Distribution context around subject transaction.

> Interactive chart pending export: Local empirical resale distribution.

The transaction sits well above the local empirical high-percentile band, signaling unusual pricing before any model is applied.

## Proposed Solution

A supervised expected-price model was trained using richer structural features (type, model, area, age/lease, storey, and location context where available), then evaluated with a temporal holdout.

> Interactive chart pending export: Model accuracy benchmark.

## Results

Key outputs:

- model expected price: about `SGD 345,182`
- model 95% interval: about `SGD 283,016` to `SGD 407,347`
- actual transaction: `SGD 550,800`

The gap is large and materially above both model expectation and local historical range.

## Interpretation

The evidence stack points in one direction:

- the subject deal is substantially above expected market value
- local-distribution evidence reinforces the same conclusion
- direct comparable support is thinner than ideal, so confidence is best labeled moderate rather than absolute

## Recommended Decision

Classify this transaction as likely overpriced, and treat it as a high-priority exception for manual review or negotiation challenge.
