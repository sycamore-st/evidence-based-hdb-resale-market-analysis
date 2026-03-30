from __future__ import annotations

import argparse
from dataclasses import asdict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from src.analysis.common.plotly_standard import apply_standard_theme, load_plotly_theme
from src.analysis.section2.S2_config import (
    QUESTION_A_MAIN_TRAINING_WINDOW,
    DEFAULT_XGBOOST_TUNING_ITERATIONS,
    MAX_REGRESSION_SAMPLE,
    QUESTION_A_DIAGNOSTIC_FEATURES,
    QUESTION_A_FEATURES,
    QUESTION_A_IMPUTATION_FEATURES,
    QUESTION_A_IMPUTATION_METHODS,
    QUESTION_A_IMPUTATION_MIN_GROUP_SIZE,
    QUESTION_A_OFFICIAL_FEATURES,
    QUESTION_A_TRAINING_WINDOWS,
    RANDOM_STATE,
    TARGET_TRANSACTION,
)
from src.analysis.section2.S2_helpers import (
    LOGGER,
    ModelResult,
    _augment_regression_features,
    _direct_regression_metric_bundle,
    _estimator_for_refit,
    _fit_direct_price_regression_models,
    _fit_regression_models,
    _load_frame,
    _normalize_subject,
    _price_preprocessor,
    _recover_direct_resale_price,
    _sample_if_needed,
    _subject_frame,
    _with_log_resale_target,
)
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS


QUESTION_A_MODEL_LABELS = {
    "linear_regression": "Linear Regression",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

QUESTION_A_WINDOW_LABELS = {
    "full_history": "Full History",
    "recent_5y": "Recent 5 Years",
    "recent_3y": "Recent 3 Years",
    "recent_1y": "Recent 1 Year",
}


def _compact_currency(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"SGD {value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"SGD {value / 1_000:.0f}K"
    return f"SGD {value:,.0f}"


def _compact_amount(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:,.0f}"


def _build_question_a_candidates() -> dict[str, object]:
    return {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=16,
            min_samples_leaf=2,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "xgboost": XGBRegressor(
            objective="reg:squarederror",
            n_estimators=160,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }


def _question_a_age_bucket(value: object, *, width: int = 5) -> float:
    if value is None or pd.isna(value):
        return np.nan
    return float(np.floor(float(value) / width) * width)


def _prepare_question_a_diagnostic_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    sample = enriched.loc[
        enriched["transaction_year"].eq(2014),
        QUESTION_A_DIAGNOSTIC_FEATURES + ["resale_price", "transaction_month", "transaction_year"],
    ].copy()
    sample["flat_age_bucket"] = sample["flat_age"].map(_question_a_age_bucket)
    sample = sample.dropna(subset=["year", "town", "flat_type", "flat_age", "resale_price"]).copy()
    sample = _with_log_resale_target(sample)
    return _sample_if_needed(sample, MAX_REGRESSION_SAMPLE)


def _build_question_a_controlled_variation_summary(frame: pd.DataFrame, *, top_n: int = 8) -> pd.DataFrame:
    summary = (
        frame.groupby(["town", "flat_type", "flat_age_bucket"], dropna=False)
        .agg(
            transaction_count=("resale_price", "size"),
            price_min=("resale_price", "min"),
            price_p25=("resale_price", lambda values: float(values.quantile(0.25))),
            price_p50=("resale_price", "median"),
            price_p75=("resale_price", lambda values: float(values.quantile(0.75))),
            price_max=("resale_price", "max"),
        )
        .reset_index()
    )
    if summary.empty:
        return summary
    summary["price_iqr"] = summary["price_p75"] - summary["price_p25"]
    summary["group_label"] = summary.apply(
        lambda row: f"{row['town']} | {row['flat_type']} | age {int(row['flat_age_bucket'])}-{int(row['flat_age_bucket']) + 4}",
        axis=1,
    )
    return summary.sort_values(["transaction_count", "price_iqr"], ascending=[False, False]).head(top_n).reset_index(drop=True)


def _build_question_a_imputation_correlation(frame: pd.DataFrame) -> pd.DataFrame:
    correlation_features = ["flat_age", *QUESTION_A_IMPUTATION_FEATURES, "resale_price"]
    available = [column for column in correlation_features if column in frame.columns]
    correlation_frame = frame[available].apply(pd.to_numeric, errors="coerce")
    correlation_matrix = correlation_frame.corr(numeric_only=True)
    return correlation_matrix.loc[available, available]


def _build_question_a_floor_area_by_flat_type_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby("flat_type", dropna=False)
        .agg(
            transaction_count=("floor_area_sqm", "size"),
            floor_area_min=("floor_area_sqm", "min"),
            floor_area_p25=("floor_area_sqm", lambda values: float(values.quantile(0.25))),
            floor_area_avg=("floor_area_sqm", "mean"),
            floor_area_p50=("floor_area_sqm", "median"),
            floor_area_p75=("floor_area_sqm", lambda values: float(values.quantile(0.75))),
            floor_area_max=("floor_area_sqm", "max"),
        )
        .reset_index()
    )
    return summary.sort_values("floor_area_p50").reset_index(drop=True)


def _build_question_a_feature_handling_table() -> pd.DataFrame:
    rows = [
        {
            "feature": "town",
            "main_model": "Yes",
            "extended_training": "Yes",
            "extended_eval": "Observed",
            "type": "Categorical",
            "preprocessing": "Most-frequent imputer + one-hot encoder",
            "note": "Case input",
        },
        {
            "feature": "flat_type",
            "main_model": "Yes",
            "extended_training": "Yes",
            "extended_eval": "Observed",
            "type": "Categorical",
            "preprocessing": "Most-frequent imputer + one-hot encoder",
            "note": "Case input",
        },
        {
            "feature": "flat_age",
            "main_model": "Yes",
            "extended_training": "Yes",
            "extended_eval": "Observed",
            "type": "Numeric",
            "preprocessing": "Median imputer",
            "note": "Case input",
        },
        {
            "feature": "floor_area_sqm",
            "main_model": "No",
            "extended_training": "Yes",
            "extended_eval": "Imputed",
            "type": "Numeric",
            "preprocessing": "Median imputer in pipeline; avg/p25/p75/mode/null in backtest",
            "note": "Hidden feature",
        },
        {
            "feature": "min_floor_level",
            "main_model": "No",
            "extended_training": "Yes",
            "extended_eval": "Imputed",
            "type": "Numeric",
            "preprocessing": "Median imputer in pipeline; avg/p25/p75/mode/null in backtest",
            "note": "Hidden feature",
        },
        {
            "feature": "max_floor_level",
            "main_model": "No",
            "extended_training": "Yes",
            "extended_eval": "Imputed",
            "type": "Numeric",
            "preprocessing": "Median imputer in pipeline; avg/p25/p75/mode/null in backtest",
            "note": "Hidden feature",
        },
        {
            "feature": "Training target: price_per_sqm",
            "main_model": "Yes",
            "extended_training": "No",
            "extended_eval": "No",
            "type": "Target",
            "preprocessing": "Time rebased, then log transformed",
            "note": "Main model path",
        },
        {
            "feature": "Training target: resale_price",
            "main_model": "No",
            "extended_training": "Yes",
            "extended_eval": "Yes",
            "type": "Target",
            "preprocessing": "Log transformed",
            "note": "Extended backtest path",
        },
        {
            "feature": "Final output: resale_price",
            "main_model": "Yes",
            "extended_training": "Yes",
            "extended_eval": "Yes",
            "type": "Target",
            "preprocessing": "Recovered from the model prediction for reporting",
            "note": "Final answer shown to user",
        },
    ]
    return pd.DataFrame(rows)


def _build_question_a_imputation_range_backtest(
        diagnostic_eval_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float]]:
    if diagnostic_eval_frame.empty or "imputation_method" not in diagnostic_eval_frame.columns:
        return pd.DataFrame(), {}

    range_frame = diagnostic_eval_frame.loc[
        diagnostic_eval_frame["imputation_method"].isin(["p25", "p75"])
    ].copy()
    if range_frame.empty:
        return pd.DataFrame(), {}

    pivot = (
        range_frame.pivot_table(
            index="holdout_row_id",
            columns="imputation_method",
            values="predicted_price",
            aggfunc="first",
        )
        .reset_index()
    )
    actuals = (
        diagnostic_eval_frame[["holdout_row_id", "actual_price", "transaction_month", "town", "flat_type", "flat_age"]]
        .drop_duplicates(subset=["holdout_row_id"])
        .copy()
    )
    detail = actuals.merge(pivot, on="holdout_row_id", how="inner")
    if detail.empty or "p25" not in detail.columns or "p75" not in detail.columns:
        return pd.DataFrame(), {}

    detail["range_low"] = detail[["p25", "p75"]].min(axis=1)
    detail["range_high"] = detail[["p25", "p75"]].max(axis=1)
    detail["range_width"] = detail["range_high"] - detail["range_low"]
    actual_positive = detail["actual_price"].astype(float) > 0
    detail["range_width_pct_of_actual"] = np.where(
        actual_positive,
        detail["range_width"] / detail["actual_price"].astype(float),
        np.nan,
    )
    detail["actual_in_range"] = (
        (detail["actual_price"].astype(float) >= detail["range_low"])
        & (detail["actual_price"].astype(float) <= detail["range_high"])
    )
    summary = {
        "coverage_rate": float(detail["actual_in_range"].mean()),
        "average_range_width": float(detail["range_width"].mean()),
        "median_range_width": float(detail["range_width"].median()),
        "average_range_width_pct_of_actual": float(detail["range_width_pct_of_actual"].mean()),
        "sample_count": int(len(detail)),
    }
    return detail, summary


def _select_question_a_imputation_group(
        reference_frame: pd.DataFrame,
        subject: dict[str, object],
) -> tuple[pd.DataFrame, list[str]]:
    subject_row = dict(subject)
    subject_row["flat_age_bucket"] = _question_a_age_bucket(subject_row.get("flat_age"))
    grouping_candidates = [
        ["year", "town", "flat_type", "flat_age_bucket"],
        ["year", "town", "flat_type"],
        ["year", "flat_type"],
        ["year"],
    ]
    selected = pd.DataFrame()
    selected_group = grouping_candidates[-1]
    for group_columns in grouping_candidates:
        subset = reference_frame.copy()
        for column in group_columns:
            subject_value = subject_row.get(column)
            if subject_value is None or pd.isna(subject_value):
                subset = pd.DataFrame()
                break
            subset = subset.loc[subset[column].eq(subject_value)].copy()
        usable = subset[QUESTION_A_IMPUTATION_FEATURES].notna().any(axis=1).sum() if not subset.empty else 0
        if usable >= QUESTION_A_IMPUTATION_MIN_GROUP_SIZE:
            selected = subset
            selected_group = group_columns
            break

    if selected.empty:
        fallback = reference_frame.loc[reference_frame["year"].eq(subject_row.get("year"))].copy()
        if fallback.empty:
            fallback = reference_frame.copy()
            selected_group = []
        else:
            selected_group = ["year"]
        selected = fallback
    return selected, selected_group


def _most_frequent_numeric(series: pd.Series) -> float:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return np.nan
    counts = cleaned.value_counts()
    top_count = counts.max()
    return float(sorted(counts[counts.eq(top_count)].index.tolist())[0])


def _build_question_a_imputation_reference(
        reference_frame: pd.DataFrame,
        subject: dict[str, object],
) -> dict[str, object]:
    selected, selected_group = _select_question_a_imputation_group(reference_frame, subject)
    method_values: dict[str, dict[str, float]] = {}
    for method in QUESTION_A_IMPUTATION_METHODS:
        values: dict[str, float] = {}
        for feature in QUESTION_A_IMPUTATION_FEATURES:
            if method == "null":
                values[feature] = np.nan
                continue
            series = pd.to_numeric(selected[feature], errors="coerce").dropna()
            if series.empty:
                values[feature] = np.nan
            elif method == "avg":
                values[feature] = float(series.mean())
            elif method == "p25":
                values[feature] = float(series.quantile(0.25))
            elif method == "p75":
                values[feature] = float(series.quantile(0.75))
            elif method == "most_frequent":
                values[feature] = _most_frequent_numeric(series)
            else:
                raise ValueError(f"Unsupported Question A imputation method: {method}")
        method_values[method] = values
    return {
        "group_columns": selected_group,
        "sample_count": int(len(selected)),
        "values": method_values,
    }


def _apply_question_a_imputation_scenario(
        frame: pd.DataFrame,
        reference_frame: pd.DataFrame,
        method: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenario_rows: list[pd.Series] = []
    reference_rows: list[dict[str, object]] = []
    for row in frame.to_dict("records"):
        reference = _build_question_a_imputation_reference(reference_frame, row)
        scenario_row = row.copy()
        scenario_row["recovery_floor_area_sqm"] = row.get("floor_area_sqm")
        for feature, value in reference["values"][method].items():
            scenario_row[feature] = value
        scenario_rows.append(pd.Series(scenario_row))
        reference_rows.append(
            {
                "transaction_month": row.get("transaction_month"),
                "town": row.get("town"),
                "flat_type": row.get("flat_type"),
                "flat_age": row.get("flat_age"),
                "imputation_method": method,
                "imputation_group": " + ".join(reference["group_columns"]) if reference["group_columns"] else "global",
                "imputation_sample_count": int(reference["sample_count"]),
                **reference["values"][method],
            }
        )
    scenario_frame = pd.DataFrame(scenario_rows)
    reference_summary = pd.DataFrame(reference_rows)
    return scenario_frame, reference_summary


def build_question_a_frame(frame: pd.DataFrame) -> pd.DataFrame:
    sample = _prepare_question_a_diagnostic_frame(frame)
    official = sample[QUESTION_A_OFFICIAL_FEATURES + ["floor_area_sqm", "resale_price", "transaction_year"]].copy()
    official = _with_log_resale_target(official)
    return official


def _build_question_a_model_frame(frame: pd.DataFrame) -> pd.DataFrame:
    sample = _prepare_question_a_diagnostic_frame(frame)
    official = sample[QUESTION_A_OFFICIAL_FEATURES + ["floor_area_sqm", "resale_price", "transaction_month",
                                                      "transaction_year"]].copy()
    official = _with_log_resale_target(official)
    return official


def _question_a_training_window_year_count(window_label: str) -> int | None:
    for label, year_count in QUESTION_A_TRAINING_WINDOWS:
        if label == window_label:
            return year_count
    raise ValueError(f"Unknown Question A training window: {window_label}")


def _build_question_a_temporal_split(
        frame: pd.DataFrame,
        *,
        window_label: str = QUESTION_A_MAIN_TRAINING_WINDOW,
) -> dict[str, object]:
    enriched = _augment_regression_features(frame)
    sample = enriched.loc[
        enriched["transaction_year"] <= 2014,
        QUESTION_A_DIAGNOSTIC_FEATURES + ["resale_price", "transaction_month", "transaction_year"],
    ].copy()
    sample["flat_age_bucket"] = sample["flat_age"].map(_question_a_age_bucket)
    sample = sample.dropna(subset=["flat_type", "town", "flat_age", "floor_area_sqm", "resale_price"]).copy()
    sample = _with_log_resale_target(sample)

    train_pool = sample.loc[sample["transaction_year"] < 2014].copy()
    test_frame = sample.loc[sample["transaction_year"] == 2014].copy()
    if train_pool.empty or test_frame.empty:
        raise ValueError("Question A temporal split requires pre-2014 training data and 2014 holdout data.")

    year_count = _question_a_training_window_year_count(window_label)
    if year_count is None:
        train_frame = train_pool.copy()
    else:
        max_year = int(train_pool["transaction_year"].max())
        start_year = max_year - year_count + 1
        train_frame = train_pool.loc[train_pool["transaction_year"] >= start_year].copy()
    if train_frame.empty:
        raise ValueError(f"Question A temporal split produced an empty training frame for window {window_label}.")

    train_frame["holdout_row_id"] = np.arange(len(train_frame), dtype=int)
    test_frame["holdout_row_id"] = np.arange(len(test_frame), dtype=int)
    official_train_frame = _with_log_resale_target(
        train_frame[
            QUESTION_A_OFFICIAL_FEATURES + ["floor_area_sqm", "resale_price", "transaction_month", "transaction_year"]
        ].copy()
    )
    official_test_frame = _with_log_resale_target(
        test_frame[
            QUESTION_A_OFFICIAL_FEATURES + ["floor_area_sqm", "resale_price", "transaction_month", "transaction_year"]
        ].copy()
    )
    return {
        "window_label": window_label,
        "train_frame": train_frame,
        "test_frame": test_frame,
        "official_train_frame": official_train_frame,
        "official_test_frame": official_test_frame,
    }


def _evaluate_question_a_training_windows(
        frame: pd.DataFrame,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    sample = enriched.loc[
        enriched["transaction_year"] <= 2014,
        QUESTION_A_OFFICIAL_FEATURES + ["floor_area_sqm", "resale_price", "transaction_month", "transaction_year"],
    ].copy()
    sample = sample.dropna(subset=["flat_type", "town", "flat_age", "floor_area_sqm", "resale_price"]).copy()
    sample = _with_log_resale_target(sample)
    train_pool = sample.loc[sample["transaction_year"] < 2014].copy()
    holdout = sample.loc[sample["transaction_year"] == 2014].copy()
    if train_pool.empty or holdout.empty:
        return pd.DataFrame()

    available_years = sorted(train_pool["transaction_year"].dropna().astype(int).unique().tolist())
    if not available_years:
        return pd.DataFrame()

    max_year = max(available_years)
    rows: list[dict[str, object]] = []
    for window_label, year_count in QUESTION_A_TRAINING_WINDOWS:
        if year_count is None:
            window_train = train_pool.copy()
            window_years = available_years
        else:
            start_year = max_year - year_count + 1
            window_train = train_pool.loc[train_pool["transaction_year"] >= start_year].copy()
            window_years = sorted(window_train["transaction_year"].dropna().astype(int).unique().tolist())
        if window_train.empty or not window_years:
            continue

        fit = _fit_direct_price_regression_models(
            window_train,
            holdout,
            features=QUESTION_A_OFFICIAL_FEATURES,
            categorical=["flat_type", "town"],
            numeric=["flat_age"],
            candidates=_build_question_a_candidates(),
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
        )
        best_metrics = next(row for row in fit["candidate_metrics"] if row["name"] == fit["best_model"])
        rows.append(
            {
                "training_window": window_label,
                "train_year_start": min(window_years),
                "train_year_end": max(window_years),
                "train_row_count": int(len(window_train)),
                "holdout_row_count": int(len(holdout)),
                "best_model": fit["best_model"],
                "mae": float(best_metrics["mae"]),
                "rmse": float(best_metrics["rmse"]),
                "mape": float(best_metrics["mape"]),
                "r2": float(best_metrics["r2"]),
            }
        )
    return pd.DataFrame(rows)


def predict_simplified_price(
        subject: dict[str, object],
        frame: pd.DataFrame | None = None,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    if frame is None:
        frame = _load_frame()
    LOGGER.info("Question A start")
    diagnostic_sample = _prepare_question_a_diagnostic_frame(frame)
    temporal_split = _build_question_a_temporal_split(frame, window_label=QUESTION_A_MAIN_TRAINING_WINDOW)
    controlled_variation_summary = _build_question_a_controlled_variation_summary(diagnostic_sample)
    imputation_correlation = _build_question_a_imputation_correlation(diagnostic_sample)
    floor_area_by_flat_type = _build_question_a_floor_area_by_flat_type_summary(diagnostic_sample)
    feature_handling_table = _build_question_a_feature_handling_table()
    LOGGER.info("Question A diagnostic sample prepared with %d rows", len(diagnostic_sample))
    train_frame = temporal_split["train_frame"].copy()
    test_frame = temporal_split["test_frame"].copy()
    official_train_frame = temporal_split["official_train_frame"].copy()
    official_test_frame = temporal_split["official_test_frame"].copy()
    split = {
        "train_frame": official_train_frame.copy(),
        "test_frame": official_test_frame.copy(),
        "holdout_months": sorted(pd.to_datetime(official_test_frame["transaction_month"]).unique().tolist()),
    }
    official_fit = _fit_direct_price_regression_models(
        split["train_frame"],
        split["test_frame"],
        features=QUESTION_A_OFFICIAL_FEATURES,
        categorical=["flat_type", "town"],
        numeric=["flat_age"],
        candidates=_build_question_a_candidates(),
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )
    official_best_metrics = next(
        row for row in official_fit["candidate_metrics"] if row["name"] == official_fit["best_model"]
    )
    LOGGER.info(
        "Question A official holdout metrics | best_model=%s rmse=%.0f mape=%.2f%% mae=%.0f r2=%.3f",
        official_fit["best_model"],
        float(official_best_metrics["rmse"]),
        float(official_best_metrics["mape"]) * 100.0,
        float(official_best_metrics["mae"]),
        float(official_best_metrics["r2"]),
    )
    eval_log_predictions = official_fit["best_pipeline"].predict(split["test_frame"][QUESTION_A_OFFICIAL_FEATURES])
    eval_predictions = _recover_direct_resale_price(eval_log_predictions)
    eval_predictions_frame = split["test_frame"][
        [column for column in ["transaction_month", "town", "flat_type", "flat_age", "resale_price"] if
         column in split["test_frame"].columns]
    ].copy()
    eval_predictions_frame["actual_price"] = eval_predictions_frame["resale_price"]
    eval_predictions_frame["predicted_price"] = eval_predictions

    official_pipeline = Pipeline(
        [
            ("preprocessor", _price_preprocessor(["flat_type", "town"], ["flat_age"])),
            ("model", _estimator_for_refit(official_fit["best_estimator"])),
        ]
    )
    official_training_sample = _with_log_resale_target(
        train_frame[QUESTION_A_OFFICIAL_FEATURES + ["resale_price"]].copy()
    )
    official_pipeline.fit(official_training_sample[QUESTION_A_OFFICIAL_FEATURES],
                          official_training_sample["log_resale_price"])
    official_prediction = float(
        _recover_direct_resale_price(
            official_pipeline.predict(_subject_frame(subject, QUESTION_A_OFFICIAL_FEATURES)),
        )[0]
    )

    diagnostic_fit = _fit_direct_price_regression_models(
        train_frame,
        test_frame,
        features=QUESTION_A_DIAGNOSTIC_FEATURES,
        categorical=["town", "flat_type"],
        numeric=["year", "flat_age", "floor_area_sqm", "min_floor_level", "max_floor_level"],
        candidates=_build_question_a_candidates(),
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )
    diagnostic_best_metrics = next(
        row for row in diagnostic_fit["candidate_metrics"] if row["name"] == diagnostic_fit["best_model"]
    )
    LOGGER.info(
        "Question A diagnostic observed holdout metrics | best_model=%s rmse=%.0f mape=%.2f%% mae=%.0f r2=%.3f",
        diagnostic_fit["best_model"],
        float(diagnostic_best_metrics["rmse"]),
        float(diagnostic_best_metrics["mape"]) * 100.0,
        float(diagnostic_best_metrics["mae"]),
        float(diagnostic_best_metrics["r2"]),
    )
    imputed_metrics: list[dict[str, object]] = []
    imputation_reference_frames: list[pd.DataFrame] = []
    diagnostic_eval_frames: list[pd.DataFrame] = []
    for method in QUESTION_A_IMPUTATION_METHODS:
        scenario_test_frame, reference_summary = _apply_question_a_imputation_scenario(test_frame, train_frame, method)
        imputation_reference_frames.append(reference_summary)
        for metric in diagnostic_fit["candidate_metrics"]:
            model_name = str(metric["name"])
            candidate_estimator = _build_question_a_candidates()[model_name]
            scenario_pipeline = Pipeline(
                [
                    ("preprocessor", _price_preprocessor(["town", "flat_type"],
                                                         ["year", "flat_age", "floor_area_sqm", "min_floor_level",
                                                          "max_floor_level"])),
                    ("model", _estimator_for_refit(candidate_estimator)),
                ]
            )
            scenario_pipeline.fit(train_frame[QUESTION_A_DIAGNOSTIC_FEATURES], train_frame["log_resale_price"])
            scenario_log_predictions = scenario_pipeline.predict(scenario_test_frame[QUESTION_A_DIAGNOSTIC_FEATURES])
            scenario_metrics = _direct_regression_metric_bundle(scenario_test_frame, scenario_log_predictions)
            imputed_metrics.append(
                {
                    "name": model_name,
                    "imputation_method": method,
                    "mae": float(scenario_metrics["mae"]),
                    "rmse": float(scenario_metrics["rmse"]),
                    "mape": float(scenario_metrics["mape"]),
                    "r2": float(scenario_metrics["r2"]),
                    "mape_uplift": float(scenario_metrics["mape"] - next(
                        row["mape"] for row in diagnostic_fit["candidate_metrics"] if row["name"] == model_name)),
                }
            )
            if model_name == diagnostic_fit["best_model"]:
                frame_view = scenario_test_frame[
                    [column for column in ["holdout_row_id", "transaction_month", "town", "flat_type", "flat_age", "resale_price"] if
                     column in scenario_test_frame.columns]
                ].copy()
                frame_view["predicted_price"] = scenario_metrics["predicted_resale_price"]
                frame_view["actual_price"] = frame_view["resale_price"].astype(float)
                frame_view["imputation_method"] = method
                diagnostic_eval_frames.append(frame_view)

    training_window_sensitivity = _evaluate_question_a_training_windows(
        frame,
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )

    diagnostic_pipeline = Pipeline(
        [
            ("preprocessor", _price_preprocessor(["town", "flat_type"],
                                                 ["year", "flat_age", "floor_area_sqm", "min_floor_level",
                                                  "max_floor_level"])),
            ("model", _estimator_for_refit(diagnostic_fit["best_estimator"])),
        ]
    )
    diagnostic_pipeline.fit(train_frame[QUESTION_A_DIAGNOSTIC_FEATURES], train_frame["log_resale_price"])
    normalized_subject = _normalize_subject(subject)
    normalized_subject.setdefault("year", 2014.0)
    normalized_subject["flat_age_bucket"] = _question_a_age_bucket(normalized_subject.get("flat_age"))
    subject_reference = _build_question_a_imputation_reference(train_frame, normalized_subject)
    prediction_under_imputations: list[dict[str, object]] = []
    prediction_lookup: dict[str, float] = {}
    for method in QUESTION_A_IMPUTATION_METHODS:
        scenario_subject = dict(normalized_subject)
        for feature, value in subject_reference["values"][method].items():
            scenario_subject[feature] = value
        predicted_price = float(
            _recover_direct_resale_price(
                diagnostic_pipeline.predict(_subject_frame(scenario_subject, QUESTION_A_DIAGNOSTIC_FEATURES)),
            )[0]
        )
        prediction_lookup[method] = predicted_price
        prediction_under_imputations.append(
            {
                "imputation_method": method,
                "predicted_price": predicted_price,
                "imputation_group": " + ".join(subject_reference["group_columns"]) if subject_reference[
                    "group_columns"] else "global",
                "imputation_sample_count": int(subject_reference["sample_count"]),
                **subject_reference["values"][method],
            }
        )

    diagnostic_eval_predictions_frame = pd.concat(diagnostic_eval_frames, ignore_index=True) if diagnostic_eval_frames else pd.DataFrame()
    imputation_range_backtest_frame, imputation_range_backtest_summary = _build_question_a_imputation_range_backtest(
        diagnostic_eval_predictions_frame
    )
    best_imputed_metrics = [row for row in imputed_metrics if row["name"] == diagnostic_fit["best_model"]]
    backtest_error_low = min((float(row["mape"]) for row in best_imputed_metrics), default=np.nan)
    backtest_error_high = max((float(row["mape"]) for row in best_imputed_metrics), default=np.nan)
    imputation_summaries = []
    for method in QUESTION_A_IMPUTATION_METHODS:
        scenario_rows = [row for row in best_imputed_metrics if row["imputation_method"] == method]
        if not scenario_rows:
            continue
        row = scenario_rows[0]
        LOGGER.info(
            "Question A imputed holdout metrics | best_model=%s imputation=%s rmse=%.0f mape=%.2f%% uplift=%.2f%%",
            diagnostic_fit["best_model"],
            method,
            float(row["rmse"]),
            float(row["mape"]) * 100.0,
            float(row["mape_uplift"]) * 100.0,
        )
        imputation_summaries.append(
            {
                "imputation_method": method,
                "rmse": float(row["rmse"]),
                "mape": float(row["mape"]),
                "mape_uplift": float(row["mape_uplift"]),
                "reference_values": subject_reference["values"][method],
            }
        )
    if imputation_range_backtest_summary:
        LOGGER.info(
            "Question A imputation range backtest | best_model=%s coverage=%.2f%% avg_width=%.0f median_width=%.0f avg_width_pct=%.2f%% sample=%d",
            diagnostic_fit["best_model"],
            float(imputation_range_backtest_summary["coverage_rate"]) * 100.0,
            float(imputation_range_backtest_summary["average_range_width"]),
            float(imputation_range_backtest_summary["median_range_width"]),
            float(imputation_range_backtest_summary["average_range_width_pct_of_actual"]) * 100.0,
            int(imputation_range_backtest_summary["sample_count"]),
        )
    recommended_low_candidates = np.asarray(
        [prediction_lookup.get("p25", np.nan), prediction_lookup.get("null", np.nan)], dtype=float)
    recommended_high_candidates = np.asarray(
        [prediction_lookup.get("p75", np.nan), prediction_lookup.get("most_frequent", np.nan)], dtype=float)
    recommended_low = float(np.nanmin(recommended_low_candidates)) if np.isfinite(
        recommended_low_candidates).any() else np.nan
    recommended_mid = float(prediction_lookup.get("avg", np.nan))
    recommended_high = float(np.nanmax(recommended_high_candidates)) if np.isfinite(
        recommended_high_candidates).any() else np.nan
    uncertainty_summary = (
        f"With only coarse attributes, practical backtest MAPE is around {backtest_error_low:.0%} to {backtest_error_high:.0%} "
        "because many flats share the same visible attributes but differ in size and floor."
        if np.isfinite(backtest_error_low) and np.isfinite(backtest_error_high)
        else "Imputation-based uncertainty could not be summarized from the current holdout."
    )
    LOGGER.info(
        "Question A complete | official_best_model=%s official_rmse=%.0f diagnostic_best_model=%s diagnostic_rmse=%.0f predicted_price=%.0f",
        official_fit["best_model"],
        float(official_best_metrics["rmse"]),
        diagnostic_fit["best_model"],
        float(diagnostic_best_metrics["rmse"]),
        official_prediction,
    )
    return {
        "features": QUESTION_A_OFFICIAL_FEATURES,
        "diagnostic_features": QUESTION_A_DIAGNOSTIC_FEATURES,
        "best_model": official_fit["best_model"],
        "candidate_metrics": official_fit["candidate_metrics"],
        "candidate_metrics_observed": diagnostic_fit["candidate_metrics"],
        "candidate_metrics_imputed": sorted(imputed_metrics,
                                            key=lambda item: (item["imputation_method"], item["mape"])),
        "predicted_price": official_prediction,
        "official_predicted_price": official_prediction,
        "diagnostic_best_model": diagnostic_fit["best_model"],
        "backtest_error_range_pct": {
            "low": backtest_error_low,
            "high": backtest_error_high,
        },
        "imputation_summaries": imputation_summaries,
        "prediction_under_imputations": prediction_under_imputations,
        "reference_imputation_values": subject_reference["values"],
        "recommended_prediction_range": {
            "low": recommended_low,
            "mid": recommended_mid,
            "high": recommended_high,
        },
        "imputation_range_backtest_frame": imputation_range_backtest_frame,
        "imputation_range_backtest_summary": imputation_range_backtest_summary,
        "question_a_uncertainty_summary": uncertainty_summary,
        "question_a_imputation_reference_frame": pd.concat(imputation_reference_frames,
                                                           ignore_index=True) if imputation_reference_frames else pd.DataFrame(),
        "diagnostic_eval_predictions_frame": diagnostic_eval_predictions_frame,
        "training_window_sensitivity": training_window_sensitivity,
        "controlled_variation_summary": controlled_variation_summary,
        "imputation_feature_correlation": imputation_correlation,
        "floor_area_by_flat_type_summary": floor_area_by_flat_type,
        "feature_handling_table": feature_handling_table,
        "split_holdout_months": [month.strftime("%Y-%m") for month in split["holdout_months"]],
        "split_method": f"temporal_holdout_train_before_2014_eval_2014_{QUESTION_A_MAIN_TRAINING_WINDOW}",
        "model_pipeline": official_pipeline,
        "diagnostic_model_pipeline": diagnostic_pipeline,
        "eval_predictions_frame": eval_predictions_frame,
    }


def build_question_a_figures(result: dict[str, object]) -> dict[str, go.Figure]:
    theme = load_plotly_theme()
    question_a_metrics = pd.DataFrame(result["candidate_metrics"]).sort_values("rmse", ascending=True).reset_index(
        drop=True
    )
    observed_metrics = pd.DataFrame(result["candidate_metrics_observed"]).sort_values("rmse", ascending=True).reset_index(
        drop=True
    )
    figures: dict[str, go.Figure] = {}

    def _prepare_model_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
        if metrics.empty:
            return metrics
        prepared = metrics.copy()
        prepared["display_name"] = prepared["name"].map(
            lambda value: QUESTION_A_MODEL_LABELS.get(str(value), str(value).replace("_", " ").title())
        )
        prepared["runtime_display"] = prepared["total_seconds"].map(lambda value: f"{float(value):.2f}s")
        prepared["rmse_display"] = prepared["rmse"].map(_compact_currency)
        prepared["mape_display"] = prepared["mape"].map(lambda value: f"{float(value):.2%}")
        return prepared

    def _build_combined_model_tradeoff_figure(
            official_metrics: pd.DataFrame,
            extended_metrics: pd.DataFrame,
    ) -> go.Figure:
        official_prepared = _prepare_model_metrics(official_metrics)
        extended_prepared = _prepare_model_metrics(extended_metrics)
        model_order = official_prepared["display_name"].tolist()
        official_mape_lookup = dict(zip(official_prepared["display_name"], official_prepared["mape"]))
        extended_mape_lookup = dict(zip(extended_prepared["display_name"], extended_prepared["mape"]))
        fig_tradeoff = go.Figure()
        fig_tradeoff.add_bar(
            x=official_prepared["display_name"],
            y=official_prepared["total_seconds"],
            name="Main Runtime",
            marker_color=theme.alpha(theme.blue, 0.58),
            marker_line={"color": theme.blue, "width": 1.2},
            text=official_prepared["runtime_display"],
            textposition="outside",
            cliponaxis=False,
            offsetgroup="main",
            customdata=official_prepared[["rmse", "mae", "r2"]].to_numpy(),
            hovertemplate=(
                "Main model: %{x}<br>Total runtime: %{y:.2f}s<br>RMSE: SGD %{customdata[0]:,.0f}"
                "<br>MAE: SGD %{customdata[1]:,.0f}<br>R2: %{customdata[2]:.3f}<extra></extra>"
            ),
        )
        fig_tradeoff.add_bar(
            x=extended_prepared["display_name"],
            y=extended_prepared["total_seconds"],
            name="Extended Runtime",
            marker_color=theme.alpha(theme.green, 0.58),
            marker_line={"color": theme.green, "width": 1.2},
            text=extended_prepared["runtime_display"],
            textposition="outside",
            cliponaxis=False,
            offsetgroup="extended",
            customdata=extended_prepared[["rmse", "mae", "r2"]].to_numpy(),
            hovertemplate=(
                "Extended backtest: %{x}<br>Total runtime: %{y:.2f}s<br>RMSE: SGD %{customdata[0]:,.0f}"
                "<br>MAE: SGD %{customdata[1]:,.0f}<br>R2: %{customdata[2]:.3f}<extra></extra>"
            ),
        )
        fig_tradeoff.add_scatter(
            x=official_prepared["display_name"],
            y=official_prepared["mape"],
            name="Main MAPE",
            mode="lines+markers",
            line={"color": "#4F6E8A", "width": 3},
            marker={"color": "#4F6E8A", "size": 10},
            cliponaxis=False,
            yaxis="y2",
            hovertemplate="Main model: %{x}<br>MAPE: %{y:.2%}<extra></extra>",
        )
        fig_tradeoff.add_scatter(
            x=extended_prepared["display_name"],
            y=extended_prepared["mape"],
            name="Extended MAPE",
            mode="lines+markers",
            line={"color": "#587553", "width": 3, "dash": "dot"},
            marker={"color": "#587553", "size": 10},
            cliponaxis=False,
            yaxis="y2",
            hovertemplate="Extended backtest: %{x}<br>MAPE: %{y:.2%}<extra></extra>",
        )
        apply_standard_theme(
            fig_tradeoff,
            title="Question A Main vs Extended Model Comparison",
            xaxis_title="Model",
            yaxis_title="Total Runtime (s)",
        )
        runtime_max = max(
            float(official_prepared["total_seconds"].max()) if not official_prepared.empty else 0.0,
            float(extended_prepared["total_seconds"].max()) if not extended_prepared.empty else 0.0,
        )
        mape_values = [
            float(value)
            for value in list(official_prepared["mape"]) + list(extended_prepared["mape"])
            if pd.notna(value)
        ]
        mape_max = max(mape_values) if mape_values else 0.15
        mape_axis_max = max(0.10, round((mape_max + 0.015) / 0.02) * 0.02)
        fig_tradeoff.update_layout(
            bargap=0.36,
            barmode="group",
            showlegend=True,
            yaxis={
                "title": "Total Runtime (s)",
                "range": [0, max(runtime_max * 1.15, runtime_max + 0.12)],
            },
            yaxis2={
                "overlaying": "y",
                "side": "right",
                "title": "MAPE",
                "tickformat": ".0%",
                "range": [0, mape_axis_max],
                "autorange": False,
                "showgrid": False,
                "linecolor": "#000000",
                "tickfont": {"color": "#000000", "size": 16},
                "title_font": {"color": "#000000", "size": 17},
            },
        )
        for display_name in model_order:
            official_mape = official_mape_lookup.get(display_name)
            extended_mape = extended_mape_lookup.get(display_name)
            if official_mape is not None:
                fig_tradeoff.add_annotation(
                    x=display_name,
                    y=float(official_mape),
                    yref="y2",
                    text=f"{float(official_mape):.2%}",
                    showarrow=False,
                    xshift=26,
                    yshift=-14,
                    font={"size": 15, "color": "#000000"},
                    bgcolor="rgba(255,255,255,0.72)",
                )
            if extended_mape is not None:
                fig_tradeoff.add_annotation(
                    x=display_name,
                    y=float(extended_mape),
                    yref="y2",
                    text=f"{float(extended_mape):.2%}",
                    showarrow=False,
                    xshift=-26,
                    yshift=14,
                    font={"size": 15, "color": "#000000"},
                    bgcolor="rgba(255,255,255,0.72)",
                )
        return fig_tradeoff

    controlled_variation = result["controlled_variation_summary"].copy()
    if not controlled_variation.empty:
        fig_variation = go.Figure()
        controlled_variation = controlled_variation.sort_values(
            ["town", "flat_type", "flat_age_bucket"],
            ascending=[True, True, True],
        ).reset_index(drop=True)
        fig_variation.add_trace(
            go.Box(
            q1=controlled_variation["price_p25"],
            median=controlled_variation["price_p50"],
            q3=controlled_variation["price_p75"],
            lowerfence=controlled_variation["price_min"],
            upperfence=controlled_variation["price_max"],
            y=controlled_variation["group_label"],
            name="Price Distribution",
            orientation="h",
            boxpoints=False,
            fillcolor=theme.alpha(theme.orange, 0.35),
            line={"color": theme.orange, "width": 1.6},
            whiskerwidth=0.7,
            customdata=controlled_variation[["transaction_count", "price_p25", "price_p50", "price_p75"]].to_numpy(),
            hovertemplate=(
                "Group: %{y}<br>Transactions: %{customdata[0]}"
                "<br>P25: SGD %{customdata[1]:,.0f}<br>P50: SGD %{customdata[2]:,.0f}"
                "<br>P75: SGD %{customdata[3]:,.0f}<br>Min-Max: SGD %{lowerfence:,.0f} to %{upperfence:,.0f}"
                "<extra></extra>"
            ),
            )
        )
        for row in controlled_variation.itertuples():
            fig_variation.add_annotation(
                x=float(row.price_p25),
                y=row.group_label,
                text=_compact_amount(row.price_p25),
                showarrow=False,
                xanchor="right",
                xshift=-8,
                yshift=-17,
                font={"size": 14, "color": "#000000"},
            )
            fig_variation.add_annotation(
                x=float(row.price_p50),
                y=row.group_label,
                text=_compact_amount(row.price_p50),
                showarrow=False,
                xanchor="center",
                yshift=-17,
                font={"size": 14, "color": "#000000"},
            )
            fig_variation.add_annotation(
                x=float(row.price_p75),
                y=row.group_label,
                text=_compact_amount(row.price_p75),
                showarrow=False,
                xanchor="left",
                xshift=8,
                yshift=-17,
                font={"size": 14, "color": "#000000"},
            )
        apply_standard_theme(
            fig_variation,
            title="Question A Price Spread After Controlling for the Three Allowed Fields",
            xaxis_title="Resale Price (SGD)",
            yaxis_title=None,
        )
        fig_variation.update_layout(showlegend=False, margin={"l": 170, "r": 36, "t": 112, "b": 130})
        fig_variation.update_yaxes(
            automargin=True,
            categoryorder="array",
            categoryarray=controlled_variation["group_label"].tolist()[::-1],
        )
        fig_variation.update_xaxes(automargin=True, title_standoff=16)
        fig_variation.add_annotation(
            xref="paper",
            yref="paper",
            x=0.92,
            y=-0.07,
            text="Resale Price (SGD)",
            showarrow=False,
            xanchor="center",
            yanchor="top",
            font={"size": 16, "color": "#000000"},
        )
        figures["S2QaF1_controlled_variation"] = fig_variation

    if (
        not question_a_metrics.empty
        and not observed_metrics.empty
        and "total_seconds" in question_a_metrics.columns
        and "total_seconds" in observed_metrics.columns
    ):
        figures["S2QaF2_model_tradeoff"] = _build_combined_model_tradeoff_figure(
            question_a_metrics,
            observed_metrics,
        )

    imputation_correlation = result.get("imputation_feature_correlation", pd.DataFrame()).copy()
    if isinstance(imputation_correlation, pd.DataFrame) and not imputation_correlation.empty:
        display_labels = {
            "flat_age": "Flat Age",
            "floor_area_sqm": "Floor Area",
            "min_floor_level": "Min Floor",
            "max_floor_level": "Max Floor",
            "resale_price": "Resale Price",
        }
        labeled_correlation = imputation_correlation.rename(index=display_labels, columns=display_labels)
        heatmap_values = labeled_correlation.to_numpy()
        heatmap_text = np.vectorize(lambda value: f"{value:.2f}")(heatmap_values)
        fig_correlation = go.Figure(
            data=[
                go.Heatmap(
                    z=heatmap_values,
                    x=labeled_correlation.columns.tolist(),
                    y=labeled_correlation.index.tolist(),
                    zmin=-1,
                    zmax=1,
                    colorscale=theme.heatmap_secondary_scale,
                    colorbar={"title": "Correlation"},
                    text=heatmap_text,
                    texttemplate="%{text}",
                    xgap=3,
                    ygap=3,
                    hovertemplate="Row: %{y}<br>Column: %{x}<br>Correlation: %{z:.2f}<extra></extra>",
                )
            ]
        )
        apply_standard_theme(
            fig_correlation,
            title="Question A Correlation of Imputed Features",
            xaxis_title="Feature",
            yaxis_title="Feature",
        )
        fig_correlation.update_layout(plot_bgcolor=theme.surface)
        figures["S2QaF5_imputation_feature_correlation"] = fig_correlation

    floor_area_by_flat_type = result.get("floor_area_by_flat_type_summary", pd.DataFrame()).copy()
    if isinstance(floor_area_by_flat_type, pd.DataFrame) and not floor_area_by_flat_type.empty:
        fig_floor_area = go.Figure(
            data=[
                go.Box(
                    q1=floor_area_by_flat_type["floor_area_p25"],
                    median=floor_area_by_flat_type["floor_area_p50"],
                    q3=floor_area_by_flat_type["floor_area_p75"],
                    lowerfence=floor_area_by_flat_type["floor_area_min"],
                    upperfence=floor_area_by_flat_type["floor_area_max"],
                    x=floor_area_by_flat_type["flat_type"],
                    name="Floor Area Distribution",
                    boxpoints=False,
                    fillcolor=theme.alpha(theme.blue, 0.35),
                    line={"color": theme.blue, "width": 1.6},
                    whiskerwidth=0.7,
                    customdata=floor_area_by_flat_type[["transaction_count", "floor_area_avg"]].to_numpy(),
                    hovertemplate=(
                        "Flat type: %{x}<br>Transactions: %{customdata[0]}"
                        "<br>Min: %{lowerfence:.0f} sqm<br>P25: %{q1:.0f} sqm"
                        "<br>P50: %{median:.0f} sqm<br>P75: %{q3:.0f} sqm"
                        "<br>Max: %{upperfence:.0f} sqm<br>Average: %{customdata[1]:.1f} sqm<extra></extra>"
                    ),
                )
            ]
        )
        for row in floor_area_by_flat_type.itertuples():
            fig_floor_area.add_annotation(
                x=row.flat_type,
                y=float(row.floor_area_p25),
                text=f"{row.floor_area_p25:.0f}",
                showarrow=False,
                xanchor="right",
                xshift=-8,
                yshift=-17,
                font={"size": 14, "color": "#000000"},
            )
            fig_floor_area.add_annotation(
                x=row.flat_type,
                y=float(row.floor_area_p50),
                text=f"{row.floor_area_p50:.0f}",
                showarrow=False,
                xanchor="center",
                yshift=-17,
                font={"size": 14, "color": "#000000"},
            )
            fig_floor_area.add_annotation(
                x=row.flat_type,
                y=float(row.floor_area_p75),
                text=f"{row.floor_area_p75:.0f}",
                showarrow=False,
                xanchor="left",
                xshift=8,
                yshift=-17,
                font={"size": 14, "color": "#000000"},
            )
        apply_standard_theme(
            fig_floor_area,
            title="Question A Floor Area Distribution by Flat Type",
            xaxis_title="Flat Type",
            yaxis_title="Floor Area (sqm)",
        )
        fig_floor_area.update_layout(margin={"l": 72, "r": 36, "t": 112, "b": 130})
        fig_floor_area.update_xaxes(automargin=True, title_standoff=16)
        fig_floor_area.update_yaxes(automargin=True, title_standoff=16)
        figures["S2QaF6_floor_area_by_flat_type"] = fig_floor_area

    feature_handling_table = result.get("feature_handling_table", pd.DataFrame()).copy()
    if isinstance(feature_handling_table, pd.DataFrame) and not feature_handling_table.empty:
        stage_columns = ["main_model", "extended_training", "extended_eval"]
        stage_labels = ["Main Model", "Extended Training", "Extended Eval"]
        status_map = {"No": 0, "Observed": 1, "Yes": 1, "Imputed": 2}
        status_text = feature_handling_table[stage_columns].copy()
        status_values = status_text.replace(status_map).infer_objects(copy=False).to_numpy(dtype=float)
        status_labels = {
            0: "Not Used",
            1: "Used / Observed",
            2: "Imputed",
        }
        status_display = status_text.apply(lambda column: column.map(lambda value: str(value).replace("_", " ")))
        fig_feature_table = make_subplots(
            rows=1,
            cols=2,
            column_widths=[0.42, 0.58],
            horizontal_spacing=0.03,
            specs=[[{"type": "table"}, {"type": "heatmap"}]],
        )
        fig_feature_table.add_trace(
            go.Table(
                header={
                    "values": ["Feature", "Data Type"],
                    "fill_color": theme.blue,
                    "font": {"color": "white", "size": 14},
                    "align": "left",
                },
                cells={
                    "values": [
                        feature_handling_table["feature"],
                        feature_handling_table["type"],
                    ],
                    "fill_color": theme.surface,
                    "font": {"color": "#000000", "size": 13},
                    "align": "left",
                    "height": 28,
                },
                columnwidth=[190, 80],
            ),
            row=1,
            col=1,
        )
        fig_feature_table.add_trace(
            go.Heatmap(
                z=status_values,
                x=stage_labels,
                y=feature_handling_table["feature"],
                zmin=0,
                zmax=2,
                colorscale=[
                    [0.0, theme.alpha(theme.border, 0.18)],
                    [0.5, theme.alpha(theme.blue, 0.42)],
                    [1.0, theme.alpha(theme.orange, 0.52)],
                ],
                xgap=3,
                ygap=3,
                showscale=False,
                text=status_display.to_numpy(),
                texttemplate="%{text}",
                hovertemplate="Feature: %{y}<br>Stage: %{x}<br>Status: %{text}<extra></extra>",
            ),
            row=1,
            col=2,
        )
        fig_feature_table.update_layout(
            title={"text": "Question A Feature Handling Before and After Imputation", "font": {"size": 24, "color": "#000000"}},
            margin={"l": 150, "r": 40, "t": 90, "b": 150},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=theme.surface,
            annotations=[
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.00,
                    "y": -0.20,
                    "text": "<b>Encoding:</b> categorical fields use most-frequent imputation + one-hot encoding",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                },
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.00,
                    "y": -0.29,
                    "text": "<b>Numeric handling:</b> pipeline uses median imputation; hidden fields use avg / p25 / p75 / mode / null scenarios in backtest",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                },
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.00,
                    "y": -0.38,
                    "text": "<b>Targets:</b> main model uses time-rebased log price per sqm; extended backtest uses log resale price",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                },
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.72,
                    "y": -0.20,
                    "text": f"<b>Legend:</b> {status_labels[0]}",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                },
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.72,
                    "y": -0.29,
                    "text": f"<b></b> {status_labels[1]}",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                },
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.72,
                    "y": -0.38,
                    "text": f"<b></b> {status_labels[2]}",
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 14, "color": "#000000"},
                },
            ],
        )
        fig_feature_table.update_xaxes(
            side="top",
            showline=True,
            linewidth=1,
            linecolor="#000000",
            showgrid=False,
            tickfont={"color": "#000000", "size": 16},
            row=1,
            col=2,
        )
        fig_feature_table.update_yaxes(
            automargin=True,
            autorange="reversed",
            showline=True,
            linewidth=1,
            linecolor="#000000",
            showgrid=False,
            tickfont={"color": "#000000", "size": 16},
            title={"text": "Feature", "font": {"color": "#000000", "size": 17}},
            row=1,
            col=2,
        )
        figures["S2QaF7_feature_handling_table"] = fig_feature_table

        fig_preprocessing_flow = go.Figure()
        fig_preprocessing_flow.update_xaxes(visible=False, range=[0, 1])
        fig_preprocessing_flow.update_yaxes(visible=False, range=[0, 1])
        fig_preprocessing_flow.update_layout(
            title={"text": "Question A Preprocessing Flow", "font": {"size": 24, "color": "#000000"}},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 20, "r": 20, "t": 70, "b": 20},
            shapes=[
                {"type": "rect", "x0": 0.05, "x1": 0.22, "y0": 0.62, "y1": 0.86, "line": {"color": theme.blue, "width": 1.5}, "fillcolor": theme.alpha(theme.blue, 0.18)},
                {"type": "rect", "x0": 0.31, "x1": 0.49, "y0": 0.62, "y1": 0.86, "line": {"color": theme.green, "width": 1.5}, "fillcolor": theme.alpha(theme.green, 0.18)},
                {"type": "rect", "x0": 0.58, "x1": 0.76, "y0": 0.62, "y1": 0.86, "line": {"color": theme.orange, "width": 1.5}, "fillcolor": theme.alpha(theme.orange, 0.18)},
                {"type": "rect", "x0": 0.82, "x1": 0.97, "y0": 0.62, "y1": 0.86, "line": {"color": theme.orange, "width": 1.5}, "fillcolor": theme.alpha(theme.orange, 0.28)},
                {"type": "rect", "x0": 0.05, "x1": 0.22, "y0": 0.14, "y1": 0.38, "line": {"color": theme.blue, "width": 1.5}, "fillcolor": theme.alpha(theme.blue, 0.18)},
                {"type": "rect", "x0": 0.31, "x1": 0.49, "y0": 0.14, "y1": 0.38, "line": {"color": theme.orange, "width": 1.5}, "fillcolor": theme.alpha(theme.orange, 0.18)},
                {"type": "rect", "x0": 0.58, "x1": 0.76, "y0": 0.14, "y1": 0.38, "line": {"color": theme.orange, "width": 1.5}, "fillcolor": theme.alpha(theme.orange, 0.18)},
                {"type": "line", "x0": 0.22, "x1": 0.31, "y0": 0.74, "y1": 0.74, "line": {"color": "#000000", "width": 1.5}},
                {"type": "line", "x0": 0.49, "x1": 0.58, "y0": 0.74, "y1": 0.74, "line": {"color": "#000000", "width": 1.5}},
                {"type": "line", "x0": 0.76, "x1": 0.82, "y0": 0.74, "y1": 0.74, "line": {"color": "#000000", "width": 1.5}},
                {"type": "line", "x0": 0.22, "x1": 0.31, "y0": 0.26, "y1": 0.26, "line": {"color": "#000000", "width": 1.5}},
                {"type": "line", "x0": 0.49, "x1": 0.58, "y0": 0.26, "y1": 0.26, "line": {"color": "#000000", "width": 1.5}},
            ],
            annotations=[
                {"x": 0.135, "y": 0.92, "xref": "paper", "yref": "paper", "text": "<b>Main Model</b>", "showarrow": False, "font": {"size": 16, "color": "#000000"}},
                {"x": 0.135, "y": 0.74, "xref": "paper", "yref": "paper", "text": "Inputs<br>town, flat_type,<br>flat_age", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
                {"x": 0.40, "y": 0.74, "xref": "paper", "yref": "paper", "text": "Preprocess<br>categorical: one-hot<br>numeric: median impute", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
                {"x": 0.67, "y": 0.74, "xref": "paper", "yref": "paper", "text": "Train target<br>log price_per_sqm", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
                {"x": 0.895, "y": 0.74, "xref": "paper", "yref": "paper", "text": "Report output<br>resale_price", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
                {"x": 0.135, "y": 0.44, "xref": "paper", "yref": "paper", "text": "<b>Extended Backtest</b>", "showarrow": False, "font": {"size": 16, "color": "#000000"}},
                {"x": 0.135, "y": 0.26, "xref": "paper", "yref": "paper", "text": "Inputs<br>3 visible features +<br>size and floor", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
                {"x": 0.40, "y": 0.26, "xref": "paper", "yref": "paper", "text": "Imputation test<br>avg / p25 / p75 /<br>mode / null", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
                {"x": 0.67, "y": 0.26, "xref": "paper", "yref": "paper", "text": "Train target<br>log resale_price", "showarrow": False, "font": {"size": 14, "color": "#000000"}},
            ],
        )
        figures["S2QaF8_preprocessing_flow"] = fig_preprocessing_flow

    imputation_range_backtest = result.get("imputation_range_backtest_frame", pd.DataFrame()).copy()
    imputation_range_backtest_summary = result.get("imputation_range_backtest_summary", {})
    if isinstance(imputation_range_backtest, pd.DataFrame) and not imputation_range_backtest.empty:
        range_preview = imputation_range_backtest.sort_values("actual_price").reset_index(drop=True).copy()
        if len(range_preview) > 60:
            preview_index = np.linspace(0, len(range_preview) - 1, 60, dtype=int)
            range_preview = range_preview.iloc[preview_index].reset_index(drop=True)
        range_preview["case_order"] = np.arange(1, len(range_preview) + 1)
        fig_range_backtest = go.Figure()
        fig_range_backtest.add_scatter(
            x=range_preview["case_order"],
            y=range_preview["range_high"],
            mode="lines",
            line={"color": theme.alpha(theme.blue, 0.0), "width": 0.5},
            hoverinfo="skip",
            showlegend=False,
        )
        fig_range_backtest.add_scatter(
            x=range_preview["case_order"],
            y=range_preview["range_low"],
            mode="lines",
            line={"color": theme.alpha(theme.blue, 0.0), "width": 0.5},
            fill="tonexty",
            fillcolor=theme.alpha(theme.blue, 0.22),
            name="p25 to p75 Range",
            customdata=range_preview[["town", "flat_type", "flat_age", "range_width"]].to_numpy(),
            hovertemplate=(
                "Case %{x}<br>Range low: SGD %{y:,.0f}"
                "<br>Town: %{customdata[0]}<br>Flat type: %{customdata[1]}"
                "<br>Flat age: %{customdata[2]:.0f}<br>Range width: SGD %{customdata[3]:,.0f}<extra></extra>"
            ),
        )
        in_range = range_preview.loc[range_preview["actual_in_range"]].copy()
        out_range = range_preview.loc[~range_preview["actual_in_range"]].copy()
        fig_range_backtest.add_scatter(
            x=in_range["case_order"],
            y=in_range["actual_price"],
            mode="markers",
            name="Actual in Range",
            marker={"color": theme.green, "size": 8, "line": {"color": theme.green, "width": 1}},
            hovertemplate="Case %{x}<br>Actual price: SGD %{y:,.0f}<extra></extra>",
        )
        fig_range_backtest.add_scatter(
            x=out_range["case_order"],
            y=out_range["actual_price"],
            mode="markers",
            name="Actual out of Range",
            marker={"color": theme.orange, "size": 8, "symbol": "diamond", "line": {"color": theme.orange, "width": 1}},
            hovertemplate="Case %{x}<br>Actual price: SGD %{y:,.0f}<extra></extra>",
        )
        apply_standard_theme(
            fig_range_backtest,
            title="Question A Range Backtest: p25 to p75 Imputation Interval",
            xaxis_title="Holdout Cases Sorted by Actual Price",
            yaxis_title="Resale Price (SGD)",
        )
        fig_range_backtest.update_layout(
            annotations=[
                {
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.01,
                    "y": 1.12,
                    "text": (
                        f"Coverage: {float(imputation_range_backtest_summary.get('coverage_rate', np.nan)):.1%}"
                        f" | Avg width: {_compact_currency(float(imputation_range_backtest_summary.get('average_range_width', np.nan)))}"
                        f" | Median width: {_compact_currency(float(imputation_range_backtest_summary.get('median_range_width', np.nan)))}"
                    ),
                    "showarrow": False,
                    "xanchor": "left",
                    "font": {"size": 15, "color": "#000000"},
                }
            ]
        )
        figures["S2QaF9_range_backtest"] = fig_range_backtest

    eval_predictions = result["eval_predictions_frame"].copy()
    if not eval_predictions.empty:
        eval_predictions = eval_predictions.assign(
            absolute_error=(eval_predictions["predicted_price"] - eval_predictions["actual_price"]).abs(),
            holdout_month_dt=pd.to_datetime(eval_predictions["transaction_month"]),
        )
        eval_predictions["holdout_quarter"] = "Q" + eval_predictions["holdout_month_dt"].dt.quarter.astype(str)
        actual_min = float(min(eval_predictions["actual_price"].min(), eval_predictions["predicted_price"].min()))
        actual_max = float(max(eval_predictions["actual_price"].max(), eval_predictions["predicted_price"].max()))
        fig_actual_vs_predicted = go.Figure()
        quarter_palette = [
            theme.orange,
            theme.blue,
            theme.green,
            "#D8B55B",
        ]
        ordered_quarters = sorted(eval_predictions["holdout_quarter"].dropna().unique().tolist(), key=lambda value: int(str(value).replace("Q", "")))
        for index, holdout_quarter in enumerate(ordered_quarters):
            quarter_frame = eval_predictions.loc[eval_predictions["holdout_quarter"].eq(holdout_quarter)].copy()
            color = quarter_palette[index % len(quarter_palette)]
            fig_actual_vs_predicted.add_scatter(
                x=quarter_frame["actual_price"],
                y=quarter_frame["predicted_price"],
                mode="markers",
                name=str(holdout_quarter),
                marker={
                    "color": theme.alpha(color, 0.60),
                    "line": {"color": color, "width": 1},
                    "size": 10,
                },
                text=[
                    f"{row.town} | {row.flat_type} | age {row.flat_age:.0f}"
                    for row in quarter_frame.itertuples()
                ],
                hovertemplate=(
                    "Holdout quarter: "
                    + str(holdout_quarter)
                    + "<br>Actual: SGD %{x:,.0f}<br>Predicted: SGD %{y:,.0f}<br>%{text}<extra></extra>"
                ),
            )
        fig_actual_vs_predicted.add_scatter(
            x=[actual_min, actual_max],
            y=[actual_min, actual_max],
            mode="lines",
            name="Perfect Prediction",
            line={"color": theme.primary_dark, "dash": "dash"},
            hoverinfo="skip",
        )
        apply_standard_theme(
            fig_actual_vs_predicted,
            title="Question A Actual vs Predicted Prices",
            xaxis_title="Actual Price (SGD)",
            yaxis_title="Predicted Price (SGD)",
        )
        standout = eval_predictions.nlargest(2, "absolute_error")
        for row in standout.itertuples():
            fig_actual_vs_predicted.add_annotation(
                x=float(row.actual_price),
                y=float(row.predicted_price),
                text=f"{row.town} | {row.flat_type}",
                showarrow=True,
                arrowhead=1,
                arrowsize=1,
                arrowwidth=1.2,
                arrowcolor=theme.orange,
                ax=50,
                ay=-35,
                bgcolor=theme.surface,
                bordercolor=theme.orange,
                borderwidth=1,
                font={"size": 13, "color": "#000000"},
            )
        figures["S2QaF3_actual_vs_predicted"] = fig_actual_vs_predicted

    training_window_sensitivity = result["training_window_sensitivity"].copy()
    if not training_window_sensitivity.empty:
        training_window_sensitivity["display_window"] = training_window_sensitivity["training_window"].map(
            lambda value: QUESTION_A_WINDOW_LABELS.get(str(value), str(value).replace("_", " ").title())
        )
        training_window_sensitivity["best_model_display"] = training_window_sensitivity["best_model"].map(
            lambda value: QUESTION_A_MODEL_LABELS.get(str(value), str(value).replace("_", " ").title())
        )
        fig_window_sensitivity = go.Figure()
        fig_window_sensitivity.add_bar(
            x=training_window_sensitivity["display_window"],
            y=training_window_sensitivity["mae"],
            name="MAE",
            marker_color=theme.alpha(theme.blue, 0.55),
            marker_line={"color": theme.blue, "width": 1},
            text=[_compact_currency(value) for value in training_window_sensitivity["mae"]],
            textposition="outside",
            cliponaxis=False,
            customdata=training_window_sensitivity[
                ["best_model_display", "train_year_start", "train_year_end", "train_row_count"]].to_numpy(),
            hovertemplate=(
                "Window: %{x}<br>MAE: SGD %{y:,.0f}<br>Best model: %{customdata[0]}"
                "<br>Training years: %{customdata[1]}-%{customdata[2]}<br>Train rows: %{customdata[3]}<extra></extra>"
            ),
            showlegend=True,
            width=0.46,
        )
        fig_window_sensitivity.add_scatter(
            x=training_window_sensitivity["display_window"],
            y=training_window_sensitivity["mape"],
            name="MAPE",
            mode="lines+markers+text",
            line={"color": theme.primary_dark, "width": 3},
            marker={"color": theme.primary_dark, "size": 10},
            text=[f"{value:.1%}" for value in training_window_sensitivity["mape"]],
            textposition="top center",
            cliponaxis=False,
            yaxis="y2",
            customdata=training_window_sensitivity[
                ["best_model_display", "train_year_start", "train_year_end", "train_row_count"]].to_numpy(),
            hovertemplate=(
                "Window: %{x}<br>MAPE: %{y:.2%}<br>Best model: %{customdata[0]}"
                "<br>Training years: %{customdata[1]}-%{customdata[2]}<br>Train rows: %{customdata[3]}<extra></extra>"
            ),
            showlegend=True,
        )
        apply_standard_theme(
            fig_window_sensitivity,
            title="Question A Training Window Sensitivity",
            xaxis_title="Training Window",
            yaxis_title="MAE (SGD)",
        )
        fig_window_sensitivity.update_layout(
            bargap=0.54,
            showlegend=True,
            yaxis2={
                "overlaying": "y",
                "side": "right",
                "title": "MAPE",
                "tickformat": ".0%",
                "showgrid": False,
                "linecolor": "#000000",
                "tickfont": {"color": "#000000", "size": 16},
                "title_font": {"color": "#000000", "size": 17},
            },
        )
        fig_window_sensitivity.update_xaxes(tickangle=-90)
        fig_window_sensitivity.update_traces(textfont={"size": 17, "color": "#000000"})
        figures["S2QaF4_training_window_sensitivity"] = fig_window_sensitivity

    return figures


def _load_question_a_reports_bundle(*, artifact_suffix: str = "") -> dict[str, object]:
    def _read_csv(name: str, *, required: bool = True, index_col: int | None = None) -> pd.DataFrame:
        path = REPORTS / f"{name}{artifact_suffix}.csv"
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Required Question A report not found: {path}")
            return pd.DataFrame()
        return pd.read_csv(path, index_col=index_col)

    range_backtest_summary = _read_csv("S2Qa_imputation_range_backtest_summary", required=False)

    return {
        "candidate_metrics": _read_csv("S2Qa_model_comparison").to_dict("records"),
        "candidate_metrics_observed": _read_csv("S2Qa_observed_model_comparison").to_dict("records"),
        "candidate_metrics_imputed": _read_csv("S2Qa_imputed_model_comparison", required=False).to_dict("records"),
        "training_window_sensitivity": _read_csv("S2Qa_training_window_sensitivity", required=False),
        "controlled_variation_summary": _read_csv("S2Qa_controlled_variation_summary"),
        "imputation_feature_correlation": _read_csv("S2Qa_imputation_feature_correlation", index_col=0),
        "floor_area_by_flat_type_summary": _read_csv("S2Qa_floor_area_by_flat_type_summary"),
        "feature_handling_table": _read_csv("S2Qa_feature_handling_table"),
        "imputation_range_backtest_frame": _read_csv("S2Qa_imputation_range_backtest", required=False),
        "imputation_range_backtest_summary": range_backtest_summary.to_dict("records")[0] if not range_backtest_summary.empty else {},
        "eval_predictions_frame": _read_csv("S2Qa_eval_predictions", required=False),
    }


def build_question_a_summary_lines(result: dict[str, object]) -> list[str]:
    question_a_results = [
        ModelResult(
            name=str(metric["name"]),
            mae=float(metric["mae"]),
            rmse=float(metric["rmse"]),
            mape=float(metric["mape"]),
            r2=float(metric["r2"]),
            fit_seconds=float(metric.get("fit_seconds", 0.0)),
            predict_seconds=float(metric.get("predict_seconds", 0.0)),
            total_seconds=float(metric.get("total_seconds", 0.0)),
        )
        for metric in result["candidate_metrics"]
    ]
    observed_table = pd.DataFrame(result["candidate_metrics_observed"])
    imputed_table = pd.DataFrame(result["candidate_metrics_imputed"])
    training_window_table = pd.DataFrame(result["training_window_sensitivity"])
    range_backtest_summary = result.get("imputation_range_backtest_summary", {})
    training_window_lines = (
        [
            "",
            "| Training Window | Best Model | RMSE | MAPE | R2 | Train Rows |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
            *[
                f"| {row['training_window']} | {row['best_model']} | {float(row['rmse']):,.0f} | {float(row['mape']):.2%} | {float(row['r2']):.3f} | {int(row['train_row_count'])} |"
                for row in training_window_table.to_dict("records")
            ],
        ]
        if not training_window_table.empty
        else []
    )
    return [
        "## Question A: Simplified Price Prediction",
        "The main answer uses only `flat_type`, `flat_age`, and `town`, because those are the fields allowed by the case prompt.",
        "We then run a second backtest with observed size and floor data, and hide those fields again with imputations, to measure how much uncertainty remains when only the three visible fields are known.",
        f"Official selected model: **{result['best_model']}**.",
        f"Diagnostic selected model with observed hidden features: **{result['diagnostic_best_model']}**.",
        result["question_a_uncertainty_summary"],
        "",
        "| Official Model | MAE | RMSE | MAPE | R2 | Fit (s) | Predict (s) | Total (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[
            f"| {row.name} | {row.mae:,.0f} | {row.rmse:,.0f} | {row.mape:.2%} | {row.r2:.3f} | "
            f"{row.fit_seconds:.2f} | {row.predict_seconds:.2f} | {row.total_seconds:.2f} |"
            for row in question_a_results
        ],
        "",
        "| Diagnostic Model | Observed MAE | Observed RMSE | Observed MAPE | Observed R2 | Fit (s) | Predict (s) | Total (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[
            f"| {row['name']} | {float(row['mae']):,.0f} | {float(row['rmse']):,.0f} | {float(row['mape']):.2%} | "
            f"{float(row['r2']):.3f} | {float(row.get('fit_seconds', 0.0)):.2f} | "
            f"{float(row.get('predict_seconds', 0.0)):.2f} | {float(row.get('total_seconds', 0.0)):.2f} |"
            for row in observed_table.to_dict('records')],
        "",
        "| Imputation | Best-model RMSE | Best-model MAPE | MAPE uplift |",
        "| --- | ---: | ---: | ---: |",
        *[
            f"| {row['imputation_method']} | {float(row['rmse']):,.0f} | {float(row['mape']):.2%} | {float(row['mape_uplift']):+.2%} |"
            for row in imputed_table.loc[imputed_table['name'].eq(result['diagnostic_best_model'])].to_dict('records')],
        "",
        "| Range Backtest | Coverage | Avg Width (SGD) | Median Width (SGD) | Avg Width (% of actual) | Sample |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| p25 to p75 price range | {float(range_backtest_summary.get('coverage_rate', np.nan)):.2%} | "
        f"{float(range_backtest_summary.get('average_range_width', np.nan)):,.0f} | "
        f"{float(range_backtest_summary.get('median_range_width', np.nan)):,.0f} | "
        f"{float(range_backtest_summary.get('average_range_width_pct_of_actual', np.nan)):.2%} | "
        f"{int(range_backtest_summary.get('sample_count', 0))} |",
        *training_window_lines,
        "",
        f"Recommended diagnostic prediction range: **SGD {result['recommended_prediction_range']['low']:,.0f} to SGD {result['recommended_prediction_range']['high']:,.0f}**, midpoint **SGD {result['recommended_prediction_range']['mid']:,.0f}**.",
        "",
    ]


def run_question_a_workflow(
        frame: pd.DataFrame,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        artifact_suffix: str = "",
) -> dict[str, object]:
    result = predict_simplified_price(
        {
            "flat_type": TARGET_TRANSACTION["flat_type"],
            "town": TARGET_TRANSACTION["town"],
            "flat_age": 2017 - TARGET_TRANSACTION["lease_commence_date"],
        },
        frame=frame,
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )
    question_a_results = [
        ModelResult(
            name=str(metric["name"]),
            mae=float(metric["mae"]),
            rmse=float(metric["rmse"]),
            mape=float(metric["mape"]),
            r2=float(metric["r2"]),
            fit_seconds=float(metric.get("fit_seconds", 0.0)),
            predict_seconds=float(metric.get("predict_seconds", 0.0)),
            total_seconds=float(metric.get("total_seconds", 0.0)),
        )
        for metric in result["candidate_metrics"]
    ]
    pd.DataFrame([asdict(row) for row in question_a_results]).to_csv(
        REPORTS / f"S2Qa_model_comparison{artifact_suffix}.csv", index=False)
    pd.DataFrame(result["candidate_metrics_observed"]).to_csv(
        REPORTS / f"S2Qa_observed_model_comparison{artifact_suffix}.csv", index=False)
    pd.DataFrame(result["candidate_metrics_imputed"]).to_csv(
        REPORTS / f"S2Qa_imputed_model_comparison{artifact_suffix}.csv", index=False)
    result["training_window_sensitivity"].to_csv(REPORTS / f"S2Qa_training_window_sensitivity{artifact_suffix}.csv",
                                                 index=False)
    result["controlled_variation_summary"].to_csv(
        REPORTS / f"S2Qa_controlled_variation_summary{artifact_suffix}.csv",
        index=False,
    )
    result["imputation_feature_correlation"].to_csv(
        REPORTS / f"S2Qa_imputation_feature_correlation{artifact_suffix}.csv"
    )
    result["floor_area_by_flat_type_summary"].to_csv(
        REPORTS / f"S2Qa_floor_area_by_flat_type_summary{artifact_suffix}.csv",
        index=False,
    )
    result["feature_handling_table"].to_csv(
        REPORTS / f"S2Qa_feature_handling_table{artifact_suffix}.csv",
        index=False,
    )
    result["imputation_range_backtest_frame"].to_csv(
        REPORTS / f"S2Qa_imputation_range_backtest{artifact_suffix}.csv",
        index=False,
    )
    pd.DataFrame([result["imputation_range_backtest_summary"]]).to_csv(
        REPORTS / f"S2Qa_imputation_range_backtest_summary{artifact_suffix}.csv",
        index=False,
    )
    result["question_a_imputation_reference_frame"].to_csv(REPORTS / f"S2Qa_imputation_reference{artifact_suffix}.csv",
                                                           index=False)
    result["diagnostic_eval_predictions_frame"].to_csv(
        REPORTS / f"S2Qa_imputed_holdout_predictions{artifact_suffix}.csv", index=False)
    return {
        "result": result,
        "summary_lines": build_question_a_summary_lines(result),
        "figures": build_question_a_figures(result),
        "supporting_outputs": [
            f"- `reports/S2Qa_model_comparison{artifact_suffix}.csv` and `reports/S2Qa_observed_model_comparison{artifact_suffix}.csv` for S2Qa.",
        ],
    }


__all__ = [
    "_build_question_a_candidates",
    "_build_question_a_imputation_reference",
    "_build_question_a_model_frame",
    "_prepare_question_a_diagnostic_frame",
    "build_question_a_figures",
    "build_question_a_frame",
    "build_question_a_summary_lines",
    "main",
    "predict_simplified_price",
    "run_question_a_workflow",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 2 Question A only.")
    parser.add_argument("--skip-plotly", action="store_true", help="Skip writing Plotly HTML artifacts.")
    parser.add_argument(
        "--reuse-reports",
        action="store_true",
        help="Reuse saved Question A CSV outputs to rebuild charts without rerunning the models.",
    )
    parser.add_argument("--tune-xgboost", action="store_true", help="Enable lightweight XGBoost tuning.")
    parser.add_argument(
        "--xgboost-tuning-iterations",
        type=int,
        default=DEFAULT_XGBOOST_TUNING_ITERATIONS,
        help="Number of sampled parameter sets when XGBoost tuning is enabled.",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    from src.analysis.section2.S2_helpers import _configure_logging, _write_plotly_assets

    _configure_logging(args.log_level)
    REPORTS.mkdir(parents=True, exist_ok=True)
    if args.reuse_reports:
        LOGGER.info("Rebuilding Question A figures from saved reports only")
        result = _load_question_a_reports_bundle()
        workflow = {"figures": build_question_a_figures(result)}
    else:
        frame = _load_frame()
        workflow = run_question_a_workflow(
            frame=frame,
            tune_xgboost=args.tune_xgboost,
            xgboost_tuning_iterations=args.xgboost_tuning_iterations,
        )
        result = workflow["result"]
        result["eval_predictions_frame"].to_csv(REPORTS / "S2Qa_eval_predictions.csv", index=False)
    if not args.skip_plotly:
        _write_plotly_assets(workflow["figures"])


if __name__ == "__main__":
    main()
