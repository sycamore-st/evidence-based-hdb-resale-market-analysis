from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover
    def tqdm(iterable=None, *args, **kwargs):
        return iterable

from src.common.config import CBD_COORDS, DTL2_TOWNS, LEASE_YEARS
from src.common.geography import load_town_centroids
from src.common.utils import as_numeric, haversine_km, month_to_timestamp


STANDARD_COLUMNS = {
    "month": "month",
    "town": "town",
    "flat_type": "flat_type",
    "block": "block",
    "street_name": "street_name",
    "storey_range": "storey_range",
    "floor_area_sqm": "floor_area_sqm",
    "flat_model": "flat_model",
    "lease_commence_date": "lease_commence_date",
    "remaining_lease": "remaining_lease",
    "resale_price": "resale_price",
}


def _log_progress(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def normalize_text(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip().str.replace(r"\s+", " ", regex=True).str.upper()
    values = values.mask(values == "")
    return values


def parse_remaining_lease_years(value: object) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    years = 0
    months = 0
    if "year" in text:
        fragment = text.split("year")[0].strip()
        years = int(fragment.split()[-1])
    if "month" in text:
        fragment = text.split("month")[0].strip()
        months = int(fragment.split()[-1])
    if "year" not in text and text.replace(".", "", 1).isdigit():
        return float(text)
    return years + months / 12


def add_location_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    town_centroids = load_town_centroids()
    frame["town_latitude"] = frame["town"].map(lambda town: town_centroids.get(town, (np.nan, np.nan))[0])
    frame["town_longitude"] = frame["town"].map(lambda town: town_centroids.get(town, (np.nan, np.nan))[1])
    frame["distance_to_cbd_km"] = frame.apply(
        lambda row: haversine_km(
            row["town_latitude"],
            row["town_longitude"],
            CBD_COORDS[0],
            CBD_COORDS[1],
        )
        if pd.notna(row["town_latitude"]) and pd.notna(row["town_longitude"])
        else np.nan,
        axis=1,
    )
    frame["is_dtl2_town"] = frame["town"].isin(DTL2_TOWNS)
    return frame


def add_mrt_proximity(frame: pd.DataFrame, mrt_stations: pd.DataFrame | None = None) -> pd.DataFrame:
    frame = frame.copy()
    if mrt_stations is None or mrt_stations.empty:
        frame["nearest_mrt_station"] = np.nan
        frame["nearest_mrt_line"] = np.nan
        frame["nearest_mrt_distance_km"] = np.nan
        return frame

    stations = mrt_stations.dropna(subset=["latitude", "longitude"]).copy()
    station_records = stations.to_dict("records")

    def nearest_station(row: pd.Series) -> pd.Series:
        if pd.isna(row["town_latitude"]) or pd.isna(row["town_longitude"]):
            return pd.Series([np.nan, np.nan, np.nan])
        best_name = None
        best_line = None
        best_distance = np.inf
        for station in station_records:
            distance = haversine_km(
                row["town_latitude"],
                row["town_longitude"],
                station["latitude"],
                station["longitude"],
            )
            if distance < best_distance:
                best_distance = distance
                best_name = station.get("station_name")
                best_line = station.get("line_name")
        return pd.Series([best_name, best_line, best_distance])

    _log_progress(
        f"Starting MRT proximity calculation for {len(frame):,} rows against {len(station_records):,} stations."
    )
    frame["nearest_mrt_station"] = np.nan
    frame["nearest_mrt_line"] = np.nan
    frame["nearest_mrt_distance_km"] = np.nan
    chunk_size = 25_000
    total_chunks = max(1, (len(frame) + chunk_size - 1) // chunk_size)
    next_checkpoint_pct = 10
    checkpoint_path = frame.attrs.get("checkpoint_path")
    checkpoint_label = frame.attrs.get("checkpoint_label", "mrt")
    for chunk_index, start in enumerate(
        tqdm(range(0, len(frame), chunk_size), total=total_chunks, desc="MRT proximity", unit="chunk"),
        start=1,
    ):
        stop = min(start + chunk_size, len(frame))
        chunk = frame.iloc[start:stop]
        chunk_result = chunk.apply(nearest_station, axis=1)
        chunk_result.index = chunk.index
        frame.loc[chunk.index, ["nearest_mrt_station", "nearest_mrt_line", "nearest_mrt_distance_km"]] = chunk_result
        _log_progress(f"Finished MRT proximity rows {start + 1:,}-{stop:,} of {len(frame):,}.")
        progress_pct = int(chunk_index * 100 / total_chunks)
        if checkpoint_path is not None and progress_pct >= next_checkpoint_pct:
            checkpoint_file = Path(checkpoint_path) / f"{checkpoint_label}_in_progress.parquet"
            frame.to_parquet(checkpoint_file, index=False)
            _log_progress(f"Saved {checkpoint_label} checkpoint at {progress_pct}% to {checkpoint_file}.")
            while progress_pct >= next_checkpoint_pct:
                next_checkpoint_pct += 10
    return frame


def add_point_of_interest_proximity(
    frame: pd.DataFrame,
    poi_frame: pd.DataFrame | None,
    *,
    label_column: str,
    output_label_column: str,
    output_distance_column: str,
) -> pd.DataFrame:
    frame = frame.copy()
    if poi_frame is None or poi_frame.empty:
        frame[output_label_column] = np.nan
        frame[output_distance_column] = np.nan
        return frame

    points = poi_frame.dropna(subset=["latitude", "longitude"]).copy()
    point_records = points.to_dict("records")

    def nearest_poi(row: pd.Series) -> pd.Series:
        if pd.isna(row["town_latitude"]) or pd.isna(row["town_longitude"]):
            return pd.Series([np.nan, np.nan])
        best_label = None
        best_distance = np.inf
        for point in point_records:
            distance = haversine_km(
                row["town_latitude"],
                row["town_longitude"],
                point["latitude"],
                point["longitude"],
            )
            if distance < best_distance:
                best_distance = distance
                best_label = point.get(label_column)
        return pd.Series([best_label, best_distance])

    _log_progress(
        f"Starting POI proximity calculation for {output_label_column} on {len(frame):,} rows against {len(point_records):,} points."
    )
    frame[output_label_column] = np.nan
    frame[output_distance_column] = np.nan
    chunk_size = 25_000
    total_chunks = max(1, (len(frame) + chunk_size - 1) // chunk_size)
    next_checkpoint_pct = 10
    checkpoint_path = frame.attrs.get("checkpoint_path")
    checkpoint_label = frame.attrs.get("checkpoint_label", output_label_column)
    for chunk_index, start in enumerate(
        tqdm(range(0, len(frame), chunk_size), total=total_chunks, desc=output_label_column, unit="chunk"),
        start=1,
    ):
        stop = min(start + chunk_size, len(frame))
        chunk = frame.iloc[start:stop]
        chunk_result = chunk.apply(nearest_poi, axis=1)
        chunk_result.index = chunk.index
        frame.loc[chunk.index, [output_label_column, output_distance_column]] = chunk_result
        _log_progress(
            f"Finished {output_label_column} rows {start + 1:,}-{stop:,} of {len(frame):,}."
        )
        progress_pct = int(chunk_index * 100 / total_chunks)
        if checkpoint_path is not None and progress_pct >= next_checkpoint_pct:
            checkpoint_file = Path(checkpoint_path) / f"{checkpoint_label}_in_progress.parquet"
            frame.to_parquet(checkpoint_file, index=False)
            _log_progress(f"Saved {checkpoint_label} checkpoint at {progress_pct}% to {checkpoint_file}.")
            while progress_pct >= next_checkpoint_pct:
                next_checkpoint_pct += 10
    return frame


def standardize_hdb_dataset(frame: pd.DataFrame, dataset_slug: str) -> pd.DataFrame:
    renamed = frame.rename(columns={column: STANDARD_COLUMNS.get(column, column) for column in frame.columns})
    for column in STANDARD_COLUMNS.values():
        if column not in renamed.columns:
            renamed[column] = np.nan

    cleaned = renamed[list(STANDARD_COLUMNS.values())].copy()
    for column in ["town", "flat_type", "block", "street_name", "storey_range", "flat_model"]:
        cleaned[column] = normalize_text(cleaned[column])

    cleaned["month"] = cleaned["month"].astype(str).str.slice(0, 7)
    cleaned["transaction_month"] = cleaned["month"].map(month_to_timestamp)
    cleaned["transaction_year"] = cleaned["transaction_month"].dt.year
    cleaned["transaction_quarter"] = cleaned["transaction_month"].dt.to_period("Q").astype(str)
    cleaned["floor_area_sqm"] = as_numeric(cleaned["floor_area_sqm"])
    cleaned["lease_commence_date"] = as_numeric(cleaned["lease_commence_date"])
    cleaned["resale_price"] = as_numeric(cleaned["resale_price"])
    cleaned["remaining_lease"] = cleaned["remaining_lease"].fillna("").astype(str).str.strip()
    cleaned["remaining_lease"] = cleaned["remaining_lease"].mask(cleaned["remaining_lease"] == "")
    cleaned["remaining_lease_years"] = cleaned["remaining_lease"].map(parse_remaining_lease_years)
    cleaned["flat_age"] = cleaned["transaction_year"] - cleaned["lease_commence_date"]
    cleaned["remaining_lease_proxy"] = LEASE_YEARS - cleaned["flat_age"]
    cleaned["remaining_lease_effective"] = cleaned["remaining_lease_years"].where(
        cleaned["remaining_lease_years"].notna(),
        cleaned["remaining_lease_proxy"],
    )
    cleaned["flat_type"] = cleaned["flat_type"].str.replace("MULTI GENERATION", "MULTI-GENERATION", regex=False)
    cleaned["flat_type_simple"] = cleaned["flat_type"].str.replace("MULTI-GENERATION", "MULTI GENERATION")
    cleaned["full_address"] = (
        cleaned["block"].fillna("").astype(str).str.strip()
        + " "
        + cleaned["street_name"].fillna("").astype(str).str.strip()
    ).str.strip()
    cleaned["data_segment"] = dataset_slug
    cleaned = add_location_features(cleaned)
    return cleaned


def merge_hdb_frames(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    standardized = [
        standardize_hdb_dataset(frame, dataset_slug=slug)
        for slug, frame in frames.items()
    ]
    merged = pd.concat(standardized, ignore_index=True)
    merged = merged.drop_duplicates(
        subset=[
            "month",
            "town",
            "flat_type",
            "block",
            "street_name",
            "storey_range",
            "floor_area_sqm",
            "flat_model",
            "lease_commence_date",
            "resale_price",
        ]
    ).sort_values(["transaction_month", "town", "block", "street_name"])
    merged["price_per_sqm"] = merged["resale_price"] / merged["floor_area_sqm"]
    return merged.reset_index(drop=True)


def parse_mrt_geojson(mrt_dir: Path) -> pd.DataFrame:
    geojson_files = list(mrt_dir.glob("*.geojson")) + list(mrt_dir.glob("*.json"))
    if not geojson_files:
        return pd.DataFrame(columns=["station_name", "line_name", "latitude", "longitude"])

    records = []
    for geojson_file in geojson_files:
        payload = json.loads(geojson_file.read_text(encoding="utf-8"))
        for feature in payload.get("features", []):
            properties = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [None, None])
            station_name = (
                properties.get("MRT_NAME")
                or properties.get("STN_NAME")
                or properties.get("STATION_NA")
                or properties.get("STATION")
                or properties.get("station_name")
                or properties.get("name")
                or properties.get("Name")
                or properties.get("NAME")
            )
            line_name = (
                properties.get("LINE")
                or properties.get("MRT_LINE")
                or properties.get("LINE_NAME")
                or properties.get("description")
                or "MRT"
            )
            if isinstance(coords, list) and len(coords) >= 2:
                longitude, latitude = coords[0], coords[1]
            else:
                longitude, latitude = None, None
            records.append(
                {
                    "station_name": station_name,
                    "line_name": line_name,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )
    stations = pd.DataFrame(records)
    stations["station_name"] = normalize_text(stations["station_name"])
    stations["line_name"] = normalize_text(stations["line_name"])
    stations = stations.dropna(subset=["station_name", "latitude", "longitude"]).copy()
    if stations.empty:
        return stations
    return (
        stations.groupby(["station_name", "line_name"], dropna=False)
        .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        .reset_index()
        .drop_duplicates()
    )


def parse_bus_stop_geojson(bus_stop_dir: Path) -> pd.DataFrame:
    geojson_files = list(bus_stop_dir.glob("*.geojson")) + list(bus_stop_dir.glob("*.json"))
    if not geojson_files:
        return pd.DataFrame(columns=["bus_stop_num", "latitude", "longitude"])

    payload = json.loads(geojson_files[0].read_text(encoding="utf-8"))
    records = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [None, None])
        longitude, latitude = (coords[0], coords[1]) if isinstance(coords, list) and len(coords) >= 2 else (None, None)
        records.append(
            {
                "bus_stop_num": properties.get("BUS_STOP_NUM"),
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    stops = pd.DataFrame(records)
    stops["bus_stop_num"] = normalize_text(stops["bus_stop_num"])
    return stops.dropna(subset=["bus_stop_num", "latitude", "longitude"]).drop_duplicates()


def _extract_school_name(description: str | None) -> str | None:
    if not description:
        return None
    match = re.search(r"SITENAME</th>\s*<td[^>]*>(.*?)</td>", description, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = re.sub(r"<[^>]+>", " ", match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        return text or None
    return None


def _polygon_centroid(coordinates: list) -> tuple[float | None, float | None]:
    if not coordinates:
        return None, None
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
    return float(np.mean(longitudes)), float(np.mean(latitudes))


def parse_school_zone_geojson(school_zone_dir: Path) -> pd.DataFrame:
    geojson_files = list(school_zone_dir.glob("*.geojson")) + list(school_zone_dir.glob("*.json"))
    if not geojson_files:
        return pd.DataFrame(columns=["school_name", "latitude", "longitude"])

    payload = json.loads(geojson_files[0].read_text(encoding="utf-8"))
    records = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        longitude, latitude = _polygon_centroid(geometry.get("coordinates", []))
        school_name = (
            properties.get("SITENAME")
            or _extract_school_name(properties.get("Description"))
            or properties.get("NAME")
            or properties.get("name")
        )
        records.append(
            {
                "school_name": school_name,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    schools = pd.DataFrame(records)
    schools["school_name"] = normalize_text(schools["school_name"])
    return schools.dropna(subset=["school_name", "latitude", "longitude"]).drop_duplicates()
