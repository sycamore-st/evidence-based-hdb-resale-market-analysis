# Web App Run Guide

This app hosts the interactive dashboard frontend for the HDB resale market analysis project.

## Prerequisites

- Node.js and npm installed locally
- Published frontend artifacts available under `artifacts/web/`

If you need to refresh the frontend data contract first, run from the repo root:

```bash
./.venv/bin/python -m src.pipeline.publish_web_artifacts
```

For Dashboard 3's heavier town-sharded payloads, publish the split JSON artifacts with:

```bash
./.venv/bin/python -m src.pipeline.publish_dashboard3_web_artifacts
```

## Run The App

From the repo root:

```bash
cd apps/web
npm install
npm run dev
```

Or use the absolute path from anywhere in your terminal:

```bash
cd /Users/claire/PycharmProjects/evidence-based-hdb-resale-market-analysis/apps/web
npm install
npm run dev
```

The local development server will start at:

- `http://localhost:3000`

## Useful Routes

- Home: `http://localhost:3000/`
- Dashboard 1: `http://localhost:3000/section1/dashboard-1`
- Dashboard 2: `http://localhost:3000/section1/dashboard-2`
- Dashboard 3: `http://localhost:3000/section1/dashboard-3`

Dashboard 1 layout presets can be switched with query params:

- `http://localhost:3000/section1/dashboard-1?layout=editorial`
- `http://localhost:3000/section1/dashboard-1?layout=balanced`
- `http://localhost:3000/section1/dashboard-1?layout=chart-heavy`

## Verification

Run a type check after meaningful frontend changes:

```bash
npm run typecheck
```

## Troubleshooting

If `cd apps/web` says `no such file or directory`, you are not in the repo root. Either:

```bash
cd /Users/claire/PycharmProjects/evidence-based-hdb-resale-market-analysis/apps/web
```

or first return to the repo root and then change into `apps/web`.

If `npm install` or `npm run dev` prints `env: node: No such file or directory`, Node.js is not installed or is not available on your shell `PATH`.

Check whether Node is available:

```bash
node -v
npm -v
```

Install Node.js if needed, for example with Homebrew:

```bash
brew install node
```

If you use `nvm`, you can instead run:

```bash
nvm install --lts
nvm use --lts
```

Then retry:

```bash
cd /Users/claire/PycharmProjects/evidence-based-hdb-resale-market-analysis/apps/web
npm install
npm run dev
```

## Notes

- The frontend is isolated in `apps/web`.
- The app reads prepared files from `artifacts/web/` rather than raw pipeline outputs.
- For local UI iteration, `apps/web/app/globals.css` is the fastest place to tune layout and visual tokens.
