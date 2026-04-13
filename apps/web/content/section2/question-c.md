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

The `flat_type` field is one of the most operationally important variables in HDB pricing analysis. It directly captures broad size class and housing format, and it is heavily used in both pricing and reporting. If that field is missing, model accuracy falls sharply and downstream analysis becomes unstable.

This study evaluates whether the missing `flat_type` can be reconstructed accurately enough for production use. The requirement is not merely academic classification accuracy. The recovered labels must be good enough to support pricing work at full-dataset scale.

## Scope and Modeling Paths

Two recovery strategies are compared:

- **Supervised classification:** predict the original flat type directly from transactions where labels are observed.
- **Unsupervised clustering:** form structural segments first, then map clusters back to flat-type labels.

The supervised feature set is:

$$
X_i = \{
\text{town}_i,\,
\text{flat\_model}_i,\,
\text{floor\_area\_sqm}_i,\,
\text{year}_i,\,
\text{age}_i,\,
\text{remaining\_lease\_years}_i,\,
\text{min\_floor\_level}_i,\,
\text{max\_floor\_level}_i,\,
\text{resale\_price}_i
\}
$$

Where:

- `town` and `flat_model` provide categorical structural context.
- `floor_area_sqm` is the strongest direct discriminator of flat type.
- `year`, `age`, and `remaining_lease_years` capture temporal and tenure structure.
- `min_floor_level` and `max_floor_level` capture storey band.
- `resale_price` captures market valuation signal that often co-varies with flat type.

The unsupervised track is intentionally narrower. In the current implementation, the clustering features are mainly:

$$
Z_i = \{\text{resale\_price}_i,\; \text{floor\_area\_sqm}_i\}
$$

This makes the comparison sharp: can the missing label be recovered from pure structural separation alone, or do we need direct supervised learning?

## Step 1: Check Whether Flat Types Are Structurally Separable

Before choosing a recovery method, we need to know whether the classes are visibly separable in the observed data.

<iframe src="/outputs/section2/charts/S2QcF5_flat_type_count.html?v=20260413" title="Flat type count distribution" data-caption="Fig 1 — Transaction count by flat type. X-axis: flat type; y-axis: transaction count. This shows the class balance in the source data and whether some labels are much more common than others."></iframe>

This first chart is included because recovery difficulty depends partly on class balance. A highly imbalanced dataset can make rare labels hard to recover even when the features are informative.

<iframe src="/outputs/section2/charts/S2QcF6_flat_type_floor_area_distribution.html?v=20260413" title="Floor area by flat type" data-caption="Fig 2 — Floor area distribution by flat type. X-axis: floor area (sqm); y-axis: flat type. Clear spacing between categories indicates that floor area is a strong discriminator."></iframe>

This chart matters because it tells us whether the recovery problem is structurally feasible. Here, the separation is strong: floor area alone already splits several classes cleanly.

<iframe src="/outputs/section2/charts/S2QcF7_flat_type_resale_price_distribution.html?v=20260413" title="Resale price by flat type" data-caption="Fig 3 — Resale price distribution by flat type. X-axis: resale price (SGD); y-axis: flat type. The overlap is wider than for floor area, showing that price helps, but is not sufficient by itself."></iframe>

This third chart complements the area view. It shows that price carries useful signal, but the overlap across classes is much larger than for floor area. That is why the supervised model uses a richer feature set rather than relying on price alone.

## Step 2: Evaluate the Unsupervised Track

The unsupervised logic is:

$$
\hat{z}_i = g(Z_i),
\qquad
\hat{y}_i = \operatorname{map}(\hat{z}_i)
$$

Where:

- $g(\cdot)$ is a clustering algorithm that assigns transaction $i$ to a latent segment.
- $\hat{z}_i$ is the cluster label.
- $\operatorname{map}(\cdot)$ converts each cluster into a flat-type label through majority-vote matching.

The key weakness is that the business label is **not** learned directly. It is recovered only after the clustering step, which creates an information-loss layer.

<iframe src="/outputs/section2/charts/S2QcF1_unsupervised_confusion.html?v=20260413" title="Unsupervised mapped confusion" data-caption="Fig 4 — Confusion matrix for the mapped unsupervised labels. X-axis: predicted flat type; y-axis: true flat type. Off-diagonal mass shows where clustering-based recovery merges nearby categories."></iframe>

We include this chart because cluster-quality statistics are not enough. The business question is whether the recovered labels match the original flat-type field, and the confusion matrix shows exactly where the method fails.

<iframe src="/outputs/section2/charts/S2QcF2_unsupervised_k_comparison.html?v=20260413" title="Unsupervised method comparison" data-caption="Fig 5 — Comparison of unsupervised methods and cluster-quality statistics. The chart contrasts mapped label accuracy with silhouette and Davies-Bouldin scores, showing that mathematically cleaner clusters do not necessarily produce better flat-type recovery."></iframe>

This comparison is important because it explains why a method with stronger cluster compactness can still be worse for the actual operational task.

<iframe src="/outputs/section2/charts/S2QcF3_unsupervised_segment_profile.html?v=20260413" title="Unsupervised segment profile" data-caption="Fig 6 — Feature profiles of the unsupervised clusters. This helps interpret which structural segments correspond cleanly to flat types and which ones blur together."></iframe>

The cluster profile chart is included to make the failure mode interpretable. It shows that some clusters represent useful structural segments, but those segments do not always map one-to-one into the business labels we need.

**Observed unsupervised performance**

- **KMeans:** mapped accuracy **0.8431**, silhouette **0.4007**, Davies-Bouldin **0.7977**
- **RBM-KMeans:** mapped accuracy **0.6174**, silhouette **0.5139**, Davies-Bouldin **0.5556**

This is the central lesson of the unsupervised track: stronger geometric clustering does not guarantee stronger label recovery.

## Step 3: Evaluate the Supervised Track

The supervised objective is simpler and better aligned with the business goal:

$$
\hat{y}_i = f(X_i),
\qquad
y_i \in \{\text{flat-type labels}\}
$$

Where:

- $f(\cdot)$ is the classifier trained directly on known flat-type labels.
- $\hat{y}_i$ is the recovered flat type.
- $y_i$ is the observed true label in the training data.

Because the target is optimized directly, the supervised model does not suffer from the cluster-to-label mapping problem.

<iframe src="/outputs/section2/charts/S2QcF8_supervised_model_summary.html?v=20260413" title="Supervised model summary" data-caption="Fig 7 — Supervised classification summary showing accuracy, precision, recall, and F1. This chart demonstrates whether a direct classifier can recover the original label at production-ready accuracy."></iframe>

<iframe src="/outputs/section2/charts/S2QcF9_supervised_confusion.html?v=20260413" title="Supervised confusion matrix" data-caption="Fig 8 — Confusion matrix for the supervised classifier. Near-total diagonal concentration indicates that the original flat-type labels are recovered almost perfectly."></iframe>

These charts are included because they answer the operational question directly: can the missing field be reconstructed at a standard high enough for downstream pricing use?

**Holdout supervised performance**

- **Holdout rows:** 15,618
- **Accuracy:** 1.000
- **Weighted F1-score:** 1.000

In the current holdout design, the supervised classifier recovers flat type almost perfectly.

## Interpretation

For the specific business objective of reconstructing the original `flat_type` field, the result is decisive:

- the **supervised classifier** is the correct operational tool;
- the **unsupervised models** are still useful for exploratory segmentation, but not for production label recovery.

The reason is not just that the supervised method scores higher. It is that it solves the right problem directly. Clustering is trying to discover latent structure; classification is trying to recover a known field. When the business requirement is faithful reconstruction of an existing label, direct supervision is the more appropriate design.

## Recommended Strategy

1. **Production recovery:** use the supervised classifier as the default pathway when `flat_type` is missing.
2. **Exploratory analytics:** retain KMeans segmentation as a secondary unsupervised lens for market structure analysis.
3. **Downstream pricing:** treat supervised recovery as safe enough for valuation and modeling workflows, given the near-perfect holdout performance.
