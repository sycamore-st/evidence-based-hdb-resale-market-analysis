from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from src.analysis.common.plotly_standard import apply_standard_theme, load_plotly_theme
from src.analysis.section2.S2_config import (
    DEFAULT_CATBOOST_TUNING_ITERATIONS,
    DEFAULT_BLEND_WEIGHTS,
    DEFAULT_COMPARABLE_EVAL_WORKERS,
    DEFAULT_COMPARABLE_ADJUSTMENT_MAX_MONTH_GAP,
    DEFAULT_HDB_COMPARABLE_AGE_YEAR_GAP,
    DEFAULT_HDB_COMPARABLE_AREA_MAX_DIFF,
    DEFAULT_HDB_COMPARABLE_BUILDING_DISTANCE_KM,
    DEFAULT_QB_LOCAL_AGE_YEAR_GAP,
    DEFAULT_QB_LOCAL_AREA_MAX_DIFF,
    DEFAULT_QB_LOCAL_WINDOW_MONTHS,
    DEFAULT_QUESTION_B_MIN_YEAR,
    DEFAULT_XGBOOST_TUNING_ITERATIONS,
    MAX_REGRESSION_SAMPLE,
    QUESTION_B_BASE_FEATURES,
    QUESTION_B_CONTEXT_FIELDS,
    QUESTION_B_OPTIONAL_FEATURES,
    QUESTION_B_XGBOOST_BEST_PARAMS,
    RANDOM_STATE,
    TARGET_TRANSACTION,
)
from src.analysis.section2.S2_helpers import (
    CatBoostRegressor,
    LOGGER,
    _augment_regression_features,
    _build_time_rebase_lookup,
    _estimator_for_refit,
    _fit_regression_models,
    _load_frame,
    _normalize_subject,
    _parse_storey_bounds,
    _price_preprocessor,
    _recover_resale_price,
    _sample_if_needed,
    _subject_frame,
    _time_rebase_factor_for_timestamp,
    _with_log_price_target,
    evaluate_predictions,
    make_temporal_split,
)
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS
TABLEAU = SECTION2_OUTPUT_RESULTS
from src.common.utils import haversine_km


def _build_question_b_candidates() -> dict[str, object]:
    candidates: dict[str, object] = {
        "linear_regression": LinearRegression(),
        "xgboost": XGBRegressor(
            objective="reg:squarederror",
            **QUESTION_B_XGBOOST_BEST_PARAMS,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }
    if CatBoostRegressor is not None:
        candidates["catboost"] = CatBoostRegressor(
            loss_function="RMSE",
            depth=8,
            learning_rate=0.05,
            iterations=400,
            random_seed=RANDOM_STATE,
            verbose=False,
        )
    return candidates


def get_question_b_features(
        frame: pd.DataFrame,
        *,
        include_optional: bool = True,
) -> tuple[list[str], list[str], list[str]]:
    features = QUESTION_B_BASE_FEATURES.copy()
    if include_optional:
        for column in QUESTION_B_OPTIONAL_FEATURES:
            if column in frame.columns and frame[column].notna().any():
                features.append(column)
    categorical = [column for column in ["flat_type", "town", "flat_model", "storey_range"] if column in features]
    numeric = [column for column in features if column not in categorical]
    return features, categorical, numeric


def build_question_b_training_frame(
        frame: pd.DataFrame,
        *,
        subject_month: pd.Timestamp | None = None,
        min_year: int = DEFAULT_QUESTION_B_MIN_YEAR,
        include_optional: bool = True,
        time_rebase_lookup: dict[pd.Timestamp, float] | None = None,
) -> pd.DataFrame:
    subject_month = pd.Timestamp(subject_month or TARGET_TRANSACTION["transaction_month"])
    enriched = _augment_regression_features(frame)
    features, _, _ = get_question_b_features(enriched, include_optional=include_optional)
    context_fields = [field for field in QUESTION_B_CONTEXT_FIELDS if field in enriched.columns]
    sample = enriched.loc[
        (enriched["transaction_month"] < subject_month) & (enriched["transaction_year"] >= min_year),
        features + context_fields + ["resale_price", "transaction_month", "lease_commence_date"],
    ].dropna(subset=QUESTION_B_BASE_FEATURES + ["resale_price"]).copy()
    sample = _with_log_price_target(sample, time_rebase_lookup=time_rebase_lookup)
    return _sample_if_needed(sample, MAX_REGRESSION_SAMPLE)


def _build_question_b_evaluation_frame(
        frame: pd.DataFrame,
        *,
        min_year: int = DEFAULT_QUESTION_B_MIN_YEAR,
        include_optional: bool = True,
        time_rebase_lookup: dict[pd.Timestamp, float] | None = None,
) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    features, _, _ = get_question_b_features(enriched, include_optional=include_optional)
    context_fields = [field for field in QUESTION_B_CONTEXT_FIELDS if field in enriched.columns]
    sample = enriched.loc[
        enriched["transaction_year"] >= min_year,
        features + context_fields + ["resale_price", "transaction_month", "lease_commence_date"],
    ].dropna(subset=QUESTION_B_BASE_FEATURES + ["resale_price"]).copy()
    sample = _with_log_price_target(sample, time_rebase_lookup=time_rebase_lookup)
    return _sample_if_needed(sample, MAX_REGRESSION_SAMPLE)


def _build_question_b_comparable_frame(
        frame: pd.DataFrame,
        *,
        min_year: int = DEFAULT_QUESTION_B_MIN_YEAR,
) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    keep_columns = [
        "transaction_month",
        "transaction_year",
        "month",
        "town",
        "flat_type",
        "flat_model",
        "storey_range",
        "floor_area_sqm",
        "age",
        "flat_age",
        "remaining_lease_effective",
        "remaining_lease_years",
        "min_floor_level",
        "max_floor_level",
        "lease_commence_date",
        "resale_price",
        "block",
        "street_name",
        "building_key",
        "building_latitude",
        "building_longitude",
    ]
    optional_columns = [column for column in QUESTION_B_OPTIONAL_FEATURES if column in enriched.columns]
    existing_columns = [column for column in keep_columns + optional_columns if column in enriched.columns]
    comparable = enriched.loc[
        enriched["transaction_year"] >= min_year,
        existing_columns,
    ].dropna(
        subset=[
            "transaction_month",
            "town",
            "flat_type",
            "flat_model",
            "floor_area_sqm",
            "lease_commence_date",
            "resale_price",
            "building_key",
            "building_latitude",
            "building_longitude",
        ]
    ).copy()
    return comparable


def _build_question_b_distribution_contexts(
        frame: pd.DataFrame,
        *,
        subject: dict[str, object],
) -> dict[str, pd.DataFrame]:
    sample = frame.copy()
    sample["transaction_month"] = pd.to_datetime(sample["transaction_month"])
    subject_month = pd.Timestamp(subject["transaction_month"])
    for column in ["town", "flat_type"]:
        if column in sample.columns and subject.get(column) is not None and not pd.isna(subject.get(column)):
            sample = sample.loc[sample[column].eq(subject[column])].copy()
    sample["resale_price"] = pd.to_numeric(sample["resale_price"], errors="coerce")
    sample = sample.loc[sample["resale_price"].notna()].copy()
    return {
        "before_2017_11": sample.loc[sample["transaction_month"] < subject_month].copy(),
        "year_2017": sample.loc[sample["transaction_month"].dt.year.eq(2017)].copy(),
        "year_2018": sample.loc[sample["transaction_month"].dt.year.eq(2018)].copy(),
    }


def _evaluate_question_b_random_split(
        evaluation_frame: pd.DataFrame,
        *,
        features: list[str],
        categorical: list[str],
        numeric: list[str],
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        tune_catboost: bool = False,
        catboost_tuning_iterations: int = DEFAULT_CATBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    train_frame, test_frame = train_test_split(
        evaluation_frame,
        test_size=0.25,
        random_state=RANDOM_STATE,
    )
    model_fit = _fit_regression_models(
        train_frame.copy(),
        test_frame.copy(),
        features=features,
        categorical=categorical,
        numeric=numeric,
        candidates=_build_question_b_candidates(),
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
        tune_catboost=tune_catboost,
        catboost_tuning_iterations=catboost_tuning_iterations,
    )
    best_metrics = next(row for row in model_fit["candidate_metrics"] if row["name"] == model_fit["best_model"])
    predictions = _recover_resale_price(
        model_fit["best_pipeline"].predict(test_frame[features]),
        test_frame["floor_area_sqm"],
        test_frame["time_rebase_factor_1990"] if "time_rebase_factor_1990" in test_frame.columns else None,
    )
    predictions_frame = test_frame[
        [column for column in ["transaction_month", "town", "flat_type", "flat_model", "resale_price"] if column in test_frame.columns]
    ].copy()
    predictions_frame["actual_price"] = predictions_frame["resale_price"]
    predictions_frame["predicted_price"] = predictions
    return {
        "best_model": model_fit["best_model"],
        "candidate_metrics": model_fit["candidate_metrics"],
        "metrics": {
            "mae": float(best_metrics["mae"]),
            "rmse": float(best_metrics["rmse"]),
            "mape": float(best_metrics["mape"]),
            "r2": float(best_metrics["r2"]),
            "sample_count": int(len(test_frame)),
        },
        "predictions_frame": predictions_frame,
    }


def resolve_subject_features(
        subject: dict[str, object],
        frame: pd.DataFrame,
        building_features: dict[str, object] | None = None,
        include_optional: bool = True,
        time_rebase_lookup: dict[pd.Timestamp, float] | None = None,
) -> dict[str, object]:
    normalized = _normalize_subject(subject)
    features, _, _ = get_question_b_features(frame, include_optional=include_optional)
    optionals = [feature for feature in QUESTION_B_OPTIONAL_FEATURES if feature in features]
    feature_source = "subject_input"
    building_features = building_features or {}
    context_fields = [
        "building_key",
        "building_latitude",
        "building_longitude",
        "block",
        "street_name",
        "lease_commence_date",
    ]

    for field in context_fields:
        current_value = normalized.get(field)
        if current_value is not None and not pd.isna(current_value):
            continue
        building_value = building_features.get(field)
        if building_value is not None and not pd.isna(building_value):
            normalized[field] = building_value

    if normalized.get("building_key") is None or pd.isna(normalized.get("building_key")):
        lookup = pd.DataFrame()
        if normalized.get("block") is not None and not pd.isna(normalized.get("block")):
            lookup = frame.loc[
                frame["town"].eq(normalized.get("town")) & frame["block"].eq(normalized.get("block"))
                ]
        if lookup.empty and normalized.get("street_name") is not None and not pd.isna(normalized.get("street_name")):
            lookup = frame.loc[
                frame["town"].eq(normalized.get("town")) & frame["street_name"].eq(normalized.get("street_name"))
                ]
        if not lookup.empty:
            first_match = lookup.iloc[0]
            for field in context_fields:
                if normalized.get(field) is None or pd.isna(normalized.get(field)):
                    matched_value = first_match.get(field)
                    if matched_value is not None and not pd.isna(matched_value):
                        normalized[field] = matched_value

    proxy_town_flat = frame.loc[
        frame["town"].eq(normalized.get("town")) & frame["flat_type"].eq(normalized.get("flat_type")),
        optionals,
    ].median(numeric_only=True)
    proxy_town = frame.loc[frame["town"].eq(normalized.get("town")), optionals].median(numeric_only=True)

    for feature in optionals:
        current_value = normalized.get(feature)
        if current_value is not None and not pd.isna(current_value):
            continue
        building_value = building_features.get(feature)
        if building_value is not None and not pd.isna(building_value):
            normalized[feature] = building_value
            feature_source = "building_exact"
            continue
        proxy_value = proxy_town_flat.get(feature, np.nan)
        if pd.isna(proxy_value):
            proxy_value = proxy_town.get(feature, np.nan)
        if not pd.isna(proxy_value):
            normalized[feature] = float(proxy_value)
            if feature_source != "building_exact":
                feature_source = "town_flat_type_proxy" if not pd.isna(
                    proxy_town_flat.get(feature, np.nan)) else "town_proxy"

    normalized["feature_source"] = feature_source
    normalized["time_rebase_factor_1990"] = _time_rebase_factor_for_timestamp(
        pd.Timestamp(normalized["transaction_month"]),
        time_rebase_lookup,
    )
    return normalized


def _same_building_mask(frame: pd.DataFrame, subject: dict[str, object]) -> pd.Series:
    building_key = subject.get("building_key")
    if building_key is not None and not pd.isna(building_key) and "building_key" in frame.columns:
        return frame["building_key"].eq(building_key)

    block = subject.get("block")
    if block is not None and not pd.isna(block) and "block" in frame.columns:
        return frame["town"].eq(subject.get("town")) & frame["block"].eq(block)

    return pd.Series(False, index=frame.index)


def _distance_to_subject_km(frame: pd.DataFrame, subject: dict[str, object]) -> pd.Series:
    lat = subject.get("building_latitude")
    lon = subject.get("building_longitude")
    if pd.isna(lat) or pd.isna(
            lon) or "building_latitude" not in frame.columns or "building_longitude" not in frame.columns:
        return pd.Series(np.nan, index=frame.index)

    return frame.apply(
        lambda row: haversine_km(lat, lon, row["building_latitude"], row["building_longitude"])
        if pd.notna(row["building_latitude"]) and pd.notna(row["building_longitude"])
        else np.nan,
        axis=1,
    )


def _prepare_comparable_source(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = _augment_regression_features(frame)
    if "min_floor_level" in prepared.columns:
        prepared["floor_level_min"] = prepared["storey_range"].map(_storey_lower_bound).where(
            prepared["storey_range"].notna(),
            pd.to_numeric(prepared["min_floor_level"], errors="coerce"),
        )
    else:
        prepared["floor_level_min"] = prepared["storey_range"].map(_storey_lower_bound)
    return prepared


def _build_nearby_building_lookup(
        frame: pd.DataFrame,
        *,
        radius_km: float = DEFAULT_HDB_COMPARABLE_BUILDING_DISTANCE_KM,
) -> dict[str, dict[str, float]]:
    required = {"building_key", "building_latitude", "building_longitude"}
    if not required.issubset(frame.columns):
        return {}

    buildings = (
        frame.loc[
            frame["building_key"].notna() & frame["building_latitude"].notna() & frame["building_longitude"].notna(),
            ["building_key", "building_latitude", "building_longitude"],
        ]
        .drop_duplicates("building_key")
        .copy()
    )
    if buildings.empty:
        return {}

    coords_radians = np.radians(buildings[["building_latitude", "building_longitude"]].to_numpy(dtype=float))
    neighbors = NearestNeighbors(metric="haversine", algorithm="ball_tree")
    neighbors.fit(coords_radians)
    distances, indices = neighbors.radius_neighbors(coords_radians, radius=radius_km / 6371.0, return_distance=True)

    building_keys = buildings["building_key"].tolist()
    lookup: dict[str, dict[str, float]] = {}
    for source_idx, source_key in enumerate(building_keys):
        lookup[source_key] = {
            building_keys[target_idx]: float(distance * 6371.0)
            for distance, target_idx in zip(distances[source_idx], indices[source_idx])
        }
    return lookup


def _build_comparable_context(frame: pd.DataFrame) -> dict[str, object]:
    prepared_frame = _prepare_comparable_source(frame)
    return {
        "prepared_frame": prepared_frame,
        "nearby_buildings": _build_nearby_building_lookup(
            prepared_frame,
            radius_km=DEFAULT_HDB_COMPARABLE_BUILDING_DISTANCE_KM,
        ),
    }


def _storey_lower_bound(value: object) -> float:
    lower, upper = _parse_storey_bounds(value)
    if pd.isna(lower):
        return np.nan
    return float(lower)


def _resolve_floor_level_min(value: object, fallback: object = np.nan) -> float:
    floor_min = _storey_lower_bound(value)
    if not pd.isna(floor_min):
        return float(floor_min)
    if fallback is None or pd.isna(fallback):
        return np.nan
    try:
        return float(fallback)
    except (TypeError, ValueError):
        return np.nan


def _month_gap_bucket(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"M_{int(max(0, round(float(value))))}"


def _area_bucket(value: object, *, step: float = 10.0) -> str | None:
    if value is None or pd.isna(value):
        return None
    lower = int(np.floor(float(value) / step) * step)
    upper = lower + int(step)
    return f"A_{lower}_{upper}"


def _floor_bucket(value: object, *, step: float = 3.0) -> str | None:
    if value is None or pd.isna(value):
        return None
    lower = int(np.floor(float(value) / step) * step)
    upper = lower + int(step)
    return f"F_{lower}_{upper}"


def extract_comparable_transactions(
        frame: pd.DataFrame,
        subject: dict[str, object] | None = None,
        min_rows: int = 2,
        comparable_context: dict[str, object] | None = None,
        month_base: pd.DataFrame | None = None,
) -> pd.DataFrame:
    subject = _normalize_subject(subject or TARGET_TRANSACTION)
    subject_month = pd.Timestamp(subject["transaction_month"])
    if month_base is not None:
        base = month_base.copy()
    else:
        prepared_frame = (
            comparable_context.get("prepared_frame")
            if comparable_context is not None and "prepared_frame" in comparable_context
            else _prepare_comparable_source(frame)
        )
        base = prepared_frame.loc[
            (prepared_frame["transaction_month"] < subject_month)
            & (prepared_frame["transaction_month"] >= subject_month - pd.DateOffset(months=36))
            ].copy()
    subject_year = int(subject_month.year)
    subject_month_num = int(subject_month.month)
    base["months_to_subject"] = (
            (subject_year - base["transaction_month"].dt.year.astype(int)) * 12
            + (subject_month_num - base["transaction_month"].dt.month.astype(int))
    ).astype(int)
    base["same_building"] = _same_building_mask(base, subject)
    subject_floor_level = _resolve_floor_level_min(
        subject.get("storey_range"),
        subject.get("min_floor_level"),
    )
    base["floor_gap"] = (base["floor_level_min"] - subject_floor_level).abs()
    base["size_gap"] = (base["floor_area_sqm"].astype(float) - float(subject["floor_area_sqm"])).abs()
    base["size_ratio_gap"] = (
            base["floor_area_sqm"].astype(float) / float(subject["floor_area_sqm"]) - 1.0
    ).abs()
    base["same_flat_type"] = base["flat_type"].eq(subject.get("flat_type"))
    base["same_flat_model"] = base["flat_model"].eq(subject.get("flat_model"))

    best_comparables = pd.DataFrame(columns=base.columns.tolist())
    selected_stage = "none"
    month_windows = [1, 3, 12, 36]

    if pd.isna(subject.get("building_latitude")) or pd.isna(subject.get("building_longitude")):
        LOGGER.info("Comparable search skipped because subject building coordinates are unavailable")
        return pd.DataFrame(columns=base.columns.tolist())

    nearby_lookup = comparable_context.get("nearby_buildings", {}) if comparable_context else {}
    subject_building_key = subject.get("building_key")
    if subject_building_key is not None and not pd.isna(subject_building_key) and subject_building_key in nearby_lookup:
        distance_map = nearby_lookup[subject_building_key]
        nearby_building_keys = set(distance_map.keys())
        base = base.loc[base["building_key"].isin(nearby_building_keys)].copy()
        if base.empty:
            LOGGER.info("No nearby-building transaction pool found for subject building")
            return pd.DataFrame(columns=base.columns.tolist())
        base["distance_to_subject_km"] = base["building_key"].map(distance_map)
    else:
        base["distance_to_subject_km"] = _distance_to_subject_km(base, subject)
        base = base.loc[
            base["distance_to_subject_km"].isna()
            | base["distance_to_subject_km"].le(DEFAULT_HDB_COMPARABLE_BUILDING_DISTANCE_KM)
            ].copy()
        if base.empty:
            LOGGER.info("No building-based comparable set found; returning no comparables")
            return pd.DataFrame(columns=base.columns.tolist())

    subject_flat_type = subject.get("flat_type")
    if subject_flat_type is not None and not pd.isna(subject_flat_type):
        base = base.loc[base["flat_type"].eq(subject_flat_type)].copy()
    if base.empty:
        return pd.DataFrame(columns=base.columns.tolist())

    subject_area = subject.get("floor_area_sqm")
    if subject_area is not None and not pd.isna(subject_area) and float(subject_area) > 0:
        base = base.loc[base["size_ratio_gap"].lt(DEFAULT_HDB_COMPARABLE_AREA_MAX_DIFF)].copy()
    if base.empty:
        return pd.DataFrame(columns=base.columns.tolist())

    subject_lease_year = subject.get("lease_commence_date")
    if (
            subject_lease_year is not None
            and not pd.isna(subject_lease_year)
            and "lease_commence_date" in base.columns
    ):
        lease_gap = (
                pd.to_numeric(base["lease_commence_date"], errors="coerce") - float(subject_lease_year)
        ).abs()
        base = base.loc[lease_gap.le(DEFAULT_HDB_COMPARABLE_AGE_YEAR_GAP)].copy()
    if base.empty:
        return pd.DataFrame(columns=base.columns.tolist())

    for month_window in month_windows:
        month_stage = base.loc[base["months_to_subject"].between(0, month_window)].copy()
        if month_stage.empty:
            continue
        stage = month_stage.loc[month_stage["floor_gap"].le(6.0)].copy()
        if len(stage) < min_rows:
            continue
        stage_name = (
            f"within_{month_window}m_local_pool_"
            f"floor6_area{int(DEFAULT_HDB_COMPARABLE_AREA_MAX_DIFF * 100)}_"
            f"age{int(DEFAULT_HDB_COMPARABLE_AGE_YEAR_GAP)}_"
            f"dist{DEFAULT_HDB_COMPARABLE_BUILDING_DISTANCE_KM:g}km"
        )
        stage["search_stage"] = stage_name
        best_comparables = stage
        if not best_comparables.empty:
            break

    if best_comparables.empty:
        LOGGER.info("No building-based comparable set found; returning no comparables")
        return pd.DataFrame(columns=base.columns.tolist())

    comparables = best_comparables.sort_values(
        ["same_building", "same_flat_model", "floor_gap", "size_gap", "transaction_month"],
        ascending=[False, False, True, True, False],
    ).copy()
    # LOGGER.info(
    #     "Comparable hierarchy selected stage=%s with %d rows",
    #     selected_stage,
    #     len(comparables),
    # )
    comparables["is_subject_transaction"] = False
    columns = [
        "month",
        "transaction_month",
        "town",
        "block",
        "street_name",
        "building_key",
        "flat_type",
        "flat_model",
        "storey_range",
        "floor_area_sqm",
        "flat_age",
        "lease_commence_date",
        "remaining_lease_effective",
        "resale_price",
        "distance_to_subject_km",
        "same_building",
        "same_flat_model",
        "floor_level_min",
        "floor_gap",
        "size_gap",
        "search_stage",
        "is_subject_transaction",
    ]
    for optional in QUESTION_B_OPTIONAL_FEATURES:
        if optional in comparables.columns and optional not in columns:
            columns.append(optional)
    return comparables.loc[:, [column for column in columns if column in comparables.columns]]


def _build_comparable_adjustment_pool(
        frame: pd.DataFrame,
        subject: dict[str, object],
        *,
        cutoff_month: pd.Timestamp | None = None,
        comparable_context: dict[str, object] | None = None,
) -> pd.DataFrame:
    subject = _normalize_subject(subject)
    effective_cutoff = pd.Timestamp(cutoff_month or subject["transaction_month"])
    prepared_frame = (
        comparable_context.get("prepared_frame")
        if comparable_context is not None and "prepared_frame" in comparable_context
        else _prepare_comparable_source(frame)
    )
    pool = prepared_frame.loc[prepared_frame["transaction_month"] < effective_cutoff].copy()
    pool = pool.dropna(subset=["resale_price", "transaction_month", "floor_area_sqm", "floor_level_min"]).copy()
    return pool


def _fit_comparable_adjustment_model(
        adjustment_pool: pd.DataFrame,
        comparables: pd.DataFrame,
        subject: dict[str, object],
        *,
        rebase_time_index_to_1990: bool = False,
) -> tuple[pd.DataFrame, dict[str, float]]:
    pool = adjustment_pool.copy()
    adjusted = comparables.copy()
    if "min_floor_level" in adjusted.columns:
        adjusted["floor_level_min"] = adjusted["storey_range"].map(_storey_lower_bound).where(
            adjusted["storey_range"].notna(),
            pd.to_numeric(adjusted["min_floor_level"], errors="coerce"),
        )
    else:
        adjusted["floor_level_min"] = adjusted["storey_range"].map(_storey_lower_bound)
    origin_month = pd.Timestamp("1990-01-01") if rebase_time_index_to_1990 else pool["transaction_month"].min()
    pool["months_index"] = (
                                   (pool["transaction_month"] - origin_month).dt.days.astype(float) / 30.0
                           ) + 1.0
    adjusted["months_index"] = (
                                       (adjusted["transaction_month"] - origin_month).dt.days.astype(float) / 30.0
                               ) + 1.0
    subject_month_index = float(
        ((pd.Timestamp(subject["transaction_month"]) - origin_month).days / 30.0) + 1.0
    )
    pool["months_from_subject"] = (subject_month_index - pool["months_index"]).abs()
    pool = pool.loc[pool["months_from_subject"].le(DEFAULT_COMPARABLE_ADJUSTMENT_MAX_MONTH_GAP)].copy()
    subject_floor_min = _resolve_floor_level_min(
        subject.get("storey_range"),
        subject.get("min_floor_level"),
    )
    adjusted["months_from_subject"] = (subject_month_index - adjusted["months_index"]).abs()
    subject_month_gap = 0.0

    if rebase_time_index_to_1990:
        pool["time_bucket"] = pool["months_index"].map(_month_gap_bucket)
        adjusted["time_bucket"] = adjusted["months_index"].map(_month_gap_bucket)
        subject_time_bucket = _month_gap_bucket(subject_month_index)
    else:
        pool["time_bucket"] = pool["months_from_subject"].map(_month_gap_bucket)
        adjusted["time_bucket"] = adjusted["months_from_subject"].map(_month_gap_bucket)
        subject_time_bucket = _month_gap_bucket(0.0)
    pool["area_bucket"] = pool["floor_area_sqm"].map(_area_bucket)
    adjusted["area_bucket"] = adjusted["floor_area_sqm"].map(_area_bucket)
    pool["floor_bucket"] = pool["floor_level_min"].map(_floor_bucket)
    adjusted["floor_bucket"] = adjusted["floor_level_min"].map(_floor_bucket)

    bucket_features = ["time_bucket", "area_bucket", "floor_bucket"]
    extra_numeric = [
        "flat_age",
        "remaining_lease_effective",
        *[feature for feature in QUESTION_B_OPTIONAL_FEATURES if feature in pool.columns],
    ]
    numeric_features: list[str] = []
    for feature in extra_numeric:
        if feature in pool.columns and pool[feature].notna().sum() >= max(20, len(pool) // 20):
            numeric_features.append(feature)
    categorical_features = [
        feature
        for feature in ["town", "flat_type", "flat_model", *bucket_features]
        if feature in pool.columns and pool[feature].nunique(dropna=True) > 1
    ]

    model_frame = pool.copy()
    for feature in numeric_features:
        model_frame[feature] = pd.to_numeric(model_frame[feature], errors="coerce")
    model_frame["log_resale_price"] = np.log(model_frame["resale_price"].astype(float))
    model_frame = model_frame.dropna(subset=numeric_features + categorical_features + ["log_resale_price"]).copy()

    if len(model_frame) < 3:
        adjusted["adjusted_price_to_subject"] = adjusted["resale_price"].astype(float)
        adjusted["time_adjustment"] = 0.0
        adjusted["size_adjustment"] = 0.0
        adjusted["floor_adjustment"] = 0.0
        adjusted["other_adjustment"] = 0.0
        return adjusted, {
            "time_coefficient": 0.0,
            "size_coefficient": 0.0,
            "floor_coefficient": 0.0,
        }

    design = pd.get_dummies(
        model_frame[numeric_features + categorical_features],
        dummy_na=False,
        drop_first=False,
    ).fillna(0.0)
    regression = LinearRegression()
    regression.fit(design, model_frame["log_resale_price"])
    numeric_fallbacks = {feature: float(model_frame[feature].median()) for feature in numeric_features}
    categorical_fallbacks = {
        feature: (
            model_frame[feature].mode(dropna=True).iloc[0]
            if feature in model_frame.columns and not model_frame[feature].mode(dropna=True).empty
            else None
        )
        for feature in categorical_features
    }

    subject_row = {}
    subject_row["time_bucket"] = subject_time_bucket
    subject_row["area_bucket"] = _area_bucket(subject.get("floor_area_sqm"))
    subject_row["floor_bucket"] = _floor_bucket(subject_floor_min)
    for feature in numeric_features:
        value = subject.get(feature, np.nan)
        if value is None or pd.isna(value):
            value = numeric_fallbacks.get(feature, 0.0)
        subject_row[feature] = float(value) if value is not None and not pd.isna(value) else np.nan
    for feature in categorical_features:
        value = subject_row.get(feature, subject.get(feature))
        subject_row[feature] = categorical_fallbacks.get(feature) if value is None or pd.isna(value) else value
    subject_design = pd.get_dummies(pd.DataFrame([subject_row]), dummy_na=False, drop_first=False).reindex(
        columns=design.columns,
        fill_value=0.0,
    ).fillna(0.0)

    adjusted_model = adjusted.copy()
    for feature in numeric_features:
        adjusted_model[feature] = pd.to_numeric(adjusted_model[feature], errors="coerce")
    for feature in categorical_features:
        if feature not in adjusted_model.columns:
            adjusted_model[feature] = np.nan
    adjusted_design = pd.get_dummies(
        adjusted_model[numeric_features + categorical_features],
        dummy_na=False,
        drop_first=False,
    ).reindex(columns=design.columns, fill_value=0.0).fillna(0.0)

    subject_pred_log = float(regression.predict(subject_design)[0])
    comparable_pred_log = regression.predict(adjusted_design)
    adjusted["adjusted_price_to_subject"] = adjusted["resale_price"].astype(float) * np.exp(
        subject_pred_log - comparable_pred_log
    )

    def _swap_bucket_prediction(bucket_feature: str) -> np.ndarray:
        cf_design = adjusted_design.astype(float).copy()
        bucket_columns = [column for column in design.columns if column.startswith(f"{bucket_feature}_")]
        if bucket_columns:
            cf_design.loc[:, bucket_columns] = subject_design.loc[0, bucket_columns].to_numpy()
        return regression.predict(cf_design)

    time_pred_log = _swap_bucket_prediction("time_bucket")
    size_pred_log = _swap_bucket_prediction("area_bucket")
    floor_pred_log = _swap_bucket_prediction("floor_bucket")
    adjusted["time_adjustment"] = adjusted["resale_price"].astype(float) * (
            np.exp(time_pred_log - comparable_pred_log) - 1.0
    )
    adjusted["size_adjustment"] = adjusted["resale_price"].astype(float) * (
            np.exp(size_pred_log - comparable_pred_log) - 1.0
    )
    adjusted["floor_adjustment"] = adjusted["resale_price"].astype(float) * (
            np.exp(floor_pred_log - comparable_pred_log) - 1.0
    )
    adjusted["other_adjustment"] = (
            adjusted["adjusted_price_to_subject"]
            - adjusted["resale_price"].astype(float)
            - adjusted["time_adjustment"]
            - adjusted["size_adjustment"]
            - adjusted["floor_adjustment"]
    )
    return adjusted, {
        "time_coefficient": 0.0,
        "size_coefficient": 0.0,
        "floor_coefficient": 0.0,
    }


def estimate_from_comparables(
        subject: dict[str, object],
        frame: pd.DataFrame,
        adjustment_config: dict[str, float] | None = None,
        *,
        cutoff_month: pd.Timestamp | None = None,
        comparable_context: dict[str, object] | None = None,
        adjustment_pool: pd.DataFrame | None = None,
        month_base: pd.DataFrame | None = None,
) -> dict[str, object]:
    subject = _normalize_subject(subject)
    comparables = extract_comparable_transactions(
        frame,
        subject=subject,
        comparable_context=comparable_context,
        month_base=month_base,
    )
    if adjustment_pool is None:
        adjustment_pool = _build_comparable_adjustment_pool(
            frame,
            subject,
            cutoff_month=cutoff_month,
            comparable_context=comparable_context,
        )
    # LOGGER.info("Comparable search returned %d reference transactions", len(comparables))
    # LOGGER.info("Comparable adjustment pool contains %d historical transactions", len(adjustment_pool))
    if comparables.empty:
        return {
            "comparables_frame": comparables,
            "comparable_count": 0,
            "estimate": np.nan,
            "time_coefficient": 0.0,
            "size_coefficient": 0.0,
            "floor_coefficient": 0.0,
        }

    adjusted, coefficients = _fit_comparable_adjustment_model(
        adjustment_pool,
        comparables,
        subject,
        rebase_time_index_to_1990=bool((adjustment_config or {}).get("rebase_time_index_to_1990", False)),
    )
    subject_ordinal = float(pd.Timestamp(subject["transaction_month"]).toordinal())
    adjusted["months_to_subject"] = (
            (subject_ordinal - adjusted["transaction_month"].map(pd.Timestamp.toordinal).astype(float)) / 30.0
    )
    if adjustment_config:
        adjusted["time_adjustment"] *= float(adjustment_config.get("time_weight", 1.0))
        adjusted["size_adjustment"] *= float(adjustment_config.get("floor_area_weight", 1.0))
        adjusted["floor_adjustment"] *= float(adjustment_config.get("floor_weight", 1.0))
        adjusted["adjusted_price_to_subject"] = (
                adjusted["resale_price"].astype(float)
                + adjusted["time_adjustment"]
                + adjusted["size_adjustment"]
                + adjusted["floor_adjustment"]
                + adjusted["other_adjustment"]
        )

    weights = 1.0 / (1.0 + adjusted["months_to_subject"].clip(lower=0.0))
    estimate = float(np.average(adjusted["adjusted_price_to_subject"], weights=weights))
    # LOGGER.info(
    #     "Comparable adjustment model complete | estimate=%.0f time_coef=%.4f size_coef=%.4f floor_coef=%.4f",
    #     estimate,
    #     coefficients["time_coefficient"],
    #     coefficients["size_coefficient"],
    #     coefficients["floor_coefficient"],
    # )
    return {
        "comparables_frame": adjusted,
        "comparable_count": int(len(adjusted)),
        "estimate": estimate,
        "comparable_reference_column": "adjusted_price_to_subject" if "adjusted_price_to_subject" in adjusted.columns else "resale_price",
        "time_coefficient": coefficients["time_coefficient"],
        "size_coefficient": coefficients["size_coefficient"],
        "floor_coefficient": coefficients["floor_coefficient"],
    }


def blend_estimates(
        ml_result: float,
        comps_result: dict[str, object],
        weights: dict[str, float] | None = None,
) -> dict[str, float]:
    weights = weights or DEFAULT_BLEND_WEIGHTS
    comps_estimate = float(comps_result.get("estimate", np.nan))
    if pd.isna(comps_estimate):
        return {"ml_weight": 1.0, "comps_weight": 0.0, "blended_estimate": float(ml_result)}
    ml_weight = float(weights["ml"])
    comps_weight = float(weights["comps"])
    blended = ml_result * ml_weight + comps_estimate * comps_weight
    return {
        "ml_weight": ml_weight,
        "comps_weight": comps_weight,
        "blended_estimate": float(blended),
    }


def _is_comparable_eligible(
        subject: dict[str, object],
        *,
        comparable_context: dict[str, object] | None = None,
        month_base: pd.DataFrame | None = None,
        min_rows: int = 2,
) -> tuple[bool, int]:
    subject_building_key = subject.get("building_key")
    subject_lat = subject.get("building_latitude")
    subject_lon = subject.get("building_longitude")
    if (
            subject_building_key is None
            or pd.isna(subject_building_key)
            or subject_lat is None
            or pd.isna(subject_lat)
            or subject_lon is None
            or pd.isna(subject_lon)
            or month_base is None
    ):
        return False, 0

    nearby_lookup = comparable_context.get("nearby_buildings", {}) if comparable_context else {}
    if subject_building_key not in nearby_lookup:
        return False, 0

    local_pool = month_base.loc[month_base["building_key"].isin(set(nearby_lookup[subject_building_key].keys()))]
    return bool(len(local_pool) >= min_rows), int(len(local_pool))


def _evaluate_blended_holdout(
        evaluation_rows: pd.DataFrame,
        *,
        full_pipeline: Pipeline,
        features: list[str],
        source_frame: pd.DataFrame,
        comparable_context: dict[str, object] | None = None,
        baseline_only: bool,
        blend_weights: dict[str, float] | None = None,
        adjustment_config: dict[str, float] | None = None,
        eval_sample_size: int | None = None,
) -> dict[str, float | int]:
    if evaluation_rows.empty:
        return {
            "mae": np.nan,
            "mape": np.nan,
            "rmse": np.nan,
            "r2": np.nan,
            "sample_size": 0,
            "ml_mae": np.nan,
            "ml_mape": np.nan,
            "ml_rmse": np.nan,
            "ml_r2": np.nan,
            "ml_sample_count": 0,
            "blended_mae": np.nan,
            "blended_mape": np.nan,
            "blended_rmse": np.nan,
            "blended_r2": np.nan,
            "blended_sample_count": 0,
            "comparable_coverage_rate": 0.0,
            "comparable_eligible_count": 0,
        }

    grouped_rows = evaluation_rows.copy()
    if eval_sample_size is not None and eval_sample_size > 0 and len(grouped_rows) > eval_sample_size:
        grouped_rows = grouped_rows.sample(eval_sample_size, random_state=RANDOM_STATE).copy()
    grouped_rows["_ml_prediction"] = _recover_resale_price(
        full_pipeline.predict(grouped_rows[features]),
        grouped_rows["floor_area_sqm"].astype(float).to_numpy(),
        grouped_rows["time_rebase_factor_1990"].astype(float).to_numpy()
        if "time_rebase_factor_1990" in grouped_rows.columns
        else None,
    )

    if baseline_only:
        metrics = evaluate_predictions(
            grouped_rows["resale_price"].astype(float).to_numpy(),
            grouped_rows["_ml_prediction"].astype(float).to_numpy(),
        )
        predictions_frame = grouped_rows[
            [column for column in ["transaction_month", "building_key", "flat_type", "town", "resale_price"] if
             column in grouped_rows.columns]
        ].copy()
        predictions_frame["ml_prediction"] = grouped_rows["_ml_prediction"].astype(float)
        predictions_frame["comps_estimate"] = np.nan
        predictions_frame["blended_prediction"] = grouped_rows["_ml_prediction"].astype(float)
        predictions_frame["ml_weight"] = 1.0
        predictions_frame["comps_weight"] = 0.0
        predictions_frame["comparable_eligible"] = False
        predictions_frame["comparable_count"] = 0
        return {
            **metrics,
            "sample_size": metrics["sample_count"],
            "ml_mae": metrics["mae"],
            "ml_mape": metrics["mape"],
            "ml_rmse": metrics["rmse"],
            "ml_r2": metrics["r2"],
            "ml_sample_count": metrics["sample_count"],
            "blended_mae": np.nan,
            "blended_mape": np.nan,
            "blended_rmse": np.nan,
            "blended_r2": np.nan,
            "blended_sample_count": 0,
            "comparable_coverage_rate": 0.0,
            "comparable_eligible_count": 0,
            "predictions_frame": predictions_frame,
        }

    group_cols = ["transaction_month", "building_key", "flat_type"]
    grouped = grouped_rows.groupby(group_cols, dropna=False, sort=False)

    month_cache: dict[pd.Timestamp, dict[str, pd.DataFrame]] = {}
    prepared_frame = (
        comparable_context.get("prepared_frame")
        if comparable_context is not None and "prepared_frame" in comparable_context
        else _prepare_comparable_source(source_frame)
    )
    for month in pd.to_datetime(grouped_rows["transaction_month"]).drop_duplicates().tolist():
        cutoff_month = pd.Timestamp(month)
        month_cache[cutoff_month] = {
            "adjustment_pool": prepared_frame.loc[prepared_frame["transaction_month"] < cutoff_month]
            .dropna(subset=["resale_price", "transaction_month", "floor_area_sqm", "floor_level_min"])
            .copy(),
            "month_base": prepared_frame.loc[
                (prepared_frame["transaction_month"] < cutoff_month)
                & (prepared_frame["transaction_month"] >= cutoff_month - pd.DateOffset(months=36))
                ].copy(),
        }

    def _score_group(group_frame: pd.DataFrame) -> tuple[
        list[float], list[float], list[float], list[float], list[dict[str, object]]]:
        cutoff_month = pd.Timestamp(group_frame["transaction_month"].iloc[0])
        shared_adjustment_pool = month_cache[cutoff_month]["adjustment_pool"]
        month_base = month_cache[cutoff_month]["month_base"]
        group_actual: list[float] = []
        group_ml_predictions: list[float] = []
        group_blended_actual: list[float] = []
        group_blended_predictions: list[float] = []
        group_rows: list[dict[str, object]] = []
        for _, row in group_frame.iterrows():
            subject = row.to_dict()
            ml_prediction = float(row["_ml_prediction"])
            group_actual.append(float(subject["resale_price"]))
            group_ml_predictions.append(float(ml_prediction))
            eligible, _ = _is_comparable_eligible(
                subject,
                comparable_context=comparable_context,
                month_base=month_base,
            )
            if not eligible:
                group_rows.append(
                    {
                        "transaction_month": subject.get("transaction_month"),
                        "building_key": subject.get("building_key"),
                        "flat_type": subject.get("flat_type"),
                        "town": subject.get("town"),
                        "actual_price": float(subject["resale_price"]),
                        "ml_prediction": ml_prediction,
                        "comps_estimate": np.nan,
                        "blended_prediction": np.nan,
                        "ml_weight": np.nan,
                        "comps_weight": np.nan,
                        "comparable_eligible": False,
                        "comparable_count": 0,
                    }
                )
                continue
            comps_result = estimate_from_comparables(
                subject,
                source_frame,
                adjustment_config=adjustment_config,
                cutoff_month=cutoff_month,
                comparable_context=comparable_context,
                adjustment_pool=shared_adjustment_pool,
                month_base=month_base,
            )
            if int(comps_result.get("comparable_count", 0)) < 2:
                group_rows.append(
                    {
                        "transaction_month": subject.get("transaction_month"),
                        "building_key": subject.get("building_key"),
                        "flat_type": subject.get("flat_type"),
                        "town": subject.get("town"),
                        "actual_price": float(subject["resale_price"]),
                        "ml_prediction": ml_prediction,
                        "comps_estimate": np.nan,
                        "blended_prediction": np.nan,
                        "ml_weight": np.nan,
                        "comps_weight": np.nan,
                        "comparable_eligible": False,
                        "comparable_count": int(comps_result.get("comparable_count", 0)),
                    }
                )
                continue
            blend_result = blend_estimates(
                ml_prediction,
                comps_result,
                weights=blend_weights,
            )
            blended_prediction = blend_result["blended_estimate"]
            group_blended_actual.append(float(subject["resale_price"]))
            group_blended_predictions.append(float(blended_prediction))
            group_rows.append(
                {
                    "transaction_month": subject.get("transaction_month"),
                    "building_key": subject.get("building_key"),
                    "flat_type": subject.get("flat_type"),
                    "town": subject.get("town"),
                    "actual_price": float(subject["resale_price"]),
                    "ml_prediction": ml_prediction,
                    "comps_estimate": float(comps_result.get("estimate", np.nan)),
                    "blended_prediction": float(blended_prediction),
                    "ml_weight": float(blend_result["ml_weight"]),
                    "comps_weight": float(blend_result["comps_weight"]),
                    "comparable_eligible": True,
                    "comparable_count": int(comps_result.get("comparable_count", 0)),
                }
            )
        return group_actual, group_ml_predictions, group_blended_actual, group_blended_predictions, group_rows

    actual_prices: list[float] = []
    ml_predictions: list[float] = []
    blended_actual_prices: list[float] = []
    blended_predictions: list[float] = []
    prediction_rows: list[dict[str, object]] = []
    grouped_items = [group_frame.copy() for _, group_frame in grouped]
    max_workers = min(DEFAULT_COMPARABLE_EVAL_WORKERS, max(1, len(grouped_items)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        iterator = executor.map(_score_group, grouped_items)
        for group_actual, group_ml_predictions, group_blended_actual, group_blended_predictions, group_rows in tqdm(
                iterator,
                total=len(grouped_items),
                desc="Question B blended evaluation",
                disable=len(grouped_items) == 0,
        ):
            actual_prices.extend(group_actual)
            ml_predictions.extend(group_ml_predictions)
            blended_actual_prices.extend(group_blended_actual)
            blended_predictions.extend(group_blended_predictions)
            prediction_rows.extend(group_rows)

    ml_metrics = evaluate_predictions(
        np.asarray(actual_prices, dtype=float),
        np.asarray(ml_predictions, dtype=float),
    )
    if blended_predictions:
        blended_metrics = evaluate_predictions(
            np.asarray(blended_actual_prices, dtype=float),
            np.asarray(blended_predictions, dtype=float),
        )
    else:
        blended_metrics = {"mae": np.nan, "mape": np.nan, "rmse": np.nan, "r2": np.nan, "sample_count": 0}
    coverage_rate = (
        float(blended_metrics["sample_count"]) / float(ml_metrics["sample_count"])
        if ml_metrics["sample_count"]
        else 0.0
    )
    return {
        "mae": blended_metrics["mae"],
        "mape": blended_metrics["mape"],
        "rmse": blended_metrics["rmse"],
        "r2": blended_metrics["r2"],
        "sample_size": blended_metrics["sample_count"],
        "ml_mae": ml_metrics["mae"],
        "ml_mape": ml_metrics["mape"],
        "ml_rmse": ml_metrics["rmse"],
        "ml_r2": ml_metrics["r2"],
        "ml_sample_count": ml_metrics["sample_count"],
        "blended_mae": blended_metrics["mae"],
        "blended_mape": blended_metrics["mape"],
        "blended_rmse": blended_metrics["rmse"],
        "blended_r2": blended_metrics["r2"],
        "blended_sample_count": blended_metrics["sample_count"],
        "comparable_coverage_rate": coverage_rate,
        "comparable_eligible_count": blended_metrics["sample_count"],
        "predictions_frame": pd.DataFrame(prediction_rows),
    }


def _confidence_label(z_score: float, comparable_count: int) -> str:
    if abs(z_score) <= 1 and comparable_count >= 10:
        return "High"
    if abs(z_score) <= 1.5 and comparable_count >= 6:
        return "Moderate"
    return "Low"


def _comparison_percentile(observed: float, reference: pd.Series) -> float | None:
    cleaned = pd.to_numeric(reference, errors="coerce").dropna()
    if cleaned.empty or pd.isna(observed):
        return None
    return float((cleaned.le(float(observed)).mean()))


def _build_question_b_local_distribution(
        frame: pd.DataFrame,
        *,
        subject: dict[str, object],
        window_months: int = DEFAULT_QB_LOCAL_WINDOW_MONTHS,
) -> dict[str, object]:
    subject_month = pd.Timestamp(subject["transaction_month"])
    subject_area = pd.to_numeric(pd.Series([subject.get("floor_area_sqm")]), errors="coerce").iloc[0]
    subject_age = pd.to_numeric(pd.Series([subject.get("lease_commence_date")]), errors="coerce").iloc[0]

    sample = frame.copy()
    if "transaction_month" not in sample.columns:
        return {
            "frame": pd.DataFrame(),
            "sample_count": 0,
            "p025": np.nan,
            "p25": np.nan,
            "p50": np.nan,
            "p75": np.nan,
            "p975": np.nan,
            "percentile": None,
            "inside_95_range": None,
            "modified_z_score": np.nan,
            "outlier_flag": None,
        }

    sample["transaction_month"] = pd.to_datetime(sample["transaction_month"])
    sample = sample.loc[
        sample["transaction_month"].between(
            subject_month - pd.DateOffset(months=window_months),
            subject_month + pd.DateOffset(months=window_months),
        )
    ].copy()

    for column, subject_value in [("town", subject.get("town")), ("flat_type", subject.get("flat_type"))]:
        if subject_value is not None and not pd.isna(subject_value) and column in sample.columns:
            sample = sample.loc[sample[column].eq(subject_value)].copy()

    if not pd.isna(subject_area) and "floor_area_sqm" in sample.columns and subject_area > 0:
        area_ratio_gap = (
                                 pd.to_numeric(sample["floor_area_sqm"], errors="coerce") - float(subject_area)
                         ).abs() / float(subject_area)
        sample = sample.loc[area_ratio_gap.le(DEFAULT_QB_LOCAL_AREA_MAX_DIFF)].copy()

    if not pd.isna(subject_age) and "lease_commence_date" in sample.columns:
        age_gap = (
                pd.to_numeric(sample["lease_commence_date"], errors="coerce") - float(subject_age)
        ).abs()
        sample = sample.loc[age_gap.le(DEFAULT_QB_LOCAL_AGE_YEAR_GAP)].copy()

    sample["resale_price"] = pd.to_numeric(sample["resale_price"], errors="coerce")
    sample = sample.loc[sample["resale_price"].notna()].copy()
    prices = sample["resale_price"]
    actual_price = pd.to_numeric(pd.Series([subject.get("resale_price")]), errors="coerce").iloc[0]

    if sample.empty:
        return {
            "frame": sample,
            "sample_count": 0,
            "p025": np.nan,
            "p25": np.nan,
            "p50": np.nan,
            "p75": np.nan,
            "p975": np.nan,
            "percentile": None,
            "inside_95_range": None,
            "modified_z_score": np.nan,
            "outlier_flag": None,
        }

    median_price = float(prices.median())
    mad = float(np.median(np.abs(prices - median_price)))
    modified_z_score = (
        float(0.6745 * (actual_price - median_price) / mad)
        if not pd.isna(actual_price) and mad > 0
        else np.nan
    )
    p025 = float(prices.quantile(0.025))
    p975 = float(prices.quantile(0.975))
    inside_95_range = None if pd.isna(actual_price) else bool(p025 <= actual_price <= p975)
    percentile = _comparison_percentile(float(actual_price), prices) if not pd.isna(actual_price) else None
    outlier_flag = None if pd.isna(modified_z_score) else bool(abs(modified_z_score) > 3.5)

    return {
        "frame": sample.sort_values("transaction_month").copy(),
        "sample_count": int(len(sample)),
        "p025": p025,
        "p25": float(prices.quantile(0.25)),
        "p50": median_price,
        "p75": float(prices.quantile(0.75)),
        "p975": p975,
        "percentile": percentile,
        "inside_95_range": inside_95_range,
        "modified_z_score": modified_z_score,
        "outlier_flag": outlier_flag,
    }


def _build_question_b_confidence(
        *,
        model_mape: float | None,
        model_sample_count: int,
        comparable_count: int,
        feature_source: str,
        inside_model_interval: bool | None,
) -> tuple[str, list[str], list[str]]:
    positive: list[str] = []
    negative: list[str] = []

    if model_mape is not None and not pd.isna(model_mape):
        if model_mape <= 0.06:
            positive.append(f"Holdout MAPE is low at {model_mape:.1%}.")
        elif model_mape <= 0.09:
            positive.append(f"Holdout MAPE is reasonable at {model_mape:.1%}.")
        else:
            negative.append(f"Holdout MAPE is relatively high at {model_mape:.1%}.")

    if model_sample_count >= 1000:
        positive.append(f"The validation set is reasonably large with {model_sample_count:,} holdout transactions.")
    elif model_sample_count < 250:
        negative.append(f"The validation set is small with only {model_sample_count:,} holdout transactions.")

    if comparable_count >= 6:
        positive.append(f"There are {comparable_count} comparable transactions supporting the assessment.")
    elif comparable_count >= 2:
        positive.append(f"There are {comparable_count} comparable transactions for a secondary reasonableness check.")
        negative.append("Comparable support is still limited, so the secondary range is less stable.")
    else:
        negative.append("Comparable support is limited, so the secondary range check is weak.")

    if feature_source == "building_exact":
        positive.append("The subject uses exact building-level features.")
    elif "proxy" in str(feature_source):
        negative.append("The subject relies on proxy location features rather than an exact building match.")

    negative.append("Unobserved factors such as renovation quality, facing, and view are not captured.")

    if inside_model_interval is False:
        negative.append("The observed transaction falls outside the model-based 95% validation range.")

    if len(positive) >= 3 and len(negative) <= 2:
        level = "High"
    elif len(positive) >= 2:
        level = "Moderate"
    else:
        level = "Low"

    return level, positive[:3], negative[:3]


def _build_question_b_final_assessment(
        *,
        actual_price: float,
        expected_price: float,
        inside_model_interval: bool | None,
        inside_comparable_range: bool | None,
        comparable_percentile: float | None,
) -> str:
    if pd.isna(actual_price):
        return "No observed transaction price supplied for the subject."

    if actual_price > expected_price:
        direction = "above"
    elif actual_price < expected_price:
        direction = "below"
    else:
        direction = "in line with"

    if inside_model_interval is True and (inside_comparable_range is True or inside_comparable_range is None):
        return f"The transaction appears reasonable: the observed price is {direction} the expected price but remains within the expected range."
    if inside_model_interval is False and inside_comparable_range is True:
        return f"The transaction looks somewhat {direction} the model expectation, but comparable evidence suggests it is still within a plausible local range."
    if inside_model_interval is False and inside_comparable_range is False:
        if comparable_percentile is not None and comparable_percentile >= 0.9:
            return "The transaction appears overpriced: it is above both the model-based range and the upper end of comparable transactions."
        if comparable_percentile is not None and comparable_percentile <= 0.1:
            return "The transaction appears underpriced: it is below both the model-based range and the lower end of comparable transactions."
        return "The transaction appears mispriced relative to both the model-based range and comparable evidence."
    if inside_model_interval is True and inside_comparable_range is False:
        return "The transaction is within the model-based range, but comparable evidence suggests it sits at an extreme of the local market."
    return f"The transaction is {direction} the expected price, with limited secondary comparable support."


def _subject_row_for_reference(subject: dict[str, object], actual_price: float | None) -> pd.DataFrame:
    subject = _normalize_subject(subject)
    row = {
        "month": subject["month"],
        "transaction_month": subject["transaction_month"],
        "town": subject["town"],
        "block": subject.get("block"),
        "street_name": subject.get("street_name"),
        "building_key": subject.get("building_key"),
        "flat_type": subject["flat_type"],
        "flat_model": subject["flat_model"],
        "storey_range": subject["storey_range"],
        "floor_area_sqm": subject["floor_area_sqm"],
        "flat_age": subject["flat_age"],
        "lease_commence_date": subject.get("lease_commence_date"),
        "remaining_lease_effective": subject["remaining_lease_effective"],
        "resale_price": actual_price,
        "distance_to_subject_km": 0.0,
        "is_subject_transaction": True,
    }
    for optional in QUESTION_B_OPTIONAL_FEATURES:
        if optional in subject:
            row[optional] = subject[optional]
    return pd.DataFrame([row])


def score_transaction(
        subject: dict[str, object],
        frame: pd.DataFrame,
        options: dict[str, object] | None = None,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        tune_catboost: bool = False,
        catboost_tuning_iterations: int = DEFAULT_CATBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    options = options or {}
    LOGGER.info("Question B start")
    normalized_subject = _normalize_subject(subject)
    min_year = int(options.get("min_year", DEFAULT_QUESTION_B_MIN_YEAR))
    baseline_only = bool(options.get("baseline_only", False))
    use_comparables = bool(options.get("use_comparables", False))
    run_random_split_validation = bool(options.get("run_random_split_validation", False))
    rebase_time_index_to_1990 = bool((options.get("adjustment_config") or {}).get("rebase_time_index_to_1990", False))
    time_rebase_lookup = _build_time_rebase_lookup(frame) if rebase_time_index_to_1990 else None
    evaluation_frame = _build_question_b_evaluation_frame(
        frame,
        min_year=min_year,
        include_optional=not baseline_only,
        time_rebase_lookup=time_rebase_lookup,
    )
    comparable_frame = _build_question_b_comparable_frame(frame, min_year=min_year)
    LOGGER.info(
        "Question B evaluation frame prepared with %d rows | baseline_only=%s min_year=%s",
        len(evaluation_frame),
        baseline_only,
        min_year,
    )
    features, categorical, numeric = get_question_b_features(
        evaluation_frame,
        include_optional=not baseline_only,
    )
    comparable_context = None
    if use_comparables:
        comparable_context = _build_comparable_context(comparable_frame)
    resolved_subject = resolve_subject_features(
        normalized_subject,
        evaluation_frame,
        building_features=options.get("building_features"),
        include_optional=not baseline_only,
        time_rebase_lookup=time_rebase_lookup,
    )
    split = make_temporal_split(evaluation_frame)
    model_fit = _fit_regression_models(
        split["train_frame"],
        split["test_frame"],
        features=features,
        categorical=categorical,
        numeric=numeric,
        candidates=_build_question_b_candidates(),
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
        tune_catboost=tune_catboost,
        catboost_tuning_iterations=catboost_tuning_iterations,
    )
    best_name = str(model_fit["best_model"])
    holdout_log_predictions = model_fit["best_pipeline"].predict(split["test_frame"][features])
    holdout_predictions = _recover_resale_price(
        holdout_log_predictions,
        split["test_frame"]["floor_area_sqm"],
        split["test_frame"]["time_rebase_factor_1990"] if "time_rebase_factor_1990" in split[
            "test_frame"].columns else None,
    )
    residual_sigma = float(np.std(split["test_frame"]["resale_price"] - holdout_predictions))

    full_pipeline = Pipeline(
        [
            ("preprocessor", _price_preprocessor(categorical, numeric)),
            ("model", _estimator_for_refit(model_fit["best_estimator"])),
        ]
    )
    full_pipeline.fit(split["train_frame"][features], split["train_frame"]["log_price_per_sqm"])
    subject_features = _subject_frame(resolved_subject, features)
    ml_estimate = float(
        _recover_resale_price(
            full_pipeline.predict(subject_features),
            np.array([float(resolved_subject["floor_area_sqm"])]),
            np.array([float(resolved_subject.get("time_rebase_factor_1990", 1.0))]),
        )[0]
    )

    if not use_comparables:
        comps_result = {
            "comparables_frame": pd.DataFrame(),
            "comparable_count": 0,
            "estimate": np.nan,
            "time_coefficient": 0.0,
            "size_coefficient": 0.0,
            "floor_coefficient": 0.0,
        }
        blend = {"ml_weight": 1.0, "comps_weight": 0.0, "blended_estimate": float(ml_estimate)}
    else:
        LOGGER.info("Question B running comparable-sales estimation")
        comps_result = estimate_from_comparables(
            resolved_subject,
            comparable_frame,
            adjustment_config=options.get("adjustment_config"),
            cutoff_month=pd.Timestamp(resolved_subject["transaction_month"]),
            comparable_context=comparable_context,
        )
        blend = blend_estimates(ml_estimate, comps_result, weights=options.get("blend_weights"))
    predicted_price = float(blend["blended_estimate"])
    blended_validation = _evaluate_blended_holdout(
        split["test_frame"],
        full_pipeline=full_pipeline,
        features=features,
        source_frame=comparable_frame,
        comparable_context=comparable_context,
        baseline_only=not use_comparables,
        blend_weights=options.get("blend_weights"),
        adjustment_config=options.get("adjustment_config"),
        eval_sample_size=options.get("eval_sample_size"),
    )
    LOGGER.info(
        (
            "Question B holdout metrics | "
            "ml_sample=%d ml_rmse=%.0f ml_mape=%.2f%% | "
            "blended_sample=%d blended_rmse=%.0f blended_mape=%.2f%% | "
            "coverage=%.2f%%"
        ),
        int(blended_validation["ml_sample_count"]),
        float(blended_validation["ml_rmse"]) if not pd.isna(blended_validation["ml_rmse"]) else float("nan"),
        float(blended_validation["ml_mape"]) * 100 if not pd.isna(blended_validation["ml_mape"]) else float("nan"),
        int(blended_validation["blended_sample_count"]),
        float(blended_validation["blended_rmse"]) if not pd.isna(blended_validation["blended_rmse"]) else float("nan"),
        float(blended_validation["blended_mape"]) * 100 if not pd.isna(blended_validation["blended_mape"]) else float(
            "nan"),
        float(blended_validation["comparable_coverage_rate"]) * 100,
    )
    random_split_validation = None
    if run_random_split_validation:
        random_split_validation = _evaluate_question_b_random_split(
            evaluation_frame,
            features=features,
            categorical=categorical,
            numeric=numeric,
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
            tune_catboost=tune_catboost,
            catboost_tuning_iterations=catboost_tuning_iterations,
        )
        LOGGER.info(
            "Question B random-split metrics | best_model=%s sample=%d rmse=%.0f mape=%.2f%% mae=%.0f r2=%.3f",
            random_split_validation["best_model"],
            int(random_split_validation["metrics"]["sample_count"]),
            float(random_split_validation["metrics"]["rmse"]),
            float(random_split_validation["metrics"]["mape"]) * 100.0,
            float(random_split_validation["metrics"]["mae"]),
            float(random_split_validation["metrics"]["r2"]),
        )

    expected_price = float(ml_estimate)
    actual_price = resolved_subject.get("resale_price")
    actual_price = float(actual_price) if actual_price is not None and not pd.isna(actual_price) else np.nan
    residual = actual_price - expected_price if not pd.isna(actual_price) else np.nan
    residual_pct = residual / expected_price if expected_price and not pd.isna(residual) else np.nan
    absolute_deviation = abs(residual) if not pd.isna(residual) else np.nan
    percentage_deviation = abs(actual_price - expected_price) / expected_price if expected_price and not pd.isna(
        residual) else np.nan
    lower_bound = expected_price - 1.96 * residual_sigma
    upper_bound = expected_price + 1.96 * residual_sigma
    inside_model_interval = None if pd.isna(actual_price) else bool(lower_bound <= actual_price <= upper_bound)
    z_score = residual / residual_sigma if residual_sigma and not pd.isna(residual) else 0.0
    comparables = comps_result["comparables_frame"].copy()
    comparable_count = int(comps_result["comparable_count"])
    comparable_reference_column = str(comps_result.get("comparable_reference_column", "resale_price"))
    comparable_reference = (
        pd.to_numeric(comparables[comparable_reference_column], errors="coerce")
        if comparable_count and comparable_reference_column in comparables.columns
        else pd.Series(dtype=float)
    )
    median_comparable_price = float(
        comparable_reference.median()) if comparable_count and not comparable_reference.empty else np.nan
    comparable_p10_price = float(
        comparable_reference.quantile(0.10)) if comparable_count and not comparable_reference.empty else np.nan
    comparable_p90_price = float(
        comparable_reference.quantile(0.90)) if comparable_count and not comparable_reference.empty else np.nan
    actual_vs_comparable_percentile = (
        _comparison_percentile(actual_price, comparable_reference)
        if comparable_count and not pd.isna(actual_price)
        else None
    )
    inside_comparable_range = (
        None
        if comparable_count < 2 or pd.isna(actual_price) or pd.isna(comparable_p10_price) or pd.isna(
            comparable_p90_price)
        else bool(comparable_p10_price <= actual_price <= comparable_p90_price)
    )
    local_distribution = _build_question_b_local_distribution(
        evaluation_frame,
        subject=resolved_subject,
    )
    distribution_contexts = _build_question_b_distribution_contexts(
        evaluation_frame,
        subject=resolved_subject,
    )
    confidence_level, confidence_reasons_positive, confidence_reasons_negative = _build_question_b_confidence(
        model_mape=blended_validation["ml_mape"],
        model_sample_count=int(blended_validation["ml_sample_count"]),
        comparable_count=comparable_count,
        feature_source=str(resolved_subject["feature_source"]),
        inside_model_interval=inside_model_interval,
    )
    final_assessment = _build_question_b_final_assessment(
        actual_price=actual_price,
        expected_price=expected_price,
        inside_model_interval=inside_model_interval,
        inside_comparable_range=inside_comparable_range,
        comparable_percentile=actual_vs_comparable_percentile,
    )
    subject_row = _subject_row_for_reference(resolved_subject, None if pd.isna(actual_price) else actual_price)
    explorer = pd.concat([subject_row, comparables], ignore_index=True, sort=False)
    LOGGER.info(
        "Question B complete | best_model=%s expected_price=%.0f deviation=%.0f ml_holdout_rmse=%.0f ml_holdout_mape=%.2f%% comparables=%d confidence=%s",
        best_name,
        expected_price,
        absolute_deviation if not pd.isna(absolute_deviation) else float("nan"),
        float(blended_validation["ml_rmse"]) if not pd.isna(blended_validation["ml_rmse"]) else float("nan"),
        float(blended_validation["ml_mape"]) * 100 if not pd.isna(blended_validation["ml_mape"]) else float("nan"),
        comparable_count,
        confidence_level,
    )

    return {
        "best_model": best_name,
        "features": features,
        "derived_location_features_used": [feature for feature in QUESTION_B_OPTIONAL_FEATURES if feature in features],
        "baseline_only": baseline_only,
        "candidate_metrics": model_fit["candidate_metrics"],
        "predicted_price": expected_price,
        "expected_price": expected_price,
        "ml_estimate": ml_estimate,
        "comps_estimate": float(comps_result["estimate"]) if comparable_count else np.nan,
        "actual_price": actual_price,
        "residual": residual,
        "residual_pct": residual_pct,
        "blended_error": absolute_deviation,
        "blended_error_pct": percentage_deviation,
        "absolute_deviation": absolute_deviation,
        "percentage_deviation": percentage_deviation,
        "residual_sigma": residual_sigma,
        "validation_residual_std": residual_sigma,
        "prediction_interval_low": lower_bound,
        "prediction_interval_high": upper_bound,
        "validation_rmse": float(blended_validation["ml_rmse"]) if "ml_rmse" in blended_validation else np.nan,
        "inside_model_interval": inside_model_interval,
        "z_score": z_score,
        "verdict": final_assessment,
        "final_assessment": final_assessment,
        "confidence": confidence_level,
        "confidence_level": confidence_level,
        "confidence_reasons_positive": confidence_reasons_positive,
        "confidence_reasons_negative": confidence_reasons_negative,
        "comparable_count": comparable_count,
        "comparable_median_price": median_comparable_price,
        "comparable_p10_price": comparable_p10_price,
        "comparable_p90_price": comparable_p90_price,
        "actual_vs_comparable_percentile": actual_vs_comparable_percentile,
        "inside_comparable_range": inside_comparable_range,
        "local_distribution_frame": local_distribution["frame"],
        "distribution_contexts": distribution_contexts,
        "local_distribution_count": local_distribution["sample_count"],
        "local_distribution_p025": local_distribution["p025"],
        "local_distribution_p25": local_distribution["p25"],
        "local_distribution_p50": local_distribution["p50"],
        "local_distribution_p75": local_distribution["p75"],
        "local_distribution_p975": local_distribution["p975"],
        "actual_vs_local_percentile": local_distribution["percentile"],
        "inside_local_95_range": local_distribution["inside_95_range"],
        "local_modified_z_score": local_distribution["modified_z_score"],
        "local_outlier_flag": local_distribution["outlier_flag"],
        "subject_vs_comparable_median": actual_price - median_comparable_price if comparable_count and not pd.isna(
            actual_price) else np.nan,
        "explorer_frame": explorer,
        "comparables_frame": comparables,
        "feature_source": resolved_subject["feature_source"],
        "split_holdout_months": [month.strftime("%Y-%m") for month in split["holdout_months"]],
        "blend_weights": {"ml": blend["ml_weight"], "comps": blend["comps_weight"]},
        "time_coefficient": comps_result["time_coefficient"],
        "size_coefficient": comps_result["size_coefficient"],
        "floor_coefficient": comps_result["floor_coefficient"],
        "blended_validation": blended_validation,
        "random_split_validation": random_split_validation,
        "eval_predictions_frame": blended_validation["predictions_frame"],
        "min_year": min_year,
        "subject": resolved_subject,
    }


def score_2017_transaction(
        frame: pd.DataFrame,
        options: dict[str, object] | None = None,
) -> dict[str, object]:
    return score_transaction(TARGET_TRANSACTION, frame, options=options)


def build_question_b_figures(result: dict[str, object]) -> dict[str, go.Figure]:
    theme = load_plotly_theme()
    distribution_contexts = result.get("distribution_contexts", {})
    actual_price = float(result["actual_price"]) if not pd.isna(result.get("actual_price")) else np.nan
    if distribution_contexts:
        fig_distribution_contexts = make_subplots(
            rows=1,
            cols=3,
            subplot_titles=("Before Nov 2017", "Calendar Year 2017", "Calendar Year 2018"),
            horizontal_spacing=0.08,
        )
        context_specs = [
            ("before_2017_11", 1, "Before Nov 2017"),
            ("year_2017", 2, "Calendar Year 2017"),
            ("year_2018", 3, "Calendar Year 2018"),
        ]
        for key, column_index, label in context_specs:
            context_frame = distribution_contexts.get(key, pd.DataFrame()).copy()
            if context_frame.empty:
                continue
            prices = pd.to_numeric(context_frame["resale_price"], errors="coerce").dropna()
            if prices.empty:
                continue
            counts, edges = np.histogram(prices, bins=20)
            centers = 0.5 * (edges[:-1] + edges[1:])
            q25 = float(prices.quantile(0.25))
            q75 = float(prices.quantile(0.75))
            colors = [
                theme.alpha(theme.blue, 0.35) if q25 <= center <= q75 else theme.alpha(theme.orange, 0.35)
                for center in centers
            ]
            line_colors = [theme.blue if q25 <= center <= q75 else theme.orange for center in centers]
            fig_distribution_contexts.add_bar(
                x=centers,
                y=counts,
                width=np.diff(edges),
                marker_color=colors,
                marker_line={"color": line_colors, "width": 1.2},
                showlegend=False,
                hovertemplate="Price bin center: SGD %{x:,.0f}<br>Count: %{y}<extra></extra>",
                row=1,
                col=column_index,
            )
            if not pd.isna(actual_price):
                fig_distribution_contexts.add_vline(
                    x=actual_price,
                    line_width=3,
                    line_dash="dash",
                    line_color=theme.primary_dark,
                    row=1,
                    col=column_index,
                )
                percentile = float((prices.le(actual_price)).mean())
                percentile_text = "100%" if actual_price >= float(prices.max()) else f"{percentile * 100.0:.1f}%"
                fig_distribution_contexts.add_annotation(
                    x=actual_price,
                    y=max(counts) * 0.92 if len(counts) else 1,
                    xref=f"x{column_index}" if column_index > 1 else "x",
                    yref=f"y{column_index}" if column_index > 1 else "y",
                    text=f"Subject<br>{percentile_text}",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1.4,
                    arrowcolor=theme.primary_dark,
                    ax=45,
                    ay=-40,
                    bgcolor=theme.alpha(theme.surface, 0.95),
                    bordercolor=theme.primary_dark,
                    borderwidth=1,
                    font={"size": 13, "color": "#000000"},
                )
        apply_standard_theme(
            fig_distribution_contexts,
            title="Question B Distribution Check for the Subject Transaction",
            xaxis_title="Resale Price (SGD)",
            yaxis_title="Transaction Count",
        )
        fig_distribution_contexts.update_layout(
            bargap=0.02,
            showlegend=False,
            annotations=list(fig_distribution_contexts.layout.annotations) + [
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.02,
                    "y": 1.12,
                    "text": "Orange bins are outside the 25th to 75th percentile range for that context.",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                }
            ],
        )
    else:
        fig_distribution_contexts = go.Figure()
        apply_standard_theme(
            fig_distribution_contexts,
            title="Question B Distribution Check for the Subject Transaction",
            xaxis_title="Resale Price (SGD)",
            yaxis_title="Transaction Count",
        )

    fig_b = go.Figure()
    local_distribution = result["local_distribution_frame"].copy()
    if not local_distribution.empty:
        bins = 20
        prices = pd.to_numeric(local_distribution["resale_price"], errors="coerce").dropna()
        counts, edges = np.histogram(prices, bins=bins)
        centers = 0.5 * (edges[:-1] + edges[1:])
        q25 = float(prices.quantile(0.25))
        q75 = float(prices.quantile(0.75))
        colors = [
            theme.alpha(theme.blue, 0.35) if q25 <= center <= q75 else theme.alpha(theme.orange, 0.35)
            for center in centers
        ]
        line_colors = [theme.blue if q25 <= center <= q75 else theme.orange for center in centers]
        fig_b.add_bar(
            x=centers,
            y=counts,
            width=np.diff(edges),
            name="Local Transactions",
            marker_color=colors,
            marker_line={"color": line_colors, "width": 1.2},
            opacity=1.0,
            showlegend=False,
            hovertemplate="Price bin center: SGD %{x:,.0f}<br>Count: %{y}<extra></extra>",
        )
        for value, label, color in [
            (result["actual_price"], "Actual", theme.primary_dark),
            (result["expected_price"], "Expected", theme.blue),
        ]:
            if not pd.isna(value):
                fig_b.add_vline(
                    x=float(value),
                    line_width=4,
                    line_dash="dash",
                    line_color=color,
                    annotation_text=label if label in {"Actual", "Expected"} else f"{label}: SGD {float(value):,.0f}",
                annotation_position="top",
            )
        if not pd.isna(result["prediction_interval_low"]) and not pd.isna(result["prediction_interval_high"]):
            fig_b.add_vrect(
                x0=float(result["prediction_interval_low"]),
                x1=float(result["prediction_interval_high"]),
                fillcolor=theme.alpha(theme.green, 0.16),
                line_width=0,
                layer="below",
                annotation_text="Model 95% range",
                annotation_position="top left",
            )
        max_bin_count = max(1, int(np.histogram(local_distribution["resale_price"], bins=bins)[0].max()))
        if not pd.isna(result["actual_price"]):
            fig_b.add_annotation(
                x=float(result["actual_price"]),
                y=max_bin_count * 0.84,
                text=f"Subject price<br>SGD {result['actual_price']:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.8,
                arrowcolor=theme.primary_dark,
                ax=78,
                ay=-68,
                bgcolor=theme.alpha(theme.surface, 0.96),
                bordercolor=theme.primary_dark,
                borderwidth=1,
                font={"size": 16, "color": "#000000"},
            )
        fig_b.add_annotation(
            x=float(result["expected_price"]),
            y=max_bin_count * 0.92,
            text=f"Expected price<br>SGD {result['expected_price']:,.0f}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.8,
            arrowcolor=theme.blue,
            ax=70,
            ay=-55,
            bgcolor=theme.alpha(theme.surface, 0.96),
                bordercolor=theme.blue,
                borderwidth=1,
                font={"size": 16, "color": "#000000"},
            )
        if not pd.isna(result["comps_estimate"]):
            fig_b.add_annotation(
                x=float(result["comps_estimate"]),
                y=max_bin_count * 0.72,
                text=f"Comps check<br>SGD {result['comps_estimate']:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.8,
                arrowcolor=theme.green,
                ax=-70,
                ay=-50,
                bgcolor=theme.alpha(theme.surface, 0.96),
                bordercolor=theme.green,
                borderwidth=1,
                font={"size": 16, "color": "#000000"},
            )
    apply_standard_theme(fig_b, title="Question 2 Expected Price Summary", xaxis_title="Price (SGD)", yaxis_title="Transaction Count")
    fig_b.update_layout(
        bargap=0.02,
        showlegend=False,
    )

    fig_b_distribution = go.Figure()
    if not local_distribution.empty:
        bins = 20
        fig_b_distribution.add_histogram(
            x=local_distribution["resale_price"],
            nbinsx=bins,
            name="Local Transactions",
            opacity=1.0,
            marker_color=theme.blue,
            marker_line={"color": theme.blue, "width": 1},
        )
        for value, label, color in [
            (result["actual_price"], "Actual", theme.primary_dark),
            (result["expected_price"], "Expected", theme.blue),
            (result["local_distribution_p025"], "P2.5", theme.accent),
            (result["local_distribution_p975"], "P97.5", theme.accent),
        ]:
            if not pd.isna(value):
                annotation_text = label if label in {"Actual", "Expected"} else f"{label}: SGD {float(value):,.0f}"
                fig_b_distribution.add_vline(
                    x=float(value),
                    line_width=4,
                    line_dash="dash",
                    line_color=color,
                    annotation_text=annotation_text,
                    annotation_position="top",
                )
    apply_standard_theme(
        fig_b_distribution,
        title=f"Question 2 Local +/-{DEFAULT_QB_LOCAL_WINDOW_MONTHS} Month Price Distribution",
        xaxis_title="Resale Price (SGD)",
        yaxis_title="Transaction Count",
    )
    fig_b_distribution.update_layout(bargap=0.05)
    if not local_distribution.empty:
        max_bin_count = max(1, int(np.histogram(local_distribution["resale_price"], bins=bins)[0].max()))
        if not pd.isna(result["actual_price"]):
            fig_b_distribution.add_annotation(
                x=float(result["actual_price"]),
                y=max_bin_count * 0.86,
                text=f"Subject transaction<br>SGD {result['actual_price']:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.6,
                arrowcolor=theme.orange,
                ax=70,
                ay=-60,
                bgcolor=theme.alpha(theme.surface, 0.96),
                bordercolor=theme.orange,
                borderwidth=1,
                font={"size": 16, "color": "#000000"},
            )
        fig_b_distribution.add_annotation(
            x=float(local_distribution["resale_price"].median()),
            y=0,
            yref="paper",
            text=f"Median: SGD {float(local_distribution['resale_price'].median()):,.0f}",
            showarrow=False,
            yshift=-18,
            font={"size": 15, "color": "#000000"},
        )

    fig_b_accuracy = go.Figure()
    candidate_metrics = pd.DataFrame(result.get("candidate_metrics", []))
    if not candidate_metrics.empty:
        candidate_metrics = candidate_metrics.copy()
        candidate_metrics["display_name"] = candidate_metrics["name"].replace(
            {
                "linear_regression": "Linear Regression",
                "xgboost": "XGBoost",
                "catboost": "CatBoost",
            }
        )
        fig_b_accuracy.add_bar(
            x=candidate_metrics["display_name"],
            y=candidate_metrics["rmse"],
            name="RMSE (SGD)",
            marker_color=theme.alpha(theme.blue, 0.35),
            marker_line={"color": theme.blue, "width": 1.2},
            text=[f"{float(value):,.0f}" for value in candidate_metrics["rmse"]],
            textposition="outside",
            hovertemplate="Model: %{x}<br>RMSE: SGD %{y:,.0f}<extra></extra>",
            yaxis="y",
            offsetgroup="rmse",
        )
        fig_b_accuracy.add_scatter(
            x=candidate_metrics["display_name"],
            y=candidate_metrics["mape"] * 100.0,
            mode="lines+markers",
            name="MAPE",
            marker={"color": theme.alpha(theme.orange, 0.35), "size": 10, "line": {"color": theme.orange, "width": 1.2}},
            line={"color": theme.orange, "width": 3},
            hovertemplate="Model: %{x}<br>MAPE: %{y:.2f}%<extra></extra>",
            yaxis="y2",
        )
        for index, row in enumerate(candidate_metrics.itertuples()):
            fig_b_accuracy.add_annotation(
                x=row.display_name,
                y=float(row.mape) * 100.0,
                yref="y2",
                text=f"{float(row.mape) * 100.0:.2f}%",
                showarrow=False,
                yshift=-18 if index % 2 == 0 else -34,
                font={"size": 14, "color": "#000000"},
            )
        best_model_name = result.get("best_model")
        best_row = candidate_metrics.loc[candidate_metrics["name"].eq(best_model_name)]
        if not best_row.empty:
            best_row = best_row.iloc[0]
            fig_b_accuracy.add_annotation(
                x=best_row["display_name"],
                y=float(best_row["rmse"]),
                text="Selected model",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.6,
                arrowcolor=theme.primary_dark,
                ax=55,
                ay=-45,
                bgcolor=theme.alpha(theme.surface, 0.96),
                bordercolor=theme.primary_dark,
                borderwidth=1,
                font={"size": 14, "color": "#000000"},
            )
    apply_standard_theme(
        fig_b_accuracy,
        title="Question B Holdout Model Accuracy",
        xaxis_title="Model",
        yaxis_title="RMSE (SGD)",
    )
    fig_b_accuracy.update_layout(
                yaxis={"rangemode": "tozero"},
        yaxis2={
            "title": "MAPE (%)",
            "overlaying": "y",
            "side": "right",
            "rangemode": "tozero",
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0.0},
        bargap=0.35,
        margin={"l": 72, "r": 88, "t": 112, "b": 96},
    )
    figures = {
        "S2QbF1_distribution_contexts": fig_distribution_contexts,
        "S2QbF2_assessment": fig_b,
        "S2QbF3_local_distribution": fig_b_distribution,
        "S2QbF4_model_accuracy": fig_b_accuracy,
    }
    eval_predictions = result["eval_predictions_frame"].copy()
    if not eval_predictions.empty:
        actual_column = "actual_price" if "actual_price" in eval_predictions.columns else "resale_price"
        actual_values = eval_predictions[actual_column].astype(float)
        predicted_columns = [column for column in ["ml_prediction", "blended_prediction"] if column in eval_predictions.columns]
        predicted_max = max(
            [actual_values.max(), *[pd.to_numeric(eval_predictions[column], errors="coerce").dropna().max() for column in predicted_columns if eval_predictions[column].notna().any()]]
        )
        predicted_min = min(
            [actual_values.min(), *[pd.to_numeric(eval_predictions[column], errors="coerce").dropna().min() for column in predicted_columns if eval_predictions[column].notna().any()]]
        )
        fig_b_actual_vs_predicted = go.Figure()
        fig_b_actual_vs_predicted.add_scatter(
            x=actual_values,
            y=eval_predictions["ml_prediction"],
            mode="markers",
            name="ML Prediction",
            marker={
                "color": theme.alpha(theme.blue, 0.35),
                "line": {"color": theme.blue, "width": 1.2},
                "size": 8,
            },
            hovertemplate="Actual: SGD %{x:,.0f}<br>ML predicted: SGD %{y:,.0f}<extra></extra>",
        )
        if eval_predictions["blended_prediction"].notna().any():
            fig_b_actual_vs_predicted.add_scatter(
                x=actual_values,
                y=eval_predictions["blended_prediction"],
                mode="markers",
                name="Blended Prediction",
                marker={
                    "color": theme.alpha(theme.accent, 0.48),
                    "line": {"color": theme.accent, "width": 1},
                    "size": 8,
                    "symbol": "diamond",
                },
                hovertemplate="Actual: SGD %{x:,.0f}<br>Blended predicted: SGD %{y:,.0f}<extra></extra>",
            )
        fig_b_actual_vs_predicted.add_scatter(
            x=[predicted_min, predicted_max],
            y=[predicted_min, predicted_max],
            mode="lines",
            name="Perfect Prediction",
            line={"color": theme.primary_dark, "dash": "dash"},
            hoverinfo="skip",
        )
        apply_standard_theme(
            fig_b_actual_vs_predicted,
            title="Question B Actual vs Predicted Holdout Prices",
            xaxis_title="Actual Price (SGD)",
            yaxis_title="Predicted Price (SGD)",
        )
        figures["S2Qb_actual_vs_predicted"] = fig_b_actual_vs_predicted
    random_split_validation = result.get("random_split_validation")
    random_split_predictions = pd.DataFrame()
    if (
        isinstance(random_split_validation, dict)
        and isinstance(random_split_validation.get("predictions_frame"), pd.DataFrame)
    ):
        random_split_predictions = random_split_validation["predictions_frame"].copy()
    if not random_split_predictions.empty:
        random_actual = random_split_predictions["actual_price"].astype(float)
        random_predicted = random_split_predictions["predicted_price"].astype(float)
        diagonal_min = float(min(random_actual.min(), random_predicted.min()))
        diagonal_max = float(max(random_actual.max(), random_predicted.max()))
        fig_b_random_split = go.Figure()
        fig_b_random_split.add_scatter(
            x=random_actual,
            y=random_predicted,
            mode="markers",
            name="Random Split Prediction",
            marker={
                "color": theme.alpha(theme.secondary, 0.52),
                "line": {"color": theme.secondary, "width": 1},
                "size": 8,
            },
            hovertemplate="Actual: SGD %{x:,.0f}<br>Predicted: SGD %{y:,.0f}<extra></extra>",
        )
        fig_b_random_split.add_scatter(
            x=[diagonal_min, diagonal_max],
            y=[diagonal_min, diagonal_max],
            mode="lines",
            name="Perfect Prediction",
            line={"color": theme.primary_dark, "dash": "dash"},
            hoverinfo="skip",
        )
        apply_standard_theme(
            fig_b_random_split,
            title="Question B Random-Split Actual vs Predicted",
            xaxis_title="Actual Price (SGD)",
            yaxis_title="Predicted Price (SGD)",
        )
        figures["S2Qb_random_split_actual_vs_predicted"] = fig_b_random_split
    return figures


def _write_section2_tableau_assets(transaction_assessment: dict[str, object], *, suffix: str = "") -> None:
    TABLEAU.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Writing Section 2 Tableau assets with suffix '%s'", suffix)
    actual_price = transaction_assessment["actual_price"]
    explorer = transaction_assessment["explorer_frame"].copy()
    explorer["price_gap_vs_subject"] = explorer["resale_price"] - actual_price
    explorer["price_gap_vs_subject_pct"] = explorer["price_gap_vs_subject"] / actual_price if not pd.isna(
        actual_price) else np.nan
    explorer["subject_flag"] = np.where(explorer["is_subject_transaction"], "Subject", "Comparable")
    explorer.to_csv(TABLEAU / f"S2Qb_transaction_reference{suffix}.csv", index=False)

    subject = transaction_assessment["subject"]
    summary = pd.DataFrame([{
        "town": subject["town"],
        "flat_type": subject["flat_type"],
        "flat_model": subject["flat_model"],
        "storey_range": subject["storey_range"],
        "floor_area_sqm": subject["floor_area_sqm"],
        "lease_commence_date": subject["lease_commence_date"],
        "transaction_month": subject["month"],
        "actual_price": actual_price,
        "predicted_price": transaction_assessment["predicted_price"],
        "expected_price": transaction_assessment["expected_price"],
        "ml_estimate": transaction_assessment["ml_estimate"],
        "comps_estimate": transaction_assessment["comps_estimate"],
        "prediction_interval_low": transaction_assessment["prediction_interval_low"],
        "prediction_interval_high": transaction_assessment["prediction_interval_high"],
        "inside_model_interval": transaction_assessment["inside_model_interval"],
        "residual": transaction_assessment["residual"],
        "residual_pct": transaction_assessment["residual_pct"],
        "blended_error": transaction_assessment["blended_error"],
        "blended_error_pct": transaction_assessment["blended_error_pct"],
        "absolute_deviation": transaction_assessment["absolute_deviation"],
        "percentage_deviation": transaction_assessment["percentage_deviation"],
        "validation_residual_std": transaction_assessment["validation_residual_std"],
        "confidence": transaction_assessment["confidence"],
        "confidence_level": transaction_assessment["confidence_level"],
        "confidence_reasons_positive": " | ".join(transaction_assessment["confidence_reasons_positive"]),
        "confidence_reasons_negative": " | ".join(transaction_assessment["confidence_reasons_negative"]),
        "verdict": transaction_assessment["verdict"],
        "final_assessment": transaction_assessment["final_assessment"],
        "feature_source": transaction_assessment["feature_source"],
        "comparable_count": transaction_assessment["comparable_count"],
        "comparable_median_price": transaction_assessment["comparable_median_price"],
        "comparable_p10_price": transaction_assessment["comparable_p10_price"],
        "comparable_p90_price": transaction_assessment["comparable_p90_price"],
        "actual_vs_comparable_percentile": transaction_assessment["actual_vs_comparable_percentile"],
        "inside_comparable_range": transaction_assessment["inside_comparable_range"],
        "local_distribution_count": transaction_assessment["local_distribution_count"],
        "local_distribution_p025": transaction_assessment["local_distribution_p025"],
        "local_distribution_p25": transaction_assessment["local_distribution_p25"],
        "local_distribution_p50": transaction_assessment["local_distribution_p50"],
        "local_distribution_p75": transaction_assessment["local_distribution_p75"],
        "local_distribution_p975": transaction_assessment["local_distribution_p975"],
        "actual_vs_local_percentile": transaction_assessment["actual_vs_local_percentile"],
        "inside_local_95_range": transaction_assessment["inside_local_95_range"],
        "local_modified_z_score": transaction_assessment["local_modified_z_score"],
        "local_outlier_flag": transaction_assessment["local_outlier_flag"],
        "subject_vs_comparable_median": transaction_assessment["subject_vs_comparable_median"],
    }])
    summary.to_csv(TABLEAU / f"S2Qb_subject_summary{suffix}.csv", index=False)


def build_question_b_summary_lines(result: dict[str, object]) -> list[str]:
    comparable_position = (
        f"Actual price sits at roughly the **{result['actual_vs_comparable_percentile']:.0%} percentile** of the adjusted comparable distribution."
        if result["actual_vs_comparable_percentile"] is not None
        else "Comparable percentile is unavailable because there are too few comparable transactions."
    )
    local_position = (
        f"Within the local +/-{DEFAULT_QB_LOCAL_WINDOW_MONTHS} month transaction cohort, the price sits at roughly the **{result['actual_vs_local_percentile']:.0%} percentile**."
        if result["actual_vs_local_percentile"] is not None
        else f"Local +/-{DEFAULT_QB_LOCAL_WINDOW_MONTHS} month percentile is unavailable because the cohort is too small."
    )
    comparable_range_line = (
        f"Adjusted comparable range (P10-P90): **SGD {result['comparable_p10_price']:,.0f} to SGD {result['comparable_p90_price']:,.0f}**."
        if not pd.isna(result["comparable_p10_price"]) and not pd.isna(result["comparable_p90_price"])
        else "Adjusted comparable range unavailable because there are too few comparable transactions."
    )
    local_range_line = (
        f"Local +/-{DEFAULT_QB_LOCAL_WINDOW_MONTHS} month empirical 95% range: **SGD {result['local_distribution_p025']:,.0f} to SGD {result['local_distribution_p975']:,.0f}** from **{result['local_distribution_count']}** transactions."
        if not pd.isna(result["local_distribution_p025"]) and not pd.isna(result["local_distribution_p975"])
        else f"Local +/-{DEFAULT_QB_LOCAL_WINDOW_MONTHS} month empirical range unavailable because the cohort is too small."
    )
    return [
        "## Question B: Transaction Reasonableness Assessment",
        f"Best expected-price model: **{result['best_model']}**.",
        f"Shared holdout months: `{', '.join(result['split_holdout_months'])}`.",
        f"Feature source for the subject: **{result['feature_source']}**.",
        "",
        "| Model | MAE | RMSE | MAPE | R2 |",
        "| --- | ---: | ---: | ---: | ---: |",
        *[f"| {metric['name']} | {metric['mae']:,.0f} | {metric['rmse']:,.0f} | {metric['mape']:.2%} | {metric['r2']:.3f} |" for metric in
          result['candidate_metrics']],
        "",
        f"Expected price from the model: **SGD {result['expected_price']:,.0f}**.",
        f"Actual price: **SGD {result['actual_price']:,.0f}**.",
        f"Deviation from expected price: **SGD {result['absolute_deviation']:,.0f}** ({result['percentage_deviation']:.1%}).",
        f"Holdout RMSE for the selected model: **SGD {next(metric['rmse'] for metric in result['candidate_metrics'] if metric['name'] == result['best_model']):,.0f}**.",
        (
            (
                "Notebook-style random 75/25 split benchmark: "
                f"**{result['random_split_validation']['best_model']}** with "
                f"RMSE **SGD {result['random_split_validation']['metrics']['rmse']:,.0f}**, "
                f"MAPE **{result['random_split_validation']['metrics']['mape']:.2%}**, "
                f"R2 **{result['random_split_validation']['metrics']['r2']:.3f}**."
            )
            if result.get("random_split_validation") is not None
            else "Notebook-style random 75/25 split benchmark was skipped for this run."
        ),
        f"95% expected range from validation residuals: **SGD {result['prediction_interval_low']:,.0f} to SGD {result['prediction_interval_high']:,.0f}**.",
        ("Observed price is **inside** the model-based range." if result[
                                                                      'inside_model_interval'] is True else "Observed price is **outside** the model-based range." if
        result[
            'inside_model_interval'] is False else "Observed price cannot be checked against the model-based range."),
        f"Comparable transactions used for context: **{result['comparable_count']}**.",
        comparable_range_line,
        comparable_position,
        ("Observed price is **inside** the comparable-based range." if result[
                                                                           'inside_comparable_range'] is True else "Observed price is **outside** the comparable-based range." if
        result['inside_comparable_range'] is False else "Comparable-based range check is unavailable."),
        local_range_line,
        local_position,
        ("Observed price is **inside** the local empirical 95% range." if result[
                                                                              'inside_local_95_range'] is True else "Observed price is **outside** the local empirical 95% range." if
        result['inside_local_95_range'] is False else "Local empirical range check is unavailable."),
        (
            f"Robust outlier check (modified z-score): **{result['local_modified_z_score']:.2f}**, flagged outlier = **{result['local_outlier_flag']}**." if not pd.isna(
                result['local_modified_z_score']) and result[
                                                                                                                                                                 'local_outlier_flag'] is not None else "Robust outlier check is unavailable because the local cohort is too small or too concentrated."),
        f"Assessment: **{result['final_assessment']}**",
        f"Confidence: **{result['confidence_level']}**.",
        ("Confidence positives: " + "; ".join(result['confidence_reasons_positive']) + "." if result[
            'confidence_reasons_positive'] else "Confidence positives: none highlighted."),
        ("Confidence limitations: " + "; ".join(result['confidence_reasons_negative']) + "." if result[
            'confidence_reasons_negative'] else "Confidence limitations: none highlighted."),
        "",
    ]


def run_question_b_workflow(
        frame: pd.DataFrame,
        *,
        question_b_options: dict[str, object] | None = None,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        tune_catboost: bool = False,
        catboost_tuning_iterations: int = DEFAULT_CATBOOST_TUNING_ITERATIONS,
        artifact_suffix: str = "",
) -> dict[str, object]:
    question_b_options = question_b_options or {}
    result = score_transaction(
        TARGET_TRANSACTION,
        frame,
        options=question_b_options,
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
        tune_catboost=tune_catboost,
        catboost_tuning_iterations=catboost_tuning_iterations,
    )
    pd.DataFrame(result['candidate_metrics']).to_csv(REPORTS / f"S2Qb_model_comparison{artifact_suffix}.csv",
                                                     index=False)
    pd.DataFrame([{
        "actual_price": result["actual_price"],
        "expected_price": result["expected_price"],
        "prediction_interval_low": result["prediction_interval_low"],
        "prediction_interval_high": result["prediction_interval_high"],
        "comps_estimate": result["comps_estimate"],
        "local_distribution_p025": result["local_distribution_p025"],
        "local_distribution_p975": result["local_distribution_p975"],
        "best_model": result["best_model"],
    }]).to_csv(
        REPORTS / f"S2Qb_assessment_summary{artifact_suffix}.csv",
        index=False,
    )
    if result["random_split_validation"] is not None:
        pd.DataFrame(result["random_split_validation"]["candidate_metrics"]).to_csv(
            REPORTS / f"S2Qb_random_split_model_comparison{artifact_suffix}.csv",
            index=False,
        )
    result['comparables_frame'].to_csv(REPORTS / f"S2Qb_comparables{artifact_suffix}.csv", index=False)
    local_distribution_frame = result.get("local_distribution_frame", pd.DataFrame()).copy()
    local_distribution_frame.to_csv(
        REPORTS / f"S2Qb_local_distribution_frame{artifact_suffix}.csv",
        index=False,
    )
    distribution_contexts = result.get("distribution_contexts", {})
    if distribution_contexts:
        context_frames = [
            context_frame.assign(distribution_context=context_name)
            for context_name, context_frame in distribution_contexts.items()
            if not context_frame.empty
        ]
        if context_frames:
            pd.concat(
                context_frames,
                ignore_index=True,
            ).to_csv(
                REPORTS / f"S2Qb_distribution_contexts{artifact_suffix}.csv",
                index=False,
            )
    result['eval_predictions_frame'].to_csv(REPORTS / f"S2Qb_blended_holdout_predictions{artifact_suffix}.csv",
                                            index=False)
    if result["random_split_validation"] is not None:
        result["random_split_validation"]["predictions_frame"].to_csv(
            REPORTS / f"S2Qb_random_split_predictions{artifact_suffix}.csv",
            index=False,
        )
    _write_section2_tableau_assets(result, suffix=artifact_suffix)
    return {
        "result": result,
        "summary_lines": build_question_b_summary_lines(result),
        "figures": build_question_b_figures(result),
        "supporting_outputs": [
            f"- `reports/S2Qb_model_comparison{artifact_suffix}.csv`, `reports/S2Qb_comparables{artifact_suffix}.csv`, and Tableau S2Qb extracts.",
        ],
    }


def _load_question_b_reports_bundle(*, artifact_suffix: str = "") -> dict[str, object]:
    def _read_csv(name: str, *, required: bool = True) -> pd.DataFrame:
        path = REPORTS / f"{name}{artifact_suffix}.csv"
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required Question B report not found: {path}")
            return pd.DataFrame()
        return pd.read_csv(path)

    summary = _read_csv("S2Qb_assessment_summary").to_dict("records")[0]
    distribution_contexts_frame = _read_csv("S2Qb_distribution_contexts", required=False)
    distribution_contexts: dict[str, pd.DataFrame] = {}
    if not distribution_contexts_frame.empty and "distribution_context" in distribution_contexts_frame.columns:
        for context_name, context_frame in distribution_contexts_frame.groupby("distribution_context", dropna=False):
            distribution_contexts[str(context_name)] = context_frame.drop(columns=["distribution_context"]).copy()

    return {
        **summary,
        "candidate_metrics": _read_csv("S2Qb_model_comparison").to_dict("records"),
        "local_distribution_frame": _read_csv("S2Qb_local_distribution_frame", required=False),
        "distribution_contexts": distribution_contexts,
        "eval_predictions_frame": _read_csv("S2Qb_blended_holdout_predictions", required=False),
        "random_split_validation": (
            {
                "candidate_metrics": _read_csv("S2Qb_random_split_model_comparison", required=False).to_dict("records"),
                "predictions_frame": _read_csv("S2Qb_random_split_predictions", required=False),
            }
            if (REPORTS / f"S2Qb_random_split_model_comparison{artifact_suffix}.csv").exists()
            else None
        ),
    }


__all__ = [
    "_build_comparable_context",
    "_build_question_b_candidates",
    "_build_question_b_comparable_frame",
    "_build_question_b_evaluation_frame",
    "_build_question_b_final_assessment",
    "_build_question_b_confidence",
    "build_question_b_figures",
    "build_question_b_summary_lines",
    "estimate_from_comparables",
    "get_question_b_features",
    "main",
    "resolve_subject_features",
    "run_question_b_workflow",
    "score_2017_transaction",
    "score_transaction",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 2 Question B only.")
    comparable_group = parser.add_mutually_exclusive_group()
    comparable_group.add_argument("--baseline-only", action="store_true")
    comparable_group.add_argument("--with-comparables", action="store_true")
    parser.add_argument("--min-year", type=int, default=DEFAULT_QUESTION_B_MIN_YEAR)
    parser.add_argument("--eval-sample-size", type=int, default=None)
    parser.add_argument("--rebase-time-index-to-1990", action="store_true")
    parser.add_argument("--tune-xgboost", action="store_true")
    parser.add_argument("--tune-catboost", action="store_true")
    parser.add_argument(
        "--xgboost-tuning-iterations",
        type=int,
        default=DEFAULT_XGBOOST_TUNING_ITERATIONS,
    )
    parser.add_argument(
        "--catboost-tuning-iterations",
        type=int,
        default=DEFAULT_CATBOOST_TUNING_ITERATIONS,
    )
    parser.add_argument(
        "--run-random-split-validation",
        action="store_true",
        help="Run the extra notebook-style 75/25 random split validation benchmark.",
    )
    parser.add_argument("--skip-plotly", action="store_true", help="Skip writing Plotly HTML artifacts.")
    parser.add_argument(
        "--reuse-reports",
        action="store_true",
        help="Reuse saved Question B CSV outputs to rebuild charts without rerunning the models.",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    from src.analysis.section2.S2_helpers import _configure_logging, _write_plotly_assets

    _configure_logging(args.log_level)
    REPORTS.mkdir(parents=True, exist_ok=True)
    baseline_only = bool(args.baseline_only)
    suffix = "_baseline" if baseline_only else ""
    if args.reuse_reports:
        LOGGER.info("Rebuilding Question B figures from saved reports only")
        workflow = {"figures": build_question_b_figures(_load_question_b_reports_bundle(artifact_suffix=suffix))}
    else:
        frame = _load_frame()
        workflow = run_question_b_workflow(
            frame=frame,
            question_b_options={
                "baseline_only": baseline_only,
                "use_comparables": args.with_comparables,
                "min_year": args.min_year,
                "eval_sample_size": args.eval_sample_size,
                "run_random_split_validation": args.run_random_split_validation,
                "adjustment_config": {
                    "rebase_time_index_to_1990": args.rebase_time_index_to_1990,
                },
            },
            tune_xgboost=args.tune_xgboost,
            xgboost_tuning_iterations=args.xgboost_tuning_iterations,
            tune_catboost=args.tune_catboost,
            catboost_tuning_iterations=args.catboost_tuning_iterations,
            artifact_suffix=suffix,
        )
        result = workflow["result"]
        result["eval_predictions_frame"].to_csv(
            REPORTS / f"S2Qb_blended_holdout_predictions{suffix}.csv",
            index=False,
        )
    if not args.skip_plotly:
        _write_plotly_assets(workflow["figures"], suffix=suffix)


if __name__ == "__main__":
    main()
