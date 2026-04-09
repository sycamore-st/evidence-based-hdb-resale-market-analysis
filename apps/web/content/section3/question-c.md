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

<iframe src="/outputs/section3/charts/S3QcF1_dtl2_treated_vs_control.html" title="DTL2 treated versus control trend"></iframe>

<iframe src="/outputs/section3/charts/S3QcF3_dtl2_mrt_proximity_bands.html" title="Price gradient by station distance"></iframe>

<iframe src="/outputs/section3/charts/S3QcF4_dtl2_treatment_map.html" title="DTL2 treatment assignment map"></iframe>

These views suggest stronger post-opening performance near stations, but descriptive trends alone are not sufficient for causal interpretation.

## Proposed Solution

Use a difference-in-differences framework, then validate assumptions with event-study diagnostics.

<iframe src="/outputs/section3/charts/S3QcF2_dtl2_event_study_coefficients.html" title="DTL2 event-study coefficients"></iframe>

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
