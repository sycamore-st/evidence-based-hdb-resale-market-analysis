from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
import statsmodels.formula.api as smf

from src.analysis.section3.S3_helpers import (
    ACCENT,
    BLUE,
    GRAY,
    GREEN,
    ORANGE,
    REPORTS,
    SECTION3_FIGURE_REPORTS,
    annotate_bar_values,
    annotate_point_values,
    annotate_series_endpoints,
    configure_logging,
    load_frame,
    load_figure_data,
    save_chart_data,
    save_plotly_figure,
    save_svg_and_html,
    set_write_html,
    style_bar_patches,
)
from src.common.config import PROJECT_ROOT, SECTION1_OUTPUT_DIAGNOSTICS
from src.pipeline.features import parse_mrt_geojson
from src.pipeline.hdb_api import fetch_mrt_dataset_dir

DTL2_STAGE2_STATIONS = [
    "BUKIT PANJANG MRT STATION",
    "CASHEW MRT STATION",
    "HILLVIEW MRT STATION",
    "BEAUTY WORLD MRT STATION",
    "KING ALBERT PARK MRT STATION",
    "SIXTH AVENUE MRT STATION",
    "TAN KAH KEE MRT STATION",
    "BOTANIC GARDENS MRT STATION",
    "STEVENS MRT STATION",
    "NEWTON MRT STATION",
    "LITTLE INDIA MRT STATION",
    "ROCHOR MRT STATION",
]
DTL2_BUKIT_TIMAH_CORRIDOR_TOWNS = [
    "BUKIT PANJANG",
    "CHOA CHU KANG",
    "BUKIT BATOK",
    "BUKIT TIMAH",
]
DTL2_STAGE2_OPEN_DATE = pd.Timestamp("2015-12-27")
DTL2_STAGE2_POST_MONTH = pd.Timestamp("2015-12-01")
DTL2_STAGE2_EVENT_YEAR = 2016
TREATMENT_DISTANCE_KM = 1.0
CONTROL_MIN_DISTANCE_KM = 1.5
CONTROL_MAX_DISTANCE_KM = 4.0
MATCH_CONTROL_MIN_DISTANCE_KM = 1.5
MATCH_CONTROL_MAX_DISTANCE_KM = 4.0
MATCH_CONTROLS_PER_TREATED = 2
DTL2_EXPERIMENT_TREATMENT_BANDS_KM = [
    (0.0, 0.25, "0-250m"),
    (0.25, 0.50, "250-500m"),
    (0.50, 0.75, "500-750m"),
    (0.75, 1.00, "750m-1.0km"),
]
DTL2_EXPERIMENT_CONTROL_LABEL = "1.5-4.0km control"
PLANNING_AREA_BOUNDARIES_PATH = SECTION1_OUTPUT_DIAGNOSTICS / "planning_area_boundaries_2019.geojson"
PLANNING_AREA_BOUNDARIES_FALLBACK_PATH = (
    PROJECT_ROOT / "outputs_submission" / "section1" / "results" / "diagnostics" / "planning_area_boundaries_2019.geojson"
)
CORRIDOR_MAP_LABEL_STATIONS = [
    "BUKIT PANJANG MRT STATION",
    "BEAUTY WORLD MRT STATION",
    "BOTANIC GARDENS MRT STATION",
    "LITTLE INDIA MRT STATION",
]
TREATMENT_FOCUS_STATIONS = [
    "BEAUTY WORLD MRT STATION",
    "BUKIT PANJANG MRT STATION",
    "CHOA CHU KANG MRT STATION",
]
TREATMENT_LABEL_STATIONS = [
    "BEAUTY WORLD MRT STATION",
    "HILLVIEW MRT STATION",
    "CASHEW MRT STATION",
    "BUKIT PANJANG MRT STATION",
    "CHOA CHU KANG MRT STATION",
]


def _slugify(value: str) -> str:
    return value.lower().replace("/", "_").replace(" ", "_")


def _rgba_string(color: str, alpha: float) -> str:
    color = color.lstrip("#")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    return f"rgba({red},{green},{blue},{alpha:.2f})"


def _save_model_outputs(stem: str, model: object) -> tuple[str, str]:
    SECTION3_FIGURE_REPORTS.mkdir(parents=True, exist_ok=True)
    summary_path = SECTION3_FIGURE_REPORTS / f"{stem}_summary.txt"
    coef_path = SECTION3_FIGURE_REPORTS / f"{stem}_coefficients.csv"
    summary_path.write_text(str(model.summary()), encoding="utf-8")
    coef_table = pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.values,
            "pvalue": model.pvalues.reindex(model.params.index).values,
            "ci_low": model.conf_int().iloc[:, 0].reindex(model.params.index).values,
            "ci_high": model.conf_int().iloc[:, 1].reindex(model.params.index).values,
        }
    )
    coef_table.to_csv(coef_path, index=False)
    return str(summary_path), str(coef_path)


def _load_dtl2_station_points() -> pd.DataFrame:
    stations = parse_mrt_geojson(fetch_mrt_dataset_dir(refresh=False))
    dtl2 = stations.loc[stations["station_name"].isin(DTL2_STAGE2_STATIONS)].copy()
    if dtl2.empty:
        raise ValueError("No DTL2 stations were found in the MRT station dataset.")
    return dtl2.reset_index(drop=True)


def _load_named_station_points(station_names: list[str]) -> pd.DataFrame:
    stations = parse_mrt_geojson(fetch_mrt_dataset_dir(refresh=False))
    selected = stations.loc[stations["station_name"].isin(station_names)].copy()
    if selected.empty:
        raise ValueError(f"No MRT stations were found for {station_names}.")
    missing = sorted(set(station_names) - set(selected["station_name"].unique()))
    if missing:
        raise ValueError(f"Missing MRT station(s) in dataset: {missing}")
    order_map = {name: index for index, name in enumerate(station_names)}
    selected["station_order"] = selected["station_name"].map(order_map)
    return selected.sort_values("station_order").drop(columns="station_order").reset_index(drop=True)


def _focus_and_secondary_station_points(dtl2_stations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    focus_stations = _load_named_station_points(TREATMENT_FOCUS_STATIONS)
    secondary_stations = dtl2_stations.loc[~dtl2_stations["station_name"].isin(focus_stations["station_name"])].copy()
    if not secondary_stations.empty:
        secondary_order = {name: index for index, name in enumerate(DTL2_STAGE2_STATIONS)}
        secondary_stations["station_order"] = secondary_stations["station_name"].map(secondary_order)
        secondary_stations = secondary_stations.sort_values("station_order").drop(columns="station_order")
    return focus_stations.reset_index(drop=True), secondary_stations.reset_index(drop=True)


def _attach_dtl2_distance(sample: pd.DataFrame, dtl2_stations: pd.DataFrame) -> pd.DataFrame:
    enriched = sample.copy()
    coords = enriched[["building_latitude", "building_longitude"]].to_numpy(dtype=float)
    station_coords = dtl2_stations[["latitude", "longitude"]].to_numpy(dtype=float)

    lat1 = np.radians(coords[:, 0])[:, None]
    lon1 = np.radians(coords[:, 1])[:, None]
    lat2 = np.radians(station_coords[:, 0])[None, :]
    lon2 = np.radians(station_coords[:, 1])[None, :]
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    distances = 6371.0 * c

    station_names = dtl2_stations["station_name"].to_numpy()
    nearest_index = distances.argmin(axis=1)
    enriched["dtl2_distance_km"] = distances[np.arange(len(enriched)), nearest_index]
    enriched["nearest_dtl2_station"] = station_names[nearest_index]
    return enriched


def _event_study_sample(sample: pd.DataFrame) -> pd.DataFrame:
    event = sample.copy()
    # Annual event time is anchored to the first full post-opening year.
    event["event_time"] = event["transaction_year"] - DTL2_STAGE2_EVENT_YEAR
    event = event.loc[event["event_time"].between(-4, 2)].copy()
    for event_time in [-4, -3, -2, 0, 1, 2]:
        suffix = f"m{abs(event_time)}" if event_time < 0 else f"p{event_time}"
        event[f"treated_event_{suffix}"] = ((event["treated"] == 1) & (event["event_time"] == event_time)).astype(int)
    return event


def _event_study_table(model: object) -> pd.DataFrame:
    conf_int = model.conf_int()
    rows: list[dict[str, object]] = []
    mapping = {
        -4: "treated_event_m4",
        -3: "treated_event_m3",
        -2: "treated_event_m2",
        0: "treated_event_p0",
        1: "treated_event_p1",
        2: "treated_event_p2",
    }
    for event_time, term in mapping.items():
        coef = float(model.params[term])
        ci_low = float(conf_int.loc[term].iloc[0])
        ci_high = float(conf_int.loc[term].iloc[1])
        rows.append(
            {
                "event_time": event_time,
                "period_group": "Pre" if event_time < 0 else "Post",
                "label": f"{event_time:+d}",
                "coefficient": coef,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "effect_pct": float((np.exp(coef) - 1.0) * 100.0),
                "effect_pct_ci_low": float((np.exp(ci_low) - 1.0) * 100.0),
                "effect_pct_ci_high": float((np.exp(ci_high) - 1.0) * 100.0),
                "pvalue": float(model.pvalues[term]),
            }
        )
    return pd.DataFrame(rows).sort_values("event_time").reset_index(drop=True)


def _joint_test_pvalue(model: object, terms: list[str]) -> float:
    hypothesis = " = 0, ".join(terms) + " = 0"
    test = model.wald_test(hypothesis)
    return float(np.asarray(test.pvalue).item())


def _assign_experiment_distance_band(distances: pd.Series) -> pd.Series:
    band = pd.Series(pd.NA, index=distances.index, dtype="object")
    numeric = pd.to_numeric(distances, errors="coerce")
    for lower, upper, label in DTL2_EXPERIMENT_TREATMENT_BANDS_KM:
        if lower == 0.0:
            mask = (numeric >= lower) & (numeric <= upper)
        else:
            mask = (numeric > lower) & (numeric <= upper)
        band.loc[mask] = label
    control_mask = (numeric > CONTROL_MIN_DISTANCE_KM) & (numeric <= CONTROL_MAX_DISTANCE_KM)
    band.loc[control_mask] = DTL2_EXPERIMENT_CONTROL_LABEL
    return band


def _distance_band_experiment_effects(model: object) -> pd.DataFrame:
    conf_int = model.conf_int()
    rows: list[dict[str, object]] = []
    term_prefix = f"post:C(distance_experiment_band, Treatment(reference='{DTL2_EXPERIMENT_CONTROL_LABEL}'))[T."
    for _, _, label in DTL2_EXPERIMENT_TREATMENT_BANDS_KM:
        term = f"{term_prefix}{label}]"
        coef = float(model.params[term])
        ci_low = float(conf_int.loc[term].iloc[0])
        ci_high = float(conf_int.loc[term].iloc[1])
        rows.append(
            {
                "distance_band": label,
                "coefficient": coef,
                "effect_pct": float((np.exp(coef) - 1.0) * 100.0),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "effect_pct_ci_low": float((np.exp(ci_low) - 1.0) * 100.0),
                "effect_pct_ci_high": float((np.exp(ci_high) - 1.0) * 100.0),
                "pvalue": float(model.pvalues[term]),
            }
        )
    return pd.DataFrame(rows)


def _run_in_town_nearby_control_search(sample: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for town_name in DTL2_BUKIT_TIMAH_CORRIDOR_TOWNS:
        town_sample = sample.loc[sample["town"].eq(town_name)].copy()
        if town_sample.empty:
            continue
        for treat_km in [0.25, 0.5, 0.75, 1.0]:
            for width in [0.25, 0.5, 0.75, 1.0]:
                control_min = treat_km
                control_max = treat_km + width
                df = town_sample.loc[
                    (town_sample["dtl2_distance_km"] <= treat_km)
                    | (
                        (town_sample["dtl2_distance_km"] > control_min)
                        & (town_sample["dtl2_distance_km"] <= control_max)
                    )
                ].copy()
                df["treated"] = (df["dtl2_distance_km"] <= treat_km).astype(int)
                treated_rows = int(df["treated"].sum())
                control_rows = int((df["treated"] == 0).sum())
                if treated_rows < 80 or control_rows < 80:
                    continue
                did_model = smf.ols(
                    "log_price ~ treated * post + flat_age + floor_area_sqm + C(flat_type) + C(transaction_year)",
                    data=df,
                ).fit(cov_type="HC3")
                pre_period = df.loc[df["post"].eq(0)].copy()
                pretrend_model = smf.ols(
                    "log_price ~ treated * year_index + flat_age + floor_area_sqm + C(flat_type)",
                    data=pre_period,
                ).fit(cov_type="HC3")
                event_sample = _event_study_sample(df)
                event_terms = ["treated_event_m4", "treated_event_m3", "treated_event_m2", "treated_event_p0", "treated_event_p1", "treated_event_p2"]
                event_model = smf.ols(
                    "log_price ~ flat_age + floor_area_sqm + C(flat_type) + C(transaction_year) + " + " + ".join(event_terms),
                    data=event_sample,
                ).fit(cov_type="HC3")
                rows.append(
                    {
                        "town": town_name,
                        "treat_km": treat_km,
                        "control_min_km": control_min,
                        "control_max_km": control_max,
                        "control_width_km": width,
                        "rows": int(len(df)),
                        "treated_rows": treated_rows,
                        "control_rows": control_rows,
                        "did_effect_pct": float(np.exp(did_model.params["treated:post"]) - 1.0),
                        "did_p": float(did_model.pvalues["treated:post"]),
                        "pretrend_p": float(pretrend_model.pvalues["treated:year_index"]),
                        "lead_joint_p": _joint_test_pvalue(event_model, ["treated_event_m4", "treated_event_m3", "treated_event_m2"]),
                        "post_joint_p": _joint_test_pvalue(event_model, ["treated_event_p0", "treated_event_p1", "treated_event_p2"]),
                    }
                )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["town", "lead_joint_p", "pretrend_p"],
        ascending=[True, False, False]
    ).reset_index(drop=True)


def _building_pretrend_features(pre_period: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        pre_period.groupby("building_key")
        .agg(
            treated=("treated", "max"),
            town=("town", "first"),
            dtl2_distance_km=("dtl2_distance_km", "first"),
            building_latitude=("building_latitude", "first"),
            building_longitude=("building_longitude", "first"),
            avg_log_price=("log_price", "mean"),
            avg_price_per_sqm=("price_per_sqm", "mean"),
            avg_floor_area_sqm=("floor_area_sqm", "mean"),
            avg_flat_age=("flat_age", "mean"),
            transactions=("log_price", "size"),
            years_observed=("transaction_year", "nunique"),
        )
        .reset_index()
    )

    slope_rows: list[dict[str, object]] = []
    for building_key, group in pre_period.groupby("building_key"):
        ordered = group.sort_values("transaction_year")
        years = ordered["transaction_year"].to_numpy(dtype=float)
        values = ordered["log_price"].to_numpy(dtype=float)
        if np.unique(years).size < 2:
            slope = 0.0
        else:
            slope = float(np.polyfit(years, values, 1)[0])
        slope_rows.append({"building_key": building_key, "pretrend_slope": slope})

    slopes = pd.DataFrame(slope_rows)
    features = grouped.merge(slopes, on="building_key", how="left")
    features["pretrend_slope"] = features["pretrend_slope"].fillna(0.0)
    return features


def _matched_building_sample(sample: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pre_period = sample.loc[sample["post"].eq(0)].copy()
    features = _building_pretrend_features(pre_period)

    treated_features = features.loc[features["treated"].eq(1)].copy()
    control_features = features.loc[features["treated"].eq(0)].copy()
    control_features = control_features.loc[
        control_features["dtl2_distance_km"].between(MATCH_CONTROL_MIN_DISTANCE_KM, MATCH_CONTROL_MAX_DISTANCE_KM, inclusive="right")
    ].copy()

    match_columns = [
        "avg_log_price",
        "pretrend_slope",
        "avg_price_per_sqm",
        "avg_floor_area_sqm",
        "avg_flat_age",
    ]

    available_controls = control_features.copy()
    matches: list[dict[str, object]] = []

    for town, treated_town in treated_features.groupby("town"):
        control_pool = available_controls.loc[available_controls["town"].eq(town)].copy()
        if control_pool.empty:
            continue

        combined = pd.concat([treated_town[match_columns], control_pool[match_columns]], axis=0)
        scales = combined.std(ddof=0).replace(0, 1.0).fillna(1.0)

        for _, treated_row in treated_town.sort_values("building_key").iterrows():
            if control_pool.empty:
                break
            treated_vector = ((treated_row[match_columns] - combined.mean()) / scales).to_numpy(dtype=float)
            control_matrix = ((control_pool[match_columns] - combined.mean()) / scales).to_numpy(dtype=float)
            distances = np.sqrt(((control_matrix - treated_vector) ** 2).sum(axis=1))
            ranked = control_pool.assign(match_distance=distances).sort_values(["match_distance", "building_key"])
            selected = ranked.head(MATCH_CONTROLS_PER_TREATED).copy()
            for _, control_row in selected.iterrows():
                matches.append(
                    {
                        "treated_building_key": treated_row["building_key"],
                        "control_building_key": control_row["building_key"],
                        "town": town,
                        "treated_distance_km": float(treated_row["dtl2_distance_km"]),
                        "control_distance_km": float(control_row["dtl2_distance_km"]),
                        "match_distance": float(control_row["match_distance"]),
                        "treated_avg_log_price": float(treated_row["avg_log_price"]),
                        "control_avg_log_price": float(control_row["avg_log_price"]),
                        "treated_pretrend_slope": float(treated_row["pretrend_slope"]),
                        "control_pretrend_slope": float(control_row["pretrend_slope"]),
                    }
                )
            control_pool = control_pool.loc[~control_pool["building_key"].isin(selected["building_key"])].copy()
            available_controls = available_controls.loc[
                ~available_controls["building_key"].isin(selected["building_key"])
            ].copy()

    matches_df = pd.DataFrame(matches)
    if matches_df.empty:
        return sample.iloc[0:0].copy(), matches_df

    matched_keys = pd.unique(
        pd.concat(
            [
                matches_df["treated_building_key"],
                matches_df["control_building_key"],
            ],
            ignore_index=True,
        )
    )
    matched_sample = sample.loc[sample["building_key"].isin(matched_keys)].copy()
    matched_sample["matched_design"] = matched_sample["building_key"].isin(matches_df["treated_building_key"]).map({True: "Treated", False: "Matched control"})
    return matched_sample, matches_df


def _plotly_treated_vs_control_figure(plot_df: pd.DataFrame, scope_label: str) -> go.Figure:
    fig = go.Figure()
    color_map = {"Control buildings": BLUE, "Near DTL2 buildings": ORANGE}
    for group_name, group in plot_df.groupby("group"):
        ordered = group.sort_values("transaction_year")
        fig.add_trace(
            go.Scatter(
                x=ordered["transaction_year"],
                y=ordered["median_price"],
                mode="lines+markers+text",
                name=group_name,
                text=[""] * (len(ordered) - 1) + [f"{ordered['median_price'].iloc[-1]:,.0f}"],
                textposition="top center",
                line={"color": color_map[group_name], "width": 2.2},
                marker={
                    "size": 8,
                    "color": "rgba(247,242,232,0.3)",
                    "line": {"color": color_map[group_name], "width": 2},
                },
                hovertemplate="Group: %{fullData.name}<br>Year: %{x}<br>Median Price: SGD %{y:,.0f}<extra></extra>",
            )
        )
    fig.add_vline(x=DTL2_STAGE2_EVENT_YEAR, line_dash="dash", line_color=GRAY, line_width=1)
    fig.update_layout(
        title=f"Median resale price: near vs farther buildings in {scope_label}",
        xaxis_title="Transaction Year",
        yaxis_title="Resale Price (SGD)",
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _plotly_event_study_figure(event_df: pd.DataFrame, scope_label: str) -> go.Figure:
    fig = go.Figure()
    color_map = {"Pre": ORANGE, "Post": GREEN}
    for period_group, group in event_df.groupby("period_group"):
        ordered = group.sort_values("event_time")
        fig.add_trace(
            go.Scatter(
                x=ordered["event_time"],
                y=ordered["effect_pct"],
                mode="markers+text",
                name=f"{period_group}-opening",
                text=ordered["label_text"],
                textposition="bottom center",
                marker={
                    "size": 9,
                    "color": "rgba(247,242,232,0.35)",
                    "line": {"color": color_map[period_group], "width": 2},
                },
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": ordered["effect_pct_ci_high"] - ordered["effect_pct"],
                    "arrayminus": ordered["effect_pct"] - ordered["effect_pct_ci_low"],
                    "color": color_map[period_group],
                    "thickness": 1.6,
                    "width": 0,
                },
                hovertemplate="Event Time: %{x}<br>Effect: %{y:.2f}%<extra></extra>",
            )
        )
    fig.add_hline(y=0, line_dash="dash", line_color=GRAY, line_width=1)
    fig.add_vline(x=-0.5, line_dash="dot", line_color=GRAY, line_width=1)
    fig.update_layout(
        title=f"Event-study coefficients around the DTL2 opening: {scope_label}",
        xaxis_title=f"Years Relative to {DTL2_STAGE2_EVENT_YEAR}",
        yaxis_title="Adjusted Price Effect (%)",
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
        annotations=[
            {
                "x": 0.01,
                "y": 0.02,
                "xref": "paper",
                "yref": "paper",
                "text": "Lead coefficients test whether near-station flats were already on a different path before the first full post-opening year.",
                "showarrow": False,
                "xanchor": "left",
                "yanchor": "bottom",
                "font": {"size": 11, "color": "#000000"},
                "bgcolor": "rgba(0,0,0,0)",
            }
        ],
    )
    return fig


def _plotly_proximity_bands_figure(proximity_data: pd.DataFrame, scope_label: str) -> go.Figure:
    fig = go.Figure()
    color_map = {"Pre-2016": BLUE, "Post-2016": GREEN}
    for period, group in proximity_data.groupby("period"):
        ordered = group.copy()
        fig.add_trace(
            go.Bar(
                x=ordered["distance_band"],
                y=ordered["median_price_psm"],
                name=period,
                marker={
                    "color": f"rgba({int(int(color_map[period][1:3],16))}, {int(int(color_map[period][3:5],16))}, {int(int(color_map[period][5:7],16))}, 0.4)",
                    "line": {"color": color_map[period], "width": 1.2},
                },
                text=ordered["median_price_psm"].map(lambda value: f"{value:.0f}"),
                textposition="outside",
                hovertemplate="Band: %{x}<br>Median Price/sqm: SGD %{y:,.0f}<extra></extra>",
            )
        )
    fig.update_layout(
        title=f"Price per sqm by DTL2 distance band: {scope_label}",
        xaxis_title="Distance to DTL2 Station",
        yaxis_title="Resale Price (SGD per sqm)",
        barmode="group",
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _plotly_parallel_search_figure(search_df: pd.DataFrame) -> go.Figure:
    towns = [town for town in DTL2_BUKIT_TIMAH_CORRIDOR_TOWNS if town in search_df["town"].unique()]
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[town.title() for town in towns],
        horizontal_spacing=0.09,
        vertical_spacing=0.18,
    )
    control_labels = sorted(search_df["control_max_km"].map(lambda value: f"{value:.2f}km").unique().tolist())
    treat_labels = ["0.25km", "0.50km", "0.75km", "1.00km"]
    row_col = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for town, (row, col) in zip(towns, row_col):
        town_df = search_df.loc[search_df["town"].eq(town)].copy()
        if town_df.empty:
            continue
        town_df["control_label"] = town_df.apply(
            lambda r: f"({r['control_min_km']:.2f}, {r['control_max_km']:.2f}]",
            axis=1,
        )
        town_df["treat_label"] = town_df["treat_km"].map(lambda value: f"{value:.2f}km")
        fig.add_trace(
            go.Scatter(
                x=town_df["control_label"],
                y=town_df["treat_label"],
                mode="markers+text",
                text=town_df["did_effect_pct"].map(lambda value: f"{value*100:.1f}%"),
                textposition="middle center",
                marker={
                    "size": 34,
                    "color": town_df["did_effect_pct"] * 100.0,
                    "colorscale": [
                        [0.0, _rgba_string(BLUE, 0.25)],
                        [0.5, _rgba_string("#D8C6AF", 0.55)],
                        [1.0, _rgba_string(ORANGE, 0.55)],
                    ],
                    "cmin": float((search_df["did_effect_pct"] * 100.0).min()),
                    "cmax": float((search_df["did_effect_pct"] * 100.0).max()),
                    "line": {"color": "#8C7B66", "width": 0.8},
                    "showscale": town == towns[-1],
                    "colorbar": {
                        "title": "β3 (% effect)",
                        "len": 0.82,
                        "x": 1.03,
                    },
                },
                customdata=np.stack(
                    [
                        town_df["did_effect_pct"] * 100.0,
                        town_df["did_p"],
                        town_df["pretrend_p"],
                        town_df["lead_joint_p"],
                        town_df["treated_rows"],
                        town_df["control_rows"],
                    ],
                    axis=1,
                ),
                hovertemplate=(
                    f"{town.title()}<br>"
                    "Treatment radius: %{y}<br>"
                    "Control ring: %{x}<br>"
                    "β3 effect: %{customdata[0]:.2f}%<br>"
                    "DiD p-value: %{customdata[1]:.3g}<br>"
                    "Linear pretrend p: %{customdata[2]:.3g}<br>"
                    "Lead-joint p: %{customdata[3]:.3g}<br>"
                    "Treated rows: %{customdata[4]:.0f}<br>"
                    "Control rows: %{customdata[5]:.0f}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=row,
            col=col,
        )
        fig.update_xaxes(title_text="Control Ring", row=row, col=col, tickangle=-30, categoryorder="array", categoryarray=sorted(town_df["control_label"].unique().tolist()))
        fig.update_yaxes(title_text="Treatment Radius", row=row, col=col, categoryorder="array", categoryarray=treat_labels[::-1])
    fig.update_layout(
        title="Question C design search: β3 across treatment and control choices",
        annotations=list(fig.layout.annotations) + [
            {
                "x": 0.01,
                "y": -0.09,
                "xref": "paper",
                "yref": "paper",
                "text": "Each dot is one in-town DiD design. Color and label show β3; hover shows the parallel-trend diagnostics used to rank the designs.",
                "showarrow": False,
                "xanchor": "left",
                "yanchor": "top",
                "font": {"size": 11, "color": "#000000"},
                "bgcolor": "rgba(0,0,0,0)",
            }
        ],
        height=760,
        width=1180,
    )
    return fig


def _town_label_annotation(building_points: pd.DataFrame, town_name: str) -> dict[str, object]:
    lon_min = float(building_points["building_longitude"].min())
    lon_max = float(building_points["building_longitude"].max())
    lat_min = float(building_points["building_latitude"].min())
    lat_max = float(building_points["building_latitude"].max())
    lon_span = max(lon_max - lon_min, 0.003)
    lat_span = max(lat_max - lat_min, 0.003)
    return {
        "x": lon_min + lon_span * 0.08,
        "y": lat_max + lat_span * 0.10,
        "xref": "x",
        "yref": "y",
        "text": town_name.title(),
        "showarrow": False,
        "xanchor": "left",
        "yanchor": "bottom",
        "font": {"size": 16, "color": "#111111"},
        "bgcolor": "rgba(247,242,232,0.82)",
        "bordercolor": "rgba(163,148,128,0.55)",
        "borderwidth": 1,
    }


def _plotly_treatment_map_figure(
    building_points: pd.DataFrame,
    dtl2_stations: pd.DataFrame,
    scope_label: str,
    town_name: str | None = None,
    labeled_stations: list[str] | None = None,
    secondary_stations: pd.DataFrame | None = None,
) -> go.Figure:
    fig = go.Figure()
    polygons, (lon_min, lon_max, lat_min, lat_max) = _load_singapore_basemap_polygons()
    for polygon in polygons:
        fig.add_trace(
            go.Scatter(
                x=polygon[:, 0],
                y=polygon[:, 1],
                mode="lines",
                fill="toself",
                fillcolor="rgba(214,204,186,0.18)",
                line={"color": "rgba(163,148,128,0.55)", "width": 0.8},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    control = building_points.loc[building_points["treated"].eq(0)]
    treated = building_points.loc[building_points["treated"].eq(1)]
    if not control.empty:
        fig.add_trace(
            go.Scatter(
                x=control["building_longitude"],
                y=control["building_latitude"],
                mode="markers",
                name="Control buildings",
                marker={"size": 5, "color": "rgba(247,242,232,0.15)", "line": {"color": BLUE, "width": 0.8}},
                hovertemplate="Control building<extra></extra>",
            )
        )
    if not treated.empty:
        fig.add_trace(
            go.Scatter(
                x=treated["building_longitude"],
                y=treated["building_latitude"],
                mode="markers",
                name="Within 1km of focus stations",
                marker={"size": 6, "color": "rgba(247,242,232,0.22)", "line": {"color": ORANGE, "width": 0.9}},
                hovertemplate="Treated building<extra></extra>",
            )
        )
    if len(dtl2_stations) >= 2:
        fig.add_trace(
            go.Scatter(
                x=dtl2_stations["longitude"],
                y=dtl2_stations["latitude"],
                mode="lines",
                name="Focus corridor",
                line={"color": GREEN, "width": 2.5},
                hoverinfo="skip",
            )
        )
    if secondary_stations is not None and not secondary_stations.empty:
        secondary_labels = secondary_stations["station_name"].str.replace(" MRT STATION", "", regex=False).str.title()
        fig.add_trace(
            go.Scatter(
                x=secondary_stations["longitude"],
                y=secondary_stations["latitude"],
                mode="markers",
                name="Other DTL stations",
                marker={"symbol": "circle", "size": 7, "color": ACCENT, "line": {"color": ACCENT, "width": 1}},
                customdata=np.array(secondary_labels).reshape(-1, 1),
                hovertemplate="%{customdata[0]}<extra></extra>",
            )
        )
    for _, station in dtl2_stations.iterrows():
        circle = _circle_polygon(float(station["latitude"]), float(station["longitude"]), TREATMENT_DISTANCE_KM)
        fig.add_trace(
            go.Scatter(
                x=circle["longitude"],
                y=circle["latitude"],
                mode="lines",
                line={"color": GREEN, "width": 1},
                opacity=0.55,
                hoverinfo="skip",
                showlegend=False,
            )
        )
    if labeled_stations is None:
        station_labels = pd.Series([""] * len(dtl2_stations), index=dtl2_stations.index, dtype="object")
    else:
        station_labels = dtl2_stations["station_name"].where(
            dtl2_stations["station_name"].isin(labeled_stations),
            "",
        ).str.replace(" MRT STATION", "", regex=False).str.title()
    fig.add_trace(
        go.Scatter(
            x=dtl2_stations["longitude"],
            y=dtl2_stations["latitude"],
            mode="markers+text",
            name="Focus stations",
            marker={"symbol": "x", "size": 8, "color": GREEN, "line": {"color": GREEN, "width": 1.2}},
            text=station_labels,
            textposition="top right",
            customdata=np.array(
                dtl2_stations["station_name"].str.replace(" MRT STATION", "", regex=False).str.title()
            ).reshape(-1, 1),
            hovertemplate="%{customdata[0]}<extra></extra>",
        )
    )
    focus_lon = pd.concat(
        [
            building_points["building_longitude"].dropna(),
            dtl2_stations["longitude"].dropna(),
            secondary_stations["longitude"].dropna() if secondary_stations is not None and not secondary_stations.empty else pd.Series(dtype=float),
        ],
        ignore_index=True,
    )
    focus_lat = pd.concat(
        [
            building_points["building_latitude"].dropna(),
            dtl2_stations["latitude"].dropna(),
            secondary_stations["latitude"].dropna() if secondary_stations is not None and not secondary_stations.empty else pd.Series(dtype=float),
        ],
        ignore_index=True,
    )
    zoom_lon_min = float(focus_lon.min())
    zoom_lon_max = float(focus_lon.max())
    zoom_lat_min = float(focus_lat.min())
    zoom_lat_max = float(focus_lat.max())
    zoom_lon_span = max(zoom_lon_max - zoom_lon_min, 0.03)
    zoom_lat_span = max(zoom_lat_max - zoom_lat_min, 0.03)
    zoom_lon_pad = zoom_lon_span * 0.14
    zoom_lat_pad = zoom_lat_span * 0.18
    fig.update_layout(
        title=None,
        xaxis={"visible": False, "range": [zoom_lon_min - zoom_lon_pad, zoom_lon_max + zoom_lon_pad]},
        yaxis={
            "visible": False,
            "range": [zoom_lat_min - zoom_lat_pad, zoom_lat_max + zoom_lat_pad],
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        legend={
            "title": None,
            "bgcolor": "rgba(0,0,0,0)",
            "x": 0.01,
            "y": 0.99,
            "xanchor": "left",
            "yanchor": "top",
        },
    )
    if town_name is not None and not building_points.empty:
        fig.update_layout(annotations=[_town_label_annotation(building_points, town_name)])
    return fig


def _plot_event_study(stem: str, event_df: pd.DataFrame, scope_label: str) -> tuple[str, str, str | None]:
    return save_plotly_figure(
        stem,
        _plotly_event_study_figure(event_df.copy(), scope_label),
        title=f"Event-study coefficients around the DTL2 opening: {scope_label}",
        data=event_df.copy(),
    )


def _circle_polygon(lat: float, lon: float, radius_km: float, points: int = 120) -> pd.DataFrame:
    bearings = np.linspace(0.0, 2.0 * np.pi, points)
    earth_radius_km = 6371.0
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    angular = radius_km / earth_radius_km

    lat_points = np.arcsin(
        np.sin(lat_rad) * np.cos(angular)
        + np.cos(lat_rad) * np.sin(angular) * np.cos(bearings)
    )
    lon_points = lon_rad + np.arctan2(
        np.sin(bearings) * np.sin(angular) * np.cos(lat_rad),
        np.cos(angular) - np.sin(lat_rad) * np.sin(lat_points),
    )
    return pd.DataFrame(
        {
            "latitude": np.degrees(lat_points),
            "longitude": np.degrees(lon_points),
        }
    )


def _iter_geojson_rings(geometry: dict[str, object]) -> list[list[list[float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        return [ring for ring in coordinates if ring]
    if geometry_type == "MultiPolygon":
        rings: list[list[list[float]]] = []
        for polygon in coordinates:
            rings.extend(ring for ring in polygon if ring)
        return rings
    return []


def _load_singapore_basemap_polygons() -> tuple[list[np.ndarray], tuple[float, float, float, float]]:
    basemap_path = PLANNING_AREA_BOUNDARIES_PATH
    if not basemap_path.exists() and PLANNING_AREA_BOUNDARIES_FALLBACK_PATH.exists():
        basemap_path = PLANNING_AREA_BOUNDARIES_FALLBACK_PATH
    if not basemap_path.exists():
        raise FileNotFoundError(
            "Singapore planning-area GeoJSON is missing. "
            f"Expected `{PLANNING_AREA_BOUNDARIES_PATH}` or fallback `{PLANNING_AREA_BOUNDARIES_FALLBACK_PATH}`."
        )

    basemap = json.loads(basemap_path.read_text(encoding="utf-8"))
    polygons: list[np.ndarray] = []
    lon_min = float("inf")
    lon_max = float("-inf")
    lat_min = float("inf")
    lat_max = float("-inf")

    for feature in basemap.get("features", []):
        geometry = feature.get("geometry") or {}
        for ring in _iter_geojson_rings(geometry):
            polygon = np.asarray(ring, dtype=float)
            if polygon.ndim != 2 or polygon.shape[0] < 3:
                continue
            polygons.append(polygon)
            lon_min = min(lon_min, float(polygon[:, 0].min()))
            lon_max = max(lon_max, float(polygon[:, 0].max()))
            lat_min = min(lat_min, float(polygon[:, 1].min()))
            lat_max = max(lat_max, float(polygon[:, 1].max()))

    if not polygons:
        raise ValueError("Singapore planning-area GeoJSON did not contain any usable polygons.")
    return polygons, (lon_min, lon_max, lat_min, lat_max)


def _draw_singapore_basemap(ax) -> tuple[float, float, float, float]:
    polygons, bounds = _load_singapore_basemap_polygons()
    for polygon in polygons:
        ax.add_patch(
            MplPolygon(
                polygon,
                closed=True,
                facecolor=(0.84, 0.80, 0.73, 0.34),
                edgecolor=(0.64, 0.58, 0.50, 0.62),
                linewidth=0.55,
                zorder=0,
            )
        )
    return bounds


def _plot_treatment_map(
    stem: str,
    building_points: pd.DataFrame,
    dtl2_stations: pd.DataFrame,
    scope_label: str,
    town_name: str | None = None,
    labeled_stations: list[str] | None = None,
    secondary_stations: pd.DataFrame | None = None,
) -> tuple[str, str, str | None]:
    return save_plotly_figure(
        stem,
        _plotly_treatment_map_figure(
            building_points,
            dtl2_stations,
            scope_label,
            town_name=town_name,
            labeled_stations=labeled_stations,
            secondary_stations=secondary_stations,
        ),
        title=None,
        data=building_points,
    )


def _plot_town_outputs(
    sample: pd.DataFrame,
    dtl2_stations: pd.DataFrame,
    stem_prefix: str,
    scope_label: str,
    town_name: str | None,
    map_label_stations: list[str] | None = None,
) -> dict[str, str | None]:
    f0_svg = None
    f0_html = str(Path("outputs/section3/charts") / f"{stem_prefix}F0_did_framework.html")
    f0_data = None

    plot_df = sample.groupby(["transaction_year", "treated"]).agg(median_price=("resale_price", "median")).reset_index()
    plot_df["group"] = plot_df["treated"].map({0: "Control buildings", 1: "Near DTL2 buildings"})
    f1_svg, f1_html, f1_data = save_plotly_figure(
        f"{stem_prefix}F1_dtl2_treated_vs_control",
        _plotly_treated_vs_control_figure(plot_df.copy(), scope_label),
        title=f"Median resale price: near vs farther buildings in {scope_label}",
        data=plot_df.copy(),
    )

    event_sample = _event_study_sample(sample)
    event_terms = ["treated_event_m4", "treated_event_m3", "treated_event_m2", "treated_event_p0", "treated_event_p1", "treated_event_p2"]
    event_formula = "log_price ~ flat_age + floor_area_sqm + C(flat_type) + C(transaction_year) + " + " + ".join(event_terms)
    if sample["town"].nunique() > 1:
        event_formula = "log_price ~ flat_age + floor_area_sqm + C(flat_type) + C(town) + C(transaction_year) + " + " + ".join(event_terms)
    event_model = smf.ols(event_formula, data=event_sample).fit(cov_type="HC3")
    event_df = _event_study_table(event_model)
    event_df["label_text"] = event_df["effect_pct"].map(lambda value: f"{value:.1f}%")
    f2_svg, f2_html, f2_data = _plot_event_study(f"{stem_prefix}F2_dtl2_event_study_coefficients", event_df, scope_label)

    proximity_plot = sample.copy()
    proximity_plot["distance_band"] = pd.cut(
        proximity_plot["dtl2_distance_km"],
        bins=[0.0, 0.5, 1.0, 2.0, 4.0],
        labels=["0-500m", "500m-1.0km", "1.0-2.0km", "2.0-4.0km"],
        include_lowest=True,
    )
    proximity_plot = proximity_plot.groupby(["post", "distance_band"]).agg(median_price_psm=("price_per_sqm", "median")).reset_index()
    proximity_plot["period"] = proximity_plot["post"].map({0: "Pre-2016", 1: "Post-2016"})
    f3_svg, f3_html, f3_data = save_plotly_figure(
        f"{stem_prefix}F3_dtl2_mrt_proximity_bands",
        _plotly_proximity_bands_figure(proximity_plot.copy(), scope_label),
        title=f"Price per sqm by DTL2 distance band: {scope_label}",
        data=proximity_plot.copy(),
    )

    focus_stations, secondary_stations = _focus_and_secondary_station_points(dtl2_stations)
    building_points = sample[["building_latitude", "building_longitude"]].drop_duplicates().copy()
    building_points = _attach_dtl2_distance(building_points, focus_stations)
    building_points["treated"] = (building_points["dtl2_distance_km"] <= TREATMENT_DISTANCE_KM).astype(int)
    f4_svg, f4_html, f4_data = _plot_treatment_map(
        f"{stem_prefix}F4_dtl2_treatment_map",
        building_points,
        focus_stations,
        scope_label,
        town_name=town_name,
        labeled_stations=map_label_stations if map_label_stations is not None else focus_stations["station_name"].tolist(),
        secondary_stations=secondary_stations,
    )
    return {
        "f0_chart": f0_svg,
        "f0_html": f0_html,
        "f0_data": f0_data,
        "f1_chart": f1_svg,
        "f1_html": f1_html,
        "f1_data": f1_data,
        "f2_chart": f2_svg,
        "f2_html": f2_html,
        "f2_data": f2_data,
        "f3_chart": f3_svg,
        "f3_html": f3_html,
        "f3_data": f3_data,
        "f4_chart": f4_svg,
        "f4_html": f4_html,
        "f4_data": f4_data,
    }


def rebuild_question_c_figures() -> None:
    _rebuild_s3qc_f1()
    _rebuild_s3qc_f2()
    _rebuild_s3qc_f3()
    _rebuild_s3qc_f4()
    _rebuild_s3qc_f5()


def _rebuild_s3qc_f1() -> None:
    plot_df = load_figure_data("S3QcF1_dtl2_treated_vs_control")
    save_plotly_figure(
        "S3QcF1_dtl2_treated_vs_control",
        _plotly_treated_vs_control_figure(plot_df, "the DTL2 Bukit Timah corridor"),
        title="Median resale price: near vs farther buildings in the DTL2 Bukit Timah corridor",
        data=plot_df,
    )


def _rebuild_s3qc_f2() -> None:
    event_df = load_figure_data("S3QcF2_dtl2_event_study_coefficients")
    if "label_text" not in event_df.columns:
        event_df["label_text"] = event_df["effect_pct"].map(lambda value: f"{value:.1f}%")
    _plot_event_study("S3QcF2_dtl2_event_study_coefficients", event_df, "the DTL2 Bukit Timah corridor")


def _rebuild_s3qc_f3() -> None:
    proximity_data = load_figure_data("S3QcF3_dtl2_mrt_proximity_bands")
    save_plotly_figure(
        "S3QcF3_dtl2_mrt_proximity_bands",
        _plotly_proximity_bands_figure(proximity_data, "the DTL2 Bukit Timah corridor"),
        title="Price per sqm by DTL2 distance band: the DTL2 Bukit Timah corridor",
        data=proximity_data,
    )


def _rebuild_s3qc_f4() -> None:
    map_data = load_figure_data("S3QcF4_dtl2_treatment_map")
    buildings = (
        map_data[["building_latitude", "building_longitude"]]
        .dropna()
        .drop_duplicates()
        .copy()
    )
    dtl_stations = _load_dtl2_station_points()
    focus_stations, secondary_stations = _focus_and_secondary_station_points(dtl_stations)
    buildings = _attach_dtl2_distance(buildings, focus_stations)
    buildings["treated"] = (buildings["dtl2_distance_km"] <= TREATMENT_DISTANCE_KM).astype(int)
    _plot_treatment_map(
        "S3QcF4_dtl2_treatment_map",
        buildings,
        focus_stations,
        "the four-station Bukit corridor treatment design",
        labeled_stations=TREATMENT_LABEL_STATIONS,
        secondary_stations=secondary_stations,
    )


def _rebuild_s3qc_f5() -> None:
    search_df = load_figure_data("S3QcF5_in_town_design_search")
    save_plotly_figure(
        "S3QcF5_in_town_design_search",
        _plotly_parallel_search_figure(search_df),
        title="Question C design search: β3 across treatment and control choices",
        data=search_df,
    )


def analyze_dtl2(frame: pd.DataFrame) -> dict[str, object]:
    dtl2_stations = _load_dtl2_station_points()
    sample = frame.loc[
        (frame["transaction_month"] >= pd.Timestamp("2012-01-01"))
        & (frame["transaction_month"] <= pd.Timestamp("2018-12-01"))
        & (frame["town"].isin(DTL2_BUKIT_TIMAH_CORRIDOR_TOWNS))
    ].copy()
    sample = sample.dropna(
        subset=[
            "resale_price",
            "price_per_sqm",
            "flat_age",
            "floor_area_sqm",
            "flat_type",
            "town",
            "transaction_year",
            "building_latitude",
            "building_longitude",
        ]
    )
    sample = _attach_dtl2_distance(sample, dtl2_stations)
    sample = sample.loc[
        (sample["dtl2_distance_km"] <= TREATMENT_DISTANCE_KM)
        | (
            (sample["dtl2_distance_km"] > CONTROL_MIN_DISTANCE_KM)
            & (sample["dtl2_distance_km"] <= CONTROL_MAX_DISTANCE_KM)
        )
    ].copy()
    sample["treated"] = (sample["dtl2_distance_km"] <= TREATMENT_DISTANCE_KM).astype(int)
    # Transactions are monthly, so use the opening month as the closest feasible post indicator.
    sample["post"] = (sample["transaction_month"] >= DTL2_STAGE2_POST_MONTH).astype(int)
    sample["log_price"] = np.log(sample["resale_price"])
    sample["year_index"] = sample["transaction_year"] - int(sample["transaction_year"].min())
    sample["distance_experiment_band"] = _assign_experiment_distance_band(sample["dtl2_distance_km"])

    did_model = smf.ols(
        "log_price ~ treated * post + flat_age + floor_area_sqm + C(flat_type) + C(town) + C(transaction_year)",
        data=sample,
    ).fit(cov_type="HC3")
    did_effect = float(did_model.params["treated:post"])
    did_pvalue = float(did_model.pvalues["treated:post"])
    did_summary_path, did_coef_path = _save_model_outputs("S3Qc_model_did", did_model)

    pre_period = sample.loc[sample["post"].eq(0)].copy()
    pretrend_model = smf.ols(
        "log_price ~ treated * year_index + flat_age + floor_area_sqm + C(flat_type) + C(town)",
        data=pre_period,
    ).fit(cov_type="HC3")
    pretrend_effect = float(pretrend_model.params["treated:year_index"])
    pretrend_pvalue = float(pretrend_model.pvalues["treated:year_index"])
    pretrend_summary_path, pretrend_coef_path = _save_model_outputs("S3Qc_model_pretrend", pretrend_model)

    event_sample = _event_study_sample(sample)
    event_terms = [
        "treated_event_m4",
        "treated_event_m3",
        "treated_event_m2",
        "treated_event_p0",
        "treated_event_p1",
        "treated_event_p2",
    ]
    event_model = smf.ols(
        "log_price ~ flat_age + floor_area_sqm + C(flat_type) + C(town) + C(transaction_year) + "
        + " + ".join(event_terms),
        data=event_sample,
    ).fit(cov_type="HC3")
    event_summary_path, event_coef_path = _save_model_outputs("S3Qc_model_event_study", event_model)
    event_df = _event_study_table(event_model)
    event_df["label_text"] = event_df["effect_pct"].map(lambda value: f"{value:.1f}%")
    pretrend_joint_pvalue = _joint_test_pvalue(event_model, ["treated_event_m4", "treated_event_m3", "treated_event_m2"])
    post_joint_pvalue = _joint_test_pvalue(event_model, ["treated_event_p0", "treated_event_p1", "treated_event_p2"])

    experiment_sample = sample.loc[sample["distance_experiment_band"].notna()].copy()
    band_experiment_model = smf.ols(
        f"log_price ~ post * C(distance_experiment_band, Treatment(reference='{DTL2_EXPERIMENT_CONTROL_LABEL}')) "
        "+ flat_age + floor_area_sqm + C(flat_type) + C(town) + C(transaction_year)",
        data=experiment_sample,
    ).fit(cov_type="HC3")
    band_experiment_summary_path, band_experiment_coef_path = _save_model_outputs(
        "S3Qc_model_distance_band_experiment",
        band_experiment_model,
    )
    band_experiment_effects = _distance_band_experiment_effects(band_experiment_model)
    band_experiment_effects_path = save_chart_data("S3Qc_distance_band_experiment_effects", band_experiment_effects)
    in_town_search = _run_in_town_nearby_control_search(sample)
    in_town_search_path = save_chart_data("S3Qc_parallel_trend_nearby_controls_by_town", in_town_search) if not in_town_search.empty else None
    best_in_town = (
        in_town_search.sort_values(["town", "lead_joint_p", "pretrend_p"], ascending=[True, False, False]).groupby("town").head(1)
        if not in_town_search.empty
        else pd.DataFrame()
    )
    search_chart_svg = search_chart_html = search_chart_data = None
    if not in_town_search.empty:
        search_chart_svg, search_chart_html, search_chart_data = save_plotly_figure(
            "S3QcF5_in_town_design_search",
            _plotly_parallel_search_figure(in_town_search.copy()),
            title="Question C design search: β3 across treatment and control choices",
            data=in_town_search.copy(),
        )

    matched_sample, matched_pairs = _matched_building_sample(sample)
    matched_summary: dict[str, object] = {}
    if not matched_sample.empty:
        matched_did_model = smf.ols(
            "log_price ~ treated * post + flat_age + floor_area_sqm + C(flat_type) + C(town) + C(transaction_year)",
            data=matched_sample,
        ).fit(cov_type="HC3")
        matched_pre_period = matched_sample.loc[matched_sample["post"].eq(0)].copy()
        matched_pretrend_model = smf.ols(
            "log_price ~ treated * year_index + flat_age + floor_area_sqm + C(flat_type) + C(town)",
            data=matched_pre_period,
        ).fit(cov_type="HC3")
        matched_event_sample = _event_study_sample(matched_sample)
        matched_event_model = smf.ols(
            "log_price ~ flat_age + floor_area_sqm + C(flat_type) + C(town) + C(transaction_year) + "
            + " + ".join(event_terms),
            data=matched_event_sample,
        ).fit(cov_type="HC3")
        matched_event_df = _event_study_table(matched_event_model)
        matched_pairs_path = save_chart_data("S3Qc_matched_building_pairs", matched_pairs)
        matched_did_summary_path, matched_did_coef_path = _save_model_outputs("S3Qc_model_matched_did", matched_did_model)
        matched_pretrend_summary_path, matched_pretrend_coef_path = _save_model_outputs(
            "S3Qc_model_matched_pretrend",
            matched_pretrend_model,
        )
        matched_event_summary_path, matched_event_coef_path = _save_model_outputs(
            "S3Qc_model_matched_event_study",
            matched_event_model,
        )
        matched_summary = {
            "matched_rows": int(len(matched_sample)),
            "matched_treated_rows": int(matched_sample["treated"].sum()),
            "matched_control_rows": int((matched_sample["treated"] == 0).sum()),
            "matched_buildings": int(matched_sample["building_key"].nunique()),
            "matched_treated_buildings": int(matched_sample.loc[matched_sample["treated"].eq(1), "building_key"].nunique()),
            "matched_control_buildings": int(matched_sample.loc[matched_sample["treated"].eq(0), "building_key"].nunique()),
            "matched_pairs": int(len(matched_pairs)),
            "controls_per_treated": MATCH_CONTROLS_PER_TREATED,
            "matching_control_definition": f"Distance to DTL2 station in ({MATCH_CONTROL_MIN_DISTANCE_KM:.1f}, {MATCH_CONTROL_MAX_DISTANCE_KM:.1f}] km",
            "matching_features": ["avg_log_price", "pretrend_slope", "avg_price_per_sqm", "avg_floor_area_sqm", "avg_flat_age"],
            "matched_did_effect_log_points": float(matched_did_model.params["treated:post"]),
            "matched_did_effect_pct": float(np.exp(matched_did_model.params["treated:post"]) - 1.0),
            "matched_did_pvalue": float(matched_did_model.pvalues["treated:post"]),
            "matched_pretrend_effect_log_points_per_year": float(matched_pretrend_model.params["treated:year_index"]),
            "matched_pretrend_pvalue": float(matched_pretrend_model.pvalues["treated:year_index"]),
            "matched_pretrend_leads_joint_pvalue": _joint_test_pvalue(
                matched_event_model,
                ["treated_event_m4", "treated_event_m3", "treated_event_m2"],
            ),
            "matched_post_event_joint_pvalue": _joint_test_pvalue(
                matched_event_model,
                ["treated_event_p0", "treated_event_p1", "treated_event_p2"],
            ),
            "matched_event_study_coefficients": matched_event_df.to_dict(orient="records"),
            "model_outputs": {
                "matched_pairs": matched_pairs_path,
                "matched_did_summary": matched_did_summary_path,
                "matched_did_coefficients": matched_did_coef_path,
                "matched_pretrend_summary": matched_pretrend_summary_path,
                "matched_pretrend_coefficients": matched_pretrend_coef_path,
                "matched_event_study_summary": matched_event_summary_path,
                "matched_event_study_coefficients": matched_event_coef_path,
            },
        }

    overall_chart_outputs = _plot_town_outputs(
        sample,
        dtl2_stations,
        "S3Qc",
        "the DTL2 Bukit Timah corridor",
        None,
        map_label_stations=CORRIDOR_MAP_LABEL_STATIONS,
    )
    town_chart_outputs: dict[str, dict[str, str | None]] = {}
    for town_name in DTL2_BUKIT_TIMAH_CORRIDOR_TOWNS:
        town_slug = _slugify(town_name)
        town_sample = sample.loc[sample["town"].eq(town_name)].copy()
        if town_sample.empty:
            continue
        town_stations = dtl2_stations.loc[
            dtl2_stations["station_name"].isin(town_sample["nearest_dtl2_station"].dropna().unique())
        ].copy()
        if town_stations.empty:
            town_stations = dtl2_stations.copy()
        town_chart_outputs[town_name] = _plot_town_outputs(
            town_sample,
            town_stations,
            f"S3Qc_{town_slug}_",
            town_name.title(),
            town_name,
        )

    summary = {
        "banner_statement": "Near-station buildings in the Bukit Timah corridor saw a post-opening uplift, but the pre-trend evidence still means the effect should be presented cautiously.",
        "hypothesis": "Downtown Line Stage 2 increased resale prices for buildings closer to Stage 2 stations relative to farther buildings in the same Bukit Timah corridor towns.",
        "method": "Building-level difference-in-differences within Bukit Timah corridor towns using distance to DTL2 Stage 2 stations, plus an event-study pre-trend check.",
        "controls": ["flat_age", "floor_area_sqm", "flat_type", "town fixed effects", "year fixed effects"],
        "analysis_towns": DTL2_BUKIT_TIMAH_CORRIDOR_TOWNS,
        "dtl2_stage2_stations": DTL2_STAGE2_STATIONS,
        "treatment_definition": f"Distance to DTL2 station <= {TREATMENT_DISTANCE_KM:.1f} km",
        "control_definition": f"Distance to DTL2 station in ({CONTROL_MIN_DISTANCE_KM:.1f}, {CONTROL_MAX_DISTANCE_KM:.1f}] km",
        "rows": int(len(sample)),
        "treated_rows": int(sample["treated"].sum()),
        "control_rows": int((sample["treated"] == 0).sum()),
        "opening_date": str(DTL2_STAGE2_OPEN_DATE.date()),
        "post_month_start": str(DTL2_STAGE2_POST_MONTH.date()),
        "event_study_reference_year": DTL2_STAGE2_EVENT_YEAR,
        "did_effect_log_points": did_effect,
        "did_effect_pct": float(np.exp(did_effect) - 1),
        "did_pvalue": did_pvalue,
        "pretrend_effect_log_points_per_year": pretrend_effect,
        "pretrend_pvalue": pretrend_pvalue,
        "pretrend_leads_joint_pvalue": pretrend_joint_pvalue,
        "post_event_joint_pvalue": post_joint_pvalue,
        "distance_band_experiment_reference": DTL2_EXPERIMENT_CONTROL_LABEL,
        "distance_band_experiment_effects": band_experiment_effects.to_dict(orient="records"),
        "in_town_parallel_trend_search": best_in_town.to_dict(orient="records"),
        "event_study_coefficients": event_df.to_dict(orient="records"),
        "interpretation": (
            "Near-station buildings in the Bukit Timah corridor show a positive post-opening uplift, but the lead coefficients are jointly significant before opening, so the causal claim must be qualified."
            if pretrend_joint_pvalue < 0.05
            else "The building-level DiD estimate is consistent with a price uplift for buildings closer to DTL2 Stage 2 stations in the Bukit Timah corridor."
            if did_effect > 0 and did_pvalue < 0.05
            else "The building-level DiD estimate does not support a statistically clear DTL2 Stage 2 price uplift in the Bukit Timah corridor base specification."
        ),
        "chart_commentary": [
            "Use the corridor charts for the pooled result, then show the same four charts town by town so the comparison logic is consistent.",
            "Use each town's event-study coefficients to show where the pre-trend problem is strongest and where it improves.",
            "Use each town's distance-band chart as supporting intuition for how the price-per-sqm gradient changes locally.",
            "Use each town's map to show exactly how the 1km exposure region is defined around the relevant DTL2 Stage 2 stations.",
            "Use the design-search chart to show how β3 changes across treatment radii and nearby control rings, and why pretrend fit rather than raw uplift drives the preferred design.",
        ],
        "limitations": [
            "The lead coefficients indicate that near-station buildings were already on a different path before 2016.",
            "The post indicator uses the opening month because the transaction data is monthly, while the actual opening date was 2015-12-27.",
            "Distance bands improve exposure measurement, but they still do not fully control for project-level amenity differences near stations.",
        ],
        "matched_control_experiment": matched_summary,
        "town_chart_outputs": town_chart_outputs,
        "design_search_chart": {
            "chart": search_chart_svg,
            "html": search_chart_html,
            "data": search_chart_data,
        },
        "model_outputs": {
            "did_summary": did_summary_path,
            "did_coefficients": did_coef_path,
            "pretrend_summary": pretrend_summary_path,
            "pretrend_coefficients": pretrend_coef_path,
            "event_study_summary": event_summary_path,
            "event_study_coefficients": event_coef_path,
            "distance_band_experiment_summary": band_experiment_summary_path,
            "distance_band_experiment_coefficients": band_experiment_coef_path,
            "distance_band_experiment_effects": band_experiment_effects_path,
            "in_town_parallel_trend_search": in_town_search_path,
            **matched_summary.get("model_outputs", {}),
        },
        "charts": [overall_chart_outputs[key] for key in ["f0_chart", "f1_chart", "f2_chart", "f3_chart", "f4_chart"] if overall_chart_outputs[key]],
        "chart_html": [overall_chart_outputs[key] for key in ["f0_html", "f1_html", "f2_html", "f3_html", "f4_html"] if overall_chart_outputs[key]],
        "chart_data": [overall_chart_outputs[key] for key in ["f0_data", "f1_data", "f2_data", "f3_data", "f4_data"] if overall_chart_outputs[key]],
    }
    if search_chart_svg:
        summary["charts"].append(search_chart_svg)
    if search_chart_html:
        summary["chart_html"].append(search_chart_html)
    if search_chart_data:
        summary["chart_data"].append(search_chart_data)

    policy_summary_path = REPORTS / "policy_summary.json"
    if policy_summary_path.exists():
        try:
            full_summary = json.loads(policy_summary_path.read_text(encoding="utf-8"))
            full_summary["question_c"] = summary
            policy_summary_path.write_text(json.dumps(full_summary, indent=2), encoding="utf-8")
        except json.JSONDecodeError:
            pass

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 3 Question C analysis.")
    parser.add_argument("--figures-only", action="store_true")
    parser.add_argument("--skip-html", action="store_true")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    configure_logging(args.log_level)
    set_write_html(not args.skip_html)
    if args.figures_only:
        rebuild_question_c_figures()
        return
    summary = analyze_dtl2(load_frame())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
