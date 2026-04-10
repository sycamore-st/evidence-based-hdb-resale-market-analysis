---
title: "Can We Recover Missing Flat Type Without Losing Pricing Accuracy?"
kicker: "Section 2 / Question C"
description: "A comparative evaluation of supervised classification and unsupervised clustering for the reconstruction of missing HDB flat type data."
section: "section2"
slug: "flat-type-recovery"
order: 3
---

# Can We Recover Missing Flat Type Without Losing Pricing Accuracy?

## Business Context

The absence of the `flat_type` attribute in production data leads to a significant degradation in pricing model performance and downstream analytical accuracy. This study evaluates the feasibility of reconstructing this missing field using available transaction characteristics. The objective is to identify a recovery method that is highly accurate, computationally efficient, and scalable across the full HDB transaction history.

## Scope and Requirements

The recovery architecture compares two distinct methodological paths:

- **Supervised Classification:** Direct prediction of flat type using historical labels.
- **Unsupervised Clustering:** Segmenting data based on structural similarities and mapping clusters back to flat-type labels.

Performance is evaluated based on **label recovery precision** and **operational scalability** on the full dataset of **972,320** records.

## Step 1: Exploratory Data Analysis (Feature Separability)

<iframe src="/outputs/section2/charts/S2QcF5_flat_type_count.html" title="Flat type count distribution"></iframe>

<iframe src="/outputs/section2/charts/S2QcF6_flat_type_floor_area_distribution.html" title="Floor area by flat type"></iframe>

<iframe src="/outputs/section2/charts/S2QcF7_flat_type_resale_price_distribution.html" title="Resale price by flat type"></iframe>

Initial analysis reveals strong structural separation between flat types, particularly within the **floor area** dimension. For instance, the median area for 3-room flats is **67 sqm**, compared to **119 sqm** for 5-room flats. This high degree of feature variance provides a robust foundation for automated recovery.

## Step 2: Unsupervised Modeling Track

The unsupervised approach involves partitioning the data and utilizing a majority-vote mapping strategy to assign labels.

<iframe src="/outputs/section2/charts/S2QcF1_unsupervised_confusion.html" title="Unsupervised mapped confusion"></iframe>

<iframe src="/outputs/section2/charts/S2QcF2_unsupervised_k_comparison.html" title="Unsupervised method comparison"></iframe>

<iframe src="/outputs/section2/charts/S2QcF3_unsupervised_segment_profile.html" title="Unsupervised segment profile"></iframe>

**Comparative Performance:**

- **KMeans:** Mapped Accuracy: **0.8431** | Silhouette: **0.4007** | Davies-Bouldin: **0.7977**
- **RBM-KMeans:** Mapped Accuracy: **0.6174** | Silhouette: **0.5139** | Davies-Bouldin: **0.5556**

While the RBM-KMeans approach improves mathematical compactness (as indicated by the Silhouette and DBI scores), it results in a significant loss of mapped label accuracy. Consequently, it is deemed suboptimal for this specific business requirement.

## Step 3: Supervised Modeling Track

The supervised model demonstrates near-perfect reconstruction of the missing attributes on the holdout set:

<iframe src="/outputs/section2/charts/S2QcF8_supervised_model_summary.html" title="Supervised model summary"></iframe>

<iframe src="/outputs/section2/charts/S2QcF9_supervised_confusion.html" title="Supervised confusion matrix"></iframe>

**Holdout Performance Metrics:**

- **Holdout Rows:** 15,618
- **Accuracy:** **1.000**
- **Weighted F1-Score:** **1.000**

The supervised approach significantly outperforms unsupervised mapped recovery in all tested metrics.

## Step 4: Mathematical Framework

The **unsupervised objective** is characterized by an intermediate mapping step which introduces information loss:

$$
\hat{z}_i = g(X_i), \quad \hat{y}_i = \text{map}(\hat{z}_i)
$$

Where $g(X_i)$ represents the clustering function and $\text{map}(\cdot)$ is the majority-vote assignment.

In contrast, the **supervised objective** directly optimizes for the target labels:

$$
\hat{y}_i = f(X_i), \quad y_i \in \{\text{flat types}\}
$$

## Interpretation

For the specific operational goal of recovering the original `flat_type` field, supervised modeling is the superior solution. While unsupervised segmentation provides value for exploratory grouping and identifying novel market clusters, it lacks the precision required for direct label reconstruction.

## Recommended Strategy

Deploy the **supervised recovery model** as the primary operational pathway for handling missing `flat_type` values. Retain the **KMeans segmentation** as a secondary layer to support exploratory analytics and market segmentation tasks.
