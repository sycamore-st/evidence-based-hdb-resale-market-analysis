from __future__ import annotations

import argparse

from src.analysis.section1.dashboard_1 import (
    export_dashboard_1_assets,
    export_planning_area_assets,
)
from src.analysis.section1.dashboard_2 import build_building_transaction_budget_extract, export_dashboard_2_assets
from src.analysis.section1.dashboard_3 import (
    export_dashboard_3_assets,
)
from src.analysis.section1.helpers import (
    ensure_section1_results_dir,
    load_planning_area_geojson_payload,
    load_processed_frame,
    section1_output_path,
)
from src.common.utils import write_markdown


def write_dashboard_spec() -> None:
    ensure_section1_results_dir()
    spec_path = section1_output_path("dashboard_spec.md", kind="diagnostic")
    write_markdown(
        spec_path,
        [
            "# Tableau Dashboard Spec",
            "",
            "## Dashboard 1: Market Overview",
            "- Line chart: yearly transactions by town with `flat_type` filter.",
            "- Dual-axis or side-by-side line chart: yearly median price vs median price per sqm.",
            "- KPI tiles: latest-year national transactions and national median price.",
            "",
            "## Dashboard 2: Budget to Space",
            "- Parameter: `budget`.",
            "- Ranked bar chart: towns and flat types sorted by `median_floor_area` among options below the budget.",
            "- Scatter plot: `median_price` vs `median_floor_area`, colored by town and sized by transactions.",
            "",
            "## Dashboard 3: Location Optimizer",
            "- Parameter: `budget`.",
            "- Map: town centroids with tooltips for price, floor area, nearest MRT, and CBD distance.",
            "- Ranked table: `overall_location_score`, `median_price`, `nearest_mrt_station`, `nearest_mrt_distance_km`.",
            "",
            "All dashboards should keep a prominent banner headline, a flat-type filter, and concise annotations that tie directly to the insight being shown.",
        ],
    )


def write_field_dictionary() -> None:
    import pandas as pd

    field_dictionary = pd.DataFrame(
        [
            ("Transaction Year", "Calendar year of the transaction"),
            ("Town", "HDB town or NATIONAL aggregate"),
            ("Flat Type", "Flat type used for filters, including ALL FLAT TYPE"),
            ("Transactions", "Number of observed transactions"),
            ("Median Price", "Median resale price in SGD"),
            ("Median Price Per Sqm", "Median resale price per square meter"),
            ("Median Floor Area", "Median floor area in square meters"),
            ("Region Key", "Stable selection key shared between the map and dashboard fact table"),
            ("Region Label", "Display label shared between the map and dashboard fact table"),
            ("Region Type", "Region type in the dashboard fact table: hdb_town, planning_area_only, or country"),
            ("budget", "Buyer input budget used for dashboard B"),
            ("budget_slack", "Budget minus town-flat median price"),
            ("nearest_mrt_station", "Closest MRT station to the town centroid"),
            ("nearest_mrt_distance_km", "Distance in km from town centroid to closest MRT station"),
            ("distance_to_cbd_km", "Distance in km from town centroid to Raffles Place proxy"),
            ("overall_location_score", "Composite index for budget, MRT access, and CBD proximity"),
            ("Planning Area", "URA planning area used to join the polygon map to HDB towns where possible"),
            ("Region Match Status", "Mapping quality flag: direct, approximate, or unmatched"),
            ("Distance To Cbd Km", "Distance in km from town centroid to Raffles Place proxy"),
            ("Nearest Mrt Distance Km", "Distance in km from town centroid to closest MRT station"),
            ("Median Flat Age", "Median flat age in years"),
        ],
        columns=["field_name", "description"],
    )
    field_dictionary.to_csv(section1_output_path("field_dictionary.csv", kind="diagnostic"), index=False)


def export_tableau_assets(frame) -> None:
    planning_payload = load_planning_area_geojson_payload()
    export_planning_area_assets(frame, planning_payload)
    export_dashboard_1_assets(frame)
    export_dashboard_2_assets(frame)
    building_budget = build_building_transaction_budget_extract(frame)
    export_dashboard_3_assets(
        frame,
        building_budget=building_budget,
        town_boundary_geojson=section1_output_path("planning_area_hdb_map_2019.geojson", kind="final"),
    )
    write_field_dictionary()
    write_dashboard_spec()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Section 1 Tableau assets from the processed resale dataset.")
    parser.parse_args()
    frame = load_processed_frame()
    export_tableau_assets(frame)


if __name__ == "__main__":
    main()
