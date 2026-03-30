from __future__ import annotations

import argparse
import json

import pandas as pd

from src.common.geography import HDB_TOWN_TO_PLANNING_AREAS, get_planning_area_to_town_map
from src.analysis.section1.helpers import (
    ensure_section1_results_dir,
    load_planning_area_geojson_payload,
    load_processed_frame,
    section1_output_path,
    write_section1_csv,
)

ALL_FLAT_TYPE_LABEL = "ALL FLAT TYPE"

PLANNING_AREA_MAP_EXPORT_COLUMNS = [
    "transaction_year",
    "planning_area_name_single",
    "town",
    "flat_type",
    "planning_area_match_status",
    "map_label",
    "map_region_key",
    "map_region_type",
    "transactions",
    "median_price",
    "median_floor_area",
    "median_price_per_sqm",
    "distance_to_cbd_km",
    "nearest_mrt_distance_km",
    "median_flat_age",
]

PLANNING_AREA_OVERVIEW_EXPORT_COLUMNS = [
    "planning_area_name",
    "town",
    "planning_area_match_status",
    "map_label",
    "map_region_key",
    "map_region_type",
    "transactions",
    "median_price",
    "median_floor_area",
    "median_price_per_sqm",
    "distance_to_cbd_km",
    "nearest_mrt_distance_km",
    "median_flat_age",
]

DASHBOARD_MARKET_EXPORT_COLUMNS = [
    "transaction_year",
    "town",
    "flat_type",
    "transactions",
    "median_price",
    "median_price_per_sqm",
    "median_floor_area",
    "map_region_key",
    "map_label",
    "map_region_type",
]
def planning_area_match_status(town: str) -> str:
    if town == "KALLANG/WHAMPOA":
        return "approximate"
    if town in HDB_TOWN_TO_PLANNING_AREAS:
        return "direct"
    return "unmatched"


def build_overview_extract(frame: pd.DataFrame) -> pd.DataFrame:
    by_town = (
        frame.groupby(["transaction_year", "town", "flat_type"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    national = (
        frame.groupby(["transaction_year", "flat_type"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    national["town"] = "NATIONAL"
    return pd.concat([national, by_town], ignore_index=True)


def build_market_overview_dashboard_extract(frame: pd.DataFrame) -> pd.DataFrame:
    base = (
        frame.groupby(["transaction_year", "town", "flat_type"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    town_all = (
        frame.groupby(["transaction_year", "town"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    town_all["flat_type"] = ALL_FLAT_TYPE_LABEL
    national_flat = (
        frame.groupby(["transaction_year", "flat_type"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    national_flat["town"] = "NATIONAL"
    national_all = (
        frame.groupby(["transaction_year"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
        )
        .reset_index()
    )
    national_all["town"] = "NATIONAL"
    national_all["flat_type"] = ALL_FLAT_TYPE_LABEL

    dashboard = pd.concat([base, town_all, national_flat, national_all], ignore_index=True)
    dashboard["is_national"] = dashboard["town"].eq("NATIONAL")
    dashboard["is_all_flat_type"] = dashboard["flat_type"].eq(ALL_FLAT_TYPE_LABEL)
    dashboard["town_scope"] = dashboard["town"].where(~dashboard["is_national"], "NATIONAL")
    dashboard["flat_type_scope"] = dashboard["flat_type"].where(~dashboard["is_all_flat_type"], ALL_FLAT_TYPE_LABEL)
    dashboard["map_region_key"] = dashboard["town"]
    dashboard["map_label"] = dashboard["map_region_key"]
    dashboard["map_region_type"] = dashboard["town"].where(~dashboard["is_national"], "country")
    dashboard["map_region_type"] = dashboard["map_region_type"].where(
        dashboard["map_region_type"].eq("country"),
        "hdb_town",
    )
    return dashboard.sort_values(["transaction_year", "town", "flat_type"]).reset_index(drop=True)


def build_planning_area_map_extract(frame: pd.DataFrame) -> pd.DataFrame:
    recent = frame[frame["transaction_year"] >= 2018].copy()
    grouped = (
        recent.groupby(["town"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_floor_area=("floor_area_sqm", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            town_latitude=("town_latitude", "median"),
            town_longitude=("town_longitude", "median"),
            distance_to_cbd_km=("distance_to_cbd_km", "median"),
            nearest_mrt_distance_km=("nearest_mrt_distance_km", "median"),
            median_flat_age=("flat_age", "median"),
        )
        .reset_index()
    )
    grouped["planning_area_name"] = grouped["town"].map(
        lambda town: "|".join(HDB_TOWN_TO_PLANNING_AREAS.get(town, [])) or None
    )
    grouped["planning_area_match_status"] = grouped["town"].map(planning_area_match_status)
    grouped["map_label"] = grouped["town"]
    grouped["map_region_key"] = grouped["town"]
    grouped["map_region_type"] = "hdb_town"
    return grouped.sort_values(["planning_area_match_status", "town", "median_price"], ascending=[True, True, False])


def build_planning_area_map_extract_by_year(frame: pd.DataFrame, planning_areas: list[str] | None = None) -> pd.DataFrame:
    recent = frame[frame["transaction_year"] >= 2018].copy()
    grouped = (
        recent.groupby(["transaction_year", "town", "flat_type"], dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            median_price=("resale_price", "median"),
            median_floor_area=("floor_area_sqm", "median"),
            median_price_per_sqm=("price_per_sqm", "median"),
            town_latitude=("town_latitude", "median"),
            town_longitude=("town_longitude", "median"),
            distance_to_cbd_km=("distance_to_cbd_km", "median"),
            nearest_mrt_distance_km=("nearest_mrt_distance_km", "median"),
            median_flat_age=("flat_age", "median"),
        )
        .reset_index()
    )
    years = sorted(recent["transaction_year"].dropna().unique())
    flat_types = sorted(recent["flat_type"].dropna().unique())
    if planning_areas is None:
        planning_areas = sorted(get_planning_area_to_town_map())
    planning_area_to_town = get_planning_area_to_town_map()
    scaffold_records = []
    for year in years:
        for planning_area_name in planning_areas:
            town = planning_area_to_town.get(planning_area_name)
            match_status = "direct" if town else "unmatched"
            if town == "KALLANG/WHAMPOA":
                match_status = "approximate"
            map_label = town or planning_area_name
            for flat_type in flat_types:
                scaffold_records.append(
                    {
                        "transaction_year": year,
                        "planning_area_name_single": planning_area_name,
                        "town": town,
                        "flat_type": flat_type,
                        "planning_area_match_status": match_status,
                        "map_label": map_label,
                        "map_region_key": town or planning_area_name,
                        "map_region_type": "hdb_town" if town else "planning_area_only",
                    }
                )
    scaffold = pd.DataFrame(scaffold_records)
    grouped["planning_area_name_single"] = grouped["town"].map(
        lambda town: HDB_TOWN_TO_PLANNING_AREAS.get(town, [None])[0]
        if len(HDB_TOWN_TO_PLANNING_AREAS.get(town, [])) == 1
        else None
    )
    grouped = scaffold.merge(grouped, on=["transaction_year", "town", "flat_type"], how="left", suffixes=("", "_agg"))
    grouped["transactions"] = grouped["transactions"].fillna(0).astype(int)
    grouped["planning_area_name"] = grouped["town"].map(
        lambda town: "|".join(HDB_TOWN_TO_PLANNING_AREAS.get(town, [])) or None
    )
    grouped["planning_area_name_single"] = grouped["planning_area_name_single"].fillna(grouped["planning_area_name_single_agg"])
    grouped["planning_area_name_single"] = grouped["planning_area_name_single"].fillna(grouped["planning_area_name"])
    grouped["planning_area_match_status"] = grouped["planning_area_match_status"].fillna(
        grouped["town"].map(planning_area_match_status)
    )
    grouped["map_label"] = grouped["map_label"].fillna(grouped["town"])
    grouped["map_region_key"] = grouped["map_region_key"].fillna(grouped["town"])
    grouped["map_region_type"] = grouped["map_region_type"].fillna("hdb_town")
    drop_columns = [column for column in grouped.columns if column.endswith("_agg")]
    if drop_columns:
        grouped = grouped.drop(columns=drop_columns)
    return grouped.sort_values(
        ["transaction_year", "planning_area_match_status", "map_label", "flat_type"],
        ascending=[False, True, True, True],
    )


def build_map_region_diagnostics(frame: pd.DataFrame, planning_areas: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    transaction_towns = sorted(set(frame["town"].dropna()))
    mapped_towns = sorted(HDB_TOWN_TO_PLANNING_AREAS.keys())
    transaction_towns_not_in_map = sorted(set(transaction_towns) - set(mapped_towns))
    planning_area_to_town = get_planning_area_to_town_map()
    map_regions_without_transaction_mapping = sorted(
        planning_area for planning_area in planning_areas if planning_area not in planning_area_to_town
    )
    left = pd.DataFrame({"transaction_town_not_in_region_map": transaction_towns_not_in_map})
    right = pd.DataFrame({"region_map_area_without_transaction_town_mapping": map_regions_without_transaction_mapping})
    return left, right


def print_map_region_diagnostics(
    transaction_towns_not_in_map: pd.DataFrame,
    region_map_areas_without_mapping: pd.DataFrame,
) -> None:
    missing_towns = transaction_towns_not_in_map["transaction_town_not_in_region_map"].dropna().tolist()
    missing_regions = (
        region_map_areas_without_mapping["region_map_area_without_transaction_town_mapping"].dropna().tolist()
    )

    print("Transaction towns not in region map mapping:")
    if missing_towns:
        for town in missing_towns:
            print(f"- {town}")
    else:
        print("- None")


def export_dashboard_1_assets(frame: pd.DataFrame) -> dict[str, str]:
    ensure_section1_results_dir()
    overview = build_overview_extract(frame)
    market_overview = build_market_overview_dashboard_extract(frame)
    write_section1_csv(overview, "overview_transactions.csv", kind="final")
    write_section1_csv(
        market_overview.loc[:, DASHBOARD_MARKET_EXPORT_COLUMNS],
        "dashboard_market_overview.csv",
        kind="final",
    )

    return {
        "overview_transactions": str(section1_output_path("overview_transactions.csv", kind="final")),
        "dashboard_market_overview": str(section1_output_path("dashboard_market_overview.csv", kind="final")),
    }


def export_planning_area_assets(frame: pd.DataFrame, payload: dict | None) -> dict[str, str]:
    ensure_section1_results_dir()
    if payload is None:
        return {}
    target_geojson = section1_output_path(
        "planning_area_boundaries_2019.geojson",
        kind="diagnostic"
    )
    target_geojson.write_text(json.dumps(payload), encoding="utf-8")

    map_extract = build_planning_area_map_extract(frame)
    write_section1_csv(
        map_extract.loc[:, PLANNING_AREA_OVERVIEW_EXPORT_COLUMNS],
        "planning_area_map_metrics.csv",
        kind="final",
    )

    planning_areas = sorted(
        {
            feature.get("properties", {}).get("PLN_AREA_N")
            for feature in payload.get("features", [])
            if feature.get("properties", {}).get("PLN_AREA_N")
        }
    )
    map_extract_by_year = build_planning_area_map_extract_by_year(frame, planning_areas)
    write_section1_csv(
        map_extract_by_year.loc[:, PLANNING_AREA_MAP_EXPORT_COLUMNS],
        "planning_area_map_metrics_by_year.csv",
        kind="final",
    )

    enriched_payload = json.loads(json.dumps(payload))
    planning_area_to_town = get_planning_area_to_town_map()
    for feature in enriched_payload.get("features", []):
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
    enriched_geojson = section1_output_path("planning_area_hdb_map_2019.geojson", kind="final")
    enriched_geojson.write_text(json.dumps(enriched_payload), encoding="utf-8")

    lookup = pd.DataFrame(
        [
            {
                "town": town,
                "planning_area_name": "|".join(HDB_TOWN_TO_PLANNING_AREAS.get(town, [])) or None,
                "planning_area_match_status": planning_area_match_status(town),
            }
            for town in sorted(set(frame["town"].dropna()))
        ]
    )
    write_section1_csv(lookup, "planning_area_town_lookup.csv", kind="diagnostic")
    left, right = build_map_region_diagnostics(frame, planning_areas)
    write_section1_csv(left, "transaction_towns_not_in_region_map.csv", kind="diagnostic")
    write_section1_csv(right, "region_map_areas_without_transaction_town_mapping.csv", kind="diagnostic")
    print_map_region_diagnostics(left, right)
    return {
        "planning_area_boundaries": str(target_geojson),
        "planning_area_map_metrics": str(section1_output_path("planning_area_map_metrics.csv", kind="final")),
        "planning_area_map_metrics_by_year": str(section1_output_path("planning_area_map_metrics_by_year.csv", kind="final")),
        "planning_area_hdb_map": str(enriched_geojson),
        "planning_area_town_lookup": str(section1_output_path("planning_area_town_lookup.csv", kind="diagnostic")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Section 1 Dashboard 1 market-overview assets.")
    parser.parse_args()
    frame = load_processed_frame()
    export_planning_area_assets(frame, load_planning_area_geojson_payload())
    export_dashboard_1_assets(frame)


if __name__ == "__main__":
    main()
