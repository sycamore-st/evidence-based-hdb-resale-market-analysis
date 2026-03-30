# Section 2 Question C Case Note

## 1. Business Question

The business question for Section 2 Question C is:

> If flat type is hidden, can we recover it well enough to preserve downstream price-estimation quality?

The workflow intentionally studies two solution paths:

1. a **supervised classifier**, which directly predicts flat type
2. an **unsupervised segmentation approach**, which clusters transactions first and then maps segments back to flat types

This is not only a classification problem. It is also a business-impact problem:

> How much pricing accuracy do we lose when flat type is no longer known exactly?

The analysis code for this question lives in [section2_question_c.py](/src/analysis/section2/section2_question_c.py).

## 2. EDA

The EDA opens with the basic market structure of flat types before any model is fit.

### 2.1 Flat-type count distribution

Outputs:

- [S2QcF4_flat_type_count.svg](/outputs/section2/charts/S2QcF4_flat_type_count.svg)
- [S2Qc_flat_type_distribution_summary.csv](/outputs/section2/results/S2Qc_flat_type_distribution_summary.csv)

Preview:

![S2QcF4](/outputs/section2/charts/S2QcF4_flat_type_count.svg)

This chart shows that the data are highly imbalanced across flat types. In the saved summary:

- `4 ROOM`: `4,945` transactions
- `3 ROOM`: `3,159`
- `5 ROOM`: `2,844`
- `EXECUTIVE`: `926`
- `2 ROOM`: `117`
- `1 ROOM`: `4`
- `MULTI-GENERATION`: `1`

Interpretation:

- most predictive power will be driven by the common classes
- rare flat types are structurally harder to learn well

### 2.2 Floor-area distribution by flat type

Outputs:

- [S2QcF5_flat_type_floor_area_distribution.svg](/outputs/section2/charts/S2QcF5_flat_type_floor_area_distribution.svg)

Preview:

![S2QcF5](/outputs/section2/charts/S2QcF5_flat_type_floor_area_distribution.svg)

This is the most intuitive separation chart. Floor area strongly differs across flat types.

Examples from the saved summary:

- `3 ROOM` median area: `67 sqm`
- `4 ROOM` median area: `94 sqm`
- `5 ROOM` median area: `120 sqm`
- `EXECUTIVE` median area: `145 sqm`

Interpretation:

- flat type is not arbitrary; it is encoded in size and structure
- this is why both supervised and unsupervised recovery can work at all

### 2.3 Resale-price distribution by flat type

Outputs:

- [S2QcF6_flat_type_resale_price_distribution.svg](/outputs/section2/charts/S2QcF6_flat_type_resale_price_distribution.svg)

Preview:

![S2QcF6](/outputs/section2/charts/S2QcF6_flat_type_resale_price_distribution.svg)

Price also separates flat types, though less cleanly than area because location and age still matter.

Interpretation:

- resale price carries flat-type information
- but using price as an input can also make the task easier than a purely structural recovery problem

## 3. Solution

### 3.1 Unsupervised track

The unsupervised track fits `MiniBatchKMeans` clusters and then maps each recovered segment to the modal flat type observed in training data.

The main reported setup now fixes the cluster count at **7 clusters** so the segmentation aligns with the primary HDB flat categories. We still export an elbow-style diagnostic over several `k` values as supporting evidence, but the headline holdout accuracy is reported for the fixed `k=7` solution.

Saved outputs:

- [S2Qc_flat_type_unsupervised.json](/outputs/section2/results/S2Qc_flat_type_unsupervised.json)
- [S2Qc_unsupervised_k_comparison.csv](/outputs/section2/results/S2Qc_unsupervised_k_comparison.csv)
- [S2QcF1_unsupervised_confusion.svg](/outputs/section2/charts/S2QcF1_unsupervised_confusion.svg)
- [S2QcF2_unsupervised_k_comparison.svg](/outputs/section2/charts/S2QcF2_unsupervised_k_comparison.svg)
- [S2QcF3_unsupervised_segment_profile.svg](/outputs/section2/charts/S2QcF3_unsupervised_segment_profile.svg)

Preview:
![S2QcF1_unsupervised_confusion.svg](/outputs/section2/charts/S2QcF1_unsupervised_confusion.svg)
![S2QcF2_unsupervised_k_comparison.svg](/outputs/section2/charts/S2QcF2_unsupervised_k_comparison.svg)
![S2QcF3_unsupervised_segment_profile.svg](/outputs/section2/charts/S2QcF3_unsupervised_segment_profile.svg)

In the saved run:

- fixed cluster count: `7`
- mapped holdout accuracy: about `0.642`

How this accuracy is evaluated:

- fit KMeans on the training months only
- assign each training cluster to the most common observed `flat_type` in that cluster
- predict cluster membership for the holdout months
- convert each predicted cluster into a predicted flat type using the train-set mapping
- compare that mapped predicted flat type against the true holdout `flat_type`

So this is not raw clustering purity. It is a mapped holdout classification accuracy based on cluster-to-label assignment.

So as a direct flat-type recovery method, the unsupervised track is much weaker than the supervised one.

But the downstream pricing result is interesting:

- pricing RMSE with known flat type: about `30,065`
- pricing RMSE with recovered segment: about `29,246`
- delta: about `-819`

This means the segment representation can still be useful for pricing even when it is not a very good label-for-label flat-type classifier.

Interpretation:

- clustering may recover latent price-relevant housing segments rather than the exact official flat-type labels
- that can still help a pricing model, even if classification accuracy is mediocre
- the elbow plot is useful as a diagnostic, but the reported business result should stay anchored on the fixed 7-cluster setup because that is the most interpretable alignment with the HDB category structure


### 3.2 Supervised track

Uses a strict time-aware train-test split.

- the **latest 9 months** are held out for evaluation
- the training set uses the **immediately preceding rolling window**, capped at about **5 years** of history before the holdout starts
- in practice, this should be described as using the prior **3-5 years** when that amount of history is available

This matters because the business use case is operational recovery on future transactions, not random row reconstruction inside a mixed-time sample.

The supervised track predicts `flat_type` directly from:

- town
- flat model
- floor area
- year
- age
- remaining lease
- min and max floor level
- resale price

Saved outputs:

- [S2Qc_flat_type_classifier.json](/outputs/section2/results/S2Qc_flat_type_classifier.json)
- [S2Qc_supervised_per_class_accuracy.csv](/outputs/section2/results/S2Qc_supervised_per_class_accuracy.csv)
- [S2QcF7_supervised_model_summary.svg](/outputs/section2/charts/S2QcF7_supervised_model_summary.svg)
- [S2QcF8_supervised_confusion.svg](/outputs/section2/charts/S2QcF8_supervised_confusion.svg)

![S2QcF7_supervised_model_summary.svg](/outputs/section2/charts/S2QcF7_supervised_model_summary.svg)
![S2QcF8_supervised_confusion.svg](/outputs/section2/charts/S2QcF8_supervised_confusion.svg)

In the saved run, the selected classifier is logistic regression with:

- accuracy: about `0.984`
- weighted F1: about `0.985`

Per-class accuracy is especially strong for the major classes:

- `4 ROOM`: `99.4%`
- `5 ROOM`: `100.0%`
- `3 ROOM`: `96.7%`
- `EXECUTIVE`: `96.9%`

The main weakness is very rare classes like `2 ROOM`, and essentially no coverage for the extremely rare categories.

#### Downstream pricing impact

This is the key business metric.

- pricing RMSE with known flat type: about `30,065`
- pricing RMSE with recovered flat type: about `30,396`
- degradation: only about `331`

That means the supervised recovery track preserves almost all of the pricing performance.

## 4. Interpretation

The most defensible interpretation of Question C is:

- on methodology, the evaluation should be framed as a future-facing test: latest 9 months for evaluation, prior rolling 3-5 years for training
- if the goal is to recover the official flat type accurately, the supervised approach wins by a wide margin
- if the goal is only to preserve downstream pricing quality, both approaches can still be informative, but the supervised method is cleaner and much easier to explain
- the unsupervised method is interesting as a segmentation exercise, but it should not be presented as equally good at recovering the true flat-type label

So the business answer is:

> Yes, hidden flat type can be recovered well enough to preserve pricing quality, and the supervised classifier does this extremely well on the common classes. The unsupervised approach is weaker as a label-recovery tool, but it still captures useful housing segments for pricing.
