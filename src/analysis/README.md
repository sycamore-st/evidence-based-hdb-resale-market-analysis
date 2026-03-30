# Analysis Guide

This folder contains the downstream analytics and export logic built on top of the processed resale dataset.

## Canonical Entry Points

Run the full project workflow:

```bash
./.venv/bin/python -m src.analysis.run_all
```

Run Section 2 only:

```bash
./.venv/bin/python -m src.analysis.section2.S2_models
```

Run Section 3 only:

```bash
./.venv/bin/python -m src.analysis.section3.S3_policy
```

Run Section 1 Tableau exports from an existing processed dataset:

```bash
./.venv/bin/python -m src.analysis.section1.tableau_export
```

## Folder Responsibilities

- `run_all.py`: top-level orchestrator; builds the dataset if needed, exports Section 1 assets, runs Section 2 and Section 3, and writes a run summary
- `deck.py`: writes the slide outline and generated `.pptx` support deck
- `common/`: shared plotting and analysis helpers
- `section1/`: Tableau-facing exports for the dashboard workstream
- `section2/`: pricing-model evaluation, comparables analysis, and classification outputs
- `section3/`: policy-analysis workflows, figure generation, and summary reports

## Section 1 Files

- `tableau_export.py`: canonical Section 1 export entrypoint
- `dashboard_1.py`: market-overview extracts
- `dashboard_2.py`: budget-to-space extracts
- `dashboard_3.py`: location optimizer and building-level extracts
- `town_indicator_assets.py`: supporting town-level indicator table for Dashboard 1
- `helpers.py`: shared Section 1 loading and export helpers

## Section 2 Files

- `S2_models.py`: canonical Section 2 entrypoint
- `section2_question_a.py`: question A price-model benchmarking
- `section2_question_b.py`: question B valuation and comparables workflow
- `section2_question_c.py`: question C classification and segmentation workflow
- `S2_helpers.py` and `S2_config.py`: shared configuration, loading, and artifact-writing helpers
- `S2_ppt_summary.py`: markdown summaries for presentation use

## Section 3 Files

- `S3_policy.py`: canonical Section 3 entrypoint
- `section3_question_a.py`: town-value analysis
- `section3_question_b.py`: flat-size trend analysis
- `section3_question_c.py`: Downtown Line Stage 2 policy analysis
- `section3_question_d.py`: COE relationship analysis
- `S3_helpers.py`: shared loading, chart-writing, and reporting helpers

## Main Outputs

- `outputs/section1/`: dashboard tables, GeoJSON files, diagnostics, and screenshots
- `outputs/section2/results/`: modeling summaries, comparison tables, and question-level artifacts
- `outputs/section3/results/`: policy summaries and figure source tables
- `outputs/section3/charts/`: selected static charts for review and deck generation
- `deck/Evidence-Based HDB Resale Market Analysis.pptx`: generated support deck
