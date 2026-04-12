# Evidence-Based HDB Resale Market Analysis

This repository contains code, curated outputs, and web assets for an analysis project on Singapore HDB resale market trends, valuation, and policy interpretation.

## Deliverables

- [Evidence-Based HDB Resale Market Analysis.pptx](deck/Evidence-Based%20HDB%20Resale%20Market%20Analysis.pptx)
- [HDB Resale Market Analysis Tableau.twbx](deck/HDB%20Resale%20Market%20Analysis%20Tableau.twbx)
- [Live Web App](https://hdb-resale-market-analysis.vercel.app)

The work is organized into three sections:

- Section 1: buyer-facing dashboard data products
- Section 2: resale-price modeling and comparables analysis
- Section 3: policy analysis on affordability, flat sizes, transport access, and COE effects

## Explore the Web App

Start from the [landing page](https://hdb-resale-market-analysis.vercel.app), which links to the three main sections and the section menu.

### Section 1: Interactive Dashboards

- [Section 1 home](https://hdb-resale-market-analysis.vercel.app/section1) - overview of the buyer-facing dashboard suite
- [Dashboard 1: Market overview](https://hdb-resale-market-analysis.vercel.app/section1/dashboard-1) - transaction volume, pricing, and long-run market trends
- [Dashboard 2: Budget to space](https://hdb-resale-market-analysis.vercel.app/section1/dashboard-2) - compare how much floor area different budgets can buy
- [Dashboard 3: Location optimizer](https://hdb-resale-market-analysis.vercel.app/section1/dashboard-3) - shortlist buildings by budget, transport access, and nearby amenities

### Section 2: Modeling And Valuation

- [Section 2 home](https://hdb-resale-market-analysis.vercel.app/section2) - overview of the modeling and valuation section
- [Question A: Price prediction with restricted fields](https://hdb-resale-market-analysis.vercel.app/section2/question-a) - estimate resale prices when only visible listing fields are available
- [Question B: Target transaction valuation](https://hdb-resale-market-analysis.vercel.app/section2/question-b) - assess whether a subject resale transaction looks materially over- or under-valued
- [Question B Extended: Interactive valuation workbench](https://hdb-resale-market-analysis.vercel.app/section2/question-b-extended) - interactively inspect model estimates, local distributions, and comparable transactions
- [Question C: Recover missing flat type](https://hdb-resale-market-analysis.vercel.app/section2/question-c) - compare supervised and unsupervised approaches for recovering flat type

### Section 3: Policy And Market Interpretation

- [Section 3 home](https://hdb-resale-market-analysis.vercel.app/section3) - overview of the policy-focused analysis section
- [Question A: Is Yishun truly cheaper?](https://hdb-resale-market-analysis.vercel.app/section3/question-a) - test whether Yishun remains discounted after controlling for observed housing characteristics
- [Question B: Are newer flats becoming smaller?](https://hdb-resale-market-analysis.vercel.app/section3/question-b) - examine floor-area compression over time across flat types
- [Question C: Did DTL2 lift nearby prices?](https://hdb-resale-market-analysis.vercel.app/section3/question-c) - estimate whether the Downtown Line Stage 2 opening is associated with a local resale premium
- [Question D: Do outer towns react more to COE?](https://hdb-resale-market-analysis.vercel.app/section3/question-d) - test whether outer-town resale values are more sensitive to car-ownership cost shocks

## What This Repo Contains

- reproducible Python pipeline and analysis code under `src/`
- frontend application under `apps/web/`
- published web artifacts under `artifacts/web/`
- selected outputs under `outputs/`
- deck support artifacts under `deck/`
- local data caches under `data/` (intentionally ignored in git)

## Repository Structure

```text
.
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── content/
│       ├── docs/
│       └── lib/
├── artifacts/
│   └── web/
├── deck/
├── outputs/
├── scripts/
├── src/
│   ├── analysis/
│   ├── common/
│   └── pipeline/
├── pyproject.toml
└── README.md
```

## Folder Guides

- [Pipeline Guide](src/pipeline/README.md)
- [Analysis Guide](src/analysis/README.md)
- [Frontend Architecture](apps/web/docs/frontend_architecture.md)
- [Web App Run Guide](apps/web/README.md)
- [Scripts Guide](scripts/README.md)

## Environment Setup

This project uses Python 3.10+ and is defined by [pyproject.toml](pyproject.toml).

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e .
```

## Core Commands

Build the canonical processed dataset:

```bash
./.venv/bin/python -m src.pipeline.build_resale_analysis_dataset
```

Build Section 1 building/tableau assets:

```bash
./.venv/bin/python -m src.pipeline.build_building_tableau_assets
```

Run the end-to-end analysis workflow:

```bash
./.venv/bin/python -m src.analysis.run_all
```

Publish frontend-ready artifacts:

```bash
./.venv/bin/python -m src.pipeline.publish_web_artifacts
./.venv/bin/python -m src.pipeline.publish_dashboard3_web_artifacts
```

Validate web artifact contract:

```bash
./.venv/bin/python -m src.pipeline.validate_web_artifacts
```

Upload web assets to R2:

```bash
bash scripts/upload_web_assets_r2.sh <bucket-name>
```

Run frontend locally:

```bash
cd apps/web
npm install
npm run dev
```

## Live Deployment

Current Vercel project: `hdb-resale-market-analysis`

- Production domain: `https://hdb-resale-market-analysis.vercel.app`
- Preview domain pattern: `https://hdb-resale-market-analysis-git-<branch>-sycamore-sts-projects.vercel.app`

Required environment variables for artifact loading (especially Dashboard 3):

- `ASSET_BASE_URL`
- `NEXT_PUBLIC_ASSET_BASE_URL`
- `SECTION1_DATA_BASE_URL`

If these are missing in Preview/Development, Dashboard 3 may fall back to empty defaults (for example, missing budget/building selectors).

See [apps/web/README.md](apps/web/README.md) for local run and troubleshooting details.

## Release Flow

- Push changes to `dev` and validate Preview deployment.
- Merge `dev` into `production`.
- Verify production deployment at `https://hdb-resale-market-analysis.vercel.app`.

## Tracked Outputs vs Local Caches

Tracked in git:

- selected Section 1 export tables, diagnostics, and screenshot references
- Section 2 modeling summaries and result tables
- Section 3 policy summaries, figure tables, and selected static figures
- web content and deployable assets needed for reproducible review

Not tracked in git:

- `data/raw/` source downloads
- `data/processed/` rebuildable checkpoints and datasets
- generated `.html` and `.png` chart exports
- temporary training logs, IDE files, and local caches

## Notes

- Tableau dashboards are assembled manually in Tableau Desktop from exported Section 1 files in `outputs/section1/results/`.
- The frontend reads prepared files from `artifacts/web/` and does not depend on raw pipeline intermediates.
- Some outputs are intentionally pretracked so readers can inspect the work without rerunning the full pipeline.
