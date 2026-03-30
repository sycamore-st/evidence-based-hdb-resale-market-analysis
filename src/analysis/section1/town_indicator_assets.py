from __future__ import annotations

import json
import re
from pathlib import Path

import plotly.graph_objects as go
import pandas as pd

from src.analysis.common.plotly_standard import configure_plotly_png_browser, load_plotly_theme
from src.analysis.section1.helpers import ensure_section1_results_dir, section1_output_path, write_section1_csv


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _iter_exterior_rings(geometry: dict) -> list[list[list[float]]]:
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        return [coords[0]] if coords else []
    if geom_type == "MultiPolygon":
        return [polygon[0] for polygon in coords if polygon]
    return []


def _collect_bounds(features: list[dict]) -> tuple[float, float, float, float]:
    min_lon = float("inf")
    min_lat = float("inf")
    max_lon = float("-inf")
    max_lat = float("-inf")
    for feature in features:
        for ring in _iter_exterior_rings(feature["geometry"]):
            for lon, lat in ring:
                min_lon = min(min_lon, lon)
                min_lat = min(min_lat, lat)
                max_lon = max(max_lon, lon)
                max_lat = max(max_lat, lat)
    return min_lon, min_lat, max_lon, max_lat


def _add_feature_traces(
    fig: go.Figure,
    features: list[dict],
    *,
    fillcolor: str,
    linecolor: str,
    line_width: float,
) -> None:
    for feature in features:
        for ring in _iter_exterior_rings(feature["geometry"]):
            lons = [point[0] for point in ring]
            lats = [point[1] for point in ring]
            fig.add_trace(
                go.Scatter(
                    x=lons,
                    y=lats,
                    mode="lines",
                    fill="toself",
                    fillcolor=fillcolor,
                    line={"color": linecolor, "width": line_width},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


def build_town_indicator_assets(
    town_boundary_geojson: Path,
    svg_output_dir: Path,
    png_output_dir: Path,
) -> pd.DataFrame:
    configure_plotly_png_browser()
    payload = json.loads(town_boundary_geojson.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    theme = load_plotly_theme()

    min_lon, min_lat, max_lon, max_lat = _collect_bounds(features)
    lon_pad = (max_lon - min_lon) * 0.06
    lat_pad = (max_lat - min_lat) * 0.06
    x_range = [min_lon - lon_pad, max_lon + lon_pad]
    y_range = [min_lat - lat_pad, max_lat + lat_pad]

    town_names = sorted(
        {
            feature["properties"].get("Town")
            for feature in features
            if feature.get("properties", {}).get("Town")
        }
    )
    svg_output_dir.mkdir(parents=True, exist_ok=True)
    png_output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    for town in town_names:
        town_features = [feature for feature in features if feature["properties"].get("Town") == town]
        other_features = [feature for feature in features if feature["properties"].get("Town") != town]

        fig = go.Figure()
        _add_feature_traces(
            fig,
            other_features,
            fillcolor=theme.alpha(theme.text_muted, 0.18),
            linecolor=theme.alpha(theme.text_muted, 0.30),
            line_width=0.4,
        )
        _add_feature_traces(
            fig,
            town_features,
            fillcolor=theme.secondary_soft,
            linecolor=theme.secondary,
            line_width=0.9,
        )
        fig.update_layout(
            width=240,
            height=150,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            xaxis={
                "visible": False,
                "showgrid": False,
                "zeroline": False,
                "range": x_range,
            },
            yaxis={
                "visible": False,
                "showgrid": False,
                "zeroline": False,
                "scaleanchor": "x",
                "scaleratio": 1,
                "range": y_range,
            },
        )
        stem = _slugify(town)
        svg_filename = f"{stem}.svg"
        png_filename = f"{stem}.png"
        svg_path = svg_output_dir / svg_filename
        png_path = png_output_dir / png_filename
        fig.write_image(svg_path, format="svg")
        fig.write_image(png_path, format="png", scale=2)
        manifest_rows.append(
            {
                "town": town,
                "town_indicator_svg": svg_filename,
                "town_indicator_svg_path": str(svg_path),
                "town_indicator_png": png_filename,
                "town_indicator_png_path": str(png_path),
            }
        )

    return pd.DataFrame(manifest_rows).sort_values("town").reset_index(drop=True)


def export_town_indicator_assets() -> dict[str, str]:
    ensure_section1_results_dir()
    geojson_path = section1_output_path("planning_area_hdb_map_2019.geojson", kind="final")
    svg_dir = section1_output_path("town_indicator_svgs", kind="final")
    png_dir = section1_output_path("town_indicator_pngs", kind="final")
    manifest = build_town_indicator_assets(geojson_path, svg_dir, png_dir)
    write_section1_csv(manifest, "town_indicator_assets.csv", kind="final")
    return {
        "town_indicator_manifest": str(section1_output_path("town_indicator_assets.csv", kind="final")),
        "town_indicator_svg_directory": str(svg_dir),
        "town_indicator_png_directory": str(png_dir),
    }


def main() -> None:
    export_town_indicator_assets()


if __name__ == "__main__":
    main()
