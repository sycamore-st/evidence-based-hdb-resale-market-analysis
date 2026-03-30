# Pipeline Guide

This folder contains the data-ingestion and feature-engineering code that prepares the reusable transaction dataset and the building-level Tableau assets.

## Canonical Entry Points

Run the general processed dataset build:

```bash
./.venv/bin/python -m src.pipeline.build_resale_analysis_dataset
```

Run the building-centric Section 1 asset build:

```bash
./.venv/bin/python -m src.pipeline.build_building_tableau_assets
```

Use `build_resale_analysis_dataset.py` when you need the main processed resale dataset for Section 2, Section 3, or the full-project run.

Use `build_building_tableau_assets.py` when you need the building geometry, POI, and optimizer exports used by the Tableau workflow.

## Files And Responsibilities

- `build_resale_analysis_dataset.py`: main transaction pipeline; fetches HDB resale data, adds MRT/bus/school proximity, and writes the processed dataset
- `build_building_tableau_assets.py`: main building pipeline; prepares planning-area geometry, building-level POI metrics, matching outputs, and Dashboard 3 extracts
- `ingest_sources.py`: fetches raw source tables and geospatial inputs used by the building pipeline
- `hdb_api.py`: low-level data.gov.sg and HDB dataset download helpers
- `features.py`: transaction cleaning, merging, and location-enrichment utilities
- `map_entities.py`: town, planning-area, and building mapping logic
- `calculate_building_poi.py`: building-level POI aggregation helpers used by the building pipeline
- `pipeline_common.py`: shared pipeline logging, checkpoint, and path helpers

## Main Inputs

- public HDB resale transaction datasets
- public MRT, bus stop, school-zone, planning-area, and building geometry datasets
- cached local raw downloads under `data/raw/`

## Main Outputs

- `data/processed/hdb_resale_processed.parquet`
- `data/processed/hdb_resale_processed.csv`
- `outputs/section1/results/final/building_geometry_lookup.csv`
- `outputs/section1/results/final/building_optimizer.csv`
- `outputs/section1/results/final/building_poi_points.csv`
- `outputs/section1/results/final/hdb_existing_buildings.geojson`
- `outputs/section1/results/diagnostics/building_optimizer_raw.csv`
- `outputs/section1/results/diagnostics/building_transaction_match_summary.csv`

## Practical Run Order

1. Run `build_resale_analysis_dataset.py` to create the canonical processed dataset.
2. Run `build_building_tableau_assets.py` to create Section 1 building assets.
3. Run `src.analysis.run_all` if you want the full analysis stack after the processed dataset exists.
