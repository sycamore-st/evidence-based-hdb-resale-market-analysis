from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from src.common.config import WEB_OVERVIEW_ARTIFACTS
from src.common.utils import slugify


DASHBOARD3_ROOT = WEB_OVERVIEW_ARTIFACTS / "dashboard3"
TOWNS_ROOT = DASHBOARD3_ROOT / "towns"


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _candidate_score(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["median_floor_area"].fillna(0) * 1.8
        + frame["budget_slack"].fillna(0) / 15_000
        + frame["school_count_within_1km"].fillna(0) * 4
        - frame["nearest_mrt_distance_km"].fillna(1.5) * 25
        - frame["distance_to_cbd_km"].fillna(12) * 0.55
    )


def _choose_candidates(
    rows: list[dict[str, Any]],
    *,
    year: int,
    budget: int,
    flat_types: list[str] | None,
    top_n: int,
) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    filtered = frame.loc[(frame["transaction_year"] == year) & (frame["budget"] == budget)].copy()
    if flat_types:
        filtered = filtered.loc[filtered["flat_type"].isin(flat_types)].copy()
    filtered = filtered.loc[
        (filtered["building_match_status"] == "matched_geometry") & (filtered["has_building_geometry"] == "Yes")
    ].copy()
    if filtered.empty:
        return filtered

    filtered["score"] = _candidate_score(filtered)
    filtered = filtered.sort_values(
        ["score", "median_floor_area", "budget_slack", "transactions"],
        ascending=[False, False, False, False],
    )
    grouped = filtered.groupby("building_key", as_index=False).first()
    return grouped.head(top_n).reset_index(drop=True)


def _focus_bounds(
    candidates: pd.DataFrame,
    poi_points: list[dict[str, Any]],
    selected_key: str | None,
) -> tuple[dict[str, float], str | None]:
    if candidates.empty:
        return {"min_lon": 103.9, "max_lon": 103.95, "min_lat": 1.31, "max_lat": 1.34}, None

    selected = selected_key if selected_key in set(candidates["building_key"]) else str(candidates.iloc[0]["building_key"])
    selected_row = candidates.loc[candidates["building_key"] == selected].iloc[0]
    points = [
        (float(selected_row["building_longitude"]), float(selected_row["building_latitude"])),
    ]
    for item in poi_points:
        points.append((float(item["poi_longitude"]), float(item["poi_latitude"])))

    min_lon = min(point[0] for point in points)
    max_lon = max(point[0] for point in points)
    min_lat = min(point[1] for point in points)
    max_lat = max(point[1] for point in points)
    lon_pad = max((max_lon - min_lon) * 0.35, 0.0035)
    lat_pad = max((max_lat - min_lat) * 0.35, 0.0028)
    return {
        "min_lon": min_lon - lon_pad,
        "max_lon": max_lon + lon_pad,
        "min_lat": min_lat - lat_pad,
        "max_lat": max_lat + lat_pad,
    }, selected


def _zoom_for_bounds(bounds: dict[str, float]) -> float:
    lon_span = max(bounds["max_lon"] - bounds["min_lon"], 0.001)
    lat_span = max(bounds["max_lat"] - bounds["min_lat"], 0.001)
    span = max(lon_span, lat_span)
    if span < 0.005:
        return 16
    if span < 0.01:
        return 15
    if span < 0.02:
        return 14
    if span < 0.04:
        return 13
    return 12


def render_dashboard3_plotly_map(
    *,
    town: str,
    year: int,
    budget: int,
    flat_types: list[str] | None,
    top_n: int,
    output_path: Path,
    selected_building_key: str | None = None,
) -> Path:
    slug = slugify(town)
    town_dir = TOWNS_ROOT / slug
    if not town_dir.exists():
        raise FileNotFoundError(f"Town artifacts not found for {town!r} at {town_dir}")

    buildings = _load_json(town_dir / "buildings.json")
    geometry = _load_json(town_dir / "geometry.json")
    poi_points = _load_json(town_dir / "poi_points.json")

    candidates = _choose_candidates(
        buildings,
        year=year,
        budget=budget,
        flat_types=flat_types,
        top_n=top_n,
    )
    if candidates.empty:
        raise ValueError(f"No matching buildings found for {town}, year={year}, budget={budget}")

    bounds, selected_key = _focus_bounds(candidates, poi_points, selected_building_key)
    visible_keys = set(candidates["building_key"].astype(str))
    selected_key = selected_key or str(candidates.iloc[0]["building_key"])

    visible_features = [
        {
            "type": "Feature",
            "properties": {"building_key": feature["properties"]["Building Key"]},
            "geometry": feature["geometry"],
        }
        for feature in geometry["features"]
        if feature["properties"]["Building Key"] in visible_keys
    ]

    choropleth = go.Choroplethmap(
        geojson={"type": "FeatureCollection", "features": visible_features},
        locations=[feature["properties"]["building_key"] for feature in visible_features],
        z=[2 if feature["properties"]["building_key"] == selected_key else 1 for feature in visible_features],
        featureidkey="properties.building_key",
        colorscale=[
            [0.0, "rgba(86,120,165,0.10)"],
            [0.5, "rgba(86,120,165,0.22)"],
            [1.0, "rgba(86,120,165,0.60)"],
        ],
        zmin=1,
        zmax=2,
        showscale=False,
        marker={"line": {"color": "rgba(90,102,120,0.62)", "width": 1.2}, "opacity": 0.8},
        hovertemplate="%{location}<extra></extra>",
        name="Buildings",
    )

    poi_frame = pd.DataFrame(poi_points)
    poi_color = {
        "Bus Stop": "rgba(204, 93, 76, 0.9)",
        "MRT": "rgba(74, 110, 158, 0.95)",
        "School": "rgba(122, 164, 138, 0.95)",
    }
    poi_symbol = {"Bus Stop": "cross", "MRT": "diamond", "School": "circle"}

    poi_traces = []
    for poi_type in ["Bus Stop", "MRT", "School"]:
        subset = poi_frame.loc[poi_frame["poi_type"] == poi_type].copy()
        if subset.empty:
            continue
        poi_traces.append(
            go.Scattermap(
                lon=subset["poi_longitude"],
                lat=subset["poi_latitude"],
                mode="markers",
                marker={"size": 10, "color": poi_color[poi_type], "symbol": poi_symbol[poi_type]},
                text=[f"{poi_type}: {name}" for name in subset["poi_name"]],
                hovertemplate="%{text}<extra></extra>",
                name=poi_type,
            )
        )

    selected = candidates.loc[candidates["building_key"] == selected_key].iloc[0]
    selected_trace = go.Scattermap(
        lon=[selected["building_longitude"]],
        lat=[selected["building_latitude"]],
        mode="markers+text",
        marker={"size": 18, "color": "rgba(230, 137, 53, 0.95)", "symbol": "square"},
        text=[f"Block {selected['block']} / {selected['flat_type']}"],
        textposition="top right",
        textfont={"size": 13, "color": "#26231f"},
        hovertemplate=(
            f"Block {selected['block']}<br>"
            f"{selected['flat_type']}<br>"
            f"Median area: {selected['median_floor_area']:.0f} sqm<br>"
            f"Median price: SGD {selected['median_price']:,.0f}<extra></extra>"
        ),
        name="Selected",
    )

    fig = go.Figure(data=[choropleth, *poi_traces, selected_trace])
    fig.update_layout(
        map={
            "style": "carto-positron",
            "center": {"lon": (bounds["min_lon"] + bounds["max_lon"]) / 2, "lat": (bounds["min_lat"] + bounds["max_lat"]) / 2},
            "zoom": _zoom_for_bounds(bounds),
        },
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 0.01,
            "xanchor": "left",
            "x": 0.01,
            "bgcolor": "rgba(255,255,255,0.82)",
        },
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path, include_plotlyjs="cdn")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a standalone Plotly HTML map for Dashboard 3 town artifacts.")
    parser.add_argument("--town", default="BEDOK")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--budget", type=int, default=800000)
    parser.add_argument("--flat-type", dest="flat_types", action="append", help="Repeat to filter to one or more flat types.")
    parser.add_argument("--top-n", type=int, default=40)
    parser.add_argument("--selected-building-key", default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=WEB_OVERVIEW_ARTIFACTS / "dashboard3" / "standalone-bedok-map.html",
    )
    args = parser.parse_args()

    output = render_dashboard3_plotly_map(
        town=args.town,
        year=args.year,
        budget=args.budget,
        flat_types=args.flat_types,
        top_n=args.top_n,
        output_path=args.output,
        selected_building_key=args.selected_building_key,
    )
    print(f"Wrote {output}", flush=True)


if __name__ == "__main__":
    main()
