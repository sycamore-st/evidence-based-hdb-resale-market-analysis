---
title: "Can We Recover Missing Flat Type Without Losing Pricing Accuracy?"
kicker: "Section 2 / Question C"
description: "A supervised-vs-unsupervised comparison for recovering hidden flat type and protecting downstream valuation quality."
section: "section2"
slug: "question-c"
order: 3
---

# Can We Recover Missing Flat Type Without Losing Pricing Accuracy?

## Business Context

If flat type is missing, downstream valuation quality can degrade. The business question is whether we can recover that missing field well enough to keep pricing decisions reliable.

Two recovery paths are compared:

- supervised classification
- unsupervised segmentation mapped back to flat-type labels

## Constraints And Requirement

The requirement is dual:

- recover flat type accurately
- preserve downstream price-model performance

A method that classifies poorly but still preserves pricing can still be operationally useful.

## EDA: Market Structure Behind Flat Type

<iframe src="/outputs/section2/charts/S2QcF5_flat_type_count.html" title="Flat type count distribution"></iframe>

<iframe src="/outputs/section2/charts/S2QcF6_flat_type_floor_area_distribution.html" title="Floor area by flat type"></iframe>

<iframe src="/outputs/section2/charts/S2QcF7_flat_type_resale_price_distribution.html" title="Resale price by flat type"></iframe>

Flat types are strongly separated by area and partly by price, which creates a solid basis for recovery.

## Solution Path 1: Unsupervised Segmentation

<iframe src="/outputs/section2/charts/S2QcF1_unsupervised_confusion.html" title="Unsupervised mapped confusion"></iframe>

<iframe src="/outputs/section2/charts/S2QcF2_unsupervised_k_comparison.html" title="Unsupervised k comparison"></iframe>

<iframe src="/outputs/section2/charts/S2QcF3_unsupervised_segment_profile.html" title="Unsupervised segment profile"></iframe>

With fixed `k=7`, mapped holdout accuracy is about `0.642`. Label recovery is moderate, but segmentation still captures economically meaningful groups.

## Solution Path 2: Supervised Recovery

<iframe src="/outputs/section2/charts/S2QcF8_supervised_model_summary.html" title="Supervised model summary"></iframe>

<iframe src="/outputs/section2/charts/S2QcF9_supervised_confusion.html" title="Supervised confusion matrix"></iframe>

Supervised recovery performs strongly:

- accuracy about `0.984`
- weighted F1 about `0.985`

## Downstream Pricing Impact

- RMSE with known flat type: about `30,065`
- RMSE with supervised recovered type: about `30,396` (small degradation)
- RMSE with unsupervised segment proxy: about `29,246` (segment signal still useful)

## Interpretation

For strict label recovery, supervised is clearly superior. For valuation continuity, both methods can contribute, but supervised recovery is easier to defend and communicate in business settings.

## Recommended Decision

Deploy supervised flat-type recovery as the default production path when flat type is missing, with unsupervised segments kept as secondary analytical features.
