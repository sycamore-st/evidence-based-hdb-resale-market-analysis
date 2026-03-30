In [section3_question_b.py](section3_question_b.py), there are a few different formula layers for Question B.

If you mean the main modeling part, the formulas are:

For Question B, the more defensible controlled specification is the interaction model with **categorical completion-year effects**:

$$
\text{floor\_area\_sqm}_{y,f,t}
=
\alpha
+
\sum_y \lambda_y \, 1\{\text{completion\_year}=y\}
+
\sum_f \gamma_f \, 1\{\text{flat\_type}=f\}
+
\sum_{y,f} \theta_{y,f}
\bigl(1\{\text{completion\_year}=y\}\times1\{\text{flat\_type}=f\}\bigr)
+
\sum_t \delta_t \, 1\{\text{town}=t\}
+
\varepsilon_{y,f,t}
$$

That is the code at [section3_question_b.py](section3_question_b.py):
`floor_area_sqm ~ C(completion_year) * C(flat_type, Treatment(reference='4 ROOM')) + C(town)`

And it is estimated with weights:
$$
w_{y,f,t}=\text{transactions}_{y,f,t}
$$

So larger town-year-flat-type cells get more weight.

Why `C(completion_year)` instead of a linear `completion_year` term:

- flat design standards can change in steps rather than on a smooth straight line
- policy or design revisions may affect a few cohorts sharply
- a categorical year effect allows the profile to be non-linear and non-monotonic

So this model does **not** assume that each additional completion year changes floor area by the same fixed amount.

Why `floor_area_sqm` stays in levels instead of `\log(floor_area_sqm)`:

- the business question is about whether flats are getting physically smaller
- levels are directly interpretable in square metres
- the stakeholder-facing answer is easier to state as "newer flats are X sqm smaller" than as a percentage change in area
- robust `HC3` standard errors are already used for inference, so a log transform is not required just to handle heteroskedasticity

So the modeling choice is deliberate:

- use `C(completion_year)` because the completion-year relationship may be non-linear
- keep `floor_area_sqm` in levels because the question is about physical size, not percentage size change

If you mean the first chart, `S3QbF1_floor_area_over_time`, that one is not a regression formula. It is just grouped averages:

Overall line:
$$
\overline{A}_y=\frac{1}{N_y}\sum_{i:\,\text{completion\_year}_i=y}\text{floor\_area\_sqm}_i
$$

Flat-type line:
$$
\overline{A}_{y,f}=\frac{1}{N_{y,f}}\sum_{i:\,\text{completion\_year}_i=y,\ \text{flat\_type}_i=f}\text{floor\_area\_sqm}_i
$$

That comes from [section3_question_b.py](section3_question_b.py).

And the slope chart `S3QbF2` uses a simple fitted line slope from:
$$
\overline{A}_{y,f}=a_f+b_f \cdot y
$$

where `b_f` is computed by `np.polyfit(...)` in [section3_question_b.py](section3_question_b.py).
