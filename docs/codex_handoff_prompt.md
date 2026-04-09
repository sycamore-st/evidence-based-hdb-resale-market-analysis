# Codex Handoff Prompt (Copy/Paste)

You are helping me on the project `evidence-based-hdb-resale-market-analysis`.

## Repo and workflow
- Repo: `evidence-based-hdb-resale-market-analysis`
- Frontend app path: `apps/web`
- Python pipeline/analysis remains under `src/`
- I use a `dev` branch for refactor and UI work; keep `main` as stable submission baseline.
- Run frontend from:
  - `cd apps/web`
  - `npm install`
  - `npm run dev`

## What has already been implemented
- A Next.js dashboard app scaffold exists in `apps/web`.
- Interactive Section 1 Dashboard 1 page exists and is functional:
  - map selection by town
  - right-side Plotly charts (stacked transactions and price trend)
  - sandbox route for layout tuning
- Current key files:
  - `apps/web/components/section1/dashboard-one-explorer.tsx`
  - `apps/web/components/section1/dashboard-one-sandbox.tsx`
  - `apps/web/lib/section1-dashboard1.ts`
  - `apps/web/lib/section1-dashboard1-sandbox.ts`
  - `apps/web/app/globals.css`

## Design and interaction preferences (important)
- Light, clean, minimal style.
- Chart bars use transparent fill + slightly darker border line.
- Hover behavior on stacked bar chart:
  - only one custom hover card (disable default Plotly hover text)
  - card shows flat-type breakdown for hovered period
  - format each row as count first, then percentage (e.g., `9,217 (41.6%)`)
  - mini-bars should keep consistent track alignment across flat types
  - tiny categories should still be visible (minimum pixel width logic)

## Current user priorities
1. Improve dashboard layout polish and usability (fast iteration in dev mode).
2. Keep frontend isolated in `apps/web` and data contract stable via `artifacts/web/*`.
3. Continue moving manual/PPT dashboard workflows to web.
4. Prioritize practical changes that are easy to tweak live.

## Data contract direction
- Frontend consumes prepared artifacts, not raw intermediates.
- Expected artifact families:
  - `artifacts/web/overview/`
  - `artifacts/web/policy/`
  - `artifacts/web/model/`
- Typical contract files:
  - `summary.json`
  - `timeseries.json` (or parquet in future)
  - `filters.json`
  - `metadata.json`

## Requested collaboration style
- Be practical and implementation-first.
- Make direct edits and verify (`npm run typecheck`) after meaningful UI/code changes.
- Keep suggestions concrete and visual.
- For layout changes, prefer editing `apps/web/app/globals.css` and explain where to tune values quickly.

## First step you should take now
1. Read current state of:
   - `apps/web/components/section1/dashboard-one-explorer.tsx`
   - `apps/web/app/globals.css`
2. Summarize the current dashboard hover-card and layout controls in 5 bullets max.
3. Ask me what visual tweak to do next, offering 3 concrete options.

