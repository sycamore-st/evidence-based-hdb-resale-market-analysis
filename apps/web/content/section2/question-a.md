---
title: "Question A: markdown article sample"
kicker: "Section 2 / Question A"
description: "A compact example page showing how links, formulas, figures, code blocks, tables, and HTML embeds can work inside the markdown article system."
section: "section2"
slug: "question-a"
order: 1
---

# Section 2 Question A Sample

This page is intentionally short. Treat it as a writing reference for the markdown article system rather than a full case note.

## 1. Basic writing

You can write normal paragraphs, add **bold emphasis**, use inline code like `flat_type`, and link to source files such as [section2_question_a.py](/src/analysis/section2/section2_question_a.py).

You can also link directly to generated outputs, for example:

- [Controlled variation chart](/outputs/section2/charts/S2QaF1_controlled_variation.svg)
- [Model comparison csv](/outputs/section2/results/S2Qa_model_comparison.csv)

> Use short blockquotes when you want to isolate an interpretation, decision rule, or reporting takeaway.

## 2. Formula sample

Inline math works, for example $RMSE = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}$.

Displayed math also works:

$$
\hat{y} = \beta_0 + \beta_1 \cdot \text{flat\_age} + \beta_2 \cdot \text{town} + \beta_3 \cdot \text{flat\_type}
$$

This makes it easier to write compact model notes directly in markdown.

## 3. Figure sample

![Controlled variation preview](/outputs/section2/charts/S2QaF1_controlled_variation.svg)

The image above is a normal markdown figure using an output file path.

## 4. Embedded HTML sample

If you already have a small self-contained HTML graphic, you can embed it directly:

<iframe src="/sample-embed.html" title="Sample embedded html chart"></iframe>

This is a good fit for small hand-authored demos or exported HTML fragments.

## 5. Code block sample

```python
target_features = ["flat_type", "flat_age", "town"]
model.fit(train[target_features], train["resale_price"])
prediction = model.predict(test[target_features])
```

## 6. Table sample

| Model | RMSE | MAPE |
| --- | ---: | ---: |
| Linear Regression | 62,400 | 9.8% |
| Random Forest | 55,900 | 8.9% |
| XGBoost | 51,425 | 8.4% |

## 7. Suggested writing pattern

For future Section 2 and Section 3 pages, a good structure is:

1. Business question
2. EDA or context
3. Method
4. Key outputs
5. Interpretation
6. Caveats

That keeps the markdown readable while still making room for figures, embeds, formulas, and downloadable outputs.
