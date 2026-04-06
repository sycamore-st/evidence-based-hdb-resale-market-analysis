---
title: "Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?"
kicker: "Section 3 / Question C"
description: "A corridor-level treatment analysis comparing near-station and farther transactions before and after DTL2 opening."
section: "section3"
slug: "question-c"
order: 3
---

# Did Downtown Line Stage 2 Lift Nearby HDB Resale Prices?

## Business Context

The policy question is whether DTL2 improved resale values for homes closer to the new stations.

## Scope And Constraint

This is a corridor study, not a whole-island causal claim. Treated homes are near DTL2 stations; controls are farther homes in the same corridor towns.

## EDA: Treatment Visibility And Trend Shape

> Interactive chart pending export: Treated vs control trend.

> Interactive chart pending export: Price gradient by station distance.

> Interactive chart pending export: Treatment assignment map.

These views suggest stronger post-opening performance near stations, but descriptive trends alone are not sufficient for causal interpretation.

## Proposed Solution

Use a difference-in-differences framework, then validate assumptions with event-study diagnostics.

> Interactive chart pending export: Event-study coefficients.

## Results

Baseline DiD signal:

- near-station post-opening effect is positive
- estimated uplift is around low-to-mid single digits in percentage terms

But the event-study leads are also positive before opening, which weakens strict parallel-trends credibility.

## Interpretation

Operational conclusion:

- evidence is directionally consistent with a DTL2 proximity premium
- magnitude should be interpreted as suggestive rather than fully causal due to pre-trend imbalance

## Recommended Decision

Use this as strong corridor-level evidence for accessibility value, while labeling the effect as quasi-causal and prioritizing robustness checks in future updates.
