from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import numpy as np
import pandas as pd
import seaborn as sns
import plotly.graph_objects as go
from plotly.tools import mpl_to_plotly

from src.analysis.common.plotly_standard import apply_standard_theme, configure_plotly_png_browser, load_plotly_theme
from src.common.config import (
    DATA_PROCESSED,
    DTL2_TOWNS,
    SECTION3_OUTPUT_CHARTS,
    SECTION3_OUTPUT_RESULTS,
)

CHARTS = SECTION3_OUTPUT_CHARTS
REPORTS = SECTION3_OUTPUT_RESULTS

THEME = load_plotly_theme()

sns.set_theme(
    style="white",
    rc={
        "axes.facecolor": "none",
        "figure.facecolor": "none",
        "savefig.facecolor": "none",
        "axes.edgecolor": "#000000",
        "axes.labelcolor": "#000000",
        "xtick.color": "#000000",
        "ytick.color": "#000000",
        "text.color": "#000000",
        "font.family": ["Arial", "DejaVu Sans", "sans-serif"],
    },
)

SECTION3_FIGURE_REPORTS = SECTION3_OUTPUT_RESULTS
BLUE = THEME.blue
BLUE_LIGHT = "#A9B7C4"
ORANGE = THEME.orange
ORANGE_LIGHT = "#D39A7C"
GREEN = THEME.green
GREEN_LIGHT = "#A8B5A6"
ACCENT = THEME.accent
GRAY = THEME.text_muted

FAR_TOWNS = {"SENGKANG", "PUNGGOL"}
CENTRAL_COE_CONTROL_TOWNS = {
    "BISHAN",
    "BUKIT MERAH",
    "CENTRAL AREA",
    "KALLANG/WHAMPOA",
    "QUEENSTOWN",
    "TOA PAYOH",
}
DTL2_CONTROL_EXCLUSIONS = {"LIM CHU KANG", *FAR_TOWNS}

WRITE_HTML = True
LOGGER = logging.getLogger(__name__)


def set_write_html(enabled: bool) -> None:
    global WRITE_HTML
    WRITE_HTML = enabled


def should_write_html() -> bool:
    return WRITE_HTML


def format_chart_list(paths: list[str]) -> str:
    return ", ".join(f"`{Path(path).name}`" for path in paths)


def write_chart_html(image_path: Path, title: str) -> Path:
    image_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = image_path.with_suffix(".html")
    if not WRITE_HTML:
        return html_path
    html_path.write_text(
        "\n".join(
            [
                "<!DOCTYPE html>",
                "<html lang='en'>",
                "<head>",
                "  <meta charset='utf-8' />",
                f"  <title>{title}</title>",
                "  <style>",
                "    body { margin: 0; padding: 24px; background: transparent; font-family: Arial, sans-serif; }",
                "    .chart { max-width: 1200px; margin: 0 auto; }",
                "    img { width: 100%; height: auto; display: block; }",
                "  </style>",
                "</head>",
                "<body>",
                "  <div class='chart'>",
                f"    <img src='{image_path.name}' alt='{title}' />",
                "  </div>",
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )
    return html_path


def write_plotly_chart_html(stem: str, fig: go.Figure, *, title: str | None = None) -> str:
    CHARTS.mkdir(parents=True, exist_ok=True)
    html_path = CHARTS / f"{stem}.html"
    if not WRITE_HTML:
        return str(html_path)
    if title:
        apply_standard_theme(fig, title=title)
    fig.write_html(html_path, include_plotlyjs="cdn")
    return str(html_path)


def _plotly_export_size(fig: go.Figure) -> dict[str, int]:
    width = fig.layout.width
    height = fig.layout.height
    return {
        "width": int(width) if width is not None else 700,
        "height": int(height) if height is not None else 500,
    }


def save_plotly_figure(
        stem: str,
        fig: go.Figure,
        *,
        title: str | None,
        data: pd.DataFrame | None = None,
) -> tuple[str, str, str | None]:
    CHARTS.mkdir(parents=True, exist_ok=True)
    svg_path = CHARTS / f"{stem}.svg"
    png_path = CHARTS / f"{stem}.png"
    existing_layout = fig.layout.to_plotly_json()
    apply_standard_theme(fig, title=title)
    layout_overrides: dict[str, object] = {}
    for key in [
        "legend",
        "margin",
        "width",
        "height",
        "paper_bgcolor",
        "plot_bgcolor",
        "showlegend",
        "annotations",
        "xaxis",
        "yaxis",
        "xaxis2",
        "yaxis2",
    ]:
        if key in existing_layout:
            layout_overrides[key] = existing_layout[key]
    if layout_overrides:
        fig.update_layout(**layout_overrides)
    html_path = CHARTS / f"{stem}.html"
    export_size = _plotly_export_size(fig)
    configure_plotly_png_browser()
    try:
        fig.write_image(svg_path, format="svg", width=export_size["width"], height=export_size["height"])
        fig.write_image(png_path, format="png", width=export_size["width"], height=export_size["height"], scale=1)
        if WRITE_HTML:
            fig.write_html(html_path, include_plotlyjs="cdn")
    except Exception as exc:
        LOGGER.warning("Plotly static export failed for %s; falling back to HTML-only export: %s", stem, exc)
        if WRITE_HTML:
            fig.write_html(html_path, include_plotlyjs="cdn")
    data_path = save_chart_data(stem, data)
    return str(svg_path), str(html_path), data_path


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s - %(message)s",
    )


def save_chart_data(stem: str, data: pd.DataFrame | None) -> str | None:
    if data is None:
        return None
    SECTION3_FIGURE_REPORTS.mkdir(parents=True, exist_ok=True)
    data_path = SECTION3_FIGURE_REPORTS / f"{stem}.csv"
    data.to_csv(data_path, index=False)
    return str(data_path)


def style_policy_figure(fig) -> None:
    for ax in fig.axes:
        ax.grid(False)
        ax.set_facecolor("none")
        ax.title.set_color("#000000")
        ax.xaxis.label.set_color("#000000")
        ax.yaxis.label.set_color("#000000")
        ax.tick_params(axis="both", colors="#000000", labelcolor="#000000")
        ax.spines["bottom"].set_color("#000000")
        ax.spines["bottom"].set_linewidth(1.0)
        ax.spines["left"].set_color("#000000")
        ax.spines["left"].set_linewidth(1.0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)


def save_svg_and_html(stem: str, title: str, data: pd.DataFrame | None = None) -> tuple[str, str, str | None]:
    CHARTS.mkdir(parents=True, exist_ok=True)
    svg_path = CHARTS / f"{stem}.svg"
    png_path = CHARTS / f"{stem}.png"
    fig = plt.gcf()
    style_policy_figure(fig)
    html_path = CHARTS / f"{stem}.html"
    configure_plotly_png_browser()
    try:
        plotly_fig = mpl_to_plotly(fig)
        apply_standard_theme(plotly_fig, title=title)
        plotly_fig.write_image(svg_path, format="svg")
        plotly_fig.write_image(png_path, format="png", scale=3)
        if WRITE_HTML:
            plotly_fig.write_html(html_path, include_plotlyjs="cdn")
    except Exception as exc:
        LOGGER.warning("Plotly conversion failed for %s; falling back to Matplotlib static export: %s", stem, exc)
        fig.savefig(svg_path, format="svg", dpi=160, bbox_inches="tight", transparent=True)
        fig.savefig(png_path, format="png", dpi=240, bbox_inches="tight", transparent=True)
        if WRITE_HTML:
            write_chart_html(svg_path, title)
    finally:
        plt.close(fig)
    data_path = save_chart_data(stem, data)
    return str(svg_path), str(html_path), data_path


def style_bar_patches(ax, edge_colors: list[str] | None = None, alpha: float = 0.42) -> None:
    for idx, patch in enumerate(ax.patches):
        base = edge_colors[idx] if edge_colors and idx < len(edge_colors) else patch.get_facecolor()
        patch.set_facecolor(to_rgba(base, alpha))
        patch.set_edgecolor(to_rgba(base, 0.95))
        patch.set_linewidth(1.1)


def style_scatter_collection(collection, color: str, alpha: float = 0.38) -> None:
    collection.set_facecolor(to_rgba(color, alpha))
    collection.set_edgecolor(to_rgba(color, 0.9))
    collection.set_linewidth(1.0)


def annotate_scatter_labels(
        ax,
        data: pd.DataFrame,
        *,
        x: str,
        y: str,
        label: str,
        fontsize: int = 9,
        x_offset: float = 3.0,
        y_offset: float = 3.0,
) -> None:
    for _, row in data.iterrows():
        label_text = str(row[label])
        if not label_text or label_text.lower() == "nan":
            continue
        ax.annotate(
            label_text,
            (row[x], row[y]),
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=fontsize,
            color="#000000",
        )


def annotate_bar_values(
        ax,
        *,
        fmt: str = "{:.1f}",
        orientation: str = "horizontal",
        fontsize: int = 8,
        color: str = "#000000",
) -> None:
    for patch in ax.patches:
        if orientation == "horizontal":
            value = patch.get_width()
            x = value
            y = patch.get_y() + patch.get_height() / 2.0
            x_offset = 4 if value >= 0 else -4
            ha = "left" if value >= 0 else "right"
            ax.annotate(
                fmt.format(value),
                (x, y),
                xytext=(x_offset, 0),
                textcoords="offset points",
                va="center",
                ha=ha,
                fontsize=fontsize,
                color=color,
            )
        else:
            value = patch.get_height()
            x = patch.get_x() + patch.get_width() / 2.0
            y = value
            ax.annotate(
                fmt.format(value),
                (x, y),
                xytext=(0, 4),
                textcoords="offset points",
                va="bottom",
                ha="center",
                fontsize=fontsize,
                color=color,
            )


def annotate_series_endpoints(
        ax,
        data: pd.DataFrame,
        *,
        x: str,
        y: str,
        series: str,
        fmt: str = "{:.1f}",
        fontsize: int = 8,
        color_map: dict[str, str] | None = None,
) -> None:
    for series_name, group in data.groupby(series):
        ordered = group.sort_values(x)
        if ordered.empty:
            continue
        row = ordered.iloc[-1]
        color = color_map.get(series_name, "#000000") if color_map else "#000000"
        ax.annotate(
            fmt.format(float(row[y])),
            (row[x], row[y]),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            ha="left",
            fontsize=fontsize,
            color=color,
        )


def annotate_point_values(
        ax,
        data: pd.DataFrame,
        *,
        x: str,
        y: str,
        text: str | None = None,
        fmt: str = "{:.1f}",
        fontsize: int = 8,
        color: str = "#000000",
        x_offset: float = 6.0,
        y_offset: float = 0.0,
        va: str = "center",
        bbox: dict[str, object] | None = None,
) -> None:
    for _, row in data.iterrows():
        label = str(row[text]) if text else fmt.format(float(row[x]))
        ax.annotate(
            label,
            (row[x], row[y]),
            xytext=(x_offset, y_offset),
            textcoords="offset points",
            va=va,
            ha="left",
            fontsize=fontsize,
            color=color,
            bbox=bbox,
        )


def load_figure_data(stem: str) -> pd.DataFrame:
    path = SECTION3_FIGURE_REPORTS / f"{stem}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing figure data for {stem}: {path}")
    return pd.read_csv(path)


def load_saved_policy_summary() -> dict[str, object]:
    path = REPORTS / "policy_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"Saved Section 3 summary not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def question_a_target_town_from_saved_outputs() -> str:
    summary_path = REPORTS / "policy_summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        question_a = summary.get("question_a", summary.get("yishun", {}))
        target_town = question_a.get("target_town")
        if target_town:
            return str(target_town)
    return "YISHUN"


def load_frame() -> pd.DataFrame:
    path = DATA_PROCESSED / "hdb_resale_processed.parquet"
    if not path.exists():
        raise FileNotFoundError("Processed dataset missing. Run `python -m src.pipeline.build_resale_analysis_dataset` first.")
    return pd.read_parquet(path)


def age_band(series: pd.Series, width: int = 10) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    start = np.floor(numeric / width) * width
    return start.map(lambda value: f"{int(value)}-{int(value + width - 1)}" if pd.notna(value) else np.nan)


def town_reference_for_formula(sample: pd.DataFrame, preferred: str = "ANG MO KIO") -> str:
    towns = set(sample["town"].dropna().astype(str))
    if preferred in towns:
        return preferred
    return sorted(towns)[0]


def display_town_name(town: str) -> str:
    return str(town).replace("_", " ").title()


def town_slug(town: str) -> str:
    return str(town).strip().lower().replace(" ", "_")


def question_a_stem(figure_number: int, description: str, *, target_town: str) -> str:
    return f"S3QaF{figure_number}_{town_slug(target_town)}_{description}"


def town_coefficient_table(model: object) -> pd.DataFrame:
    conf_int = model.conf_int()
    rows: list[dict[str, object]] = []
    for name, value in model.params.items():
        if "C(town" not in name:
            continue
        town = name.split("T.", 1)[1].rstrip("]") if "T." in name else name
        ci_low = float(conf_int.loc[name].iloc[0])
        ci_high = float(conf_int.loc[name].iloc[1])
        rows.append(
            {
                "town": town,
                "coefficient": float(value),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "effect_pct": float((np.exp(value) - 1.0) * 100.0),
                "effect_pct_ci_low": float((np.exp(ci_low) - 1.0) * 100.0),
                "effect_pct_ci_high": float((np.exp(ci_high) - 1.0) * 100.0),
                "pvalue": float(model.pvalues[name]),
            }
        )
    return pd.DataFrame(rows)


def selected_target_town_regression_coefficients(
        model: object,
        *,
        reference_town: str,
        target_town: str,
) -> pd.DataFrame:
    conf_int = model.conf_int()
    rows: list[dict[str, object]] = []
    for name, value in model.params.items():
        if name == "Intercept":
            continue
        label: str | None = None
        group: str | None = None
        if name == "flat_age":
            label = "Flat age"
            group = "Control"
        elif name == f"C(town, Treatment(reference='{reference_town}'))[T.{target_town}]":
            label = display_town_name(target_town)
            group = "Town"
        elif name.startswith("C(flat_type"):
            label = name.split("T.", 1)[1].rstrip("]").replace("_", " ").title()
            group = "Flat type"
        elif name.startswith("C(transaction_year)[T."):
            continue
        else:
            continue
        ci_low = float(conf_int.loc[name].iloc[0])
        ci_high = float(conf_int.loc[name].iloc[1])
        rows.append(
            {
                "term": name,
                "label": label,
                "group": group,
                "coefficient": float(value),
                "ci_low": ci_low,
                "ci_high": ci_high,
                "effect_pct": float((np.exp(value) - 1.0) * 100.0),
                "effect_pct_ci_low": float((np.exp(ci_low) - 1.0) * 100.0),
                "effect_pct_ci_high": float((np.exp(ci_high) - 1.0) * 100.0),
                "pvalue": float(model.pvalues[name]),
            }
        )
    coeffs = pd.DataFrame(rows)
    if coeffs.empty:
        return coeffs
    order = {"Town": 0, "Control": 1, "Flat type": 2}
    return coeffs.sort_values(
        by=["group", "effect_pct"],
        key=lambda s: s.map(order) if s.name == "group" else s,
        ascending=[True, True],
    ).reset_index(drop=True)


def year_month_label(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.to_period("M").astype(str)
