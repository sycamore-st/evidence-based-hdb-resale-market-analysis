---
title: "Can We Recover Missing Flat Type Without Losing Pricing Accuracy?"
kicker: "Section 2 / Question C"
description: "A supervised-vs-unsupervised comparison for recovering hidden flat type at scale."
section: "section2"
slug: "question-c"
order: 3
---

# Can We Recover Missing Flat Type Without Losing Pricing Accuracy?

## Business Context

Someone mistakenly deleted the column containing data on Flat Type in the database.
While backups exist, these data are critical to HDB’s daily operations, and time would be needed to
restore these data from the backup. Senior management would like you to create a model to predict
flat type given a transaction’s other characteristics. Explain the reasons for choosing this model.


If flat type is missing, downstream analysis quality can degrade. The business question is whether we can recover that missing field well enough to keep pricing decisions reliable.

Two recovery paths are compared:

- supervised classification
- unsupervised segmentation mapped back to flat-type labels (including an RBM-based variant)

## Constraints And Requirement

The current requirement is:

- recover flat type accurately
- keep runtime practical on the full dataset (~972k rows)

This update prioritizes clustering recovery quality and scalability.

## EDA: Market Structure Behind Flat Type

<iframe src="/outputs/section2/charts/S2QcF5_flat_type_count.html" title="Flat type count distribution"></iframe>

<iframe src="/outputs/section2/charts/S2QcF6_flat_type_floor_area_distribution.html" title="Floor area by flat type"></iframe>

<iframe src="/outputs/section2/charts/S2QcF7_flat_type_resale_price_distribution.html" title="Resale price by flat type"></iframe>

Flat types are strongly separated by area and partly by price, which creates a solid basis for recovery.

## Solution Path 1: Unsupervised Segmentation

<iframe src="/outputs/section2/charts/S2QcF1_unsupervised_confusion.html" title="Unsupervised mapped confusion"></iframe>

<iframe src="/outputs/section2/charts/S2QcF2_unsupervised_k_comparison.html" title="Unsupervised k comparison"></iframe>

<iframe src="/outputs/section2/charts/S2QcF3_unsupervised_segment_profile.html" title="Unsupervised segment profile"></iframe>

With fixed `k=7`, methods compared on the full sample include:

- `kmeans`: mapped accuracy `0.8431`, Davies-Bouldin `0.7977`
- `gaussian_mixture`: mapped accuracy `0.8121`, Davies-Bouldin `1.4633`
- `rbm_kmeans` (RBM latent features + KMeans): mapped accuracy `0.5079`, Davies-Bouldin `0.5478`

Selection remains `kmeans` because mapped label recovery is materially higher.

Implementation notes for this run:

- Davies-Bouldin is computed on the full scoring dataset
- `MiniBatchKMeans` runs directly on sparse transformed features
- unsupervised pricing retraining was removed from this path

## Solution Path 2: Supervised Recovery

<iframe src="/outputs/section2/charts/S2QcF8_supervised_model_summary.html" title="Supervised model summary"></iframe>

<iframe src="/outputs/section2/charts/S2QcF9_supervised_confusion.html" title="Supervised confusion matrix"></iframe>

Supervised recovery performs strongly:

- holdout accuracy `1.000` (`15,618` rows)
- weighted F1 `1.000`

## Interpretation

For strict flat-type recovery, supervised remains clearly superior.
Within unsupervised options, RBM improved Davies-Bouldin but hurt mapped label accuracy.
For this business objective, mapped recovery accuracy is the deciding criterion, so `kmeans` is still the better unsupervised fallback.

## Recommended Decision

Deploy supervised flat-type recovery as the default production path when flat type is missing.
Keep unsupervised `kmeans` segments as a secondary analytical feature; do not replace with `rbm_kmeans` for label recovery at this stage.
