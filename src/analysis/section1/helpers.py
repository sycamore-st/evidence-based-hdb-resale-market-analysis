from __future__ import annotations

import re

import pandas as pd

from src.common.config import (
    DATA_PROCESSED,
    HDB_BUILDING_DATASET_ID,
    SECTION1_OUTPUT_DIAGNOSTICS,
    SECTION1_OUTPUT_FINAL,
    SECTION1_OUTPUT_RESULTS,
)
from src.common.geography import load_planning_area_geojson_payload as load_raw_planning_area_geojson_payload
from src.pipeline.features import parse_bus_stop_geojson, parse_mrt_geojson, parse_school_zone_geojson

SECTION1_RESULTS = SECTION1_OUTPUT_RESULTS
SECTION1_FINAL = SECTION1_OUTPUT_FINAL
SECTION1_DIAGNOSTICS = SECTION1_OUTPUT_DIAGNOSTICS

TABLEAU_EXPORT_LABELS = {
    "transaction_year": "Transaction Year",
    "town": "Town",
    "flat_type": "Flat Type",
    "transactions": "Transactions",
    "median_price": "Median Price",
    "median_price_per_sqm": "Median Price Per Sqm",
    "median_price_per_sqft": "Price Per Sqft",
    "price_per_sqm_value": "Price Per Sqm",
    "median_floor_area": "Median Floor Area",
    "median_flat_age": "Median Flat Age",
    "town_latitude": "Town Latitude",
    "town_longitude": "Town Longitude",
    "distance_to_cbd_km": "Distance To Cbd Km",
    "nearest_mrt_distance_km": "Nearest Mrt Distance Km",
    "nearest_mrt_station": "Nearest Mrt Station",
    "nearest_mrt_line": "Nearest Mrt Line",
    "nearest_bus_stop_num": "Nearest Bus Stop",
    "nearest_bus_stop_distance_km": "Nearest Bus Stop Distance Km",
    "nearest_school_name": "Nearest School",
    "nearest_school_distance_km": "Nearest School Distance Km",
    "overall_location_score": "Overall Location Score",
    "planning_area_name": "Planning Area Group",
    "planning_area_name_single": "Planning Area",
    "planning_area_match_status": "Region Match Status",
    "map_region_key": "Region Key",
    "map_label": "Region Label",
    "map_region_type": "Region Type",
    "is_national": "Is National",
    "is_all_flat_type": "Is All Flat Type",
    "town_scope": "Town Scope",
    "flat_type_scope": "Flat Type Scope",
    "budget": "Budget",
    "budget_slack": "Budget Slack",
    "metric": "Metric",
    "price_value": "Price",
    "floor_area_value": "Floor Area",
    "flat_age_value": "Flat Age",
    "size_score": "Size Score",
    "value_score": "Value Score",
    "commute_score": "Commute Score",
    "mrt_access_score": "Mrt Access Score",
    "bus_stop_access_score": "Bus Stop Access Score",
    "school_access_score": "School Access Score",
    "poi_type": "Poi Type",
    "poi_name": "Poi Name",
    "poi_latitude": "Poi Latitude",
    "poi_longitude": "Poi Longitude",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "distance_to_town_km": "Distance To Town Km",
    "distance_to_building_km": "Distance To Building Km",
    "poi_count": "Poi Count",
    "nearest_distance_km": "Nearest Distance Km",
    "median_distance_km": "Median Distance Km",
    "building_key": "Building Key",
    "block": "Block",
    "postal_code": "Postal Code",
    "building_latitude": "Building Latitude",
    "building_longitude": "Building Longitude",
    "nearest_mrt_name": "Nearest Mrt Name",
    "bus_stop_count_within_1km": "Bus Stop Count Within 1Km",
    "school_count_within_1km": "School Count Within 1Km",
    "building_match_status": "Building Match Status",
    "has_transaction_data": "Has Transaction Data",
    "has_building_geometry": "Has Building Geometry",
    "town_shape_key": "Town Shape Key",
    "town_indicator_svg": "Town Indicator Svg",
    "town_indicator_svg_path": "Town Indicator Svg Path",
    "town_indicator_png": "Town Indicator Png",
    "town_indicator_png_path": "Town Indicator Png Path",
    "legend_panel": "Legend Panel",
    "legend_value": "Legend Value",
    "legend_note": "Legend Note",
}


def ensure_section1_results_dir() -> None:
    SECTION1_RESULTS.mkdir(parents=True, exist_ok=True)
    SECTION1_FINAL.mkdir(parents=True, exist_ok=True)
    SECTION1_DIAGNOSTICS.mkdir(parents=True, exist_ok=True)


def section1_output_path(filename: str, *, kind: str = "final"):
    if kind == "final":
        return SECTION1_FINAL / filename
    if kind == "diagnostic":
        return SECTION1_DIAGNOSTICS / filename
    raise ValueError(f"Unknown Section 1 output kind: {kind}")


def write_section1_csv(df: pd.DataFrame, filename: str, *, kind: str = "final") -> None:
    labeled = label_for_tableau(df)
    labeled.to_csv(section1_output_path(filename, kind=kind), index=False)


def mirror_section1_file(filename: str, *, kind: str = "final") -> None:
    source = SECTION1_RESULTS / filename
    if not source.exists():
        return
    target = section1_output_path(filename, kind=kind)
    target.write_bytes(source.read_bytes())


def label_for_tableau(df: pd.DataFrame) -> pd.DataFrame:
    labeled = df.copy()
    if "town" in labeled.columns and "town_shape_key" not in labeled.columns:
        labeled["town_shape_key"] = (
            labeled["town"]
            .astype("string")
            .fillna("")
            .str.lower()
            .str.replace(r"[^a-z0-9]+", "_", regex=True)
            .str.strip("_")
        )
        labeled.loc[labeled["town"].isna(), "town_shape_key"] = pd.NA
    return labeled.rename(columns={column: TABLEAU_EXPORT_LABELS.get(column, column) for column in labeled.columns})


def normalize_tableau_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    if "flat_type" in normalized.columns:
        normalized["flat_type"] = (
            normalized["flat_type"].astype("string").str.replace("MULTI GENERATION", "MULTI-GENERATION", regex=False)
        )
    return normalized


def load_processed_frame() -> pd.DataFrame:
    return normalize_tableau_frame(pd.read_parquet(DATA_PROCESSED / "hdb_resale_processed.parquet"))


def load_planning_area_geojson_payload() -> dict | None:
    try:
        return load_raw_planning_area_geojson_payload()
    except FileNotFoundError:
        return None


def load_poi_sources() -> dict[str, pd.DataFrame | None]:
    mrt_points = pd.read_csv(DATA_PROCESSED / "mrt_stations.csv") if (DATA_PROCESSED / "mrt_stations.csv").exists() else None
    bus_stop_points = pd.read_csv(DATA_PROCESSED / "bus_stops.csv") if (DATA_PROCESSED / "bus_stops.csv").exists() else None
    school_points = pd.read_csv(DATA_PROCESSED / "school_zones.csv") if (DATA_PROCESSED / "school_zones.csv").exists() else None
    if mrt_points is None:
        mrt_dir = DATA_RAW / "d_210d2b691cec8a10dcdbd35c7ce26efd" / "extracted"
        if mrt_dir.exists():
            mrt_points = parse_mrt_geojson(mrt_dir)
    if bus_stop_points is None:
        bus_dir = DATA_RAW / "d_3f172c6feb3f4f92a2f47d93eed2908a" / "extracted"
        if bus_dir.exists():
            bus_stop_points = parse_bus_stop_geojson(bus_dir)
    if school_points is None:
        school_dir = DATA_RAW / "d_abf023b38d9bc451484e3d67b562bc5c" / "extracted"
        if school_dir.exists():
            school_points = parse_school_zone_geojson(school_dir)
    return {"mrt": mrt_points, "bus": bus_stop_points, "school": school_points}


def load_building_geojson_path():
    return DATA_RAW / HDB_BUILDING_DATASET_ID / "extracted" / "dataset.geojson"
