from __future__ import annotations

import pandas as pd

from src.analysis.section1.dashboard_3 import (
    build_building_poi_points_extract,
    enrich_buildings_with_poi_metrics,
)
from src.pipeline.pipeline_common import log_step, save_stage


def compute_building_poi_metrics(
    buildings: pd.DataFrame,
    *,
    mrt_points: pd.DataFrame | None,
    bus_stop_points: pd.DataFrame | None,
    school_points: pd.DataFrame | None,
) -> pd.DataFrame:
    log_step("Computing building-level POI metrics from exact building latitude/longitude.")
    enriched = enrich_buildings_with_poi_metrics(buildings, mrt_points, bus_stop_points, school_points)
    save_stage(enriched, "building_master_with_poi")
    return enriched


def build_building_poi_summary(buildings: pd.DataFrame) -> pd.DataFrame:
    summary = (
        buildings.groupby("town", dropna=False)
        .agg(
            buildings=("building_key", "nunique"),
            median_mrt_distance_km=("nearest_mrt_distance_km", "median"),
            median_bus_stop_distance_km=("nearest_bus_stop_distance_km", "median"),
            median_school_distance_km=("nearest_school_distance_km", "median"),
            median_bus_stop_count_within_1km=("bus_stop_count_within_1km", "median"),
            median_school_count_within_1km=("school_count_within_1km", "median"),
        )
        .reset_index()
        .sort_values("town")
        .reset_index(drop=True)
    )
    save_stage(summary, "building_poi_summary")
    return summary


def build_building_poi_points(
    buildings: pd.DataFrame,
    *,
    mrt_points: pd.DataFrame | None,
    bus_stop_points: pd.DataFrame | None,
    school_points: pd.DataFrame | None,
    within_km: float = 1.0,
) -> pd.DataFrame:
    log_step("Building building POI point export rows.")
    return build_building_poi_points_extract(
        buildings,
        mrt_points,
        bus_stop_points,
        school_points,
        within_km=within_km,
    )
