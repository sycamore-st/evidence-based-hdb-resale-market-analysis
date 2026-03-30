# Section 1 Dashboards

This note explains what each dashboard is meant to answer and which tracked outputs feed it.

## Dashboard 1: Market Overview

Question:
- how transaction activity and median prices vary across towns and years

Primary export code:
- `src.analysis.section1.dashboard_1`

Main tracked files:
- `outputs/section1/results/final/dashboard_market_overview.csv`
- `outputs/section1/results/final/overview_transactions.csv`
- `outputs/section1/results/final/planning_area_map_metrics.csv`
- `outputs/section1/results/final/planning_area_map_metrics_by_year.csv`
- `outputs/section1/results/final/town_indicator_assets.csv`

Representative screenshots:
- `outputs/section1/screenshot/Dashboard 1 Country View.png`
- `outputs/section1/screenshot/Dashboard 1 Town View.png`

## Dashboard 2: Budget To Space

Question:
- which town and flat-type combinations typically offer more floor area within a given budget

Primary export code:
- `src.analysis.section1.dashboard_2`

Main tracked files:
- `outputs/section1/results/final/budget_affordability.csv`
- `outputs/section1/results/final/budget_affordability_metrics.csv`
- `outputs/section1/results/final/budget_affordability_legend.csv`

Representative screenshot:
- `outputs/section1/screenshot/Dashboard 2.png`

## Dashboard 3: Location Optimizer

Question:
- which buildings and towns balance budget, space, and access to MRT, bus stops, schools, and the CBD

Primary export code:
- `src.analysis.section1.dashboard_3`
- `src.pipeline.build_building_tableau_assets`

Main tracked files:
- `outputs/section1/results/final/building_optimizer.csv`
- `outputs/section1/results/final/building_geometry_lookup.csv`
- `outputs/section1/results/final/building_poi_points.csv`
- `outputs/section1/results/final/hdb_existing_buildings.geojson`
- `outputs/section1/results/final/location_quality.csv`
- `outputs/section1/results/final/location_poi_summary.csv`
- `outputs/section1/results/final/location_poi_points.csv`

Supporting diagnostics:
- `outputs/section1/results/diagnostics/building_optimizer_raw.csv`
- `outputs/section1/results/diagnostics/building_transaction_match_summary.csv`
- `outputs/section1/results/diagnostics/field_dictionary.csv`
- `outputs/section1/results/diagnostics/dashboard_spec.md`

Representative screenshot:
- `outputs/section1/screenshot/Dashboard 3.png`

## Tableau Note

The Python code exports the tables and GeoJSON files. Final interactive dashboards are still assembled manually in Tableau Desktop.
