from __future__ import annotations

import argparse
import json
import math

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
import statsmodels.formula.api as smf
from plotly.subplots import make_subplots

from src.analysis.section3.S3_helpers import (
    BLUE,
    GRAY,
    GREEN,
    ORANGE,
    annotate_bar_values,
    annotate_point_values,
    annotate_series_endpoints,
    annotate_scatter_labels,
    age_band,
    display_town_name,
    load_figure_data,
    question_a_stem,
    question_a_target_town_from_saved_outputs,
    configure_logging,
    load_frame,
    save_svg_and_html,
    save_plotly_figure,
    selected_target_town_regression_coefficients,
    set_write_html,
    style_bar_patches,
    style_scatter_collection,
    town_coefficient_table,
    town_reference_for_formula,
    year_month_label,
)


def _pick_candidate_towns(
        sample: pd.DataFrame,
        *,
        target_town: str,
        top_flat_types: list[str],
        num_towns: int = 5,
) -> list[str]:
    candidate = sample.loc[sample["flat_type"].isin(top_flat_types)].copy()
    town_summary = (
        candidate.groupby("town")
        .agg(median_price_psm=("price_per_sqm", "median"), transactions=("price_per_sqm", "size"))
        .reset_index()
        .loc[lambda table: table["transactions"].ge(300)]
        .sort_values(["median_price_psm", "transactions"], ascending=[True, False])
    )
    towns = town_summary["town"].head(num_towns).tolist()
    if target_town not in towns:
        towns.append(target_town)
    return towns


def _target_flat_type_effects(
        model: object,
        *,
        reference_town: str,
        target_town: str,
        reference_flat_type: str,
        flat_types: list[str],
) -> pd.DataFrame:
    main_name = f"C(town, Treatment(reference='{reference_town}'))[T.{target_town}]"
    params = model.params
    cov = model.cov_params()
    main_coef = float(params.get(main_name, 0.0 if reference_town == target_town else np.nan))
    if np.isnan(main_coef):
        return pd.DataFrame(
            columns=["flat_type", "coefficient", "ci_low", "ci_high", "pvalue", "effect_pct", "effect_pct_ci_low", "effect_pct_ci_high"]
        )
    rows: list[dict[str, float | str]] = []
    for flat_type in flat_types:
        if flat_type == reference_flat_type:
            coef = main_coef
            variance = float(cov.loc[main_name, main_name]) if main_name in cov.index else 0.0
        else:
            interaction_name = (
                f"C(town, Treatment(reference='{reference_town}'))[T.{target_town}]:"
                f"C(flat_type, Treatment(reference='{reference_flat_type}'))[T.{flat_type}]"
            )
            interaction_coef = float(params.get(interaction_name, 0.0))
            coef = main_coef + interaction_coef
            variance = float(cov.loc[main_name, main_name])
            if interaction_name in cov.index and interaction_name in cov.columns:
                variance += float(cov.loc[interaction_name, interaction_name])
                variance += 2.0 * float(cov.loc[main_name, interaction_name])
        se = float(np.sqrt(max(variance, 0.0)))
        if se > 0:
            z_score = abs(coef / se)
            pvalue = float(math.erfc(z_score / math.sqrt(2.0)))
        else:
            pvalue = 0.0 if coef != 0 else np.nan
        ci_low = coef - 1.96 * se
        ci_high = coef + 1.96 * se
        rows.append(
            {
                "flat_type": flat_type,
                "coefficient": coef,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "pvalue": pvalue,
                "effect_pct": float((np.exp(coef) - 1.0) * 100.0),
                "effect_pct_ci_low": float((np.exp(ci_low) - 1.0) * 100.0),
                "effect_pct_ci_high": float((np.exp(ci_high) - 1.0) * 100.0),
            }
        )
    return pd.DataFrame(rows)


def _significance_stars(pvalue: float) -> str:
    if pd.isna(pvalue):
        return ""
    if pvalue < 0.01:
        return "***"
    if pvalue < 0.05:
        return "**"
    if pvalue < 0.10:
        return "*"
    return ""


def _plotly_rgba(color: str, alpha: float) -> str:
    rgba = to_rgba(color, alpha)
    return (
        f"rgba("
            f"{int(round(rgba[0] * 255))}, "
            f"{int(round(rgba[1] * 255))}, "
            f"{int(round(rgba[2] * 255))}, "
            f"{rgba[3]:.3f}"
        f")"
    )


def _build_s3qa_f1_plotly(plot_df: pd.DataFrame, *, target_town: str) -> go.Figure:
    town_order = plot_df.groupby("town")["price_per_sqm"].median().sort_values().index.tolist()
    flat_types = plot_df["flat_type"].dropna().drop_duplicates().tolist()
    fig = make_subplots(rows=1, cols=len(flat_types), subplot_titles=flat_types, shared_yaxes=True)

    for idx, flat_type in enumerate(flat_types, start=1):
        flat_slice = plot_df.loc[plot_df["flat_type"].eq(flat_type)].copy()
        for town in town_order:
            town_slice = flat_slice.loc[flat_slice["town"].eq(town), "price_per_sqm"].dropna()
            if town_slice.empty:
                continue
            color = ORANGE if town == target_town else BLUE
            fig.add_trace(
                go.Box(
                    y=town_slice,
                    name=display_town_name(town),
                    marker_color=color,
                    line={"color": color, "width": 1.2},
                    fillcolor=_plotly_rgba(color, 0.22),
                    boxpoints=False,
                    quartilemethod="inclusive",
                    showlegend=False,
                ),
                row=1,
                col=idx,
            )
            median_value = float(town_slice.median())
            fig.add_annotation(
                x=display_town_name(town),
                y=median_value,
                xref=f"x{idx}" if idx > 1 else "x",
                yref=f"y{idx}" if idx > 1 else "y",
                text=f"{median_value:.0f}",
                showarrow=False,
                yshift=18,
                font={"size": 11, "color": "#000000"},
            )
    return fig


def _build_s3qa_effect_figure(
        effect_df: pd.DataFrame,
        *,
        target_town: str,
        marker_size: float = 9,
        marker_line_width: float = 1.4,
        error_thickness: float = 1.8,
        error_width: float = 4,
        annotation_font_size: float = 11,
        annotation_xshift: float = 24,
) -> go.Figure:

    display_town = display_town_name(target_town)
    ordered = effect_df.copy()
    y_col = "label" if "label" in ordered.columns else "flat_type"
    ordered = ordered.sort_values("effect_pct").reset_index(drop=True)

    fig = go.Figure()
    for row in ordered.itertuples():
        label = getattr(row, y_col)
        color = ORANGE if label == display_town else (GREEN if label == "Flat age" else BLUE)
        fig.add_trace(
            go.Scatter(
                x=[float(row.effect_pct)],
                y=[label],
                mode="markers",
                marker={
                    "size": marker_size,
                    "color": _plotly_rgba(color, 0.42),
                    "line": {"color": color, "width": marker_line_width},
                },
                error_x={
                    "type": "data",
                    "symmetric": False,
                    "array": [float(row.effect_pct_ci_high - row.effect_pct)],
                    "arrayminus": [float(row.effect_pct - row.effect_pct_ci_low)],
                    "color": color,
                    "thickness": error_thickness,
                    "width": error_width,
                },
                name=str(label),
                showlegend=False,
                hovertemplate=f"{y_col.replace('_', ' ').title()}: %{{y}}<br>Effect: %{{x:.1f}}%<extra></extra>",
            )
        )
        label_text = getattr(row, "label_text", f"{float(row.effect_pct):.1f}%")
        fig.add_annotation(
            x=float(row.effect_pct),
            y=label,
            text=label_text,
            showarrow=False,
            xshift=annotation_xshift,
            font={"size": annotation_font_size, "color": "#000000"},
        )
    fig.add_vline(x=0, line_dash="dash", line_color=GRAY, line_width=1)
    # fig.update_layout(
    #     height=max(640, 26 * len(ordered) + 180),
    # )
    return fig


def _build_s3qa_f3_plotly(area_story: pd.DataFrame, *, target_town: str) -> go.Figure:

    fig = go.Figure()

    display_town = display_town_name(target_town)
    other_towns = area_story.loc[~area_story["is_target"]].copy()
    target_point = area_story.loc[area_story["is_target"]].copy()

    if not other_towns.empty:
        fig.add_trace(
            go.Scatter(
                x=other_towns["median_floor_area"],
                y=other_towns["median_resale_price"],
                mode="markers+text",
                name="Other towns",
                text=other_towns["town"].map(display_town_name),
                textposition="top center",
                marker={
                    "size": np.clip(other_towns["median_price_psm"] / 30, 10, 24),
                    "color": _plotly_rgba(BLUE, 0.38),
                    "line": {"color": BLUE, "width": 1.0},
                },
                hovertemplate="Town: %{text}<br>Median floor area: %{x:.1f} sqm<br>Median resale price: SGD %{y:,.0f}<extra></extra>",
            )
        )

    if not target_point.empty:
        fig.add_trace(
            go.Scatter(
                x=target_point["median_floor_area"],
                y=target_point["median_resale_price"],
                mode="markers+text",
                name=display_town,
                text=target_point["town"].map(display_town_name),
                textposition="top center",
                marker={
                    "size": np.clip(target_point["median_price_psm"] / 30, 12, 28),
                    "color": _plotly_rgba(ORANGE, 0.48),
                    "line": {"color": ORANGE, "width": 1.2},
                },
                hovertemplate="Town: %{text}<br>Median floor area: %{x:.1f} sqm<br>Median resale price: SGD %{y:,.0f}<extra></extra>",
            )
        )
    # fig.update_layout(height=720)
    return fig


def _prepare_f1_plot_df(plot_df: pd.DataFrame, *, target_town: str) -> tuple[pd.DataFrame, str]:
    prepared = plot_df.copy()
    resolved_target = (
        str(prepared["target_town"].iloc[0])
        if "target_town" in prepared.columns and not prepared.empty
        else target_town
    )
    return prepared, resolved_target


def _prepare_f2_effect_df(effect_df: pd.DataFrame, *, target_town: str) -> tuple[pd.DataFrame, str]:
    prepared = effect_df.copy()
    resolved_target = (
        str(prepared["target_town"].iloc[0])
        if "target_town" in prepared.columns and not prepared.empty
        else target_town
    )
    display_town = display_town_name(resolved_target)
    if "label" not in prepared.columns:
        if "town" in prepared.columns:
            prepared["label"] = prepared["town"].astype(str).str.replace("_", " ").str.title()
        else:
            prepared["label"] = display_town
    if "group" not in prepared.columns:
        prepared["group"] = np.where(prepared["label"].eq(display_town), "Town", "Control")
    if "ci_low" not in prepared.columns and "coefficient" in prepared.columns:
        prepared["ci_low"] = prepared["coefficient"]
    if "ci_high" not in prepared.columns and "coefficient" in prepared.columns:
        prepared["ci_high"] = prepared["coefficient"]
    if "effect_pct" not in prepared.columns and "coefficient" in prepared.columns:
        prepared["effect_pct"] = (np.exp(prepared["coefficient"]) - 1.0) * 100.0
        prepared["effect_pct_ci_low"] = (np.exp(prepared["ci_low"]) - 1.0) * 100.0
        prepared["effect_pct_ci_high"] = (np.exp(prepared["ci_high"]) - 1.0) * 100.0
    if "label_text" not in prepared.columns:
        if "pvalue" in prepared.columns:
            prepared["label_text"] = prepared.apply(
                lambda row: f"{row['effect_pct']:.1f}%{_significance_stars(float(row['pvalue']))}",
                axis=1,
            )
        else:
            prepared["label_text"] = prepared["effect_pct"].map(lambda value: f"{value:.1f}%")
    return prepared, resolved_target


def _prepare_f3_area_story(area_story: pd.DataFrame, *, target_town: str) -> tuple[pd.DataFrame, str]:
    prepared = area_story.copy()
    resolved_target = (
        str(prepared["target_town"].iloc[0])
        if "target_town" in prepared.columns and not prepared.empty
        else target_town
    )
    prepared["is_target"] = prepared["town"].eq(resolved_target)
    return prepared, resolved_target


def _prepare_f4_interaction_df(interaction_df: pd.DataFrame, *, target_town: str) -> tuple[pd.DataFrame, str]:
    prepared = interaction_df.copy()
    resolved_target = (
        str(prepared["target_town"].iloc[0])
        if "target_town" in prepared.columns and not prepared.empty
        else target_town
    )
    if "pvalue" in prepared.columns:
        prepared["label_text"] = prepared.apply(
            lambda row: f"{row['effect_pct']:.1f}%{_significance_stars(float(row['pvalue']))}",
            axis=1,
        )
    elif "label_text" not in prepared.columns:
        prepared["label_text"] = prepared["effect_pct"].map(lambda value: f"{value:.1f}%")
    return prepared, resolved_target


def _prepare_f5_town_df(town_df: pd.DataFrame, *, target_town: str) -> tuple[pd.DataFrame, str]:
    prepared = town_df.copy()
    resolved_target = (
        str(prepared["target_town"].iloc[0])
        if "target_town" in prepared.columns and not prepared.empty
        else target_town
    )
    prepared["town_label"] = prepared["town"].map(display_town_name)
    if "significant" not in prepared.columns:
        prepared["significant"] = prepared["pvalue"].lt(0.10)
    if "label_text" not in prepared.columns:
        prepared["label_text"] = prepared.apply(
            lambda row: f"{row['effect_pct']:.1f}%{_significance_stars(float(row['pvalue']))}",
            axis=1,
        )
    prepared = prepared.sort_values("effect_pct").reset_index(drop=True)
    return prepared, resolved_target


def _render_s3qa_f1(plot_df: pd.DataFrame, *, target_town: str) -> tuple[str, str, str | None]:
    prepared, resolved_target = _prepare_f1_plot_df(plot_df, target_town=target_town)
    fig = _build_s3qa_f1_plotly(prepared, target_town=resolved_target)
    return save_plotly_figure(
        question_a_stem(1, "candidate_towns_boxplot", target_town=resolved_target),
        fig,
        title=None,
        data=prepared,
    )


def _render_s3qa_f2(effect_df: pd.DataFrame, *, target_town: str) -> tuple[str, str, str | None]:
    prepared, resolved_target = _prepare_f2_effect_df(effect_df, target_town=target_town)
    fig = _build_s3qa_effect_figure(prepared, target_town=resolved_target)
    return save_plotly_figure(
        question_a_stem(2, "simple_regression_coefficients", target_town=resolved_target),
        fig,
        title=None,
        data=prepared.assign(target_town=resolved_target),
    )


def _render_s3qa_f3(area_story: pd.DataFrame, *, target_town: str) -> tuple[str, str, str | None]:
    prepared, resolved_target = _prepare_f3_area_story(area_story, target_town=target_town)
    fig = _build_s3qa_f3_plotly(prepared, target_town=resolved_target)
    return save_plotly_figure(
        question_a_stem(3, "price_vs_space", target_town=resolved_target),
        fig,
        title=None,
        data=prepared.drop(columns=["is_target"]),
    )


def _render_s3qa_f4(interaction_df: pd.DataFrame, *, target_town: str) -> tuple[str, str, str | None]:
    prepared, resolved_target = _prepare_f4_interaction_df(interaction_df, target_town=target_town)
    fig = _build_s3qa_effect_figure(
        prepared.rename(columns={"flat_type": "label"}),
        target_town=resolved_target,
        # marker_size=16,
        # marker_line_width=2.2,
        error_thickness=2.6,
        error_width=8,
        # annotation_font_size=16,
        annotation_xshift=34,
    )
    return save_plotly_figure(
        question_a_stem(4, "interaction_effects_by_flat_type", target_town=resolved_target),
        fig,
        title=None,
        data=prepared.assign(target_town=resolved_target),
    )


def _render_s3qa_f5(town_df: pd.DataFrame, *, target_town: str) -> tuple[str, str, str | None]:
    prepared, resolved_target = _prepare_f5_town_df(town_df, target_town=target_town)
    fig = _build_s3qa_effect_figure(
        prepared.rename(columns={"town_label": "label"}),
        target_town=resolved_target,
    )
    return save_plotly_figure(
        question_a_stem(5, "all_town_dummy_coefficients", target_town=resolved_target),
        fig,
        title=None,
        data=prepared,
    )


def rebuild_question_a_figures() -> None:
    _rebuild_s3qa_f1()
    _rebuild_s3qa_f2()
    _rebuild_s3qa_f3()
    _rebuild_s3qa_f4()
    _rebuild_s3qa_f5()


def _rebuild_s3qa_f1() -> None:
    target_town = question_a_target_town_from_saved_outputs()
    plot_df = load_figure_data(question_a_stem(1, "candidate_towns_boxplot", target_town=target_town)).copy()
    _render_s3qa_f1(plot_df, target_town=target_town)


def _rebuild_s3qa_f2() -> None:
    target_town = question_a_target_town_from_saved_outputs()
    effect_df = load_figure_data(question_a_stem(2, "simple_regression_coefficients", target_town=target_town)).copy()
    _render_s3qa_f2(effect_df, target_town=target_town)


def _rebuild_s3qa_f3() -> None:
    target_town = question_a_target_town_from_saved_outputs()
    area_story = load_figure_data(question_a_stem(3, "price_vs_space", target_town=target_town))
    _render_s3qa_f3(area_story, target_town=target_town)


def _rebuild_s3qa_f4() -> None:
    target_town = question_a_target_town_from_saved_outputs()
    interaction_df = load_figure_data(question_a_stem(4, "interaction_effects_by_flat_type", target_town=target_town)).copy()
    _render_s3qa_f4(interaction_df, target_town=target_town)


def _rebuild_s3qa_f5() -> None:
    target_town = question_a_target_town_from_saved_outputs()
    town_df = load_figure_data(question_a_stem(5, "all_town_dummy_coefficients", target_town=target_town)).copy()
    _render_s3qa_f5(town_df, target_town=target_town)


def analyze_town_value(frame: pd.DataFrame, *, target_town: str = "YISHUN") -> dict[str, object]:
    display_town = display_town_name(target_town)

    recent = frame.loc[frame["transaction_year"] >= 2018].copy()
    recent = recent.dropna(subset=["town", "flat_type", "flat_age", "price_per_sqm", "resale_price", "floor_area_sqm"])
    recent["age_band"] = age_band(recent["flat_age"])
    top_flat_types = recent["flat_type"].value_counts().head(3).index.tolist()
    reference_flat_type = top_flat_types[0]
    candidate_towns = _pick_candidate_towns(recent, target_town=target_town, top_flat_types=top_flat_types)

    banded = (
        recent.groupby(["flat_type", "age_band", "town"], dropna=False)
        .agg(
            median_price_psm=("price_per_sqm", "median"),
            median_resale_price=("resale_price", "median"),
            median_floor_area_sqm=("floor_area_sqm", "median"),
            transactions=("price_per_sqm", "size"),
        )
        .reset_index()
    )
    target_cells = banded.loc[banded["town"].eq(target_town) & banded["transactions"].ge(1)].copy()
    peer_cells = banded.loc[
        banded.set_index(["flat_type", "age_band"]).index.isin(target_cells.set_index(["flat_type", "age_band"]).index)
    ].copy()

    benchmark_rows: list[dict[str, object]] = []
    for (flat_type, band), grp in peer_cells.groupby(["flat_type", "age_band"], dropna=False):
        ordered = grp.sort_values("median_price_psm").reset_index(drop=True)
        target_rank = int(ordered.index[ordered["town"].eq(target_town)][0]) + 1
        benchmark_rows.append(
            {
                "flat_type": flat_type,
                "age_band": band,
                "peer_median_price_psm": float(grp["median_price_psm"].median()),
                "peer_min_price_psm": float(grp["median_price_psm"].min()),
                "peer_rank": target_rank,
                "peer_town_count": int(grp["town"].nunique()),
            }
        )
    peer_benchmark = pd.DataFrame(benchmark_rows)
    if peer_benchmark.empty:
        controlled_cells = pd.DataFrame(
            columns=[
                "flat_type",
                "age_band",
                "median_price_psm",
                "peer_median_price_psm",
                "gap_vs_peer_median",
                "peer_rank",
                "transactions"
            ]
        )
        weighted_gap = np.nan
        share_cheapest = np.nan
    else:
        controlled_cells = target_cells.merge(
            peer_benchmark,
            on=["flat_type", "age_band"],
            how="inner"
        )
        controlled_cells["gap_vs_peer_median"] = controlled_cells["median_price_psm"] - controlled_cells["peer_median_price_psm"]
        controlled_cells["weighted_gap"] = controlled_cells["gap_vs_peer_median"] * controlled_cells["transactions"]
        weighted_gap = float(controlled_cells["weighted_gap"].sum() / controlled_cells["transactions"].sum())
        share_cheapest = float((controlled_cells["peer_rank"] == 1).mean()) if not controlled_cells.empty else np.nan

    regression_sample = recent.copy()
    regression_sample["year_month"] = year_month_label(regression_sample["transaction_month"])
    reference_town = town_reference_for_formula(regression_sample)
    regression = smf.ols(
        f"np.log(price_per_sqm) ~ "
            f"C(town, Treatment(reference='{reference_town}')) + "
            f"C(flat_type, Treatment(reference='{reference_flat_type}')) + "
            f"flat_age + "
            f"C(year_month)",
        data=regression_sample,
    ).fit(cov_type="HC3")
    coefficient_name = f"C(town, Treatment(reference='{reference_town}'))[T.{target_town}]"
    target_coef = float(regression.params.get(coefficient_name, 0.0 if reference_town == target_town else np.nan))
    target_pvalue = float(regression.pvalues.get(coefficient_name, np.nan if reference_town != target_town else 0.0))

    if reference_town == target_town:
        target_ci_low = 0.0
        target_ci_high = 0.0
    else:
        target_ci = regression.conf_int().loc[coefficient_name]
        target_ci_low = float(target_ci.iloc[0])
        target_ci_high = float(target_ci.iloc[1])
    target_effect_pct = float((np.exp(target_coef) - 1.0) * 100.0)
    target_effect_pct_ci_low = float((np.exp(target_ci_low) - 1.0) * 100.0)
    target_effect_pct_ci_high = float((np.exp(target_ci_high) - 1.0) * 100.0)

    town_effects = town_coefficient_table(regression)
    coeffs_df = selected_target_town_regression_coefficients(
        regression,
        reference_town=reference_town,
        target_town=target_town,
    )
    interaction_model = smf.ols(
        f"np.log(price_per_sqm) ~ "
        f"C(town, Treatment(reference='{reference_town}')) * C(flat_type, Treatment(reference='{reference_flat_type}')) + "
        f"flat_age + "
        f"C(year_month)",
        data=regression_sample.loc[regression_sample["flat_type"].isin(top_flat_types)].copy(),
    ).fit(cov_type="HC3")
    interaction_df = _target_flat_type_effects(
        interaction_model,
        reference_town=reference_town,
        target_town=target_town,
        reference_flat_type=reference_flat_type,
        flat_types=top_flat_types,
    )
    if reference_town == target_town:
        town_effects = pd.concat(
            [
                pd.DataFrame(
                    [
                        {
                            "town": target_town,
                            "coefficient": 0.0,
                            "ci_low": 0.0,
                            "ci_high": 0.0,
                            "effect_pct": 0.0,
                            "effect_pct_ci_low": 0.0,
                            "effect_pct_ci_high": 0.0,
                            "pvalue": 0.0
                        }
                    ]
                ),
                town_effects,
            ],
            ignore_index=True,
        )
    if reference_town not in set(town_effects["town"]):
        town_effects = pd.concat(
            [
                town_effects,
                pd.DataFrame(
                    [
                        {
                            "town": reference_town,
                            "coefficient": 0.0,
                            "ci_low": 0.0,
                            "ci_high": 0.0,
                            "effect_pct": 0.0,
                            "effect_pct_ci_low": 0.0,
                            "effect_pct_ci_high": 0.0,
                            "pvalue": 0.0}
                    ]
                ),
            ],
            ignore_index=True,
        )
    adjusted_rank = (
        town_effects.sort_values("coefficient")
        .reset_index(drop=True)
        .assign(rank=lambda table: table.index + 1)
        .loc[lambda table: table["town"].eq(target_town), "rank"]
    )
    adjusted_rank_value = int(adjusted_rank.iloc[0]) if not adjusted_rank.empty else None

    descriptive_plot = recent.loc[
        recent["flat_type"].isin(top_flat_types) & recent["town"].isin(candidate_towns),
        ["town", "flat_type", "price_per_sqm"]
    ].copy()
    descriptive_plot["target_town"] = target_town
    qa_f1_png, qa_f1_html, qa_f1_data = _render_s3qa_f1(descriptive_plot, target_town=target_town)

    effect_df = coeffs_df.copy()
    effect_df["target_town"] = target_town
    qa_f2_png, qa_f2_html, qa_f2_data = _render_s3qa_f2(effect_df, target_town=target_town)

    interaction_df["target_town"] = target_town
    qa_f4_png, qa_f4_html, qa_f4_data = _render_s3qa_f4(interaction_df, target_town=target_town)

    town_effect_plot = town_effects.copy()
    town_effect_plot["target_town"] = target_town
    qa_f5_png, qa_f5_html, qa_f5_data = _render_s3qa_f5(town_effect_plot, target_town=target_town)

    area_story = (
        recent.groupby("town")
        .agg(
            median_resale_price=("resale_price", "median"),
            median_price_psm=("price_per_sqm", "median"),
            median_floor_area=("floor_area_sqm", "median"),
            transactions=("resale_price", "size"),
        )
        .reset_index()
        .query("transactions >= 200")
    )
    qa_f3_png, qa_f3_html, qa_f3_data = _render_s3qa_f3(
        area_story[["town", "median_resale_price", "median_price_psm", "median_floor_area", "transactions"]].assign(target_town=target_town),
        target_town=target_town,
    )

    return {
        "target_town": target_town,
        "banner_statement": f"{display_town} is better framed as a value town than as the outright cheapest town in Singapore.",
        "hypothesis": f"After controlling for flat type and age, {display_town} flats are among the cheaper resale options.",
        "method": "Controlled price-per-sqm comparison within flat-type and age bands, plus log(price-per-sqm) regression with month fixed effects.",
        "controls": ["flat_type", "flat_age", "year_month", "price_per_sqm normalization"],
        "top_flat_types": top_flat_types,
        "candidate_towns": candidate_towns,
        "reference_flat_type": reference_flat_type,
        "controlled_sample_cells": int(len(controlled_cells)),
        "weighted_gap_vs_peer_median_psm": weighted_gap,
        "share_of_cells_where_target_is_cheapest": share_cheapest,
        "regression_reference_town": reference_town,
        "target_coef_log_points": target_coef,
        "target_coef_pvalue": target_pvalue,
        "target_coef_ci_low": target_ci_low,
        "target_coef_ci_high": target_ci_high,
        "target_effect_pct": target_effect_pct,
        "target_effect_pct_ci_low": target_effect_pct_ci_low,
        "target_effect_pct_ci_high": target_effect_pct_ci_high,
        "adjusted_rank_by_town_effect": adjusted_rank_value,
        "cell_comparison_preview": controlled_cells[["flat_type", "age_band", "median_price_psm", "peer_median_price_psm", "gap_vs_peer_median", "peer_rank", "transactions"]].sort_values(["flat_type", "age_band"]).head(12).to_dict("records"),
        "interpretation": (
            f"{display_town} remains cheaper than the peer median after matching on flat type and age."
            if weighted_gap < 0
            else f"{display_town} does not remain cheaper than the peer median once flat type and age are controlled for."
        ),
        "chart_commentary": [
            "Start with the box plots to show which towns look cheapest when we focus on the three most common flat types.",
            "Then use the simple coefficient chart to show the adjusted regression result after controlling for flat type, age, and year.",
            "Add the all-town coefficient chart to compare the adjusted town ranking directly across the full market.",
            f"Use the price-versus-space scatter to explain why buyers can experience {display_town} as good value even when total prices are not the absolute lowest.",
            "End with the interaction chart to show whether the target-town discount is consistent across flat types or concentrated in a few segments.",
        ],
        "limitations": [
            "Town fixed effects still absorb other location amenities beyond the controlled variables.",
            "Band-level comparisons simplify age into buckets and do not fully equalize every unit characteristic.",
        ],
        "charts": [qa_f1_png, qa_f2_png, qa_f3_png, qa_f4_png, qa_f5_png],
        "chart_html": [qa_f1_html, qa_f2_html, qa_f3_html, qa_f4_html, qa_f5_html],
        "chart_data": [path for path in [qa_f1_data, qa_f2_data, qa_f3_data, qa_f4_data, qa_f5_data] if path],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 3 Question A analysis.")
    parser.add_argument("--target-town", default="YISHUN")
    parser.add_argument("--figures-only", action="store_true")
    parser.add_argument("--skip-html", action="store_true")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    configure_logging(args.log_level)
    set_write_html(not args.skip_html)
    if args.figures_only:
        rebuild_question_a_figures()
        return
    summary = analyze_town_value(load_frame(), target_town=str(args.target_town).upper())
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
