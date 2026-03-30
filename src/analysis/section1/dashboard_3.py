from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
from pathlib import Path

import pandas as pd
try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - fallback for minimal environments
    def tqdm(iterable=None, *args, **kwargs):
        return iterable

from src.common.geography import load_town_centroids
from src.common.utils import haversine_km
from src.analysis.section1.helpers import (
    ensure_section1_results_dir,
    load_building_geojson_path,
    load_poi_sources,
    load_processed_frame,
    section1_output_path,
    write_section1_csv,
)

LOCATION_POI_POINT_EXPORT_COLUMNS = [
    "town",
    "poi_type",
    "poi_name",
    "poi_latitude",
    "poi_longitude",
    "distance_to_town_km",
    "town_latitude",
    "town_longitude",
]

BUILDING_POI_POINT_EXPORT_COLUMNS = [
    "building_key",
    "town",
    "block",
    "postal_code",
    "poi_type",
    "poi_name",
    "latitude",
    "longitude",
    "distance_to_building_km",
]

LOCATION_POI_SUMMARY_EXPORT_COLUMNS = [
    "town",
    "poi_type",
    "poi_count",
    "nearest_distance_km",
    "median_distance_km",
]

BUILDING_GEOMETRY_EXPORT_COLUMNS = [
    "building_key",
    "town",
    "block",
    "postal_code",
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

BUILDING_OPTIMIZER_EXPORT_COLUMNS = [
    "transaction_year",
    "town",
    "block",
    "flat_type",
    "building_key",
    "postal_code",
    "building_latitude",
    "building_longitude",
    "transactions",
    "median_price",
    "median_floor_area",
    "median_price_per_sqm",
    "median_flat_age",
    "budget",
    "budget_slack",
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
    "has_transaction_data",
    "has_building_geometry",
]

BUILDING_MATCH_SUMMARY_EXPORT_COLUMNS = [
    "total_transaction_groups",
    "matched_transaction_groups",
    "unmatched_transaction_groups",
    "transaction_match_rate",
]


def build_location_extract(frame: pd.DataFrame) -> pd.DataFrame:
    for column in [
        "nearest_bus_stop_num",
        "nearest_bus_stop_distance_km",
        "nearest_school_name",
        "nearest_school_distance_km",
    ]:
        if column not in frame.columns:
            frame[column] = pd.NA
    grouped = (
        frame.groupby(
            [
                "transaction_year",
                "town",
                "flat_type",
                "nearest_mrt_station",
                "nearest_mrt_line",
                "nearest_bus_stop_num",
                "nearest_school_name",
            ],
            dropna=False,
        )
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_floor_area=("floor_area_sqm", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            town_latitude=("town_latitude", "median"),
            town_longitude=("town_longitude", "median"),
            distance_to_cbd_km=("distance_to_cbd_km", "median"),
            nearest_mrt_distance_km=("nearest_mrt_distance_km", "median"),
            nearest_bus_stop_distance_km=("nearest_bus_stop_distance_km", "median"),
            nearest_school_distance_km=("nearest_school_distance_km", "median"),
            median_flat_age=("flat_age", "median"),
        )
        .reset_index()
    )
    cbd_fallback = grouped["distance_to_cbd_km"].dropna().median()
    mrt_fallback = grouped["nearest_mrt_distance_km"].dropna().median()
    bus_fallback = grouped["nearest_bus_stop_distance_km"].dropna().median()
    school_fallback = grouped["nearest_school_distance_km"].dropna().median()
    if pd.isna(cbd_fallback):
        cbd_fallback = 0.0
    if pd.isna(mrt_fallback):
        mrt_fallback = 0.0
    if pd.isna(bus_fallback):
        bus_fallback = 0.0
    if pd.isna(school_fallback):
        school_fallback = 0.0
    grouped["value_score"] = grouped["median_floor_area"] / grouped["median_price"] * 100_000
    grouped["commute_score"] = 1 / (1 + grouped["distance_to_cbd_km"].fillna(cbd_fallback))
    grouped["mrt_access_score"] = 1 / (1 + grouped["nearest_mrt_distance_km"].fillna(mrt_fallback))
    grouped["bus_stop_access_score"] = 1 / (1 + grouped["nearest_bus_stop_distance_km"].fillna(bus_fallback))
    grouped["school_access_score"] = 1 / (1 + grouped["nearest_school_distance_km"].fillna(school_fallback))
    grouped["overall_location_score"] = (
        0.35 * grouped["value_score"].rank(pct=True)
        + 0.20 * grouped["commute_score"].rank(pct=True)
        + 0.20 * grouped["mrt_access_score"].rank(pct=True)
        + 0.15 * grouped["bus_stop_access_score"].rank(pct=True)
        + 0.10 * grouped["school_access_score"].rank(pct=True)
    )

    budget_rows = []
    for budget in [300_000, 400_000, 500_000, 600_000, 700_000, 800_000, 1_000_000]:
        eligible = grouped[grouped["median_price"] <= budget].copy()
        eligible["budget"] = budget
        eligible["budget_slack"] = budget - eligible["median_price"]
        budget_rows.append(eligible)
    return pd.concat(budget_rows, ignore_index=True).sort_values(
        ["transaction_year", "budget", "overall_location_score"],
        ascending=[False, True, False],
    )


def build_location_poi_points_extract(
    mrt_points: pd.DataFrame | None,
    bus_stop_points: pd.DataFrame | None,
    school_points: pd.DataFrame | None,
    *,
    max_distance_km: float = 3.5,
) -> pd.DataFrame:
    point_frames: list[pd.DataFrame] = []

    def prepare_points(points: pd.DataFrame | None, *, poi_type: str, name_column: str) -> None:
        if points is None or points.empty:
            return
        active = points.dropna(subset=["latitude", "longitude"]).copy()
        if active.empty:
            return
        active = active.rename(
            columns={
                name_column: "poi_name",
                "latitude": "poi_latitude",
                "longitude": "poi_longitude",
            }
        )
        active["poi_type"] = poi_type
        point_frames.append(active[["poi_type", "poi_name", "poi_latitude", "poi_longitude"]])

    prepare_points(mrt_points, poi_type="MRT", name_column="station_name")
    prepare_points(bus_stop_points, poi_type="Bus Stop", name_column="bus_stop_num")
    prepare_points(school_points, poi_type="School", name_column="school_name")

    if not point_frames:
        return pd.DataFrame(columns=LOCATION_POI_POINT_EXPORT_COLUMNS)

    poi_points = pd.concat(point_frames, ignore_index=True).dropna(subset=["poi_name"]).drop_duplicates()
    town_records = [
        {"town": town, "town_latitude": coords[0], "town_longitude": coords[1]}
        for town, coords in load_town_centroids().items()
    ]
    assigned_records: list[dict[str, object]] = []
    for point in poi_points.to_dict("records"):
        best_town = None
        best_distance = float("inf")
        for town in town_records:
            distance = haversine_km(
                town["town_latitude"],
                town["town_longitude"],
                point["poi_latitude"],
                point["poi_longitude"],
            )
            if distance < best_distance:
                best_distance = distance
                best_town = town
        if best_town is None or best_distance > max_distance_km:
            continue
        assigned_records.append(
            {
                "town": best_town["town"],
                "poi_type": point["poi_type"],
                "poi_name": point["poi_name"],
                "poi_latitude": point["poi_latitude"],
                "poi_longitude": point["poi_longitude"],
                "distance_to_town_km": best_distance,
                "town_latitude": best_town["town_latitude"],
                "town_longitude": best_town["town_longitude"],
            }
        )
    if not assigned_records:
        return pd.DataFrame(columns=LOCATION_POI_POINT_EXPORT_COLUMNS)
    assigned = pd.DataFrame(assigned_records)
    return assigned.sort_values(["town", "poi_type", "distance_to_town_km", "poi_name"]).reset_index(drop=True)


def build_location_poi_summary_extract(points: pd.DataFrame) -> pd.DataFrame:
    if points.empty:
        return pd.DataFrame(columns=LOCATION_POI_SUMMARY_EXPORT_COLUMNS)
    return (
        points.groupby(["town", "poi_type"], dropna=False)
        .agg(
            poi_count=("poi_name", "nunique"),
            nearest_distance_km=("distance_to_town_km", "min"),
            median_distance_km=("distance_to_town_km", "median"),
        )
        .reset_index()
        .sort_values(["town", "poi_type"])
        .reset_index(drop=True)
    )


_BUILDING_POI_POINT_SOURCES: list[tuple[str, list[dict[str, object]], str]] = []


def _init_building_poi_pool(point_sources: list[tuple[str, list[dict[str, object]], str]]) -> None:
    global _BUILDING_POI_POINT_SOURCES
    _BUILDING_POI_POINT_SOURCES = point_sources


def _build_building_poi_rows_for_chunk(building_rows: list[dict[str, object]], within_km: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for building in building_rows:
        building_key = building.get("building_key")
        building_lat = building.get("building_latitude")
        building_lon = building.get("building_longitude")
        if not building_key or pd.isna(building_lat) or pd.isna(building_lon):
            continue

        base = {
            "building_key": building_key,
            "town": building.get("town"),
            "block": building.get("block"),
            "postal_code": building.get("postal_code"),
        }
        rows.append(
            {
                **base,
                "poi_type": "HDB",
                "poi_name": building.get("block") or building_key,
                "latitude": building_lat,
                "longitude": building_lon,
                "distance_to_building_km": 0.0,
            }
        )

        for poi_type, points, name_column in _BUILDING_POI_POINT_SOURCES:
            for point in points:
                poi_lat = point.get("latitude")
                poi_lon = point.get("longitude")
                if pd.isna(poi_lat) or pd.isna(poi_lon):
                    continue
                distance = haversine_km(building_lat, building_lon, poi_lat, poi_lon)
                if distance > within_km:
                    continue
                rows.append(
                    {
                        **base,
                        "poi_type": poi_type,
                        "poi_name": point.get(name_column),
                        "latitude": poi_lat,
                        "longitude": poi_lon,
                        "distance_to_building_km": distance,
                    }
                )
    return rows


def _build_building_poi_rows_for_chunk_star(args: tuple[list[dict[str, object]], float]) -> list[dict[str, object]]:
    return _build_building_poi_rows_for_chunk(*args)


def build_building_poi_points_extract(
    buildings: pd.DataFrame,
    mrt_points: pd.DataFrame | None,
    bus_stop_points: pd.DataFrame | None,
    school_points: pd.DataFrame | None,
    *,
    within_km: float = 1.0,
) -> pd.DataFrame:
    if buildings is None or buildings.empty:
        return pd.DataFrame(columns=BUILDING_POI_POINT_EXPORT_COLUMNS)

    point_sources = []
    for poi_type, points, name_column in [
        ("MRT", mrt_points, "station_name"),
        ("Bus Stop", bus_stop_points, "bus_stop_num"),
        ("School", school_points, "school_name"),
    ]:
        if points is None or points.empty:
            continue
        point_sources.append((poi_type, points.to_dict("records"), name_column))

    building_rows = buildings.to_dict("records")
    chunk_size = max(1, math.ceil(len(building_rows) / 3))
    chunks = [building_rows[index:index + chunk_size] for index in range(0, len(building_rows), chunk_size)]
    rows: list[dict[str, object]] = []
    if chunks:
        with mp.Pool(processes=3, initializer=_init_building_poi_pool, initargs=(point_sources,)) as pool:
            for chunk_rows in tqdm(
                pool.imap(
                    _build_building_poi_rows_for_chunk_star,
                    [(chunk, within_km) for chunk in chunks],
                ),
                total=len(chunks),
                desc="Building POI point rows",
                unit="chunk",
            ):
                rows.extend(chunk_rows)
    if not rows:
        return pd.DataFrame(columns=BUILDING_POI_POINT_EXPORT_COLUMNS)
    return pd.DataFrame(rows).sort_values(
        ["building_key", "poi_type", "distance_to_building_km", "poi_name"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)


def _polygon_centroid_from_coords(coordinates: list) -> tuple[float | None, float | None]:
    points: list[tuple[float, float]] = []

    def collect(coord_block: list) -> None:
        if not coord_block:
            return
        first = coord_block[0]
        if isinstance(first, (int, float)) and len(coord_block) >= 2:
            points.append((float(coord_block[0]), float(coord_block[1])))
            return
        for item in coord_block:
            if isinstance(item, list):
                collect(item)

    collect(coordinates)
    if not points:
        return None, None
    longitudes, latitudes = zip(*points)
    return float(sum(longitudes) / len(longitudes)), float(sum(latitudes) / len(latitudes))


def _flatten_rings(coordinates: list) -> list[list[list[float]]]:
    rings: list[list[list[float]]] = []
    if not coordinates:
        return rings
    first = coordinates[0]
    if isinstance(first, list) and first and isinstance(first[0], (int, float)):
        return [coordinates]
    for item in coordinates:
        if isinstance(item, list):
            rings.extend(_flatten_rings(item))
    return rings


def _bounds_for_ring(ring: list[list[float]]) -> tuple[float, float, float, float] | None:
    if not ring:
        return None
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = ((yi > latitude) != (yj > latitude)) and (
            longitude < (xj - xi) * (latitude - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def parse_town_boundary_geojson(town_boundary_geojson_path: Path) -> pd.DataFrame:
    payload = json.loads(town_boundary_geojson_path.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        town = properties.get("Town")
        geometry = feature.get("geometry", {})
        if not town or not geometry:
            continue
        rings = _flatten_rings(geometry.get("coordinates", []))
        if not rings:
            continue
        bounds = [_bounds_for_ring(ring) for ring in rings]
        bounds = [bound for bound in bounds if bound is not None]
        if not bounds:
            continue
        min_x = min(bound[0] for bound in bounds)
        min_y = min(bound[1] for bound in bounds)
        max_x = max(bound[2] for bound in bounds)
        max_y = max(bound[3] for bound in bounds)
        records.append(
            {
                "town": town,
                "rings": rings,
                "bounds": (min_x, min_y, max_x, max_y),
            }
        )
    return pd.DataFrame(records)


def parse_hdb_building_geojson(building_geojson_path: Path) -> tuple[dict, pd.DataFrame]:
    payload = json.loads(building_geojson_path.read_text(encoding="utf-8"))
    records = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        longitude, latitude = _polygon_centroid_from_coords(feature.get("geometry", {}).get("coordinates", []))
        block = str(properties.get("BLK_NO") or "").strip().upper() or None
        postal_code = str(properties.get("POSTAL_COD") or "").strip() or None
        building_key = f"{block}|{postal_code}" if block and postal_code else block
        records.append(
            {
                "objectid": properties.get("OBJECTID"),
                "block": block,
                "postal_code": postal_code,
                "building_key": building_key,
                "building_latitude": latitude,
                "building_longitude": longitude,
            }
        )
    return payload, pd.DataFrame(records)


def assign_buildings_to_towns(buildings: pd.DataFrame, town_polygons: pd.DataFrame) -> pd.DataFrame:
    assigned_records = []
    polygon_records = town_polygons.to_dict("records")
    for row in tqdm(buildings.to_dict("records"), desc="Assigning buildings to towns", unit="building"):
        latitude = row.get("building_latitude")
        longitude = row.get("building_longitude")
        matched_town = pd.NA
        if pd.notna(latitude) and pd.notna(longitude):
            for polygon in polygon_records:
                min_x, min_y, max_x, max_y = polygon["bounds"]
                if not (min_x <= longitude <= max_x and min_y <= latitude <= max_y):
                    continue
                if any(_point_in_ring(longitude, latitude, ring) for ring in polygon["rings"]):
                    matched_town = polygon["town"]
                    break
        assigned = dict(row)
        assigned["town"] = matched_town
        assigned["building_match_status"] = "matched_geometry" if pd.notna(matched_town) else "unmatched_geometry"
        assigned_records.append(assigned)
    return pd.DataFrame(assigned_records)


def _nearest_distance(lat: float, lon: float, points: pd.DataFrame | None, name_col: str) -> tuple[object, float | None]:
    if points is None or points.empty or pd.isna(lat) or pd.isna(lon):
        return pd.NA, pd.NA
    best_name = pd.NA
    best_distance = math.inf
    for point in points.to_dict("records"):
        distance = haversine_km(lat, lon, point["latitude"], point["longitude"])
        if distance < best_distance:
            best_distance = distance
            best_name = point.get(name_col)
    return best_name, best_distance if math.isfinite(best_distance) else pd.NA


def _count_within_km(lat: float, lon: float, points: pd.DataFrame | None, *, threshold_km: float) -> int | pd._libs.missing.NAType:
    if points is None or points.empty or pd.isna(lat) or pd.isna(lon):
        return pd.NA
    count = 0
    for point in points.to_dict("records"):
        if haversine_km(lat, lon, point["latitude"], point["longitude"]) <= threshold_km:
            count += 1
    return count


def enrich_buildings_with_poi_metrics(
    buildings: pd.DataFrame,
    mrt_points: pd.DataFrame | None,
    bus_stop_points: pd.DataFrame | None,
    school_points: pd.DataFrame | None,
) -> pd.DataFrame:
    if buildings.empty:
        return buildings.copy()
    enriched_rows = []
    for row in tqdm(buildings.to_dict("records"), desc="Computing building POI metrics", unit="building"):
        lat = row.get("building_latitude")
        lon = row.get("building_longitude")
        mrt_name, mrt_distance = _nearest_distance(lat, lon, mrt_points, "station_name")
        bus_name, bus_distance = _nearest_distance(lat, lon, bus_stop_points, "bus_stop_num")
        school_name, school_distance = _nearest_distance(lat, lon, school_points, "school_name")
        enriched = dict(row)
        enriched["nearest_mrt_name"] = mrt_name
        enriched["nearest_mrt_distance_km"] = mrt_distance
        enriched["nearest_bus_stop_num"] = bus_name
        enriched["nearest_bus_stop_distance_km"] = bus_distance
        enriched["bus_stop_count_within_1km"] = _count_within_km(lat, lon, bus_stop_points, threshold_km=1.0)
        enriched["nearest_school_name"] = school_name
        enriched["nearest_school_distance_km"] = school_distance
        enriched["school_count_within_1km"] = _count_within_km(lat, lon, school_points, threshold_km=1.0)
        enriched["distance_to_cbd_km"] = haversine_km(lat, lon, 1.2834, 103.8607) if pd.notna(lat) and pd.notna(lon) else pd.NA
        enriched_rows.append(enriched)
    return pd.DataFrame(enriched_rows)


def build_building_transaction_match_summary(merged: pd.DataFrame) -> pd.DataFrame:
    transaction_rows = merged[merged["transaction_year"].notna()].copy()
    total = int(len(transaction_rows))
    matched = int(transaction_rows["building_latitude"].notna().sum())
    unmatched = total - matched
    rate = matched / total if total else 0.0
    return pd.DataFrame(
        [
            {
                "total_transaction_groups": total,
                "matched_transaction_groups": matched,
                "unmatched_transaction_groups": unmatched,
                "transaction_match_rate": rate,
            }
        ]
    )


def build_building_optimizer_extract(
    buildings: pd.DataFrame,
    building_transaction_budget: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    building_index = buildings[[
        "town",
        "block",
        "building_key",
        "postal_code",
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
    ]].drop_duplicates()
    merged = building_transaction_budget.merge(building_index, on=["town", "block"], how="outer")
    merged["building_match_status"] = merged["building_match_status"].where(
        merged["building_match_status"].notna(),
        pd.NA,
    )
    not_unmatched_geometry = merged["building_match_status"].ne("unmatched_geometry").fillna(True)
    merged.loc[
        merged["transaction_year"].isna()
        & merged["building_key"].notna()
        & not_unmatched_geometry,
        "building_match_status",
    ] = "building_only"
    merged.loc[merged["building_key"].isna() & merged["transaction_year"].notna(), "building_match_status"] = "transaction_only"
    merged.loc[
        merged["building_key"].notna()
        & merged["transaction_year"].notna()
        & merged["town"].notna()
        & merged["building_match_status"].eq("matched_geometry"),
        "building_match_status",
    ] = "matched_geometry"
    merged["has_transaction_data"] = merged["transaction_year"].notna().map({True: "Yes", False: "No"})
    merged["has_building_geometry"] = merged["building_latitude"].notna().map({True: "Yes", False: "No"})
    match_summary = build_building_transaction_match_summary(merged)
    return merged.sort_values(
        ["transaction_year", "budget", "town", "block", "flat_type"],
        ascending=[False, True, True, True, True],
    ).reset_index(drop=True), match_summary


def filter_building_optimizer_for_tableau(building_optimizer: pd.DataFrame) -> pd.DataFrame:
    if building_optimizer.empty:
        return building_optimizer.copy()
    filtered = building_optimizer[
        building_optimizer["building_match_status"].eq("matched_geometry")
    ].reset_index(drop=True)
    if "transaction_year" in filtered.columns:
        filtered["transaction_year"] = filtered["transaction_year"].astype("int64")
    if "budget" in filtered.columns:
        filtered["budget"] = filtered["budget"].astype("int64")
    return filtered


def export_dashboard_3_assets(
    frame: pd.DataFrame,
    *,
    building_budget: pd.DataFrame,
    town_boundary_geojson: Path,
) -> dict[str, str]:
    ensure_section1_results_dir()
    location = build_location_extract(frame)
    poi_sources = load_poi_sources()
    mrt_points = poi_sources["mrt"]
    bus_stop_points = poi_sources["bus"]
    school_points = poi_sources["school"]
    poi_points = build_location_poi_points_extract(mrt_points, bus_stop_points, school_points)
    poi_summary = build_location_poi_summary_extract(poi_points)

    write_section1_csv(location, "location_quality.csv", kind="final")
    write_section1_csv(
        poi_points.loc[:, LOCATION_POI_POINT_EXPORT_COLUMNS],
        "location_poi_points.csv",
        kind="final",
    )
    write_section1_csv(
        poi_summary.loc[:, LOCATION_POI_SUMMARY_EXPORT_COLUMNS],
        "location_poi_summary.csv",
        kind="final",
    )

    outputs = {
        "location_quality": str(section1_output_path("location_quality.csv", kind="final")),
        "location_poi_points": str(section1_output_path("location_poi_points.csv", kind="final")),
        "location_poi_summary": str(section1_output_path("location_poi_summary.csv", kind="final")),
    }

    building_geojson = load_building_geojson_path()
    if not building_geojson.exists() or not town_boundary_geojson.exists():
        return outputs

    building_payload, raw_buildings = parse_hdb_building_geojson(building_geojson)
    town_polygons = parse_town_boundary_geojson(town_boundary_geojson)
    buildings = assign_buildings_to_towns(raw_buildings, town_polygons)
    buildings = enrich_buildings_with_poi_metrics(buildings, mrt_points, bus_stop_points, school_points)
    building_poi_points = build_building_poi_points_extract(buildings, mrt_points, bus_stop_points, school_points)
    building_optimizer, building_match_summary = build_building_optimizer_extract(buildings, building_budget)
    building_optimizer_tableau = filter_building_optimizer_for_tableau(building_optimizer)

    write_section1_csv(
        building_poi_points.loc[:, BUILDING_POI_POINT_EXPORT_COLUMNS],
        "building_poi_points.csv",
        kind="final",
    )
    write_section1_csv(
        buildings.loc[:, BUILDING_GEOMETRY_EXPORT_COLUMNS],
        "building_geometry_lookup.csv",
        kind="final",
    )
    write_section1_csv(
        building_optimizer.loc[:, BUILDING_OPTIMIZER_EXPORT_COLUMNS],
        "building_optimizer_raw.csv",
        kind="diagnostic",
    )
    write_section1_csv(
        building_optimizer_tableau.loc[:, BUILDING_OPTIMIZER_EXPORT_COLUMNS],
        "building_optimizer.csv",
        kind="final",
    )
    write_section1_csv(
        building_match_summary.loc[:, BUILDING_MATCH_SUMMARY_EXPORT_COLUMNS],
        "building_transaction_match_summary.csv",
        kind="diagnostic",
    )

    properties_by_key = {
        row["building_key"]: row
        for row in buildings[BUILDING_GEOMETRY_EXPORT_COLUMNS].to_dict("records")
        if row.get("building_key")
    }
    for feature in building_payload.get("features", []):
        props = feature.get("properties", {})
        block = str(props.get("BLK_NO") or "").strip().upper() or None
        postal = str(props.get("POSTAL_COD") or "").strip() or None
        building_key = f"{block}|{postal}" if block and postal else block
        mapped = properties_by_key.get(building_key, {})
        feature["properties"] = {
            "Building Key": building_key,
            "Block": block,
            "Postal Code": postal,
            "Town": mapped.get("town"),
            "Building Match Status": mapped.get("building_match_status"),
            "Building Latitude": mapped.get("building_latitude"),
            "Building Longitude": mapped.get("building_longitude"),
        }
    hdb_geojson = section1_output_path("hdb_existing_buildings.geojson", kind="final")
    hdb_geojson.write_text(json.dumps(building_payload), encoding="utf-8")

    outputs.update(
        {
            "building_poi_points": str(section1_output_path("building_poi_points.csv", kind="final")),
            "building_geometry_lookup": str(section1_output_path("building_geometry_lookup.csv", kind="final")),
            "building_optimizer_raw": str(section1_output_path("building_optimizer_raw.csv", kind="diagnostic")),
            "building_optimizer": str(section1_output_path("building_optimizer.csv", kind="final")),
            "building_transaction_match_summary": str(section1_output_path("building_transaction_match_summary.csv", kind="diagnostic")),
            "hdb_existing_buildings": str(hdb_geojson),
        }
    )
    return outputs


def main() -> None:
    from src.analysis.section1.dashboard_1 import export_planning_area_assets
    from src.analysis.section1.dashboard_2 import build_building_transaction_budget_extract
    from src.analysis.section1.helpers import load_planning_area_geojson_payload

    parser = argparse.ArgumentParser(description="Export Section 1 Dashboard 3 location-optimizer assets.")
    parser.parse_args()
    frame = load_processed_frame()
    planning_payload = load_planning_area_geojson_payload()
    export_planning_area_assets(frame, planning_payload)
    building_budget = build_building_transaction_budget_extract(frame)
    export_dashboard_3_assets(
        frame,
        building_budget=building_budget,
        town_boundary_geojson=section1_output_path("planning_area_hdb_map_2019.geojson", kind="final"),
    )


if __name__ == "__main__":
    main()
