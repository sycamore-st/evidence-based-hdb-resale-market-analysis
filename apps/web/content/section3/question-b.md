---
title: "Are Newer HDB Flats Becoming Smaller In Meaningful Ways?"
kicker: "Section 3 / Question B"
description: "A longitudinal floor-area analysis combining descriptive trends and controlled models by flat type."
section: "section3"
slug: "question-b"
order: 2
---

# Are Newer HDB Flats Becoming Smaller In Meaningful Ways?

## Business Context

There is a persistent belief among Singapore homebuyers that each successive
generation of HDB flats is smaller than the last. The complaint is specific: a
4-room flat built in the 1990s feels noticeably larger than one completed in the
2010s, even though both carry the same flat-type label. The question is whether
this perception corresponds to a measurable and statistically robust trend, or
whether it is partly an artifact of how the housing stock has changed in
composition over time.

This distinction matters because the policy and business implications differ. 
If all flat types are uniformly shrinking, that points to a systemic change in
design standards. If only certain segments are affected, the story is more
nuanced, and targeted responses become appropriate.

## Scope and Constraints

A key methodological challenge is that the aggregate average floor area across
all HDB units is strongly influenced by the **flat-type mix** in any given year.
Periods when HDB built fewer executive units and more 3-room units will
mechanically pull the average down, without any single flat type actually
getting smaller. Similarly, towns vary in the typical size of their housing
stock. A naive trend line pooling everything would conflate genuine design
shrinkage with shifts in build programme composition.

We therefore use two parallel approaches:

- **Descriptive analysis by segment:** Raw floor area trends plotted separately
  for each flat type, removing cross-type contamination.
- **Controlled regression:** A weighted least-squares model that isolates the
  completion-year effect after explicitly holding flat type and town constant.

Note that **completion year** here refers to the year the block was built (
derived from lease commencement date), not the year of the transaction. This is
the correct variable for studying design trends. A 1990s block transacting in
2023 still reflects 1990s design decisions.

## Step 1: Long-Run Descriptive Trends

The first chart shows average floor area over completion years for all units
combined. This gives the broad shape of the trend before we disaggregate.

<iframe src="/outputs/section3/charts/S3QbF1_floor_area_over_time.html" title="Average floor area over time" data-caption="Fig 1 — Average floor area by completion year, all flat types pooled. X-axis: block completion year; Y-axis: average floor area (sqm). The overall trend is downward, but this aggregate conceals substantial variation across flat types."></iframe>

The overall average has declined, but the pooled chart is misleading because the
flat-type composition of new builds has shifted substantially decade to decade.
The next two charts disaggregate by segment, first for the three most common
types (3-room, 4-room, 5-room) and then for the sparser categories.

<iframe src="/outputs/section3/charts/S3QbF1a_floor_area_over_time.html" title="Common flat types floor area trend" data-caption="Fig 2 — Average floor area by completion year for 3-room, 4-room, and 5-room flats. Each line represents one flat type. The trend is visible within each type, but the rate of change varies considerably between them."></iframe>

<iframe src="/outputs/section3/charts/S3QbF1b_floor_area_over_time.html" title="Sparse flat types floor area trend" data-caption="Fig 3 — Average floor area by completion year for Executive and other sparse flat types. The decline is sharper here than in the common categories, and the time series is noisier due to fewer observations."></iframe>

Already from the descriptive charts, the story is heterogeneous. The three
common flat types show a gradual, relatively steady decline; the Executive and
multi-generation categories show steeper drops concentrated in specific decades.

## Step 2: Measuring the Rate of Decline by Segment

To quantify how fast each flat type is shrinking, we fit a linear trend line
within each segment using ordinary least squares on the segment-level year
averages. The slope coefficient gives the average annual change in floor area in
square metres per year.

<iframe src="/outputs/section3/charts/S3QbF2_floor_area_slope_by_type.html" title="Average annual floor-area change by flat type" data-caption="Fig 4 — Estimated annual floor-area change (slope) by flat type, derived from a linear fit within each segment. Negative values indicate shrinkage. Bars are sorted by slope magnitude; error bars show the uncertainty in the trend estimate."></iframe>

**Annual floor-area change by flat type:**

| Flat Type | Annual change (sqm/year) |
|-----------|--------------------------|
| Executive | −1.214                   |
| 5-Room    | −0.388                   |
| 4-Room    | −0.095                   |
| 3-Room    | −0.009                   |

To appreciate what these slopes mean in practice, consider the range over a
30-year window, roughly the span from the early 1990s to early 2020s. An
Executive flat has lost approximately **36 sqm** (1.214 × 30) over that period:
the difference between a generous living room and an absent one. A 5-room flat
has shed around **11.6 sqm**, roughly a small bedroom's worth of space. A 3-room
flat has held nearly constant, declining by less than 0.3 sqm over the same
period, which is barely perceptible.

## Step 3: Controlled Baseline Model

The descriptive slopes above treat each flat type in isolation. The controlled
model goes further by fitting all flat types and towns simultaneously, allowing
us to estimate the average within-type, within-town annual shrinkage:

$$
\text{floor\_area\_sqm}_i
=
\alpha

+ \beta\,\text{completion\_year}_i
+ C(\text{flat\_type}_i)
+ C(\text{town}_i)
+ \varepsilon_i
  $$

Here, $\text{completion\_year}_i$ enters as a continuous variable,
so $\hat{\beta}$ estimates the average sqm change per additional year of
completion date, after controlling for flat type and
town.

$C(\text{flat\_type}_i)$ and $C(\text{town}_i)$ are sets of dummy
variables absorbing the level differences between categories. A 5-room in
Tampines starts from a different baseline than a 3-room in Queenstown, but the
trend captured by $\hat{\beta}$ is estimated net of those differences.

The completion-year coefficient is therefore a **within-segment time trend**,
not a raw comparison across unlike flats. 
- If $\hat{\beta}$ is negative, newer
cohorts are systematically smaller even after holding flat type and town fixed.
- If it were zero, the idea of "shrinking flats" would mainly be a composition
story. 
- If it were positive, it would imply newer cohorts are actually getting
larger once we compare within the same segment. 

This makes the coefficient
economically interpretable: it is the average sqm change associated with one
more year of completion date.

**Model results:**

- **Completion-year coefficient ($\hat{\beta}$):** −0.039 sqm/year
- **95% Confidence Interval:** [−0.041, −0.037]
- **p-value:** ≈ 0

This is a small but precisely estimated coefficient. It says that, holding flat
type and town constant, each additional year of completion date is associated
with **0.039 sqm less floor area on average**, roughly 1.2 sqm per decade. The
confidence interval is tight because the sample spans decades and tens of
thousands of transactions. The effect is real and statistically unambiguous,
even if modest in any single year.

## Step 4: Interaction Model — Non-linear Year Effects by Flat Type

The controlled baseline model forces the trend to be a single straight line
across all years and flat types. But design choices are made by policy cohort,
not by linear extrapolation: a government initiative to build more compact units
in a specific decade will produce a step-change in floor area, not a smooth
gradient. To capture this, we use an interaction model with year dummies:

$$
\text{floor\_area\_sqm}_i
=
\alpha

+ C(\text{completion\_year}_i) \times C(\text{flat\_type}_i)
+ C(\text{town}_i)
+ \varepsilon_i
  $$

This specification fits a separate completion-year effect for each flat type in
each year, estimated using weighted least squares (WLS) where each cell is
weighted by the number of transactions it contains. The coefficients are then
expressed relative to the first available year for each flat type, so the chart
shows cumulative change from the starting point.

That relative-to-baseline setup is important for interpretation. The year-dummy
coefficients are **not** annual slopes. Instead, each point says: for this flat
type, how much larger or smaller were flats completed in year $t$ relative to
the earliest observed cohort, after controlling for town? Negative values
therefore indicate cumulative shrinkage from the baseline design era; flatter
lines imply design stability; sharp drops indicate distinct policy or programme
shifts rather than a smooth linear trend.

<iframe src="/outputs/section3/charts/S3QbF4a_adjusted_year_trend_by_type.html" title="Adjusted completion-year trend by flat type (group A)" data-caption="Fig 5a — Composition-adjusted floor area trend for 3-room, 4-room, and 5-room flats by completion year. Each line is a year-dummy coefficient expressed relative to the earliest observed year for that flat type, after controlling for town. Non-linear patterns in the line reflect genuine policy-driven design shifts, not sampling noise."></iframe>

<iframe src="/outputs/section3/charts/S3QbF4b_adjusted_year_trend_by_type.html" title="Adjusted completion-year trend by flat type (group B)" data-caption="Fig 5b — Same as Fig 5a, but for Executive and sparse flat types. The steeper and more volatile profiles reflect both genuine design changes and the smaller sample sizes in these categories."></iframe>

The adjusted profiles are revealing. They show that the shrinkage is not a
smooth march downward. There are periods of relative stability, punctuated by
sharper declines that correspond to specific building programmes. Executive
flats, in particular, show a concentrated step-down over a narrow band of
completion years, consistent with a design-era shift rather than a gradual
trend.

## Interpretation

The evidence supports the perception that newer HDB flats are smaller, but with
important caveats. The trend is **not uniform across the housing portfolio**:

- **Executive and 5-room flats** have undergone meaningful contraction, the kind
  that a buyer would notice in daily use.
- **4-room flats** have declined modestly; the effect over 30 years is real but
  not dramatic.
- **3-room flats** have remained essentially stable in floor area.

This suggests a **targeted recalibration** at the upper end of the flat-type
range rather than an across-the-board reduction in living standards. Whether
this reflects a deliberate policy to deliver more units at lower land cost, or
simply an alignment with changing household sizes over time, is beyond what the
data can tell us — but the pattern itself is clear.

## Recommended Strategy

1. **Metric-Driven Communication:** Replace "this flat type" with
   type-and-era-specific benchmarks when advising buyers. A 4-room completed in
   2000 and a 4-room completed in 2018 are not interchangeable size
   propositions.
2. **Granular Benchmarking:** Avoid relying on overall market averages in
   reporting, as they mask the divergent trajectories across segments. The
   Executive and 5-room stories are structurally different from the 3-room
   story.
