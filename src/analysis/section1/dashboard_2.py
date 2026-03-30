from __future__ import annotations

import argparse

import pandas as pd

from src.analysis.section1.helpers import (
    ensure_section1_results_dir,
    load_processed_frame,
    section1_output_path,
    write_section1_csv,
)

BUDGET_BUCKETS = [300_000, 400_000, 500_000, 600_000, 700_000, 800_000, 1_000_000]


def build_budget_extract(frame: pd.DataFrame) -> pd.DataFrame:
    return build_budget_extract_at_grain(frame, ["transaction_year", "town", "flat_type"])


def build_budget_extract_at_grain(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    percentiles = (
        frame.groupby(group_columns, dropna=False)
        .agg(
            transactions=("resale_price", "size"),
            min_price=("resale_price", "min"),
            median_price=("resale_price", "median"),
            max_price=("resale_price", "max"),
            median_price_per_sqm=("price_per_sqm", "median"),
            p25_price=("resale_price", lambda s: s.quantile(0.25)),
            p75_price=("resale_price", lambda s: s.quantile(0.75)),
            min_floor_area=("floor_area_sqm", "min"),
            median_floor_area=("floor_area_sqm", "median"),
            p25_floor_area=("floor_area_sqm", lambda s: s.quantile(0.25)),
            p75_floor_area=("floor_area_sqm", lambda s: s.quantile(0.75)),
            max_floor_area=("floor_area_sqm", "max"),
            min_flat_age=("flat_age", "min"),
            median_flat_age=("flat_age", "median"),
            p25_flat_age=("flat_age", lambda s: s.quantile(0.25)),
            p75_flat_age=("flat_age", lambda s: s.quantile(0.75)),
            max_flat_age=("flat_age", "max"),
        )
        .reset_index()
    )
    budget_rows = []
    for budget in BUDGET_BUCKETS:
        eligible = percentiles[percentiles["median_price"] <= budget].copy()
        eligible["budget"] = budget
        eligible["budget_slack"] = budget - eligible["median_price"]
        eligible["median_price_per_sqft"] = eligible["median_price_per_sqm"] / 10.7639104167097
        eligible["size_score"] = eligible["median_floor_area"]
        budget_rows.append(eligible)
    if not budget_rows:
        return pd.DataFrame(
            columns=percentiles.columns.tolist() + ["budget", "budget_slack", "median_price_per_sqft", "size_score"]
        )
    sort_columns = [
        column
        for column in ["transaction_year", "budget", "size_score"]
        if column in group_columns or column in {"budget", "size_score"}
    ]
    ascending = [True] * len(sort_columns)
    if "size_score" in sort_columns:
        ascending[sort_columns.index("size_score")] = False
    return pd.concat(budget_rows, ignore_index=True).sort_values(sort_columns, ascending=ascending)


def build_budget_metrics_extract(frame: pd.DataFrame) -> pd.DataFrame:
    budget = build_budget_extract(frame)
    metric_map = {
        "Min": ("min_price", "min_floor_area", "min_flat_age"),
        "P25": ("p25_price", "p25_floor_area", "p25_flat_age"),
        "Median": ("median_price", "median_floor_area", "median_flat_age"),
        "P75": ("p75_price", "p75_floor_area", "p75_flat_age"),
        "Max": ("max_price", "max_floor_area", "max_flat_age"),
    }
    metric_frames = []
    base_columns = [
        "transaction_year",
        "town",
        "flat_type",
        "transactions",
        "budget",
        "budget_slack",
        "median_price_per_sqft",
        "size_score",
    ]
    for metric_name, (price_col, floor_col, age_col) in metric_map.items():
        metric_frame = budget[base_columns].copy()
        metric_frame["metric"] = metric_name
        metric_frame["price_value"] = budget[price_col]
        metric_frame["floor_area_value"] = budget[floor_col]
        metric_frame["flat_age_value"] = budget[age_col]
        metric_frame["price_per_sqm_value"] = metric_frame["price_value"] / metric_frame["floor_area_value"]
        metric_frames.append(metric_frame)
    metric_extract = pd.concat(metric_frames, ignore_index=True)
    return metric_extract.sort_values(
        ["transaction_year", "budget", "town", "flat_type", "metric"],
        ascending=[True, True, True, True, True],
    ).reset_index(drop=True)


def build_building_transaction_budget_extract(frame: pd.DataFrame) -> pd.DataFrame:
    return build_budget_extract_at_grain(frame, ["transaction_year", "town", "block", "flat_type"])


def build_budget_legend_extract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"legend_panel": "Floor Area", "metric": "Min", "legend_value": 20, "legend_note": "Range start"},
            {"legend_panel": "Floor Area", "metric": "Median", "legend_value": 50, "legend_note": "Median dot"},
            {"legend_panel": "Floor Area", "metric": "Max", "legend_value": 80, "legend_note": "Range end"},
            {"legend_panel": "Price", "metric": "Min", "legend_value": 20, "legend_note": "Range start"},
            {"legend_panel": "Price", "metric": "Median", "legend_value": 50, "legend_note": "Median dot"},
            {"legend_panel": "Price", "metric": "Max", "legend_value": 80, "legend_note": "Range end"},
        ]
    )


def export_dashboard_2_assets(frame: pd.DataFrame) -> dict[str, str]:
    ensure_section1_results_dir()
    budget = build_budget_extract(frame)
    budget_metrics = build_budget_metrics_extract(frame)
    budget_legend = build_budget_legend_extract()
    write_section1_csv(budget, "budget_affordability.csv", kind="final")
    write_section1_csv(budget_metrics, "budget_affordability_metrics.csv", kind="final")
    write_section1_csv(budget_legend, "budget_affordability_legend.csv", kind="final")
    return {
        "budget_affordability": str(section1_output_path("budget_affordability.csv", kind="final")),
        "budget_affordability_metrics": str(section1_output_path("budget_affordability_metrics.csv", kind="final")),
        "budget_affordability_legend": str(section1_output_path("budget_affordability_legend.csv", kind="final")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Section 1 Dashboard 2 budget-to-space assets.")
    parser.parse_args()
    frame = load_processed_frame()
    export_dashboard_2_assets(frame)


if __name__ == "__main__":
    main()
