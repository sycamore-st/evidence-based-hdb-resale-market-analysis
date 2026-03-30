from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import statsmodels.formula.api as smf
from matplotlib.colors import to_rgba
from plotly.subplots import make_subplots

from src.analysis.section3.S3_helpers import (
    ACCENT,
    BLUE,
    BLUE_LIGHT,
    GRAY,
    GREEN,
    ORANGE,
    SECTION3_FIGURE_REPORTS,
    annotate_bar_values,
    annotate_point_values,
    annotate_series_endpoints,
    configure_logging,
    load_figure_data,
    load_frame,
    save_plotly_figure,
    save_svg_and_html,
    set_write_html,
    should_write_html,
    style_bar_patches,
    write_plotly_chart_html,
)
from src.analysis.common.plotly_standard import apply_standard_theme, load_plotly_theme


MAJOR_FLAT_TYPES = ["1 ROOM", "2 ROOM", "3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"]
COMMON_FLAT_TYPES = ["3 ROOM", "4 ROOM", "5 ROOM"]
SPARSE_FLAT_TYPES = ["1 ROOM", "2 ROOM", "EXECUTIVE"]
FLAT_TYPE_COLOR_MAP = {
    "1 ROOM": "#B8C3CC",
    "2 ROOM": "#95A7B6",
    "3 ROOM": BLUE_LIGHT,
    "4 ROOM": ORANGE,
    "5 ROOM": GREEN,
    "EXECUTIVE": ACCENT,
}


def _derive_completion_year(frame: pd.DataFrame) -> pd.Series:
    if "lease_commence_date" in frame.columns:
        numeric_year = pd.to_numeric(frame["lease_commence_date"], errors="coerce")
        if numeric_year.notna().any():
            return numeric_year
        derived = pd.to_datetime(frame["lease_commence_date"], errors="coerce").dt.year
        if derived.notna().any():
            return derived
    return pd.to_numeric(frame["transaction_year"], errors="coerce") - pd.to_numeric(frame["flat_age"], errors="coerce")


def _connected_scatter_labels(
        ax,
        data: pd.DataFrame,
        *,
        x: str,
        y: str,
        series: str,
        color_map: dict[str, str],
) -> None:
    for series_name, group in data.groupby(series):
        ordered = group.sort_values(x)
        if ordered.empty:
            continue
        start_row = ordered.iloc[0]
        end_row = ordered.iloc[-1]
        ax.annotate(
            f"{start_row[y]:.1f}",
            (start_row[x], start_row[y]),
            xytext=(-8, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=9,
            color=color_map.get(series_name, "#000000"),
        )
        ax.annotate(
            f"{end_row[y]:.1f}",
            (end_row[x], end_row[y]),
            xytext=(8, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
            color=color_map.get(series_name, "#000000"),
        )


def _adjusted_completion_profile(
        model: object,
        *,
        reference_town: str,
        observed_pairs: pd.DataFrame,
) -> pd.DataFrame:
    prediction_frame = observed_pairs.copy()
    prediction_frame["town"] = reference_town
    prediction = model.get_prediction(prediction_frame)
    interval = prediction.summary_frame(alpha=0.05)
    return prediction_frame.assign(
        adjusted_floor_area=interval["mean"].to_numpy(),
        ci_low=interval["mean_ci_lower"].to_numpy(),
        ci_high=interval["mean_ci_upper"].to_numpy(),
    )


def _relative_coefficient_profile(profile: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for flat_type, group in profile.groupby("flat_type"):
        ordered = group.sort_values("completion_year").copy()
        baseline = ordered.iloc[0]
        ordered["baseline_year"] = int(baseline["completion_year"])
        ordered["coef_vs_baseline"] = ordered["adjusted_floor_area"] - float(baseline["adjusted_floor_area"])
        ordered["ci_low_vs_baseline"] = ordered["ci_low"] - float(baseline["adjusted_floor_area"])
        ordered["ci_high_vs_baseline"] = ordered["ci_high"] - float(baseline["adjusted_floor_area"])
        rows.append(ordered)
    return pd.concat(rows, ignore_index=True)


def _selected_years(years: pd.Series, step: int) -> set[int]:
    available = sorted(pd.to_numeric(years, errors="coerce").dropna().astype(int).unique().tolist())
    selected = {year for year in available if year % step == 0}
    if available:
        selected.add(available[-1])
    return selected


def _write_floor_area_over_time_svg(
        data: pd.DataFrame,
        *,
        output_path: str | Path,
        title: str | None,
        panels: list[tuple[str, list[str]]],
        figsize: tuple[float, float] | None = None,
) -> None:
    output = Path(output_path)
    png_output = output.with_suffix(".png")
    resolved_figsize = figsize or ((13 if len(panels) > 1 else 7), 5.2)
    fig, axes = plt.subplots(1, len(panels), figsize=resolved_figsize, sharey=True)
    if len(panels) == 1:
        axes = [axes]

    for idx, (ax, (panel_title, members)) in enumerate(zip(axes, panels)):
        subset = data.loc[data["series"].isin(["Overall average", *members])].copy()
        if subset.empty:
            continue
        for series_name, group in subset.groupby("series"):
            ordered = group.sort_values("completion_year")
            color = BLUE if series_name == "Overall average" else FLAT_TYPE_COLOR_MAP.get(series_name, BLUE_LIGHT)
            ax.plot(
                ordered["completion_year"],
                ordered["avg_floor_area"],
                color=color,
                linewidth=2.2,
                marker="o",
                markersize=4.8,
                markerfacecolor="white",
                markeredgewidth=1.4,
                label=series_name,
            )
        _connected_scatter_labels(
            ax,
            subset,
            x="completion_year",
            y="avg_floor_area",
            series="series",
            color_map={"Overall average": BLUE, **FLAT_TYPE_COLOR_MAP},
        )
        ax.set_title(panel_title, fontsize=15, color="#000000")
        ax.set_xlabel("Completion Year", fontsize=13, color="#000000")
        if idx == 0:
            ax.set_ylabel("Floor Area (sqm)", fontsize=13, color="#000000")
        ax.grid(False)
        ax.set_facecolor("none")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#000000")
        ax.spines["left"].set_color("#000000")
        ax.tick_params(axis="both", colors="#000000", labelcolor="#000000")
        ax.legend(frameon=False, fontsize=10, loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=min(2, len(members) + 1))

    if title:
        fig.suptitle(title, fontsize=20, color="#000000", y=0.98)
    fig.patch.set_alpha(0.0)
    fig.tight_layout(rect=(0, 0, 1, 0.9 if title else 0.96))
    fig.savefig(png_output, format="png", dpi=240, bbox_inches="tight", transparent=True)
    plt.close(fig)


def _type_groups_for_plot(data: pd.DataFrame, *, series_col: str) -> list[tuple[str, list[str]]]:
    available = set(data[series_col].dropna().astype(str))
    groups: list[tuple[str, list[str]]] = []
    common = [flat_type for flat_type in COMMON_FLAT_TYPES if flat_type in available]
    sparse = [flat_type for flat_type in SPARSE_FLAT_TYPES if flat_type in available]
    if common:
        groups.append(("Common types", common))
    if sparse:
        groups.append(("Sparse / niche types", sparse))
    return groups or [("All types", sorted(available))]


def _save_model_outputs(model: object, *, stem: str) -> tuple[str, str]:
    SECTION3_FIGURE_REPORTS.mkdir(parents=True, exist_ok=True)
    summary_path = SECTION3_FIGURE_REPORTS / f"{stem}_summary.txt"
    coefficients_path = SECTION3_FIGURE_REPORTS / f"{stem}_coefficients.csv"
    summary_path.write_text(model.summary().as_text(), encoding="utf-8")
    conf_int = model.conf_int()
    coefficient_table = pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.values,
            "std_error": model.bse.values,
            "t_value": model.tvalues.values,
            "p_value": model.pvalues.values,
            "ci_low": conf_int.iloc[:, 0].values,
            "ci_high": conf_int.iloc[:, 1].values,
        }
    )
    coefficient_table.to_csv(coefficients_path, index=False)
    return str(summary_path), str(coefficients_path)


def _write_single_group_plotly_chart(
        stem: str,
        data: pd.DataFrame,
        *,
        year_col: str,
        series_col: str,
        y_col: str,
        title: str,
        color_map: dict[str, str],
        yaxis_title: str,
        hover_value_label: str,
) -> str:
    fig = go.Figure()
    for series_name, group in data.groupby(series_col):
        ordered = group.sort_values(year_col).copy()
        color = color_map.get(str(series_name), BLUE)
        fig.add_trace(
            go.Scatter(
                x=ordered[year_col],
                y=ordered[y_col],
                mode="lines+markers+text",
                name=str(series_name),
                text=ordered.apply(
                    lambda row: f"{int(row[year_col])}: {row[y_col]:.1f}"
                    if int(row[year_col]) in _selected_years(ordered[year_col], 10 if ordered[year_col].nunique() > 10 else 5)
                    else "",
                    axis=1,
                ),
                textposition="top center",
                line={"color": color, "width": 2},
                marker={"size": 8, "color": "rgba(0,0,0,0)", "line": {"color": color, "width": 2}},
                hovertemplate=(
                    "Series: %{fullData.name}<br>"
                    "Completion Year: %{x}<br>"
                    f"{hover_value_label}: " + "%{y:.1f} sqm<extra></extra>"
                ),
            )
        )
    apply_standard_theme(fig, title=title, xaxis_title="Completion Year", yaxis_title=yaxis_title)
    return write_plotly_chart_html(stem, fig)


def _single_group_scatter_plotly_figure(
        data: pd.DataFrame,
        *,
        year_col: str,
        series_col: str,
        y_col: str,
        title: str,
        color_map: dict[str, str],
        yaxis_title: str,
        hover_value_label: str,
) -> go.Figure:
    fig = go.Figure()
    for series_name, group in data.groupby(series_col):
        ordered = group.sort_values(year_col).copy()
        color = color_map.get(str(series_name), BLUE)
        fig.add_trace(
            go.Scatter(
                x=ordered[year_col],
                y=ordered[y_col],
                mode="lines+markers",
                name=str(series_name),
                line={"color": color, "width": 2},
                marker={
                    "size": 8,
                    "color": f"rgba({int(to_rgba(color)[0]*255)}, {int(to_rgba(color)[1]*255)}, {int(to_rgba(color)[2]*255)}, 0.22)",
                    "line": {"color": color, "width": 2},
                },
                hovertemplate=(
                    "Series: %{fullData.name}<br>"
                    "Completion Year: %{x}<br>"
                    f"{hover_value_label}: " + "%{y:.1f}<extra></extra>"
                ),
            )
        )
        start_row = ordered.iloc[0]
        end_row = ordered.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=[start_row[year_col], end_row[year_col]],
                y=[start_row[y_col], end_row[y_col]],
                mode="text",
                text=[f"{start_row[y_col]:.1f}", f"{end_row[y_col]:.1f}"],
                textposition=["middle left", "middle right"],
                textfont={"color": color, "size": 11},
                showlegend=False,
                hoverinfo="skip",
            )
        )
    apply_standard_theme(fig, title=title, xaxis_title="Completion Year", yaxis_title=yaxis_title)
    fig.update_layout(
        legend={
            "title": None,
            "bgcolor": "rgba(0,0,0,0)",
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.08,
            "xanchor": "center",
            "x": 0.5,
        },
        margin={"t": 110},
    )
    return fig


def _horizontal_bar_plotly_figure(
        data: pd.DataFrame,
        *,
        x_col: str,
        y_col: str,
        title: str,
        xaxis_title: str,
) -> go.Figure:
    ordered = data.sort_values(x_col).copy()
    fill_colors = []
    edge_colors = []
    for label in ordered[y_col]:
        rgba = to_rgba(FLAT_TYPE_COLOR_MAP.get(label, BLUE), 0.42)
        fill_colors.append(f"rgba({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)}, {rgba[3]:.2f})")
        edge_colors.append(FLAT_TYPE_COLOR_MAP.get(label, BLUE))
    fig = go.Figure(
        go.Bar(
            x=ordered[x_col],
            y=ordered[y_col],
            orientation="h",
            marker={"color": fill_colors, "line": {"color": edge_colors, "width": 1.3}},
            text=ordered[x_col].map(lambda value: f"{value:.2f}"),
            textposition="outside",
            hovertemplate="%{y}<br>Average annual change: %{x:.2f} sqm<extra></extra>",
        )
    )
    apply_standard_theme(fig, title=title, xaxis_title=xaxis_title, yaxis_title="")
    fig.add_vline(x=0, line_dash="dash", line_color=GRAY, line_width=1)
    fig.update_layout(showlegend=False)
    return fig


def _connected_scatter_plotly_figure(
        data: pd.DataFrame,
        *,
        year_col: str,
        series_col: str,
        y_col: str,
        title: str | None,
        color_map: dict[str, str],
        yaxis_title: str,
        hover_value_label: str,
        width: int | None = None,
        height: int | None = None,
) -> go.Figure:
    theme = load_plotly_theme()
    groups = _type_groups_for_plot(data, series_col=series_col)
    fig = make_subplots(rows=1, cols=len(groups), subplot_titles=[label for label, _ in groups], shared_yaxes=True)
    for col_idx, (_, members) in enumerate(groups, start=1):
        subset = data.loc[data[series_col].isin(members)].copy()
        legend_name = "legend" if col_idx == 1 else f"legend{col_idx}"
        for series_name, group in subset.groupby(series_col):
            ordered = group.sort_values(year_col).copy()
            color = color_map.get(series_name, theme.blue)
            fig.add_trace(
                go.Scatter(
                    x=ordered[year_col],
                    y=ordered[y_col],
                    mode="lines+markers",
                    name=str(series_name),
                    legendgroup=str(series_name),
                    showlegend=True,
                    legend=legend_name,
                    line={"color": color, "width": 2},
                    marker={
                        "size": 8,
                        "color": "rgba(0,0,0,0)",
                        "line": {"color": color, "width": 2},
                    },
                    hovertemplate=(
                        "Series: %{fullData.name}<br>"
                        "Completion Year: %{x}<br>"
                        f"{hover_value_label}: " + "%{y:.1f} sqm<extra></extra>"
                    ),
                ),
                row=1,
                col=col_idx,
            )
            start_row = ordered.iloc[0]
            end_row = ordered.iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=[start_row[year_col], end_row[year_col]],
                    y=[start_row[y_col], end_row[y_col]],
                    mode="text",
                    text=[f"{start_row[y_col]:.1f}", f"{end_row[y_col]:.1f}"],
                    textposition=["middle left", "middle right"],
                    textfont={"color": color, "size": 11},
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1,
                col=col_idx,
            )
    apply_standard_theme(fig, title=title, xaxis_title="Completion Year", yaxis_title=yaxis_title)
    for col_idx in range(1, len(groups) + 1):
        fig.update_xaxes(title_text="Completion Year", row=1, col=col_idx)
    fig.update_yaxes(title_text=yaxis_title, row=1, col=1)
    layout_updates: dict[str, object] = {
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.08,
            "xanchor": "center",
            "x": 0.23,
            "bgcolor": "rgba(0,0,0,0)",
        }
    }
    if len(groups) >= 2:
        layout_updates["legend2"] = {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.08,
            "xanchor": "center",
            "x": 0.77,
            "bgcolor": "rgba(0,0,0,0)",
        }
    fig.update_layout(
        **layout_updates,
        margin={"t": 64 if title is None else 120},
        width=width,
        height=height,
    )
    return fig


def rebuild_question_b_figures() -> None:
    _rebuild_s3qb_f1()
    _rebuild_s3qb_f2()
    _rebuild_s3qb_f3()
    _rebuild_s3qb_f4()


def _rebuild_s3qb_f1() -> None:
    data = load_figure_data("S3QbF1_floor_area_over_time")
    year_col = "completion_year" if "completion_year" in data.columns else "transaction_year"
    featured = data.loc[data["series"].ne("Overall average")].copy()
    overall = data.loc[data["series"].eq("Overall average")].copy()
    svg_path, _, _ = save_plotly_figure(
        "S3QbF1_floor_area_over_time",
        _connected_scatter_plotly_figure(
            data,
            year_col=year_col,
            series_col="series",
            y_col="avg_floor_area",
            title=None,
            color_map={"Overall average": BLUE, **FLAT_TYPE_COLOR_MAP},
            yaxis_title="Floor Area (sqm)",
            hover_value_label="Average Floor Area",
            width=1280,
            height=720,
        ),
        title=None,
        data=data,
    )
    _write_floor_area_over_time_svg(
        data.rename(columns={year_col: "completion_year"}) if year_col != "completion_year" else data,
        output_path=svg_path,
        title=None,
        panels=[
            ("Common types", COMMON_FLAT_TYPES),
            ("Sparse / niche types", SPARSE_FLAT_TYPES),
        ],
        figsize=(16, 5.8),
    )
    for suffix, members, label in [("a", COMMON_FLAT_TYPES, "Common flat types"), ("b", SPARSE_FLAT_TYPES, "Sparse and niche flat types")]:
        subset = featured.loc[featured["series"].isin(members)].copy()
        if subset.empty:
            continue
        panel_data = pd.concat([overall, subset], ignore_index=True, sort=False)
        subset_palette = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in members if flat_type in set(subset["series"])}
        split_svg, _, _ = save_plotly_figure(
            f"S3QbF1{suffix}_floor_area_over_time",
            _single_group_scatter_plotly_figure(
                panel_data,
                year_col=year_col,
                series_col="series",
                y_col="avg_floor_area",
                title=label,
                color_map={"Overall average": BLUE, **subset_palette},
                yaxis_title="Floor Area (sqm)",
                hover_value_label="Average Floor Area",
            ),
            title=label,
            data=panel_data,
        )
        _write_floor_area_over_time_svg(
            panel_data.rename(columns={year_col: "completion_year"}) if year_col != "completion_year" else panel_data,
            output_path=split_svg,
            title=label,
            panels=[(label, members)],
        )


def _rebuild_s3qb_f2() -> None:
    slope_plot = load_figure_data("S3QbF2_floor_area_slope_by_type")
    save_plotly_figure(
        "S3QbF2_floor_area_slope_by_type",
        _horizontal_bar_plotly_figure(
            slope_plot,
            x_col="slope",
            y_col="flat_type",
            title="Average size change by completion year",
            xaxis_title="Average Annual Change in Floor Area (sqm)",
        ),
        title="Average size change by completion year",
        data=slope_plot,
    )


def _rebuild_s3qb_f3() -> None:
    featured_decline = load_figure_data("S3QbF3_floor_area_post_2008")
    year_col = "completion_year" if "completion_year" in featured_decline.columns else "transaction_year"
    save_plotly_figure(
        "S3QbF3_floor_area_post_2008",
        _connected_scatter_plotly_figure(
            featured_decline,
            year_col=year_col,
            series_col="flat_type",
            y_col="avg_floor_area",
            title=None,
            color_map={flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in MAJOR_FLAT_TYPES if flat_type in set(featured_decline["flat_type"])},
            yaxis_title="Floor Area (sqm)",
            hover_value_label="Average Floor Area",
            width=1280,
            height=720,
        ),
        title=None,
        data=featured_decline,
    )
    for suffix, members, label in [("a", COMMON_FLAT_TYPES, "Recent completion years: common flat types"), ("b", SPARSE_FLAT_TYPES, "Recent completion years: sparse and niche flat types")]:
        subset = featured_decline.loc[featured_decline["flat_type"].isin(members)].copy()
        if subset.empty:
            continue
        subset_palette = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in members if flat_type in set(subset["flat_type"])}
        save_plotly_figure(
            f"S3QbF3{suffix}_floor_area_post_2008",
            _single_group_scatter_plotly_figure(
                subset,
                year_col=year_col,
                series_col="flat_type",
                y_col="avg_floor_area",
                title=label,
                color_map=subset_palette,
                yaxis_title="Floor Area (sqm)",
                hover_value_label="Average Floor Area",
            ),
            title=label,
            data=subset,
        )


def _rebuild_s3qb_f4() -> None:
    profile = load_figure_data("S3QbF4_adjusted_year_trend_by_type").copy()
    save_plotly_figure(
        "S3QbF4_adjusted_year_trend_by_type",
        _connected_scatter_plotly_figure(
            profile,
            year_col="completion_year",
            series_col="flat_type",
            y_col="coef_vs_baseline",
            title=None,
            color_map={flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in MAJOR_FLAT_TYPES if flat_type in set(profile["flat_type"])},
            yaxis_title="Coefficient vs baseline year (sqm)",
            hover_value_label="Coefficient vs Baseline",
            width=1280,
            height=720,
        ),
        title=None,
        data=profile,
    )
    for suffix, members, label in [("a", COMMON_FLAT_TYPES, "Year-dummy coefficients: common flat types"), ("b", SPARSE_FLAT_TYPES, "Year-dummy coefficients: sparse and niche flat types")]:
        subset = profile.loc[profile["flat_type"].isin(members)].copy()
        if subset.empty:
            continue
        subset_palette = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in members if flat_type in set(subset["flat_type"])}
        save_plotly_figure(
            f"S3QbF4{suffix}_adjusted_year_trend_by_type",
            _single_group_scatter_plotly_figure(
                subset,
                year_col="completion_year",
                series_col="flat_type",
                y_col="coef_vs_baseline",
                title=label,
                color_map=subset_palette,
                yaxis_title="Coefficient vs baseline year (sqm)",
                hover_value_label="Coefficient vs Baseline",
            ),
            title=label,
            data=subset,
        )


def analyze_flat_sizes(frame: pd.DataFrame) -> dict[str, object]:
    sample = frame.copy()
    sample["completion_year"] = _derive_completion_year(sample)
    sample = sample.dropna(subset=["floor_area_sqm", "completion_year", "flat_type", "town"]).copy()
    sample["completion_year"] = pd.to_numeric(sample["completion_year"], errors="coerce")
    sample = sample.loc[sample["completion_year"].between(1960, sample["completion_year"].max())].copy()

    overall = sample.groupby("completion_year").agg(
        avg_floor_area=("floor_area_sqm", "mean"),
        transactions=("floor_area_sqm", "size")
    ).reset_index()
    within_type = sample.groupby(["completion_year", "flat_type"]).agg(
        avg_floor_area=("floor_area_sqm", "mean"),
        transactions=("floor_area_sqm", "size")
    ).reset_index()
    overall_slope = float(
        np.polyfit(overall["completion_year"], overall["avg_floor_area"], 1)[0]
    )
    within_slopes = pd.DataFrame(
        [
            {
                "flat_type": flat_type,
                "slope": float(np.polyfit(group["completion_year"], group["avg_floor_area"], 1)[0])
            }
            for flat_type, group in within_type.groupby("flat_type")]
    )

    # Model 1 is intentionally the simple average trend specification:
    # one common completion-year slope after controlling for flat type and town.
    controlled_regression = smf.ols(
        "floor_area_sqm ~ completion_year + C(flat_type) + C(town)",
        data=sample
    ).fit(cov_type="HC3")
    controlled_coef = float(controlled_regression.params["completion_year"])
    controlled_pvalue = float(controlled_regression.pvalues["completion_year"])
    controlled_summary_path, controlled_coefficients_path = _save_model_outputs(
        controlled_regression,
        stem="S3Qb_model_controlled_completion_year",
    )
    average_within_slope = float(within_slopes["slope"].mean())

    focus_flat_types = [flat_type for flat_type in MAJOR_FLAT_TYPES if flat_type in set(sample["flat_type"])]
    interaction_sample = sample.loc[sample["flat_type"].isin(focus_flat_types)].copy()
    interaction_reference_flat_type = "4 ROOM" if "4 ROOM" in set(interaction_sample["flat_type"]) else sorted(set(interaction_sample["flat_type"]))[0]
    interaction_cells = (
        interaction_sample.groupby(["completion_year", "flat_type", "town"], as_index=False)
        .agg(
            floor_area_sqm=("floor_area_sqm", "mean"),
            transactions=("floor_area_sqm", "size"),
        )
    )
    reference_town = interaction_cells["town"].value_counts().idxmax()
    interaction_regression = smf.wls(
        f"floor_area_sqm ~ C(completion_year) * C(flat_type, Treatment(reference='{interaction_reference_flat_type}')) + C(town)",
        data=interaction_cells,
        weights=interaction_cells["transactions"],
    ).fit(cov_type="HC3")
    interaction_summary_path, interaction_coefficients_path = _save_model_outputs(
        interaction_regression,
        stem="S3Qb_model_completion_year_dummy_interaction",
    )
    observed_pairs = (
        interaction_cells.groupby(["completion_year", "flat_type"])
        .size()
        .reset_index(name="transactions")
        .loc[:, ["completion_year", "flat_type"]]
        .drop_duplicates()
    )
    adjusted_profile = _adjusted_completion_profile(
        interaction_regression,
        reference_town=reference_town,
        observed_pairs=observed_pairs,
    )

    featured_types = within_type.loc[within_type["flat_type"].isin(focus_flat_types)].copy()
    size_f1_data_frame = pd.concat(
        [
            overall.assign(series="Overall average")[["completion_year", "avg_floor_area", "transactions", "series"]],
            featured_types.assign(series=featured_types["flat_type"])[["completion_year", "avg_floor_area", "transactions", "series", "flat_type"]],
        ],
        ignore_index=True,
        sort=False,
    )
    palette_map = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in focus_flat_types}
    size_f1_svg, size_f1_html, size_f1_data = save_plotly_figure(
        "S3QbF1_floor_area_over_time",
        _connected_scatter_plotly_figure(
            size_f1_data_frame,
            year_col="completion_year",
            series_col="series",
            y_col="avg_floor_area",
            title=None,
            color_map={"Overall average": BLUE, **palette_map},
            yaxis_title="Floor Area (sqm)",
            hover_value_label="Average Floor Area",
            width=1280,
            height=720,
        ),
        title=None,
        data=size_f1_data_frame,
    )
    _write_floor_area_over_time_svg(
        size_f1_data_frame,
        output_path=size_f1_svg,
        title=None,
        panels=[
            ("Common types", COMMON_FLAT_TYPES),
            ("Sparse / niche types", SPARSE_FLAT_TYPES),
        ],
        figsize=(16, 5.8),
    )
    split_chart_svgs: list[str] = []
    split_chart_html: list[str] = []
    split_chart_data: list[str] = []
    for suffix, members, label in [("a", COMMON_FLAT_TYPES, "Common flat types"), ("b", SPARSE_FLAT_TYPES, "Sparse and niche flat types")]:
        subset = featured_types.loc[featured_types["flat_type"].isin(members)].copy()
        if subset.empty:
            continue
        subset_palette = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in members if flat_type in set(subset["flat_type"])}
        panel_data = pd.concat([overall.assign(series="Overall average"), subset.assign(series=subset["flat_type"])], ignore_index=True, sort=False)
        split_svg, split_html, split_data = save_plotly_figure(
            f"S3QbF1{suffix}_floor_area_over_time",
            _single_group_scatter_plotly_figure(
                panel_data,
                year_col="completion_year",
                series_col="series",
                y_col="avg_floor_area",
                title=label,
                color_map={"Overall average": BLUE, **subset_palette},
                yaxis_title="Floor Area (sqm)",
                hover_value_label="Average Floor Area",
            ),
            title=label,
            data=panel_data,
        )
        _write_floor_area_over_time_svg(
            panel_data,
            output_path=split_svg,
            title=label,
            panels=[(label, members)],
        )
        split_chart_svgs.append(split_svg)
        split_chart_html.append(split_html)
        if split_data:
            split_chart_data.append(split_data)

    slope_plot = within_slopes.sort_values("slope").copy()
    size_f2_svg, size_f2_html, size_f2_data = save_plotly_figure(
        "S3QbF2_floor_area_slope_by_type",
        _horizontal_bar_plotly_figure(
            slope_plot,
            x_col="slope",
            y_col="flat_type",
            title="Average size change by completion year",
            xaxis_title="Average Annual Change in Floor Area (sqm)",
        ),
        title="Average size change by completion year",
        data=slope_plot.copy(),
    )

    featured_decline = within_type.loc[within_type["completion_year"].ge(2000) & within_type["flat_type"].isin(focus_flat_types)].copy()
    palette_map_recent = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in focus_flat_types if flat_type in set(featured_decline["flat_type"])}
    size_f3_svg, size_f3_html, size_f3_data = save_plotly_figure(
        "S3QbF3_floor_area_post_2008",
        _connected_scatter_plotly_figure(
            featured_decline,
            year_col="completion_year",
            series_col="flat_type",
            y_col="avg_floor_area",
            title=None,
            color_map=palette_map_recent,
            yaxis_title="Floor Area (sqm)",
            hover_value_label="Average Floor Area",
            width=1280,
            height=720,
        ),
        title=None,
        data=featured_decline.copy(),
    )
    for suffix, members, label in [("a", COMMON_FLAT_TYPES, "Recent completion years: common flat types"), ("b", SPARSE_FLAT_TYPES, "Recent completion years: sparse and niche flat types")]:
        subset = featured_decline.loc[featured_decline["flat_type"].isin(members)].copy()
        if subset.empty:
            continue
        subset_palette = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in members if flat_type in set(subset["flat_type"])}
        split_svg, split_html, split_data = save_plotly_figure(
            f"S3QbF3{suffix}_floor_area_post_2008",
            _single_group_scatter_plotly_figure(
                subset,
                year_col="completion_year",
                series_col="flat_type",
                y_col="avg_floor_area",
                title=label,
                color_map=subset_palette,
                yaxis_title="Floor Area (sqm)",
                hover_value_label="Average Floor Area",
            ),
            title=label,
            data=subset,
        )
        split_chart_svgs.append(split_svg)
        split_chart_html.append(split_html)
        if split_data:
            split_chart_data.append(split_data)

    adjusted_profile_plot = adjusted_profile.sort_values(["flat_type", "completion_year"]).reset_index(drop=True)
    adjusted_profile_plot = _relative_coefficient_profile(adjusted_profile_plot)
    palette_map_adjusted = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in focus_flat_types}
    size_f4_svg, size_f4_html, size_f4_data = save_plotly_figure(
        "S3QbF4_adjusted_year_trend_by_type",
        _connected_scatter_plotly_figure(
            adjusted_profile_plot,
            year_col="completion_year",
            series_col="flat_type",
            y_col="coef_vs_baseline",
            title=None,
            color_map=palette_map_adjusted,
            yaxis_title="Coefficient vs baseline year (sqm)",
            hover_value_label="Coefficient vs Baseline",
            width=1280,
            height=720,
        ),
        title=None,
        data=adjusted_profile_plot.copy(),
    )
    for suffix, members, label in [("a", COMMON_FLAT_TYPES, "Year-dummy coefficients: common flat types"), ("b", SPARSE_FLAT_TYPES, "Year-dummy coefficients: sparse and niche flat types")]:
        subset = adjusted_profile_plot.loc[adjusted_profile_plot["flat_type"].isin(members)].copy()
        if subset.empty:
            continue
        subset_palette = {flat_type: FLAT_TYPE_COLOR_MAP[flat_type] for flat_type in members if flat_type in set(subset["flat_type"])}
        split_svg, split_html, split_data = save_plotly_figure(
            f"S3QbF4{suffix}_adjusted_year_trend_by_type",
            _single_group_scatter_plotly_figure(
                subset,
                year_col="completion_year",
                series_col="flat_type",
                y_col="coef_vs_baseline",
                title=label,
                color_map=subset_palette,
                yaxis_title="Coefficient vs baseline year (sqm)",
                hover_value_label="Coefficient vs Baseline",
            ),
            title=label,
            data=subset,
        )
        split_chart_svgs.append(split_svg)
        split_chart_html.append(split_html)
        if split_data:
            split_chart_data.append(split_data)

    return {
        "banner_statement": "Newer completions tend to be smaller in larger flat types, but the pattern is not universal across all flat categories.",
        "hypothesis": "If newer HDB completions are designed smaller, then average floor area should decline with completion year within flat type.",
        "method": "Track floor area by completion year, compare within flat type, and estimate a controlled completion-year trend with town controls.",
        "controls": ["flat_type", "town"],
        "overall_slope_sqm_per_completion_year": overall_slope,
        "average_within_type_slope_sqm_per_completion_year": average_within_slope,
        "controlled_completion_year_trend_coef": controlled_coef,
        "controlled_completion_year_trend_pvalue": controlled_pvalue,
        "controlled_model_summary_path": controlled_summary_path,
        "controlled_model_coefficients_path": controlled_coefficients_path,
        "interaction_reference_flat_type": interaction_reference_flat_type,
        "interaction_reference_town": reference_town,
        "interaction_model_summary_path": interaction_summary_path,
        "interaction_model_coefficients_path": interaction_coefficients_path,
        "adjusted_completion_year_profile": adjusted_profile.sort_values(["flat_type", "completion_year"]).to_dict("records"),
        "within_type_slopes": within_slopes.sort_values("flat_type").to_dict("records"),
        "interpretation": "The completion-year view points to a real design-size decline in larger flat types, especially 4-room, 5-room, and Executive flats.",
        "chart_commentary": [
            "Start with the connected-scatter chart by completion year to frame the question as a design trend rather than a transaction-mix trend.",
            "Use the slope chart to identify which flat types show the strongest decline as completion year becomes newer.",
            "Use the recent-completion chart as the clearest visual for the presentation, because the decline is easiest to see there.",
            "Use the year-dummy interaction chart on the method slide to show a non-linear adjusted completion-year profile by flat type after controlling for town.",
        ],
        "limitations": [
            "Completion year is derived from the available lease-commence information and may not equal the exact physical completion date in every case.",
            "Resale transactions may not reflect the full underlying stock of flats built in each completion year.",
        ],
        "charts": [size_f1_svg, size_f2_svg, size_f3_svg, size_f4_svg, *split_chart_svgs],
        "chart_html": [size_f1_html, size_f2_html, size_f3_html, size_f4_html, *split_chart_html],
        "chart_data": [path for path in [size_f1_data, size_f2_data, size_f3_data, size_f4_data, *split_chart_data] if path],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 3 Question B analysis.")
    parser.add_argument("--figures-only", action="store_true")
    parser.add_argument("--skip-html", action="store_true")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    configure_logging(args.log_level)
    set_write_html(not args.skip_html)
    if args.figures_only:
        rebuild_question_b_figures()
        return
    summary = analyze_flat_sizes(load_frame())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
