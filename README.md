# Evidence-Based HDB Resale Market Analysis

This repository packages the code, curated outputs, and reviewer-facing notes for a quantitative strategy case interview built on Singapore HDB resale data.

## Deliverables

- [Evidence-Based HDB Resale Market Analysis.pptx](deck/Evidence-Based%20HDB%20Resale%20Market%20Analysis.pptx)
- [HDB Resale Market Analysis Tableau.twbx](deck/HDB%20Resale%20Market%20Analysis%20Tableau.twbx)

The work is organized into three sections:

- Section 1: buyer-facing dashboard data products
- Section 2: resale-price modeling and comparables analysis
- Section 3: policy analysis on affordability, flat sizes, transport access, and COE effects

## What This Repo Contains

- reproducible Python pipeline and analysis code under `src/`
- reviewer-facing notes under `docs/`
- frontend application scaffold under `apps/web/`
- published web artifacts under `artifacts/web/`
- selected outputs under `outputs/`
- slide-deck support artifacts under `deck/`
- local data caches under `data/`, which are intentionally ignored in git

This packaged copy is meant to be readable without rerunning the full workflow, while still documenting the commands needed to reproduce the main results locally.

## Repository Structure

```text
. 
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── public/
├── artifacts/
│   └── web/
│       ├── model/
│       ├── overview/
│       └── policy/
├── configs/
│   └── design_tokens.json
├── deck/
│   ├── Evidence-Based HDB Resale Market Analysis.pptx
│   ├── HDB Resale Market Analysis Tableau.twbx
│   └── theme_tokens.json
├── docs/
│   ├── README.md
│   ├── section1_dashboards.md
│   ├── section2_question_a_case.md
│   ├── section2_question_b_case.md
│   ├── section2_question_c_case.md
│   ├── section3_policy_notes.md
│   ├── section3_question_a_case.md
│   ├── section3_question_c_case.md
│   ├── section3_question_c_model_summaries.md
│   ├── section3_question_d_case.md
│   └── section3_question_d_model_summaries.md
├── outputs/
│   ├── section1/
│   │   ├── results/
│   │   └── screenshot/
│   ├── section2/
│   │   ├── charts/
│   │   └── results/
│   └── section3/
│       ├── charts/
│       └── results/
├── src/
│   ├── analysis/
│   ├── common/
│   └── pipeline/
├── .gitignore
├── pyproject.toml
└── README.md
```

Folder-level guides:

- [Pipeline Guide](src/pipeline/README.md)
- [Analysis Guide](src/analysis/README.md)
- [Supporting Docs](docs/README.md)
- [Frontend Architecture](docs/frontend_architecture.md)
- [Web App Run Guide](apps/web/README.md)

## Environment Setup

This project uses Python 3.10+ and is defined by [pyproject.toml](pyproject.toml).

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e .
```

## Reproducing The Results

Build the canonical processed dataset:

```bash
./.venv/bin/python -m src.pipeline.build_resale_analysis_dataset
```

Build the building-level Tableau assets for Section 1:

```bash
./.venv/bin/python -m src.pipeline.build_building_tableau_assets
```

Run the end-to-end analysis workflow:

```bash
./.venv/bin/python -m src.analysis.run_all
```

Publish frontend-ready dashboard artifacts:

```bash
./.venv/bin/python -m src.pipeline.publish_web_artifacts
```

Validate the published web artifact contract:

```bash
./.venv/bin/python -m src.pipeline.validate_web_artifacts
```

Run the frontend locally from the monorepo app:

```bash
cd apps/web
npm install
npm run dev
```

From any terminal location, you can also use the absolute app path:

```bash
cd /Users/claire/PycharmProjects/evidence-based-hdb-resale-market-analysis/apps/web
npm install
npm run dev
```

If you see `env: node: No such file or directory`, install or enable Node.js first, then rerun the commands above. See [apps/web/README.md](apps/web/README.md) for the frontend run guide, key routes, troubleshooting, and the recommended `npm run typecheck` verification step.

Or run it from the repo root:

```bash
make web-install
make web-dev
```

Dashboard 1 layout presets can be switched by URL:

- `http://localhost:3000/section1/dashboard-1?layout=editorial`
- `http://localhost:3000/section1/dashboard-1?layout=balanced`
- `http://localhost:3000/section1/dashboard-1?layout=chart-heavy`

Dashboard 1 layout sandbox (live controls + URL-synced knobs):

- `http://localhost:3000/section1/dashboard-1/sandbox`

## Tracked Outputs Vs Local Caches

Tracked in git:

- selected Section 1 export tables, diagnostics, and screenshot references
- Section 2 modeling summaries and result tables
- Section 3 policy summaries, figure tables, and selected static figures
- reviewer-facing notes and deck support artifacts

Not tracked in git:

- `data/raw/` source downloads
- `data/processed/` rebuildable checkpoints and datasets
- generated `.html` and `.png` chart exports
- temporary training logs, IDE files, and local caches

## Manual Steps

- Tableau dashboards are still assembled manually in Tableau Desktop from the exported Section 1 files in `outputs/section1/results/`.
- The PowerPoint in `deck/` is a rebuildable support artifact for the final presentation workflow.
- The frontend reads prepared files from `artifacts/web/` and does not depend on raw pipeline intermediates.
- Some outputs are intentionally pretracked so a reviewer can inspect the work without rerunning the full pipeline.
