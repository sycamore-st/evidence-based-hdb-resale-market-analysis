from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from src.analysis.section1.dashboard_1 import planning_area_match_status
from src.analysis.section1.dashboard_3 import assign_buildings_to_towns, parse_town_boundary_geojson
from src.common.geography import HDB_TOWN_TO_PLANNING_AREAS, get_planning_area_to_town_map
from src.pipeline.pipeline_common import log_step, save_stage


def build_town_city_area_lookup(towns: list[str] | pd.Series) -> pd.DataFrame:
    values = sorted({str(town).strip().upper() for town in towns if pd.notna(town)})
    rows = []
    for town in values:
        city_areas = HDB_TOWN_TO_PLANNING_AREAS.get(town, [])
        rows.append(
            {
                "town": town,
                "planning_area_name": "|".join(city_areas) or None,
                "planning_area_name_single": city_areas[0] if len(city_areas) == 1 else None,
                "planning_area_match_status": planning_area_match_status(town),
            }
        )
    lookup = pd.DataFrame(rows)
    save_stage(lookup, "town_city_area_lookup")
    return lookup


def build_enriched_city_area_geojson(source_geojson: Path, output_geojson: Path) -> Path:
    with source_geojson.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    planning_area_to_town = get_planning_area_to_town_map()
    for feature in payload.get("features", []):
        source_properties = feature.get("properties", {})
        planning_area_name = source_properties.get("PLN_AREA_N")
        hdb_town = planning_area_to_town.get(planning_area_name)
        match_status = "direct" if hdb_town else "unmatched"
        if hdb_town == "KALLANG/WHAMPOA":
            match_status = "approximate"
        feature["properties"] = {
            "Planning Area": planning_area_name,
            "Town": hdb_town,
            "Region Label": hdb_town or planning_area_name,
            "Region Match Status": match_status,
            "Region Key": hdb_town or planning_area_name,
            "Region Type": "hdb_town" if hdb_town else "planning_area_only",
        }
    output_geojson.parent.mkdir(parents=True, exist_ok=True)
    output_geojson.write_text(json.dumps(payload), encoding="utf-8")
    log_step(f"Wrote enriched city-area geojson to {output_geojson}.")
    return output_geojson


def assign_buildings_to_city_areas(raw_buildings: pd.DataFrame, town_boundary_geojson: Path) -> pd.DataFrame:
    town_polygons = parse_town_boundary_geojson(town_boundary_geojson)
    log_step(f"Loaded {len(town_polygons):,} city-area polygon records.")
    buildings = assign_buildings_to_towns(raw_buildings, town_polygons)
    save_stage(buildings, "building_master_base")
    return buildings


def match_transactions_to_buildings(transactions: pd.DataFrame, buildings: pd.DataFrame) -> pd.DataFrame:
    transaction_frame = transactions.copy()
    building_frame = buildings.copy()
    if "postal_code" in transaction_frame.columns and "postal_code" in building_frame.columns:
        transaction_frame["building_key"] = transaction_frame["block"].astype("string").str.strip().str.upper() + "|" + transaction_frame["postal_code"].astype("string").str.strip()
        matched = transaction_frame.merge(
            building_frame,
            on=["building_key"],
            how="left",
            suffixes=("", "_building"),
        )
        matched["match_method"] = matched["building_latitude"].notna().map({True: "building_key", False: "unmatched"})
    else:
        matched = transaction_frame.merge(
            building_frame,
            on=["town", "block"],
            how="left",
            suffixes=("", "_building"),
        )
        matched["match_method"] = matched["building_latitude"].notna().map({True: "town_block", False: "unmatched"})

    matched["building_match_status"] = matched["building_match_status"].where(
        matched["building_match_status"].notna(),
        "transaction_only",
    )
    save_stage(matched, "transaction_building_matches")
    return matched


def copy_city_area_boundaries(source_geojson: Path, target_geojson: Path) -> Path:
    target_geojson.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_geojson, target_geojson)
    log_step(f"Copied city-area boundary geojson to {target_geojson}.")
    return target_geojson
