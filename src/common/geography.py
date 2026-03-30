from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.common.config import DATA_PROCESSED, DATA_RAW, PLANNING_AREA_DATASET_ID


TOWN_CITY_AREA_ROWS = [
    {"town": "ANG MO KIO", "city_area": "ang mo kio"},
    {"town": "BEDOK", "city_area": "bedok"},
    {"town": "BISHAN", "city_area": "bishan"},
    {"town": "BUKIT BATOK", "city_area": "bukit batok"},
    {"town": "BUKIT MERAH", "city_area": "bukit merah"},
    {"town": "BUKIT PANJANG", "city_area": "bukit panjang"},
    {"town": "BUKIT TIMAH", "city_area": "bukit timah"},
    {"town": "BUKIT TIMAH", "city_area": "tanglin"},
    {"town": "CENTRAL AREA", "city_area": "downtown core"},
    {"town": "CENTRAL AREA", "city_area": "outram"},
    {"town": "CENTRAL AREA", "city_area": "rochor"},
    {"town": "CHOA CHU KANG", "city_area": "choa chu kang"},
    {"town": "CLEMENTI", "city_area": "clementi"},
    {"town": "GEYLANG", "city_area": "geylang"},
    {"town": "HOUGANG", "city_area": "hougang"},
    {"town": "JURONG EAST", "city_area": "jurong east"},
    {"town": "JURONG WEST", "city_area": "jurong west"},
    {"town": "KALLANG/WHAMPOA", "city_area": "kallang"},
    {"town": "KALLANG/WHAMPOA", "city_area": "novena"},
    {"town": "LIM CHU KANG", "city_area": "lim chu kang"},
    {"town": "MARINE PARADE", "city_area": "marine parade"},
    {"town": "PASIR RIS", "city_area": "changi"},
    {"town": "PASIR RIS", "city_area": "pasir ris"},
    {"town": "PUNGGOL", "city_area": "punggol"},
    {"town": "QUEENSTOWN", "city_area": "queenstown"},
    {"town": "SEMBAWANG", "city_area": "sembawang"},
    {"town": "SENGKANG", "city_area": "sengkang"},
    {"town": "SERANGOON", "city_area": "serangoon"},
    {"town": "TAMPINES", "city_area": "tampines"},
    {"town": "TOA PAYOH", "city_area": "toa payoh"},
    {"town": "WOODLANDS", "city_area": "woodlands"},
    {"town": "YISHUN", "city_area": "yishun"},
]


def _normalize_planning_area(label: str) -> str:
    return label.strip().upper()


HDB_TOWN_TO_PLANNING_AREAS: dict[str, list[str]] = {}
for row in TOWN_CITY_AREA_ROWS:
    HDB_TOWN_TO_PLANNING_AREAS.setdefault(row["town"], []).append(_normalize_planning_area(row["city_area"]))


def get_planning_area_to_town_map() -> dict[str, str]:
    planning_area_to_town: dict[str, str] = {}
    for town, planning_areas in HDB_TOWN_TO_PLANNING_AREAS.items():
        for planning_area in planning_areas:
            planning_area_to_town[planning_area] = town
    return planning_area_to_town


def planning_area_dataset_geojson_path() -> Path:
    return DATA_RAW / PLANNING_AREA_DATASET_ID / "extracted" / "dataset.geojson"


def town_centroids_artifact_path() -> Path:
    return DATA_PROCESSED / "town_centroids.parquet"


def load_planning_area_geojson_payload() -> dict:
    source_geojson = planning_area_dataset_geojson_path()
    if not source_geojson.exists():
        raise FileNotFoundError(
            "Planning-area GeoJSON is missing. Run the dataset pipeline or fetch the "
            f"`{PLANNING_AREA_DATASET_ID}` open dataset first: {source_geojson}"
        )
    return json.loads(source_geojson.read_text(encoding="utf-8"))


def _iter_exterior_rings(geometry: dict) -> list[list[list[float]]]:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        return [coordinates[0]] if coordinates else []
    if geom_type == "MultiPolygon":
        return [polygon[0] for polygon in coordinates if polygon]
    return []


def _ring_area_and_centroid(ring: list[list[float]]) -> tuple[float, tuple[float, float] | None]:
    if len(ring) < 3:
        return 0.0, None

    if ring[0] != ring[-1]:
        ring = [*ring, ring[0]]

    cross_sum = 0.0
    centroid_x_sum = 0.0
    centroid_y_sum = 0.0
    for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
        cross = x0 * y1 - x1 * y0
        cross_sum += cross
        centroid_x_sum += (x0 + x1) * cross
        centroid_y_sum += (y0 + y1) * cross

    signed_area = 0.5 * cross_sum
    area = abs(signed_area)
    if area == 0:
        return 0.0, None

    centroid_x = centroid_x_sum / (6.0 * signed_area)
    centroid_y = centroid_y_sum / (6.0 * signed_area)
    return area, (centroid_y, centroid_x)


def _geometry_area_and_centroid(geometry: dict) -> tuple[float, tuple[float, float] | None]:
    total_area = 0.0
    weighted_lat_sum = 0.0
    weighted_lon_sum = 0.0

    for ring in _iter_exterior_rings(geometry):
        area, centroid = _ring_area_and_centroid(ring)
        if centroid is None or area == 0:
            continue
        latitude, longitude = centroid
        total_area += area
        weighted_lat_sum += latitude * area
        weighted_lon_sum += longitude * area

    if total_area == 0:
        return 0.0, None
    return total_area, (weighted_lat_sum / total_area, weighted_lon_sum / total_area)


def build_town_centroids(payload: dict) -> dict[str, tuple[float, float]]:
    planning_area_to_town = get_planning_area_to_town_map()
    total_area_by_town: dict[str, float] = {}
    weighted_lat_sum_by_town: dict[str, float] = {}
    weighted_lon_sum_by_town: dict[str, float] = {}

    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        town = planning_area_to_town.get(properties.get("PLN_AREA_N"))
        if not town:
            continue
        area, centroid = _geometry_area_and_centroid(feature.get("geometry", {}))
        if centroid is None or area == 0:
            continue
        latitude, longitude = centroid
        total_area_by_town[town] = total_area_by_town.get(town, 0.0) + area
        weighted_lat_sum_by_town[town] = weighted_lat_sum_by_town.get(town, 0.0) + latitude * area
        weighted_lon_sum_by_town[town] = weighted_lon_sum_by_town.get(town, 0.0) + longitude * area

    return {
        town: (
            weighted_lat_sum_by_town[town] / total_area_by_town[town],
            weighted_lon_sum_by_town[town] / total_area_by_town[town],
        )
        for town in sorted(total_area_by_town)
        if total_area_by_town[town] > 0
    }


def save_town_centroids_artifact(centroids: dict[str, tuple[float, float]]) -> Path:
    path = town_centroids_artifact_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [
            {"town": town, "town_latitude": coords[0], "town_longitude": coords[1]}
            for town, coords in sorted(centroids.items())
        ]
    )
    frame.to_parquet(path, index=False)
    return path


def load_town_centroids_artifact() -> dict[str, tuple[float, float]]:
    path = town_centroids_artifact_path()
    frame = pd.read_parquet(path)
    return {
        str(row["town"]): (float(row["town_latitude"]), float(row["town_longitude"]))
        for _, row in frame.iterrows()
    }


def build_and_save_town_centroids() -> dict[str, tuple[float, float]]:
    centroids = build_town_centroids(load_planning_area_geojson_payload())
    save_town_centroids_artifact(centroids)
    return centroids


@lru_cache(maxsize=1)
def load_town_centroids() -> dict[str, tuple[float, float]]:
    path = town_centroids_artifact_path()
    if path.exists():
        return load_town_centroids_artifact()
    return build_and_save_town_centroids()
