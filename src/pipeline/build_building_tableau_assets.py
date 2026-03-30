from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.analysis.section1.dashboard_2 import build_building_transaction_budget_extract
from src.analysis.section1.dashboard_3 import (
    BUILDING_GEOMETRY_EXPORT_COLUMNS,
    BUILDING_MATCH_SUMMARY_EXPORT_COLUMNS,
    BUILDING_OPTIMIZER_EXPORT_COLUMNS,
    build_building_optimizer_extract,
    filter_building_optimizer_for_tableau,
)
from src.analysis.section1.helpers import section1_output_path, write_section1_csv
from src.common.config import SECTION1_OUTPUT_RESULTS
from src.pipeline.calculate_building_poi import (
    build_building_poi_points,
    build_building_poi_summary,
    compute_building_poi_metrics,
)
from src.pipeline.ingest_sources import (
    fetch_building_geometry,
    fetch_planning_area_geometry,
    fetch_poi_sources,
    fetch_transactions_base,
)
from src.pipeline.map_entities import (
    assign_buildings_to_city_areas,
    build_enriched_city_area_geojson,
    build_town_city_area_lookup,
    copy_city_area_boundaries,
    match_transactions_to_buildings,
)
from src.pipeline.pipeline_common import ensure_pipeline_directories, load_stage, log_step

TABLEAU = SECTION1_OUTPUT_RESULTS


def export_building_outputs(
    *,
    transactions: pd.DataFrame,
    building_payload: dict,
    buildings_with_poi: pd.DataFrame,
    poi_points: pd.DataFrame,
) -> dict[str, str]:
    TABLEAU.mkdir(parents=True, exist_ok=True)
    building_budget = build_building_transaction_budget_extract(
        transactions[
            [
                "transaction_year",
                "town",
                "block",
                "flat_type",
                "resale_price",
                "price_per_sqm",
                "floor_area_sqm",
                "flat_age",
            ]
        ].copy()
    )
    building_optimizer_raw, match_summary = build_building_optimizer_extract(buildings_with_poi, building_budget)
    building_optimizer = filter_building_optimizer_for_tableau(building_optimizer_raw)

    outputs = {}
    write_section1_csv(poi_points, "building_poi_points.csv", kind="final")
    outputs["building_poi_points"] = str(section1_output_path("building_poi_points.csv", kind="final"))
    write_section1_csv(
        buildings_with_poi.loc[:, BUILDING_GEOMETRY_EXPORT_COLUMNS],
        "building_geometry_lookup.csv",
        kind="final",
    )
    outputs["building_geometry_lookup"] = str(section1_output_path("building_geometry_lookup.csv", kind="final"))
    write_section1_csv(
        building_optimizer_raw.loc[:, BUILDING_OPTIMIZER_EXPORT_COLUMNS],
        "building_optimizer_raw.csv",
        kind="diagnostic",
    )
    outputs["building_optimizer_raw"] = str(section1_output_path("building_optimizer_raw.csv", kind="diagnostic"))
    write_section1_csv(
        building_optimizer.loc[:, BUILDING_OPTIMIZER_EXPORT_COLUMNS],
        "building_optimizer.csv",
        kind="final",
    )
    outputs["building_optimizer"] = str(section1_output_path("building_optimizer.csv", kind="final"))
    write_section1_csv(
        match_summary.loc[:, BUILDING_MATCH_SUMMARY_EXPORT_COLUMNS],
        "building_transaction_match_summary.csv",
        kind="diagnostic",
    )
    outputs["building_transaction_match_summary"] = str(
        section1_output_path("building_transaction_match_summary.csv", kind="diagnostic")
    )

    properties_by_key = {
        row["building_key"]: row
        for row in buildings_with_poi[BUILDING_GEOMETRY_EXPORT_COLUMNS].to_dict("records")
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
    geojson_path = section1_output_path("hdb_existing_buildings.geojson", kind="final")
    geojson_path.write_text(json.dumps(building_payload), encoding="utf-8")
    outputs["hdb_existing_buildings_geojson"] = str(geojson_path)
    log_step(f"Wrote {geojson_path}")
    return outputs


def build_building_tableau_assets(
    *,
    refresh_transactions: bool = False,
    refresh_buildings: bool = False,
    refresh_planning_areas: bool = False,
    refresh_mrt: bool = False,
    refresh_bus: bool = False,
    refresh_school: bool = False,
) -> dict[str, object]:
    ensure_pipeline_directories()
    transactions = fetch_transactions_base(refresh=refresh_transactions)
    build_town_city_area_lookup(transactions["town"])

    planning_geojson = fetch_planning_area_geometry(refresh=refresh_planning_areas)
    copy_city_area_boundaries(planning_geojson, section1_output_path("planning_area_boundaries_2019.geojson", kind="diagnostic"))
    build_enriched_city_area_geojson(planning_geojson, section1_output_path("planning_area_hdb_map_2019.geojson", kind="final"))

    building_payload, raw_buildings, _ = fetch_building_geometry(refresh=refresh_buildings)
    assigned_buildings = assign_buildings_to_city_areas(
        raw_buildings,
        section1_output_path("planning_area_hdb_map_2019.geojson", kind="final"),
    )
    poi_sources = fetch_poi_sources(
        refresh_mrt=refresh_mrt,
        refresh_bus=refresh_bus,
        refresh_school=refresh_school,
    )
    buildings_with_poi = compute_building_poi_metrics(
        assigned_buildings,
        mrt_points=poi_sources["mrt"],
        bus_stop_points=poi_sources["bus"],
        school_points=poi_sources["school"],
    )
    poi_summary = build_building_poi_summary(buildings_with_poi)
    _ = match_transactions_to_buildings(transactions, buildings_with_poi)
    poi_points = build_building_poi_points(
        buildings_with_poi,
        mrt_points=poi_sources["mrt"],
        bus_stop_points=poi_sources["bus"],
        school_points=poi_sources["school"],
    )
    export_paths = export_building_outputs(
        transactions=transactions,
        building_payload=building_payload,
        buildings_with_poi=buildings_with_poi,
        poi_points=poi_points,
    )
    return {
        "transactions_base_rows": int(transactions.shape[0]),
        "town_city_area_lookup_rows": int(load_stage("town_city_area_lookup").shape[0]),
        "building_master_rows": int(buildings_with_poi.shape[0]),
        "building_poi_summary_rows": int(poi_summary.shape[0]),
        "output_paths": export_paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the building-centric Tableau assets for Section 1, including geometry, POI metrics, and optimizer outputs."
    )
    parser.add_argument("--refresh-transactions", action="store_true")
    parser.add_argument("--refresh-buildings", action="store_true")
    parser.add_argument("--refresh-planning-areas", action="store_true")
    parser.add_argument("--refresh-mrt", action="store_true")
    parser.add_argument("--refresh-bus", action="store_true")
    parser.add_argument("--refresh-school", action="store_true")
    args = parser.parse_args()
    build_building_tableau_assets(
        refresh_transactions=args.refresh_transactions,
        refresh_buildings=args.refresh_buildings,
        refresh_planning_areas=args.refresh_planning_areas,
        refresh_mrt=args.refresh_mrt,
        refresh_bus=args.refresh_bus,
        refresh_school=args.refresh_school,
    )


if __name__ == "__main__":
    main()
