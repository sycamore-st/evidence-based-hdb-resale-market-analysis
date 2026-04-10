# Frontend Architecture

The repository now treats the dashboard UI as a separate monorepo app under `apps/web/`.

## Principles

- Python code under `src/` owns ingestion, cleaning, modeling, and artifact publishing.
- The web app owns presentation and user interaction only.
- The contract between the two sides is the published JSON payloads in `artifacts/web/`.

## Frontend Layout

```text
apps/web/
├── app/
│   ├── (dashboard)/
│   │   ├── model/
│   │   ├── overview/
│   │   └── policy/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── charts/
│   ├── layout/
│   └── ui/
└── lib/
```

## Artifact Contract

Each dashboard section has four files:

- `summary.json`
- `timeseries.json`
- `filters.json`
- `metadata.json`

Each payload includes:

- `dataset_version`
- `generated_at`
- `source_coverage_end`

The frontend loads only from these published files and should not read from `outputs/` or `data/processed/` directly.

## Commands

Publish artifacts:

```bash
./.venv/bin/python -m src.pipeline.publish_web_artifacts
```

Validate artifacts:

```bash
./.venv/bin/python -m src.pipeline.validate_web_artifacts
```

Run the frontend:

```bash
cd apps/web
npm install
npm run dev
```
