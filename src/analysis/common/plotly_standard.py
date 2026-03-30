from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from src.common.config import PROJECT_ROOT


THEME_TOKENS_CANDIDATES = [
    PROJECT_ROOT / "slides" / "section1" / "theme_tokens.json",
    PROJECT_ROOT / "slides" / "theme_tokens.json",
]

PREFERRED_MACOS_BROWSER_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

@dataclass(frozen=True)
class PlotlyTheme:
    bg: str
    surface: str
    surface_alt: str
    primary: str
    primary_dark: str
    secondary: str
    secondary_soft: str
    accent: str
    border: str
    text: str
    text_muted: str
    blue: str
    green: str
    orange: str

    @property
    def color_sequence(self) -> list[str]:
        return [
            self.orange,
            self.blue,
            self.green,
            self.accent,
            self.secondary,
        ]

    @property
    def heatmap_primary_scale(self) -> list[list[float | int | str]]:
        return [
            [0.0, self.surface],
            [0.5, self.accent],
            [1.0, self.blue],
        ]

    @property
    def heatmap_secondary_scale(self) -> list[list[float | int | str]]:
        return [
            [0.0, self.surface],
            [0.5, self.secondary_soft],
            [1.0, self.green],
        ]

    @staticmethod
    def alpha(color: str, opacity: float) -> str:
        color = color.lstrip("#")
        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
        return f"rgba({red},{green},{blue},{opacity:.3f})"


@lru_cache(maxsize=1)
def load_plotly_theme() -> PlotlyTheme:
    theme_tokens_path = next((path for path in THEME_TOKENS_CANDIDATES if path.exists()), None)
    if theme_tokens_path is None:
        raise FileNotFoundError(
            "Could not find theme_tokens.json in expected slide theme locations."
        )
    payload = json.loads(theme_tokens_path.read_text(encoding="utf-8"))
    colors = payload["color"]
    return PlotlyTheme(
        bg=colors["bg"],
        surface=colors["surface"],
        surface_alt=colors["surfaceAlt"],
        primary=colors["primary"],
        primary_dark=colors["primaryDark"],
        secondary=colors["secondary"],
        secondary_soft=colors["secondarySoft"],
        accent=colors["accent"],
        border=colors["border"],
        text=colors["text"],
        text_muted=colors["textMuted"],
        blue="#7F93A6",
        green="#7B8F79",
        orange=colors["primary"],
    )


def apply_standard_theme(
        fig: go.Figure,
        *,
        title: str | None = None,
        xaxis_title: str | None = None,
        yaxis_title: str | None = None,
        xaxis_kwargs: dict[str, Any] | None = None,
        yaxis_kwargs: dict[str, Any] | None = None,
) -> go.Figure:
    theme = load_plotly_theme()
    black = "#000000"
    title_size = 20
    base_font_size = 13
    axis_title_size = 14
    legend_font_size = 12
    label_cap_size = 12
    fig.update_layout(
        title={"text": title, "font": {"size": title_size, "color": black, "family": "Georgia"}},
        font={"color": black, "size": base_font_size, "family": "Arial"},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=theme.color_sequence,
        hoverlabel={"bgcolor": theme.surface, "font": {"color": black}},
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": "rgba(0,0,0,0)",
            "font": {"color": black, "size": legend_font_size},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        margin={"l": 72, "r": 36, "t": 80, "b": 72},
        uniformtext={"minsize": 10, "mode": "hide"},
    )
    fig.update_xaxes(
        title=xaxis_title,
        showline=True,
        linewidth=1,
        linecolor=black,
        showgrid=False,
        gridcolor="rgba(0,0,0,0)",
        zerolinecolor=black,
        tickfont={"color": black, "size": base_font_size},
        title_font={"color": black, "size": axis_title_size},
        **(xaxis_kwargs or {}),
    )
    fig.update_yaxes(
        title=yaxis_title,
        showline=True,
        linewidth=1,
        linecolor=black,
        showgrid=False,
        gridcolor="rgba(0,0,0,0)",
        zerolinecolor=black,
        tickfont={"color": black, "size": base_font_size},
        title_font={"color": black, "size": axis_title_size},
        **(yaxis_kwargs or {}),
    )
    for trace in fig.data:
        for attr in ("textfont", "insidetextfont", "outsidetextfont"):
            font = getattr(trace, attr, None)
            if font is None:
                continue
            size = getattr(font, "size", None)
            if size is not None and size > label_cap_size:
                setattr(trace, attr, {**font.to_plotly_json(), "size": label_cap_size})
    for annotation in fig.layout.annotations or ():
        font = annotation.font.to_plotly_json() if annotation.font else {}
        size = font.get("size")
        if size is None or size > label_cap_size:
            annotation.font = {**font, "size": min(size or label_cap_size, label_cap_size)}
    return fig


def configure_plotly_png_browser() -> str | None:
    browser_path = os.environ.get("BROWSER_PATH")
    if browser_path and Path(browser_path).exists():
        return browser_path
    for candidate in PREFERRED_MACOS_BROWSER_PATHS:
        if Path(candidate).exists():
            os.environ["BROWSER_PATH"] = candidate
            return candidate
    return None
