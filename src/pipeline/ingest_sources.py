from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis.section1.dashboard_3 import parse_hdb_building_geojson
from src.common.config import DATA_PROCESSED
from src.pipeline.features import merge_hdb_frames, parse_bus_stop_geojson, parse_mrt_geojson, parse_school_zone_geojson
from src.pipeline.hdb_api import (
    fetch_all_hdb_raw,
    fetch_bus_stop_dataset_dir,
    fetch_hdb_building_dataset_dir,
    fetch_mrt_dataset_dir,
    fetch_planning_area_dataset_dir,
    fetch_school_zone_dataset_dir,
)
from src.pipeline.pipeline_common import log_step, save_stage


def fetch_transactions_base(refresh: bool = False) -> pd.DataFrame:
    log_step("Fetching HDB transaction sources.")
    hdb_frames = fetch_all_hdb_raw(refresh=refresh)
    frame_sizes = ", ".join(f"{slug}={len(frame):,}" for slug, frame in hdb_frames.items())
    log_step(f"Loaded HDB transaction source frames: {frame_sizes}.")
    merged = merge_hdb_frames(hdb_frames)
    log_step(f"Merged transaction base shape: {merged.shape[0]:,} rows x {merged.shape[1]:,} columns.")
    save_stage(merged, "transactions_base")
    return merged


def fetch_building_geometry(refresh: bool = False) -> tuple[dict, pd.DataFrame, Path]:
    log_step("Fetching HDB building geometry.")
    building_dir = fetch_hdb_building_dataset_dir(refresh=refresh)
    building_geojson = building_dir / "dataset.geojson"
    payload, buildings = parse_hdb_building_geojson(building_geojson)
    log_step(f"Loaded {len(buildings):,} existing HDB buildings.")
    return payload, buildings, building_geojson


def fetch_planning_area_geometry(refresh: bool = False) -> Path:
    log_step("Fetching planning area geometry.")
    planning_dir = fetch_planning_area_dataset_dir(refresh=refresh)
    planning_geojson = planning_dir / "dataset.geojson"
    log_step(f"Planning area geometry path: {planning_geojson}")
    return planning_geojson


def fetch_poi_sources(refresh_mrt: bool = False, refresh_bus: bool = False, refresh_school: bool = False) -> dict[str, pd.DataFrame]:
    log_step("Fetching POI source datasets.")
    mrt = parse_mrt_geojson(fetch_mrt_dataset_dir(refresh=refresh_mrt))
    bus = parse_bus_stop_geojson(fetch_bus_stop_dataset_dir(refresh=refresh_bus))
    school = parse_school_zone_geojson(fetch_school_zone_dataset_dir(refresh=refresh_school))
    log_step(f"Loaded {len(mrt):,} MRT records, {len(bus):,} bus stops, and {len(school):,} school records.")
    mrt.to_csv(DATA_PROCESSED / "mrt_stations.csv", index=False)
    bus.to_csv(DATA_PROCESSED / "bus_stops.csv", index=False)
    school.to_csv(DATA_PROCESSED / "school_zones.csv", index=False)
    return {"mrt": mrt, "bus": bus, "school": school}
