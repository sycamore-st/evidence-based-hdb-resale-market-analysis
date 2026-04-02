from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.common.config import (
    DATA_PROCESSED,
    SECTION2_OUTPUT_RESULTS,
    SECTION3_OUTPUT_RESULTS,
    WEB_MODEL_ARTIFACTS,
    WEB_OVERVIEW_ARTIFACTS,
    WEB_POLICY_ARTIFACTS,
)


WEB_SECTIONS = ("overview", "policy", "model")
REQUIRED_FILES = ("summary", "timeseries", "filters", "metadata")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_float(value: Any, digits: int = 1) -> float:
    if value is None:
        return 0.0
    if isinstance(value, float) and math.isnan(value):
        return 0.0
    return round(float(value), digits)


def _dataset_version(source_coverage_end: str) -> str:
    return f"web-{source_coverage_end}"


def _base_metadata(section: str, source_coverage_end: str, *, record_count: int, notes: list[str]) -> dict[str, Any]:
    generated_at = _utc_now_iso()
    return {
        "dataset_version": _dataset_version(source_coverage_end),
        "generated_at": generated_at,
        "source_coverage_end": source_coverage_end,
        "section": section,
        "record_count": record_count,
        "notes": notes,
    }


def _build_overview_from_processed() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    try:
        import pandas as pd
    except ModuleNotFoundError:
        return None

    processed_path = DATA_PROCESSED / "hdb_resale_processed.parquet"
    if not processed_path.exists():
        return None

    frame = pd.read_parquet(processed_path, columns=["month", "town", "flat_type", "resale_price"])
    if frame.empty:
        return None

    frame = frame.assign(month=frame["month"].astype(str))
    coverage_end = str(frame["month"].max())
    latest_month = frame["month"].max()
    latest_frame = frame.loc[frame["month"] == latest_month].copy()

    monthly = (
        frame.groupby("month", dropna=False)["resale_price"]
        .median()
        .reset_index()
        .sort_values("month")
        .tail(12)
    )
    monthly_counts = (
        frame.groupby("month", dropna=False)
        .size()
        .reset_index(name="transactions")
        .sort_values("month")
        .tail(12)
    )

    duplicate_rows = int(
        frame.duplicated(subset=["month", "town", "flat_type", "resale_price"], keep=False).sum()
    )
    metadata = _base_metadata(
        "overview",
        coverage_end,
        record_count=len(frame),
        notes=[
            "Overview artifacts are derived from the canonical processed resale dataset.",
            f"Duplicate check using published summary keys found {duplicate_rows} duplicated rows.",
        ],
    )
    dataset_version = metadata["dataset_version"]
    generated_at = metadata["generated_at"]

    summary = {
        **{key: metadata[key] for key in ("dataset_version", "generated_at", "source_coverage_end")},
        "headline": "Singapore HDB resale market snapshot",
        "description": "Published market metrics for the latest available month, served from the Python pipeline.",
        "cards": [
            {
                "id": "median-price",
                "label": "Latest median resale price",
                "value": f"SGD {latest_frame['resale_price'].median():,.0f}",
                "context": f"Computed from {len(latest_frame):,} transactions in {latest_month}.",
            },
            {
                "id": "transaction-count",
                "label": "Latest monthly transactions",
                "value": f"{len(latest_frame):,}",
                "context": "Transactions included in the current published month.",
            },
            {
                "id": "town-count",
                "label": "Town coverage",
                "value": f"{frame['town'].nunique():,}",
                "context": "Distinct towns represented in the processed dataset.",
            },
            {
                "id": "flat-types",
                "label": "Flat types",
                "value": f"{frame['flat_type'].nunique():,}",
                "context": "Unique flat-type categories available for filtering.",
            },
        ],
        "insights": [
            "The frontend uses only published overview artifacts, not raw pipeline intermediates.",
            "Monthly series are restricted to the latest 12 months for fast client-side rendering.",
        ],
    }

    timeseries = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "series": [
            {
                "id": "median-resale-price",
                "label": "Median resale price",
                "points": [
                    {"x": row["month"], "y": _safe_float(row["resale_price"], digits=0)}
                    for _, row in monthly.iterrows()
                ],
            },
            {
                "id": "transactions",
                "label": "Monthly transaction count",
                "points": [
                    {"x": row["month"], "y": _safe_float(row["transactions"], digits=0)}
                    for _, row in monthly_counts.iterrows()
                ],
            },
        ],
    }

    filters = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "filters": [
            {
                "id": "town",
                "label": "Town",
                "options": sorted(frame["town"].dropna().astype(str).unique().tolist())[:12],
            },
            {
                "id": "flat_type",
                "label": "Flat type",
                "options": sorted(frame["flat_type"].dropna().astype(str).unique().tolist()),
            },
            {
                "id": "month",
                "label": "Recent month",
                "options": monthly["month"].astype(str).tolist(),
            },
        ],
    }
    return summary, timeseries, filters, metadata


def build_overview_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    published = _build_overview_from_processed()
    if published is not None:
        return published

    coverage_end = "2026-03"
    metadata = _base_metadata(
        "overview",
        coverage_end,
        record_count=6,
        notes=[
            "Fallback sample overview artifacts are committed so the frontend can boot without local processed data.",
            "Run `python -m src.pipeline.publish_web_artifacts` after rebuilding the pipeline to replace the sample data.",
        ],
    )
    dataset_version = metadata["dataset_version"]
    generated_at = metadata["generated_at"]
    summary = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "headline": "Singapore HDB resale market snapshot",
        "description": "A light-weight overview surface built from prepared dashboard artifacts.",
        "cards": [
            {
                "id": "median-price",
                "label": "Latest median resale price",
                "value": "SGD 545,000",
                "context": "Sample artifact for local frontend bootstrapping.",
            },
            {
                "id": "transaction-count",
                "label": "Latest monthly transactions",
                "value": "2,180",
                "context": "Replace with real pipeline outputs when processed data is available.",
            },
            {
                "id": "town-count",
                "label": "Town coverage",
                "value": "26",
                "context": "Intended contract shape for filter population.",
            },
            {
                "id": "flat-types",
                "label": "Flat types",
                "value": "7",
                "context": "Published as stable frontend metadata.",
            },
        ],
        "insights": [
            "Overview data is designed to be served from static JSON payloads.",
            "Heavy processing stays in Python so the web UI stays fast and stable.",
        ],
    }
    timeseries = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "series": [
            {
                "id": "median-resale-price",
                "label": "Median resale price",
                "points": [
                    {"x": "2025-10", "y": 512000},
                    {"x": "2025-11", "y": 519000},
                    {"x": "2025-12", "y": 524000},
                    {"x": "2026-01", "y": 531000},
                    {"x": "2026-02", "y": 538000},
                    {"x": "2026-03", "y": 545000},
                ],
            },
            {
                "id": "transactions",
                "label": "Monthly transaction count",
                "points": [
                    {"x": "2025-10", "y": 2040},
                    {"x": "2025-11", "y": 2088},
                    {"x": "2025-12", "y": 2124},
                    {"x": "2026-01", "y": 2147},
                    {"x": "2026-02", "y": 2179},
                    {"x": "2026-03", "y": 2180},
                ],
            },
        ],
    }
    filters = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "filters": [
            {"id": "town", "label": "Town", "options": ["ANG MO KIO", "BEDOK", "QUEENSTOWN", "TAMPINES", "YISHUN"]},
            {"id": "flat_type", "label": "Flat type", "options": ["3 ROOM", "4 ROOM", "5 ROOM", "EXECUTIVE"]},
            {"id": "month", "label": "Recent month", "options": ["2026-01", "2026-02", "2026-03"]},
        ],
    }
    return summary, timeseries, filters, metadata


def build_policy_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    policy_summary = _read_json(SECTION3_OUTPUT_RESULTS / "policy_summary.json")
    question_a = policy_summary["question_a"]
    flat_sizes = policy_summary["flat_sizes"]
    coverage_end = "2026-03"
    metadata = _base_metadata(
        "policy",
        coverage_end,
        record_count=len(question_a.get("cell_comparison_preview", [])),
        notes=[
            "Policy artifacts summarize Section 3 findings into card and chart payloads.",
            "The current payloads are built from tracked analysis outputs already present in the repository.",
        ],
    )
    dataset_version = metadata["dataset_version"]
    generated_at = metadata["generated_at"]
    preview = question_a.get("cell_comparison_preview", [])[:6]
    adjusted_profile = flat_sizes.get("adjusted_completion_year_profile", [])[:6]
    summary = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "headline": question_a["banner_statement"],
        "description": "Condensed policy evidence translated into frontend-friendly cards and chart-ready data.",
        "cards": [
            {
                "id": "yishun-effect",
                "label": "Adjusted Yishun effect",
                "value": f"{_safe_float(question_a['target_effect_pct'])}%",
                "context": "Estimated controlled price-per-sqm effect relative to the reference town.",
            },
            {
                "id": "yishun-rank",
                "label": "Adjusted town rank",
                "value": str(question_a["adjusted_rank_by_town_effect"]),
                "context": "Rank after controlling for flat type, age, and year.",
            },
            {
                "id": "completion-slope",
                "label": "Within-type floor-area slope",
                "value": f"{_safe_float(flat_sizes['average_within_type_slope_sqm_per_completion_year'])} sqm/year",
                "context": "Average within-flat-type completion-year slope from the policy analysis.",
            },
            {
                "id": "top-flat-types",
                "label": "Primary flat types",
                "value": ", ".join(question_a["top_flat_types"]),
                "context": "Most important flat types highlighted in the current policy narrative.",
            },
        ],
        "insights": [
            question_a["banner_statement"],
            flat_sizes["banner_statement"],
            "The dashboard contract keeps explanatory text alongside quantitative metrics for static-site publishing.",
        ],
    }
    timeseries = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "series": [
            {
                "id": "gap-vs-peer-median",
                "label": "Gap vs peer median by age band",
                "points": [
                    {"x": item["age_band"], "y": _safe_float(item["gap_vs_peer_median"], digits=0)}
                    for item in preview
                ],
            },
            {
                "id": "adjusted-floor-area",
                "label": "Adjusted floor area by completion year",
                "points": [
                    {
                        "x": str(item["completion_year"]),
                        "y": _safe_float(item["adjusted_floor_area"], digits=1),
                    }
                    for item in adjusted_profile
                ],
            },
        ],
    }
    filters = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "filters": [
            {"id": "target_town", "label": "Target town", "options": [question_a["target_town"]]},
            {"id": "candidate_towns", "label": "Candidate towns", "options": question_a["candidate_towns"][:6]},
            {"id": "flat_type", "label": "Highlighted flat types", "options": question_a["top_flat_types"]},
        ],
    }
    return summary, timeseries, filters, metadata


def build_model_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    classifier = _read_json(SECTION2_OUTPUT_RESULTS / "S2Qc_flat_type_classifier.json")
    key_numbers = _read_json(SECTION3_OUTPUT_RESULTS / "S3Qa_model_key_numbers.json")
    coverage_end = "2026-03"
    per_class = [
        item
        for item in classifier.get("per_class_accuracy", [])
        if item.get("per_class_accuracy") is not None
        and not (isinstance(item.get("per_class_accuracy"), float) and math.isnan(item.get("per_class_accuracy")))
    ]
    metadata = _base_metadata(
        "model",
        coverage_end,
        record_count=len(per_class),
        notes=[
            "Model artifacts combine classifier diagnostics with headline econometric takeaways.",
            "Frontend chart payloads are simplified to avoid exposing raw training intermediates.",
        ],
    )
    dataset_version = metadata["dataset_version"]
    generated_at = metadata["generated_at"]
    summary = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "headline": "Model diagnostics and interpretable outputs",
        "description": "Prepared model summaries for the dashboard layer, published independently from notebooks and slide builds.",
        "cards": [
            {
                "id": "classifier-accuracy",
                "label": "Flat-type classifier accuracy",
                "value": f"{_safe_float(classifier['accuracy'] * 100)}%",
                "context": f"Best model: {classifier['best_model']}.",
            },
            {
                "id": "weighted-f1",
                "label": "Weighted F1",
                "value": f"{_safe_float(classifier['weighted_f1'] * 100)}%",
                "context": "Holdout classification quality across the observed flat types.",
            },
            {
                "id": "pricing-delta",
                "label": "Recovered-type RMSE delta",
                "value": f"SGD {_safe_float(classifier['pricing_rmse_delta'], digits=0):,.0f}",
                "context": "Incremental pricing error after recovering missing flat types.",
            },
            {
                "id": "yishun-effect",
                "label": "Controlled Yishun effect",
                "value": f"{_safe_float(key_numbers['target_effect_pct'])}%",
                "context": f"Relative to {key_numbers['reference_town']} in the town-effect regression.",
            },
        ],
        "insights": [
            "Classifier diagnostics are published in a compact, frontend-safe format.",
            "Econometric headline numbers can coexist with machine-learning diagnostics in one dashboard surface.",
            "Live model training is intentionally out of scope for the first web version.",
        ],
    }
    timeseries = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "series": [
            {
                "id": "per-class-accuracy",
                "label": "Per-class accuracy",
                "points": [
                    {"x": item["flat_type"], "y": _safe_float(item["per_class_accuracy"] * 100)}
                    for item in per_class
                ],
            },
            {
                "id": "interaction-effect",
                "label": "Interaction effect by flat type",
                "points": [
                    {"x": item["flat_type"], "y": _safe_float(item["effect_pct"])}
                    for item in key_numbers["interaction_effects"]
                ],
            },
        ],
    }
    filters = {
        "dataset_version": dataset_version,
        "generated_at": generated_at,
        "source_coverage_end": coverage_end,
        "filters": [
            {"id": "best_model", "label": "Published model", "options": [classifier["best_model"]]},
            {"id": "flat_type", "label": "Flat type", "options": [item["flat_type"] for item in per_class]},
            {"id": "reference_town", "label": "Reference town", "options": [key_numbers["reference_town"]]},
        ],
    }
    return summary, timeseries, filters, metadata


def build_web_artifact_bundle() -> dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]]:
    return {
        "overview": build_overview_payloads(),
        "policy": build_policy_payloads(),
        "model": build_model_payloads(),
    }


def artifact_directory(section: str) -> Path:
    mapping = {
        "overview": WEB_OVERVIEW_ARTIFACTS,
        "policy": WEB_POLICY_ARTIFACTS,
        "model": WEB_MODEL_ARTIFACTS,
    }
    return mapping[section]
