from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from src.common.config import DATA_PROCESSED, ensure_directories
from src.common.geography import build_and_save_town_centroids
from src.pipeline.features import (
    add_mrt_proximity,
    add_point_of_interest_proximity,
    merge_hdb_frames,
    parse_bus_stop_geojson,
    parse_mrt_geojson,
    parse_school_zone_geojson,
)
from src.pipeline.hdb_api import fetch_all_hdb_raw, fetch_bus_stop_dataset_dir, fetch_mrt_dataset_dir, fetch_school_zone_dataset_dir
from src.pipeline.hdb_api import fetch_planning_area_dataset_dir


def log_step(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def _stage_path(stage: str) -> Path:
    return DATA_PROCESSED / f"hdb_resale_{stage}.parquet"


def _save_stage(frame: pd.DataFrame, stage: str) -> Path:
    path = _stage_path(stage)
    frame.to_parquet(path, index=False)
    log_step(f"Saved stage checkpoint `{stage}` to {path}.")
    return path


def _load_stage(stage: str) -> pd.DataFrame:
    path = _stage_path(stage)
    if not path.exists():
        raise FileNotFoundError(f"Stage checkpoint missing: {path}")
    log_step(f"Loading stage checkpoint `{stage}` from {path}.")
    return pd.read_parquet(path)


def _merge_location_lookup(base_frame: pd.DataFrame, lookup: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    keys = ["town", "town_latitude", "town_longitude"]
    lookup_columns = keys + columns
    merged = base_frame.drop(columns=[column for column in columns if column in base_frame.columns], errors="ignore").merge(
        lookup.loc[:, [column for column in lookup_columns if column in lookup.columns]],
        on=keys,
        how="left",
    )
    return merged


def _enrich_by_town_location(
    frame: pd.DataFrame,
    *,
    kind: str,
    points: pd.DataFrame | None = None,
    mrt_stations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    unique_locations = frame[["town", "town_latitude", "town_longitude"]].drop_duplicates().reset_index(drop=True)
    unique_locations.attrs["checkpoint_path"] = str(DATA_PROCESSED)
    unique_locations.attrs["checkpoint_label"] = f"town_{kind}"
    log_step(f"Computing {kind} proximity on {len(unique_locations):,} unique town locations instead of {len(frame):,} rows.")

    if kind == "mrt":
        lookup = add_mrt_proximity(unique_locations, mrt_stations)
        return _merge_location_lookup(
            frame,
            lookup,
            ["nearest_mrt_station", "nearest_mrt_line", "nearest_mrt_distance_km"],
        )

    if kind == "bus":
        lookup = add_point_of_interest_proximity(
            unique_locations,
            points,
            label_column="bus_stop_num",
            output_label_column="nearest_bus_stop_num",
            output_distance_column="nearest_bus_stop_distance_km",
        )
        return _merge_location_lookup(frame, lookup, ["nearest_bus_stop_num", "nearest_bus_stop_distance_km"])

    if kind == "school":
        lookup = add_point_of_interest_proximity(
            unique_locations,
            points,
            label_column="school_name",
            output_label_column="nearest_school_name",
            output_distance_column="nearest_school_distance_km",
        )
        return _merge_location_lookup(frame, lookup, ["nearest_school_name", "nearest_school_distance_km"])

    raise ValueError(f"Unsupported enrichment kind: {kind}")


def _override_with_building_metrics(
    frame: pd.DataFrame,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    try:
        from src.pipeline.build_building_tableau_assets import build_building_tableau_assets
    except Exception as exc:  # pragma: no cover
        log_step(f"Skipping building-level enrichment because building pipeline helpers could not be imported: {exc}")
        return frame

    building_master_path = DATA_PROCESSED / "building_master_with_poi.parquet"
    if not building_master_path.exists() or refresh:
        log_step("Building master missing or refresh requested; running canonical building pipeline.")
        build_building_tableau_assets(
            refresh_buildings=refresh,
            refresh_planning_areas=refresh,
            refresh_mrt=refresh,
            refresh_bus=refresh,
            refresh_school=refresh,
        )
    if not building_master_path.exists():
        log_step("Building enrichment skipped because building_master_with_poi.parquet is still unavailable.")
        return frame

    log_step(f"Loading canonical building master from {building_master_path}.")
    buildings = pd.read_parquet(building_master_path)
    if buildings.empty:
        log_step("Building enrichment skipped because the canonical building master is empty.")
        return frame

    building_lookup = (
        buildings[
            [
                "town",
                "block",
                "building_key",
                "building_latitude",
                "building_longitude",
                "nearest_mrt_name",
                "nearest_mrt_distance_km",
                "nearest_bus_stop_num",
                "nearest_bus_stop_distance_km",
                "bus_stop_count_within_1km",
                "nearest_school_name",
                "nearest_school_distance_km",
                "school_count_within_1km",
                "distance_to_cbd_km",
                "building_match_status",
            ]
        ]
        .drop_duplicates(subset=["town", "block"])
        .copy()
    )
    merged = frame.merge(building_lookup, on=["town", "block"], how="left", suffixes=("", "_building"))
    exact_columns = [
        "nearest_mrt_distance_km",
        "nearest_bus_stop_num",
        "nearest_bus_stop_distance_km",
        "bus_stop_count_within_1km",
        "nearest_school_name",
        "nearest_school_distance_km",
        "school_count_within_1km",
        "distance_to_cbd_km",
    ]
    for column in exact_columns:
        building_column = f"{column}_building"
        if building_column in merged.columns:
            merged[column] = merged[building_column].where(merged[building_column].notna(), merged.get(column))
    if "nearest_mrt_name" in merged.columns:
        merged["nearest_mrt_station"] = merged["nearest_mrt_name"].where(
            merged["nearest_mrt_name"].notna(),
            merged.get("nearest_mrt_station"),
        )
    log_step(
        f"Building-level enrichment matched {int(merged['building_key'].notna().sum()):,} transaction rows on town/block."
    )
    drop_columns = [column for column in merged.columns if column.endswith("_building")] + ["nearest_mrt_name"]
    return merged.drop(columns=drop_columns, errors="ignore")


def build_resale_analysis_dataset(
    refresh: bool = False,
    *,
    refresh_hdb: bool = False,
    refresh_mrt: bool = False,
    refresh_bus: bool = False,
    refresh_school: bool = False,
    start_stage: str = "base",
) -> None:
    log_step("Ensuring project data directories exist.")
    ensure_directories()
    stage_order = ["base", "mrt", "bus", "school", "export"]
    if start_stage not in stage_order:
        raise ValueError(f"start_stage must be one of {stage_order}.")

    mrt_stations = pd.DataFrame()
    bus_stops = pd.DataFrame()
    school_zones = pd.DataFrame()

    if stage_order.index(start_stage) <= stage_order.index("base"):
        log_step("Fetching cached or upstream HDB resale datasets.")
        hdb_frames = fetch_all_hdb_raw(refresh=refresh or refresh_hdb)
        planning_area_dir = fetch_planning_area_dataset_dir(refresh=refresh)
        log_step(f"Planning-area dataset directory: {planning_area_dir}")
        town_centroids = build_and_save_town_centroids()
        log_step(f"Saved {len(town_centroids):,} town centroids to processed artifact.")
        frame_sizes = ", ".join(f"{slug}={len(frame):,}" for slug, frame in hdb_frames.items())
        log_step(f"Loaded HDB source frames: {frame_sizes}.")
        log_step("Merging and standardizing HDB resale datasets.")
        merged = merge_hdb_frames(hdb_frames)
        log_step(f"Merged frame shape: {merged.shape[0]:,} rows x {merged.shape[1]:,} columns.")
        _save_stage(merged, "base")
    else:
        merged = _load_stage("base")

    if stage_order.index(start_stage) <= stage_order.index("mrt"):
        log_step("Fetching MRT open dataset.")
        mrt_dir = fetch_mrt_dataset_dir(refresh=refresh or refresh_mrt)
        log_step(f"MRT dataset directory: {mrt_dir}")
        mrt_stations = parse_mrt_geojson(mrt_dir)
        log_step(f"Parsed {len(mrt_stations):,} MRT records.")
        merged = _enrich_by_town_location(merged, kind="mrt", mrt_stations=mrt_stations)
        log_step("Completed MRT proximity enrichment.")
        _save_stage(merged, "with_mrt")
    else:
        merged = _load_stage("with_mrt")
        mrt_stations_path = DATA_PROCESSED / "mrt_stations.csv"
        if mrt_stations_path.exists():
            mrt_stations = pd.read_csv(mrt_stations_path)

    if stage_order.index(start_stage) <= stage_order.index("bus"):
        log_step("Fetching bus stop open dataset.")
        bus_stop_dir = fetch_bus_stop_dataset_dir(refresh=refresh or refresh_bus)
        log_step(f"Bus stop dataset directory: {bus_stop_dir}")
        bus_stops = parse_bus_stop_geojson(bus_stop_dir)
        log_step(f"Parsed {len(bus_stops):,} bus stop records.")
        merged = _enrich_by_town_location(merged, kind="bus", points=bus_stops)
        log_step("Completed bus stop proximity enrichment.")
        _save_stage(merged, "with_bus")
    else:
        merged = _load_stage("with_bus")
        bus_stops_path = DATA_PROCESSED / "bus_stops.csv"
        if bus_stops_path.exists():
            bus_stops = pd.read_csv(bus_stops_path)

    if stage_order.index(start_stage) <= stage_order.index("school"):
        log_step("Fetching school zone open dataset.")
        school_zone_dir = fetch_school_zone_dataset_dir(refresh=refresh or refresh_school)
        log_step(f"School zone dataset directory: {school_zone_dir}")
        school_zones = parse_school_zone_geojson(school_zone_dir)
        log_step(f"Parsed {len(school_zones):,} school zone records.")
        merged = _enrich_by_town_location(merged, kind="school", points=school_zones)
        merged = _override_with_building_metrics(merged, refresh=refresh)
        log_step("Completed school proximity enrichment.")
        _save_stage(merged, "with_school")
    else:
        merged = _load_stage("with_school")
        school_zones_path = DATA_PROCESSED / "school_zones.csv"
        if school_zones_path.exists():
            school_zones = pd.read_csv(school_zones_path)

    parquet_path = DATA_PROCESSED / "hdb_resale_processed.parquet"
    csv_path = DATA_PROCESSED / "hdb_resale_processed.csv"
    log_step(f"Writing processed parquet to {parquet_path}.")
    merged.to_parquet(parquet_path, index=False)
    log_step(f"Writing processed CSV to {csv_path}.")
    merged.to_csv(csv_path, index=False)

    stations_path = DATA_PROCESSED / "mrt_stations.csv"
    log_step(f"Writing MRT lookup CSV to {stations_path}.")
    mrt_stations.to_csv(stations_path, index=False)
    bus_stop_path = DATA_PROCESSED / "bus_stops.csv"
    log_step(f"Writing bus stop lookup CSV to {bus_stop_path}.")
    bus_stops.to_csv(bus_stop_path, index=False)
    school_zone_path = DATA_PROCESSED / "school_zones.csv"
    log_step(f"Writing school zone lookup CSV to {school_zone_path}.")
    school_zones.to_csv(school_zone_path, index=False)
    log_step("Resale analysis dataset build complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the general processed HDB resale dataset used by Section 2, Section 3, and overall analytics."
    )
    parser.add_argument("--refresh", action="store_true", help="Re-download upstream sources even if cached.")
    parser.add_argument(
        "--start-stage",
        choices=["base", "mrt", "bus", "school", "export"],
        default="base",
        help="Resume from a saved processing stage instead of rebuilding from scratch.",
    )
    parser.add_argument("--refresh-hdb", action="store_true", help="Refresh only the HDB raw sources.")
    parser.add_argument("--refresh-mrt", action="store_true", help="Refresh only the MRT open dataset.")
    parser.add_argument("--refresh-bus", action="store_true", help="Refresh only the bus stop open dataset.")
    parser.add_argument("--refresh-school", action="store_true", help="Refresh only the school zone open dataset.")
    args = parser.parse_args()
    build_resale_analysis_dataset(
        refresh=args.refresh,
        refresh_hdb=args.refresh_hdb,
        refresh_mrt=args.refresh_mrt,
        refresh_bus=args.refresh_bus,
        refresh_school=args.refresh_school,
        start_stage=args.start_stage,
    )


if __name__ == "__main__":
    main()
