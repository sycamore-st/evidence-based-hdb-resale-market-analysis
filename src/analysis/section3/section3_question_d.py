from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import statsmodels.formula.api as smf

from src.analysis.section3.S3_helpers import (
    ACCENT,
    BLUE,
    CENTRAL_COE_CONTROL_TOWNS,
    FAR_TOWNS,
    GREEN,
    GRAY,
    ORANGE,
    annotate_scatter_labels,
    annotate_series_endpoints,
    configure_logging,
    load_frame,
    load_figure_data,
    save_plotly_figure,
    save_svg_and_html,
    set_write_html,
    year_month_label,
)
from src.pipeline.hdb_api import fetch_coe_raw


SECTION3_RESULTS = Path("outputs/section3/results")


def _save_model_outputs(stem: str, model: object) -> tuple[str, str]:
    SECTION3_RESULTS.mkdir(parents=True, exist_ok=True)
    summary_path = SECTION3_RESULTS / f"{stem}_summary.txt"
    coef_path = SECTION3_RESULTS / f"{stem}_coefficients.csv"
    summary_path.write_text(str(model.summary()), encoding="utf-8")
    conf = model.conf_int()
    coef_table = pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.values,
            "pvalue": model.pvalues.reindex(model.params.index).values,
            "ci_low": conf.iloc[:, 0].reindex(model.params.index).values,
            "ci_high": conf.iloc[:, 1].reindex(model.params.index).values,
        }
    )
    coef_table.to_csv(coef_path, index=False)
    return str(summary_path), str(coef_path)


def _rgba_string(color: str, alpha: float) -> str:
    rgba = to_rgba(color, alpha)
    return f"rgba({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)}, {rgba[3]:.2f})"


def _indexed_trends_plotly_figure(data: pd.DataFrame, *, title: str) -> go.Figure:
    fig = go.Figure()
    town_data = data.loc[data["series"].ne("COE index")].copy()
    coe_data = data.loc[data["series"].eq("COE index")].copy()
    color_map = {
        "CENTRAL AREA": BLUE,
        "PUNGGOL": ORANGE,
        "SENGKANG": GREEN,
        "Central adjusted housing index": BLUE,
        "Sengkang/Punggol adjusted housing index": ORANGE,
        "COE index": ACCENT,
    }
    for series_name, group in town_data.groupby("series"):
        ordered = group.sort_values("month")
        fig.add_trace(
            go.Scatter(
                x=ordered["month"],
                y=ordered["index_value"],
                mode="lines+markers+text",
                name=series_name,
                text=[""] * (len(ordered) - 1) + [f"{ordered['index_value'].iloc[-1]:.1f}"],
                textposition="top center",
                line={"color": color_map.get(series_name, BLUE), "width": 2.2},
                marker={"size": 7, "color": _rgba_string(color_map.get(series_name, BLUE), 0.25), "line": {"color": color_map.get(series_name, BLUE), "width": 1.8}},
                hovertemplate="%{fullData.name}<br>%{x|%Y-%m}<br>Index: %{y:.1f}<extra></extra>",
            )
        )
    if not coe_data.empty:
        ordered = coe_data.sort_values("month")
        fig.add_trace(
            go.Scatter(
                x=ordered["month"],
                y=ordered["index_value"],
                mode="lines+markers+text",
                name="COE index",
                text=[""] * (len(ordered) - 1) + [f"{ordered['index_value'].iloc[-1]:.1f}"],
                textposition="top center",
                line={"color": ACCENT, "width": 2.2, "dash": "dash"},
                marker={"size": 7, "color": _rgba_string(ACCENT, 0.22), "line": {"color": ACCENT, "width": 1.8}},
                yaxis="y2",
                hovertemplate="COE index<br>%{x|%Y-%m}<br>Index: %{y:.1f}<extra></extra>",
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis={"title": "Housing Index (Start = 100)"},
        yaxis2={"title": "COE Index (Start = 100)", "overlaying": "y", "side": "right"},
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _spread_plotly_figure(spread: pd.DataFrame) -> go.Figure:
    ordered = spread.sort_values("month").copy()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ordered["month"],
            y=ordered["far_minus_central"],
            mode="lines+markers+text",
            name="Far minus central",
            text=[""] * (len(ordered) - 1) + [f"{ordered['far_minus_central'].iloc[-1]:.0f}"],
            textposition="top center",
            line={"color": BLUE, "width": 2.2},
            marker={"size": 7, "color": _rgba_string(BLUE, 0.25), "line": {"color": BLUE, "width": 1.8}},
            hovertemplate="%{x|%Y-%m}<br>Spread: SGD %{y:,.0f}<extra></extra>",
        )
    )
    if "coe_index" in ordered.columns:
        fig.add_trace(
            go.Scatter(
                x=ordered["month"],
                y=ordered["coe_index"],
                mode="lines+markers+text",
                name="COE index",
                text=[""] * (len(ordered) - 1) + [f"{ordered['coe_index'].iloc[-1]:.1f}"],
                textposition="top center",
                line={"color": ACCENT, "width": 2.2, "dash": "dash"},
                marker={"size": 7, "color": _rgba_string(ACCENT, 0.22), "line": {"color": ACCENT, "width": 1.8}},
                yaxis="y2",
                hovertemplate="COE index<br>%{x|%Y-%m}<br>Index: %{y:.1f}<extra></extra>",
            )
        )
    fig.add_hline(y=0, line_dash="dash", line_color=GRAY, line_width=1)
    fig.update_layout(
        title="Far-town vs central-town resale price spread",
        xaxis_title="Month",
        yaxis={"title": "Resale Price Spread (SGD)"},
        yaxis2={"title": "COE Index (Start = 100)", "overlaying": "y", "side": "right"},
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _indexed_spread_plotly_figure(spread: pd.DataFrame) -> go.Figure:
    ordered = spread.sort_values("month").copy()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ordered["month"],
            y=ordered["far_minus_central_index"],
            mode="lines+markers+text",
            name="Adjusted far minus central",
            text=[""] * (len(ordered) - 1) + [f"{ordered['far_minus_central_index'].iloc[-1]:.1f}"],
            textposition="top center",
            line={"color": ORANGE, "width": 2.2},
            marker={"size": 7, "color": _rgba_string(ORANGE, 0.22), "line": {"color": ORANGE, "width": 1.8}},
            hovertemplate="%{x|%Y-%m}<br>Adjusted spread: %{y:.1f} index points<extra></extra>",
        )
    )
    if "coe_index" in ordered.columns:
        fig.add_trace(
            go.Scatter(
                x=ordered["month"],
                y=ordered["coe_index"],
                mode="lines+markers+text",
                name="COE index",
                text=[""] * (len(ordered) - 1) + [f"{ordered['coe_index'].iloc[-1]:.1f}"],
                textposition="top center",
                line={"color": ACCENT, "width": 2.2, "dash": "dash"},
                marker={"size": 7, "color": _rgba_string(ACCENT, 0.22), "line": {"color": ACCENT, "width": 1.8}},
                yaxis="y2",
                hovertemplate="COE index<br>%{x|%Y-%m}<br>Index: %{y:.1f}<extra></extra>",
            )
        )
    fig.add_hline(y=0, line_dash="dash", line_color=GRAY, line_width=1)
    fig.update_layout(
        title="Adjusted far-town vs central-town housing index spread",
        xaxis_title="Month",
        yaxis={"title": "Adjusted Housing Index Spread"},
        yaxis2={"title": "COE Index (Start = 100)", "overlaying": "y", "side": "right"},
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _scatter_regression_plotly_figure(scatter_df: pd.DataFrame) -> go.Figure:
    ordered = scatter_df.dropna(subset=["avg_coe_premium", "far_minus_central"]).copy()
    slope, intercept = np.polyfit(ordered["avg_coe_premium"], ordered["far_minus_central"], 1)
    x_line = np.linspace(float(ordered["avg_coe_premium"].min()), float(ordered["avg_coe_premium"].max()), 100)
    y_line = intercept + slope * x_line
    sample_labels = ordered.sort_values("avg_coe_premium").iloc[[0, len(ordered) // 2, len(ordered) - 1]].copy() if len(ordered) >= 3 else ordered.copy()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ordered["avg_coe_premium"],
            y=ordered["far_minus_central"],
            mode="markers",
            name="Monthly observations",
            marker={"size": 7, "color": _rgba_string(ORANGE, 0.22), "line": {"color": ORANGE, "width": 1.1}},
            hovertemplate="COE Premium: SGD %{x:,.0f}<br>Spread: SGD %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="Trend line",
            line={"color": ORANGE, "width": 2.2},
            hoverinfo="skip",
        )
    )
    if not sample_labels.empty:
        fig.add_trace(
            go.Scatter(
                x=sample_labels["avg_coe_premium"],
                y=sample_labels["far_minus_central"],
                mode="text",
                text=sample_labels["far_minus_central"].map(lambda value: f"{value:.0f}"),
                textposition="top center",
                showlegend=False,
                hoverinfo="skip",
            )
        )
    fig.add_hline(y=0, line_dash="dash", line_color=GRAY, line_width=1)
    fig.update_layout(
        title="COE premium and far-town price spread",
        xaxis_title="COE Premium (SGD)",
        yaxis_title="Resale Price Spread (SGD)",
        legend={"title": None, "bgcolor": "rgba(0,0,0,0)"},
    )
    return fig


def _partial_regression_plotly_figure(partial_df: pd.DataFrame, *, title: str) -> go.Figure:
    plot_df = partial_df.sort_values("display_order", ascending=False).copy()
    color_map = {
        "Central towns COE elasticity": BLUE,
        "Extra Sengkang/Punggol sensitivity": ORANGE,
        "Implied Sengkang/Punggol elasticity": GREEN,
        "Central-town raw-price COE elasticity": BLUE,
        "Extra far-town raw-price sensitivity": ORANGE,
        "Implied far-town raw-price elasticity": GREEN,
        "Central adjusted index COE elasticity": BLUE,
        "Extra far-town index sensitivity": ORANGE,
        "Implied far-town index elasticity": GREEN,
    }

    def _stars(pvalue: float) -> str:
        if pd.isna(pvalue):
            return ""
        if pvalue < 0.01:
            return "***"
        if pvalue < 0.05:
            return "**"
        if pvalue < 0.10:
            return "*"
        return ""

    fig = go.Figure()
    point_annotations: list[dict[str, object]] = []
    for _, row in plot_df.iterrows():
        color = color_map[row["label"]]
        label_text = f"{row['effect_pct']:.2f}%{_stars(float(row['pvalue']))}"
        fig.add_trace(
            go.Scatter(
                x=[row["effect_pct_ci_low"], row["effect_pct_ci_high"]],
                y=[row["label"], row["label"]],
                mode="lines",
                line={"color": color, "width": 5},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[row["effect_pct"]],
                y=[row["label"]],
                mode="markers",
                name=row["label"],
                marker={"size": 18, "color": _rgba_string(color, 0.18), "line": {"color": color, "width": 2.6}},
                hovertemplate=(
                    f"{row['label']}<br>"
                    "Effect: %{x:.2f}%<br>"
                    f"CI: {row['effect_pct_ci_low']:.2f}% to {row['effect_pct_ci_high']:.2f}%<extra></extra>"
                ),
            )
        )
        point_annotations.append(
            {
                "x": float(row["effect_pct"]),
                "y": row["label"],
                "text": label_text,
                "showarrow": False,
                "xshift": 44,
                "font": {"size": 18, "color": "#000000"},
                "xanchor": "left",
                "yanchor": "middle",
                "bgcolor": "rgba(255,255,255,0.96)",
                "bordercolor": "rgba(0,0,0,0)",
            }
        )
    fig.add_vline(x=0, line_dash="dash", line_color=GRAY, line_width=1)
    fig.update_layout(
        title=title,
        xaxis_title="Approx. % resale-price change for a 1% COE increase",
        yaxis_title="",
        width=1180,
        height=780,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 120, "b": 130, "l": 240, "r": 120},
        annotations=point_annotations + [
            {
                "x": 0.01,
                "y": -0.18,
                "xref": "paper",
                "yref": "paper",
                "text": "Each row shows the point estimate and 95% confidence interval. Stars mark significance: * p<0.10, ** p<0.05, *** p<0.01.",
                "showarrow": False,
                "xanchor": "left",
                "yanchor": "bottom",
                "font": {"size": 14, "color": "#000000"},
                "bgcolor": "rgba(0,0,0,0)",
            }
        ],
    )
    fig.update_xaxes(tickfont={"size": 16}, title_font={"size": 17})
    fig.update_yaxes(tickfont={"size": 18})
    return fig


def rebuild_question_d_figures() -> None:
    _rebuild_s3qd_f1()
    _rebuild_s3qd_f1b()
    _rebuild_s3qd_f2()
    _rebuild_s3qd_f2b()
    _rebuild_s3qd_f3()
    _rebuild_s3qd_f4()
    _rebuild_s3qd_f5()


def _rebuild_s3qd_f1() -> None:
    data = load_figure_data("S3QdF1_indexed_coe_and_resale_trends")
    if "series" not in data.columns:
        town_data = data[["month", "town", "price_index"]].rename(columns={"town": "series", "price_index": "index_value"})
        coe_data = data[["month", "coe_index"]].drop_duplicates().assign(series="COE index").rename(columns={"coe_index": "index_value"})
        data = pd.concat([town_data, coe_data], ignore_index=True, sort=False)
    save_plotly_figure(
        "S3QdF1_indexed_coe_and_resale_trends",
        _indexed_trends_plotly_figure(data, title="Indexed COE and resale price trends"),
        title="Indexed COE and resale price trends",
        data=data,
    )


def _month_effect_index(model: object, months: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    baseline_month = months[0]
    rows.append({"year_month": baseline_month, "log_index_effect": 0.0})
    for month in months[1:]:
        term = f"C(year_month)[T.{month}]"
        rows.append({"year_month": month, "log_index_effect": float(model.params.get(term, 0.0))})
    index_df = pd.DataFrame(rows)
    index_df["index_value"] = 100.0 * np.exp(index_df["log_index_effect"])
    index_df["month"] = pd.to_datetime(index_df["year_month"] + "-01")
    return index_df


def _plot_adjusted_index_chart(index_df: pd.DataFrame) -> tuple[str, str, str | None]:
    return save_plotly_figure(
        "S3QdF1b_adjusted_indexed_coe_and_resale_trends",
        _indexed_trends_plotly_figure(index_df, title="Adjusted housing price indices vs COE"),
        title="Adjusted housing price indices vs COE",
        data=index_df,
    )


def _rebuild_s3qd_f2() -> None:
    spread = load_figure_data("S3QdF2_far_vs_central_price_spread")
    save_plotly_figure(
        "S3QdF2_far_vs_central_price_spread",
        _spread_plotly_figure(spread),
        title="Far-town vs central-town resale price spread",
        data=spread,
    )


def _rebuild_s3qd_f2b() -> None:
    spread = load_figure_data("S3QdF2b_adjusted_far_vs_central_index_spread")
    save_plotly_figure(
        "S3QdF2b_adjusted_far_vs_central_index_spread",
        _indexed_spread_plotly_figure(spread),
        title="Adjusted far-town vs central-town housing index spread",
        data=spread,
    )


def _rebuild_s3qd_f3() -> None:
    scatter_df = load_figure_data("S3QdF3_coe_vs_price_spread")
    save_plotly_figure(
        "S3QdF3_coe_vs_price_spread",
        _scatter_regression_plotly_figure(scatter_df),
        title="COE premium and far-town price spread",
        data=scatter_df,
    )


def _plot_partial_regression(partial_df: pd.DataFrame) -> tuple[str, str, str | None]:
    return save_plotly_figure(
        "S3QdF4_coe_regression_coefficients",
        _partial_regression_plotly_figure(
            partial_df,
            title="What the raw-price regression says about COE sensitivity",
        ),
        title="What the raw-price regression says about COE sensitivity",
        data=partial_df.sort_values("display_order", ascending=False).copy(),
    )


def _rebuild_s3qd_f4() -> None:
    coefficient_df = load_figure_data("S3QdF4_coe_regression_coefficients")
    _plot_partial_regression(coefficient_df)


def _plot_adjusted_partial_regression(partial_df: pd.DataFrame) -> tuple[str, str, str | None]:
    return save_plotly_figure(
        "S3QdF5_adjusted_index_regression_coefficients",
        _partial_regression_plotly_figure(
            partial_df,
            title="What the adjusted-index regression says about COE sensitivity",
        ),
        title="What the adjusted-index regression says about COE sensitivity",
        data=partial_df.sort_values("display_order", ascending=False).copy(),
    )


def _rebuild_s3qd_f5() -> None:
    coefficient_df = load_figure_data("S3QdF5_adjusted_index_regression_coefficients")
    _plot_adjusted_partial_regression(coefficient_df)


def _rebuild_s3qd_f1b() -> None:
    adjusted_df = load_figure_data("S3QdF1b_adjusted_indexed_coe_and_resale_trends")
    _plot_adjusted_index_chart(adjusted_df)


def _build_adjusted_index_spread(index_df: pd.DataFrame) -> pd.DataFrame:
    housing_only = index_df.loc[index_df["series"].isin(["Central adjusted housing index", "Sengkang/Punggol adjusted housing index"])].copy()
    pivoted = (
        housing_only.pivot(index="month", columns="series", values="index_value")
        .dropna()
        .reset_index()
        .rename(
            columns={
                "Central adjusted housing index": "central_index",
                "Sengkang/Punggol adjusted housing index": "far_index",
            }
        )
    )
    pivoted["far_minus_central_index"] = pivoted["far_index"] - pivoted["central_index"]
    coe_only = (
        index_df.loc[index_df["series"].eq("COE index"), ["month", "index_value"]]
        .rename(columns={"index_value": "coe_index"})
        .drop_duplicates()
    )
    pivoted = pivoted.merge(coe_only, on="month", how="left")
    return pivoted


def _normalize_coe_columns(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = {column: column.lower().strip().replace(" ", "_") for column in frame.columns}
    cleaned = frame.rename(columns=renamed).copy()
    month_col = next((col for col in cleaned.columns if "month" in col), None)
    premium_col = next((col for col in cleaned.columns if "quota_premium" in col or col == "premium"), None)
    vehicle_col = next((col for col in cleaned.columns if "vehicle_class" in col or col == "vehicle_category"), None)
    if not month_col or not premium_col or not vehicle_col:
        raise ValueError(f"Unexpected COE schema: {list(cleaned.columns)}")
    cleaned["month"] = pd.to_datetime(cleaned[month_col].astype(str).str[:7] + "-01", errors="coerce")
    cleaned["premium"] = pd.to_numeric(cleaned[premium_col], errors="coerce")
    cleaned["vehicle_class"] = cleaned[vehicle_col].astype(str).str.upper().str.strip()
    return cleaned[["month", "vehicle_class", "premium"]].dropna()


def _summarize_interaction_model(
    model: object,
    *,
    baseline_term: str,
    interaction_term: str,
    baseline_label: str,
    interaction_label: str,
    total_label: str,
    baseline_plain_english: str,
    interaction_plain_english: str,
    total_plain_english: str,
) -> tuple[pd.DataFrame, dict[str, float]]:
    base_effect = float(model.params[baseline_term])
    interaction_effect = float(model.params[interaction_term])
    base_pvalue = float(model.pvalues[baseline_term])
    interaction_pvalue = float(model.pvalues[interaction_term])
    cov = model.cov_params()
    total_far_effect = base_effect + interaction_effect
    total_far_variance = (
        float(cov.loc[baseline_term, baseline_term])
        + float(cov.loc[interaction_term, interaction_term])
        + 2.0 * float(cov.loc[baseline_term, interaction_term])
    )
    total_far_std = math.sqrt(max(total_far_variance, 0.0))
    total_far_ci_low = total_far_effect - 1.96 * total_far_std
    total_far_ci_high = total_far_effect + 1.96 * total_far_std
    conf_int = model.conf_int()
    coefficient_df = pd.DataFrame(
        [
            {
                "term": baseline_term,
                "label": baseline_label,
                "effect_pct": base_effect * 100.0,
                "effect_pct_ci_low": float(conf_int.loc[baseline_term].iloc[0]) * 100.0,
                "effect_pct_ci_high": float(conf_int.loc[baseline_term].iloc[1]) * 100.0,
                "pvalue": base_pvalue,
                "display_order": 0,
                "plain_english": baseline_plain_english,
            },
            {
                "term": interaction_term,
                "label": interaction_label,
                "effect_pct": interaction_effect * 100.0,
                "effect_pct_ci_low": float(conf_int.loc[interaction_term].iloc[0]) * 100.0,
                "effect_pct_ci_high": float(conf_int.loc[interaction_term].iloc[1]) * 100.0,
                "pvalue": interaction_pvalue,
                "display_order": 1,
                "plain_english": interaction_plain_english,
            },
            {
                "term": "combined_far_town_effect",
                "label": total_label,
                "effect_pct": total_far_effect * 100.0,
                "effect_pct_ci_low": total_far_ci_low * 100.0,
                "effect_pct_ci_high": total_far_ci_high * 100.0,
                "pvalue": np.nan,
                "display_order": 2,
                "plain_english": total_plain_english,
            },
        ]
    )
    return coefficient_df, {
        "base_effect": base_effect,
        "interaction_effect": interaction_effect,
        "base_pvalue": base_pvalue,
        "interaction_pvalue": interaction_pvalue,
        "total_far_effect": total_far_effect,
        "total_far_ci_low": total_far_ci_low,
        "total_far_ci_high": total_far_ci_high,
    }


def analyze_coe_link(frame: pd.DataFrame, refresh: bool = False) -> dict[str, object]:
    coe_raw = fetch_coe_raw(refresh=refresh)
    coe = _normalize_coe_columns(coe_raw)
    coe = coe.loc[coe["vehicle_class"].isin(["A", "B", "CATEGORY A", "CATEGORY B"])].copy()
    coe_monthly = coe.groupby("month").agg(avg_coe_premium=("premium", "mean")).reset_index()

    transaction_panel = frame.loc[frame["town"].isin(FAR_TOWNS | CENTRAL_COE_CONTROL_TOWNS)].copy()
    transaction_panel = transaction_panel.dropna(
        subset=["transaction_month", "town", "resale_price", "flat_age", "floor_area_sqm", "flat_type"]
    )
    transaction_panel["log_resale_price"] = np.log(transaction_panel["resale_price"])
    transaction_panel["year_month"] = year_month_label(transaction_panel["transaction_month"])
    valid_months = sorted(coe_monthly["month"].dt.to_period("M").astype(str).unique().tolist())
    transaction_panel = transaction_panel.loc[transaction_panel["year_month"].isin(valid_months)].copy()
    transaction_panel["group"] = np.where(
        transaction_panel["town"].isin(FAR_TOWNS),
        "Sengkang/Punggol adjusted housing index",
        "Central adjusted housing index",
    )

    adjusted_index_rows: list[pd.DataFrame] = []
    hedonic_model_outputs: dict[str, dict[str, str]] = {}
    for group_name, group_frame in transaction_panel.groupby("group"):
        hedonic = smf.ols(
            "log_resale_price ~ C(year_month) + flat_age + floor_area_sqm + C(flat_type) + C(town)",
            data=group_frame,
        ).fit()
        summary_path, coef_path = _save_model_outputs(f"S3Qd_{group_name.lower().replace('/', '_').replace(' ', '_')}_hedonic", hedonic)
        hedonic_model_outputs[group_name] = {"summary": summary_path, "coefficients": coef_path}
        months = sorted(group_frame["year_month"].unique().tolist())
        group_index = _month_effect_index(hedonic, months)
        group_index["series"] = group_name
        adjusted_index_rows.append(group_index)
    adjusted_index = pd.concat(adjusted_index_rows, ignore_index=True)
    adjusted_coe = coe_monthly.copy()
    adjusted_coe["index_value"] = 100.0 * adjusted_coe["avg_coe_premium"] / adjusted_coe["avg_coe_premium"].iloc[0]
    adjusted_coe["series"] = "COE index"
    adjusted_index_plot = pd.concat(
        [
            adjusted_index[["month", "series", "index_value"]],
            adjusted_coe[["month", "series", "index_value"]],
        ],
        ignore_index=True,
        sort=False,
    )

    panel = frame.loc[frame["town"].isin(FAR_TOWNS | CENTRAL_COE_CONTROL_TOWNS)].copy()
    panel = panel.dropna(subset=["transaction_month", "town", "resale_price"])
    monthly = panel.groupby(["transaction_month", "town"]).agg(median_price=("resale_price", "median"), transactions=("resale_price", "size")).reset_index().rename(columns={"transaction_month": "month"})
    linked = monthly.merge(coe_monthly, on="month", how="inner")
    linked["far_town"] = linked["town"].isin(FAR_TOWNS).astype(int)
    linked["log_price"] = np.log(linked["median_price"])
    linked["log_coe"] = np.log(linked["avg_coe_premium"])
    linked["log_coe_centered"] = linked["log_coe"] - linked["log_coe"].mean()
    linked["year_month"] = linked["month"].dt.to_period("M").astype(str)

    adjusted_panel = (
        adjusted_index.loc[:, ["month", "series", "index_value"]]
        .merge(coe_monthly, on="month", how="inner")
        .copy()
    )
    adjusted_panel["far_town"] = adjusted_panel["series"].eq("Sengkang/Punggol adjusted housing index").astype(int)
    adjusted_panel["log_adj_price"] = np.log(adjusted_panel["index_value"])
    adjusted_panel["log_coe"] = np.log(adjusted_panel["avg_coe_premium"])
    adjusted_panel["log_coe_centered"] = adjusted_panel["log_coe"] - adjusted_panel["log_coe"].mean()

    raw_model = smf.ols(
        "log_price ~ log_coe_centered * far_town + C(town) + C(year_month)",
        data=linked,
    ).fit(cov_type="HC3")
    raw_interaction_summary_path, raw_interaction_coef_path = _save_model_outputs(
        "S3Qd_raw_price_interaction",
        raw_model,
    )
    raw_coefficient_df, raw_effects = _summarize_interaction_model(
        raw_model,
        baseline_term="log_coe_centered",
        interaction_term="log_coe_centered:far_town",
        baseline_label="Central-town raw-price COE elasticity",
        interaction_label="Extra far-town raw-price sensitivity",
        total_label="Implied far-town raw-price elasticity",
        baseline_plain_english="For the central-town raw median price, a 1% COE increase is associated with this % change in price.",
        interaction_plain_english="This is the extra COE sensitivity of raw median prices in Sengkang/Punggol relative to the central towns.",
        total_plain_english="This is the total implied COE sensitivity for far-town raw median prices: baseline plus extra sensitivity.",
    )
    raw_far_town_level_at_avg_coe = float(raw_model.params["far_town"])
    raw_far_town_level_at_avg_coe_pvalue = float(raw_model.pvalues["far_town"])

    adjusted_model = smf.ols("log_adj_price ~ log_coe_centered * far_town", data=adjusted_panel).fit(cov_type="HC3")
    interaction_summary_path, interaction_coef_path = _save_model_outputs("S3Qd_main_interaction", adjusted_model)
    coefficient_df, adjusted_effects = _summarize_interaction_model(
        adjusted_model,
        baseline_term="log_coe_centered",
        interaction_term="log_coe_centered:far_town",
        baseline_label="Central adjusted index COE elasticity",
        interaction_label="Extra far-town index sensitivity",
        total_label="Implied far-town index elasticity",
        baseline_plain_english="For the central adjusted housing index, a 1% COE increase is associated with this % change in the index.",
        interaction_plain_english="This is the extra COE sensitivity of the far-town adjusted index relative to the central adjusted index.",
        total_plain_english="This is the total implied COE sensitivity for the far-town adjusted housing index: baseline plus extra sensitivity.",
    )
    far_town_level_at_avg_coe = float(adjusted_model.params["far_town"])
    far_town_level_at_avg_coe_pvalue = float(adjusted_model.pvalues["far_town"])

    spread = (
        linked.groupby(["month", "far_town"]).agg(median_price=("median_price", "mean")).reset_index().pivot(index="month", columns="far_town", values="median_price").rename(columns={0: "central_towns", 1: "far_towns"}).dropna().reset_index()
    )
    spread["far_minus_central"] = spread["far_towns"] - spread["central_towns"]
    spread = spread.merge(
        coe_monthly.assign(coe_index=lambda df: 100.0 * df["avg_coe_premium"] / df["avg_coe_premium"].iloc[0])[
            ["month", "avg_coe_premium", "coe_index"]
        ],
        on="month",
        how="left",
    )

    coe_f2_svg, coe_f2_html, coe_f2_data = save_plotly_figure(
        "S3QdF2_far_vs_central_price_spread",
        _spread_plotly_figure(spread.copy()),
        title="Far-town vs central-town resale price spread",
        data=spread.copy(),
    )

    scatter_df = spread.copy()
    coe_f3_svg, coe_f3_html, coe_f3_data = save_plotly_figure(
        "S3QdF3_coe_vs_price_spread",
        _scatter_regression_plotly_figure(scatter_df.copy()),
        title="COE premium and far-town price spread",
        data=scatter_df.copy(),
    )

    indexed_towns = linked.loc[linked["town"].isin(sorted(FAR_TOWNS | {"CENTRAL AREA"}))].copy()
    indexed_towns["price_index"] = indexed_towns.groupby("town")["median_price"].transform(lambda s: 100 * s / s.iloc[0])
    coe_index = coe_monthly.copy()
    coe_index["coe_index"] = 100 * coe_index["avg_coe_premium"] / coe_index["avg_coe_premium"].iloc[0]
    indexed_plot_data = indexed_towns[["month", "town", "price_index"]].rename(columns={"town": "series", "price_index": "index_value"})
    coe_index_plot_data = coe_index[["month", "coe_index"]].assign(series="COE index").rename(columns={"coe_index": "index_value"})
    indexed_chart_data = pd.concat([indexed_plot_data, coe_index_plot_data], ignore_index=True, sort=False)
    coe_f1_svg, coe_f1_html, coe_f1_data = save_plotly_figure(
        "S3QdF1_indexed_coe_and_resale_trends",
        _indexed_trends_plotly_figure(indexed_chart_data, title="Indexed COE and resale price trends"),
        title="Indexed COE and resale price trends",
        data=indexed_chart_data,
    )
    coe_f1b_svg, coe_f1b_html, coe_f1b_data = _plot_adjusted_index_chart(adjusted_index_plot.copy())
    adjusted_index_spread = _build_adjusted_index_spread(adjusted_index_plot.copy())
    coe_f2b_svg, coe_f2b_html, coe_f2b_data = save_plotly_figure(
        "S3QdF2b_adjusted_far_vs_central_index_spread",
        _indexed_spread_plotly_figure(adjusted_index_spread.copy()),
        title="Adjusted far-town vs central-town housing index spread",
        data=adjusted_index_spread.copy(),
    )
    coe_f4_svg, coe_f4_html, coe_f4_data = _plot_partial_regression(raw_coefficient_df.copy())
    coe_f5_svg, coe_f5_html, coe_f5_data = _plot_adjusted_partial_regression(coefficient_df.copy())

    return {
        "banner_statement": "The key issue is differential COE sensitivity, not simple co-movement. A positive far-town interaction is consistent with a housing-car substitution story, but the sign is not guaranteed by the prompt itself.",
        "hypothesis": "If buyers substitute toward cheaper far-out flats to preserve a housing-plus-car budget when COE rises, Sengkang and Punggol should show a more positive COE response than central towns. If higher COE mainly suppresses car demand, the interaction could instead be negative.",
        "method": "Two parallel town-month models are estimated for comparison: a raw median-price interaction model with town and month fixed effects, and a two-step adjusted-index model that first builds hedonic monthly housing indices and then regresses the adjusted index on centered log COE and its interaction with the far-town indicator.",
        "controls": ["raw model controls for town and month fixed effects", "first-stage hedonic controls for flat age, floor area, flat type, and town", "second-stage far-town indicator interaction on adjusted indices"],
        "source": "Singapore data.gov.sg COE dataset",
        "far_towns": sorted(FAR_TOWNS),
        "control_towns": sorted(CENTRAL_COE_CONTROL_TOWNS),
        "rows": int(len(adjusted_panel)),
        "raw_price_rows": int(len(linked)),
        "raw_price_relative_far_town_coe_effect": raw_effects["interaction_effect"],
        "raw_price_relative_far_town_coe_effect_pvalue": raw_effects["interaction_pvalue"],
        "raw_price_central_town_coe_elasticity": raw_effects["base_effect"],
        "raw_price_central_town_coe_elasticity_pvalue": raw_effects["base_pvalue"],
        "raw_price_far_town_total_coe_elasticity": raw_effects["total_far_effect"],
        "raw_price_far_town_level_difference_at_average_coe": raw_far_town_level_at_avg_coe,
        "raw_price_far_town_level_difference_at_average_coe_pvalue": raw_far_town_level_at_avg_coe_pvalue,
        "relative_far_town_coe_effect": adjusted_effects["interaction_effect"],
        "relative_far_town_coe_effect_pvalue": adjusted_effects["interaction_pvalue"],
        "central_town_coe_elasticity": adjusted_effects["base_effect"],
        "central_town_coe_elasticity_pvalue": adjusted_effects["base_pvalue"],
        "far_town_total_coe_elasticity": adjusted_effects["total_far_effect"],
        "far_town_level_difference_at_average_coe": far_town_level_at_avg_coe,
        "far_town_level_difference_at_average_coe_pvalue": far_town_level_at_avg_coe_pvalue,
        "average_coe_premium": float(linked["avg_coe_premium"].mean()),
        "average_log_coe": float(adjusted_panel["log_coe"].mean()),
        "raw_price_coefficient_explanations": [
            {
                "term": "log_coe_centered",
                "plain_label": "Central-town raw-price COE elasticity",
                "value": raw_effects["base_effect"],
                "plain_english": "For the central-town raw median price, a 1% increase in COE is associated with about this % change in price.",
            },
            {
                "term": "far_town",
                "plain_label": "Far-town raw-price gap at average COE",
                "value": raw_far_town_level_at_avg_coe,
                "plain_english": "Because COE is centered, this compares the average raw price level of the far towns against the central towns when COE is at its average level.",
            },
            {
                "term": "log_coe_centered:far_town",
                "plain_label": "Extra far-town raw-price COE sensitivity",
                "value": raw_effects["interaction_effect"],
                "plain_english": "This measures the extra COE sensitivity of Sengkang/Punggol raw median prices relative to central towns. A positive value supports a substitution story; a negative value would suggest far-town demand weakens when car ownership becomes more expensive.",
            },
        ],
        "coefficient_explanations": [
            {
                "term": "log_coe_centered",
                "plain_label": "Central adjusted index COE elasticity",
                "value": adjusted_effects["base_effect"],
                "plain_english": "For the central adjusted housing index, a 1% increase in COE is associated with about this % change in the index.",
            },
            {
                "term": "far_town",
                "plain_label": "Far-town adjusted-index gap at average COE",
                "value": far_town_level_at_avg_coe,
                "plain_english": "Because COE is centered, this compares the average level of the far-town adjusted index against the central adjusted index when COE is at its average level.",
            },
            {
                "term": "log_coe_centered:far_town",
                "plain_label": "Extra far-town index COE sensitivity",
                "value": adjusted_effects["interaction_effect"],
                "plain_english": "This is the key term for the online claim. It measures the extra COE sensitivity of the far-town adjusted housing index relative to the central adjusted index. A positive sign supports a substitution channel; a negative sign would support a car-affordability squeeze instead.",
            },
        ],
        "interpretation": "Both the raw-price and adjusted-index models point to a positive extra far-town COE sensitivity. That is directionally consistent with a housing-car substitution story, where buyers lean toward cheaper far-out flats when COE rises. The adjusted-index version is the preferred estimate because it first removes shifts in flat age, size, flat type, and town mix before testing the relative COE sensitivity." if adjusted_effects["interaction_effect"] > 0 and adjusted_effects["interaction_pvalue"] < 0.10 else "The raw-price and adjusted-index comparison does not yield a statistically clear differential COE sensitivity for the far towns after accounting for the model structure.",
        "chart_commentary": [
            "Open with the indexed chart only as intuition: far-town prices and COE can appear to move together over time, but co-movement alone does not pin down the mechanism.",
            "Use the adjusted-index chart to show the same story after controlling for flat type, age, floor area, and town composition.",
            "Use the adjusted-index spread chart to show the relative performance gap after removing composition changes, which is closer to the actual question than raw co-movement.",
            "Then explain that the real test is differential sensitivity, and that the sign is theoretically ambiguous unless we explicitly assume a housing-car substitution channel.",
            "Use the far-town-versus-central spread chart to show the comparison that actually matters for the claim.",
            "Use the raw-price coefficient chart first to show the benchmark town-month result using median prices and explain that a positive interaction supports substitution while a negative interaction would support a pure affordability squeeze.",
            "Then use the adjusted-index coefficient chart to show the preferred estimate after composition adjustment: baseline central-index COE sensitivity, extra far-town sensitivity, and the implied total sensitivity for the far-town adjusted index.",
        ],
        "limitations": [
            "This is a town-level association, not direct evidence that individual households used housing savings to buy cars.",
            "Sengkang and Punggol also changed in many other ways over the sample period, including amenities, transport access, and housing mix.",
            "The second-stage regression is still a reduced-form association on adjusted indices, so other macro forces can co-move with both COE and housing demand.",
        ],
        "model_outputs": {
            "raw_price_interaction_summary": raw_interaction_summary_path,
            "raw_price_interaction_coefficients": raw_interaction_coef_path,
            "main_interaction_summary": interaction_summary_path,
            "main_interaction_coefficients": interaction_coef_path,
            "hedonic_models": hedonic_model_outputs,
        },
        "charts": [coe_f1_svg, coe_f1b_svg, coe_f2_svg, coe_f2b_svg, coe_f3_svg, coe_f4_svg, coe_f5_svg],
        "chart_html": [coe_f1_html, coe_f1b_html, coe_f2_html, coe_f2b_html, coe_f3_html, coe_f4_html, coe_f5_html],
        "chart_data": [path for path in [coe_f1_data, coe_f1b_data, coe_f2_data, coe_f2b_data, coe_f3_data, coe_f4_data, coe_f5_data] if path],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 3 Question D analysis.")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--figures-only", action="store_true")
    parser.add_argument("--skip-html", action="store_true")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    configure_logging(args.log_level)
    set_write_html(not args.skip_html)
    if args.figures_only:
        rebuild_question_d_figures()
        return
    summary = analyze_coe_link(load_frame(), refresh=args.refresh)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
