# Scripts Guide

This folder contains shell helpers for uploading prepared web artifacts to Cloudflare R2.

## Prerequisites

- Node.js and npm installed
- Wrangler CLI available via `npx wrangler`
- Cloudflare authentication configured (`npx wrangler login`)
- Existing R2 bucket name

## Script

- `upload_web_assets_r2.sh <bucket-name>`
  - Uploads:
    - `artifacts/web/**`
    - `outputs/section2/charts/**`
    - `outputs/section2/results/**`
    - `outputs/section3/charts/**`

## Usage

From repo root:

```bash
bash scripts/upload_web_assets_r2.sh <bucket-name>
```

Example:

```bash
bash scripts/upload_web_assets_r2.sh hdb-resale-assets
```

## Notes

- Both scripts preserve repository-relative paths in the bucket key.
- Run artifact publish steps before upload, for example:
  - `./.venv/bin/python -m src.pipeline.publish_web_artifacts`
  - `./.venv/bin/python -m src.pipeline.publish_dashboard3_web_artifacts`
