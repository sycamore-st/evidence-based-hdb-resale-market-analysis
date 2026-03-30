# Section 3 Policy Notes

This note keeps the small amount of interpretation context that is easier to read in prose than to infer from the code alone.

## Question A: Is Yishun The Cheapest?

The intended claim is not that Yishun is always the single lowest-price town on every raw metric. The stronger and more defensible framing is that Yishun is a value town after accounting for flat size and comparable peers.

Relevant code:
- `src.analysis.section3.section3_question_a`

## Question B: Are Flats Getting Smaller?

The key distinction is between:

- changes in the mix of flat types sold
- within-flat-type changes in floor area over time

The Section 3 workflow explicitly separates these so the summary does not overstate a national shrinkage narrative.

Relevant code:
- `src.analysis.section3.section3_question_b`

## Question C: Did Downtown Line Stage 2 Affect Nearby Resale Prices?

This is presented as a controlled treatment-versus-comparison exercise with explicit pre-trend caution, not as a definitive causal estimate.

Relevant code:
- `src.analysis.section3.section3_question_c`

## Question D: Are Far-From-Central Towns More Sensitive To COE?

The analysis is framed around relative sensitivity, not simple co-movement. The useful management question is whether outer towns respond differently from central towns after controls, not whether both series move together in raw charts. That same logic should be applied both to raw price spreads and to the gap between the adjusted housing indices. The preferred regression is now a second-stage adjusted town-month model built on those hedonic indices.

Relevant code:
- `src.analysis.section3.section3_question_d`
