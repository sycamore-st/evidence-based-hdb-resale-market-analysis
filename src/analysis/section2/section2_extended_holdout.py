from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from src.analysis.section2.S2_config import (
    DEFAULT_XGBOOST_TUNING_ITERATIONS,
    DEFAULT_XGBOOST_TUNING_FOLDS,
    QUESTION_B_XGBOOST_BEST_PARAMS,
    RANDOM_STATE,
)
from src.analysis.section2.S2_helpers import (
    LOGGER,
    _augment_regression_features,
    _configure_logging,
    _estimator_for_refit,
    _load_frame,
    _price_preprocessor,
    _recover_resale_price,
    _tune_xgboost_estimator,
    _with_log_price_target,
    evaluate_predictions,
)
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS
EXTENDED_HOLDOUT_CUTOFF = pd.Timestamp("2024-06-30")
EXTENDED_HOLDOUT_MIN_MONTH = pd.Timestamp("2022-06-01")
EXTENDED_HOLDOUT_LOOKBACK_MONTHS = 36
ROLLING_EVAL_START = pd.Timestamp("2025-06-30")
ROLLING_TUNING_MODES = ("off", "first", "quarterly", "monthly_light")
ROLLING_LIGHT_TUNING_GRID = {
    "n_estimators": [180, 260],
    "max_depth": [4, 6],
    "learning_rate": [0.08, 0.12],
    "min_child_weight": [1, 3],
    "subsample": [0.75, 1.0],
    "colsample_bytree": [0.85, 1.0],
}

EXTENDED_HOLDOUT_CATEGORICAL_CANDIDATES = [
    "month",
    "town",
    "flat_type",
    "block",
    "street_name",
    "storey_range",
    "flat_model",
    "remaining_lease",
    "transaction_quarter",
    "full_address",
    "data_segment",
    "nearest_mrt_station",
    "nearest_mrt_line",
    "nearest_bus_stop_num",
    "nearest_school_name",
    "building_key",
    "building_match_status",
]

EXTENDED_HOLDOUT_NUMERIC_CANDIDATES = [
    "transaction_year",
    "year",
    "lease_commence_date",
    "floor_area_sqm",
    "remaining_lease_years",
    "flat_age",
    "age",
    "remaining_lease_proxy",
    "remaining_lease_effective",
    "town_latitude",
    "town_longitude",
    "distance_to_cbd_km",
    "nearest_mrt_distance_km",
    "nearest_bus_stop_distance_km",
    "nearest_school_distance_km",
    "building_latitude",
    "building_longitude",
    "bus_stop_count_within_1km",
    "school_count_within_1km",
    "min_floor_level",
    "max_floor_level",
    "history_3y_group_avg_price",
    "history_3y_group_median_price",
    "history_3y_group_txn_count",
]

EXTENDED_HOLDOUT_GROUP_COLUMNS = ["street_name", "block", "flat_type", "storey_range"]


def _build_extended_holdout_history_features(
        frame: pd.DataFrame,
        *,
        lookback_months: int = EXTENDED_HOLDOUT_LOOKBACK_MONTHS,
) -> pd.DataFrame:
    monthly = (
        frame.groupby(EXTENDED_HOLDOUT_GROUP_COLUMNS + ["transaction_month"], dropna=False)
        .agg(
            monthly_avg_price=("resale_price", "mean"),
            monthly_median_price=("resale_price", "median"),
            monthly_txn_count=("resale_price", "size"),
        )
        .reset_index()
        .sort_values(EXTENDED_HOLDOUT_GROUP_COLUMNS + ["transaction_month"])
    )
    if monthly.empty:
        return frame

    def _rolling(group: pd.DataFrame) -> pd.DataFrame:
        ordered = group.sort_values("transaction_month").copy()
        shifted_count = ordered["monthly_txn_count"].shift(1)
        shifted_weighted_mean = (ordered["monthly_avg_price"] * ordered["monthly_txn_count"]).shift(1)
        rolling_count = shifted_count.rolling(lookback_months, min_periods=1).sum()
        rolling_weighted_sum = shifted_weighted_mean.rolling(lookback_months, min_periods=1).sum()
        ordered["history_3y_group_txn_count"] = rolling_count
        ordered["history_3y_group_avg_price"] = rolling_weighted_sum / rolling_count
        ordered["history_3y_group_median_price"] = ordered["monthly_median_price"].shift(1).rolling(
            lookback_months, min_periods=1
        ).median()
        return ordered[
            EXTENDED_HOLDOUT_GROUP_COLUMNS
            + [
                "transaction_month",
                "history_3y_group_avg_price",
                "history_3y_group_median_price",
                "history_3y_group_txn_count",
            ]
        ]

    history = (
        monthly.groupby(EXTENDED_HOLDOUT_GROUP_COLUMNS, dropna=False, group_keys=False)
        .apply(_rolling)
        .reset_index(drop=True)
    )
    return frame.merge(history, on=EXTENDED_HOLDOUT_GROUP_COLUMNS + ["transaction_month"], how="left")


def build_extended_holdout_training_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    enriched["transaction_month"] = pd.to_datetime(enriched["transaction_month"]).dt.to_period("M").dt.to_timestamp()
    enriched = _build_extended_holdout_history_features(enriched)
    enriched = _with_log_price_target(enriched)
    enriched = enriched.loc[enriched["transaction_month"].notna()].copy()
    return enriched


def get_extended_holdout_features(frame: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    categorical = [
        column for column in EXTENDED_HOLDOUT_CATEGORICAL_CANDIDATES
        if column in frame.columns and frame[column].notna().any()
    ]
    numeric = [
        column for column in EXTENDED_HOLDOUT_NUMERIC_CANDIDATES
        if column in frame.columns and frame[column].notna().any()
    ]
    features = categorical + numeric
    return features, categorical, numeric


def build_extended_holdout_split(
        frame: pd.DataFrame,
        *,
        cutoff: pd.Timestamp = EXTENDED_HOLDOUT_CUTOFF,
        min_month: pd.Timestamp = EXTENDED_HOLDOUT_MIN_MONTH,
) -> dict[str, pd.DataFrame | pd.Timestamp]:
    cutoff_month = pd.Timestamp(cutoff).to_period("M").to_timestamp()
    min_train_month = pd.Timestamp(min_month).to_period("M").to_timestamp()
    train_frame = frame.loc[
        (frame["transaction_month"] >= min_train_month) &
        (frame["transaction_month"] <= cutoff_month)
    ].copy()
    test_frame = frame.loc[frame["transaction_month"] > cutoff_month].copy()
    if train_frame.empty or test_frame.empty:
        raise ValueError("Extended holdout split produced an empty train or test frame.")
    return {
        "min_train_month": min_train_month,
        "cutoff_month": cutoff_month,
        "train_frame": train_frame,
        "test_frame": test_frame,
    }


def _build_prediction_frame(test_frame: pd.DataFrame, predictions: np.ndarray) -> pd.DataFrame:
    predictions_frame = test_frame[
        [
            column
            for column in [
                "transaction_month",
                "town",
                "flat_type",
                "block",
                "street_name",
                "storey_range",
                "resale_price",
                "history_3y_group_avg_price",
                "history_3y_group_median_price",
                "history_3y_group_txn_count",
            ]
            if column in test_frame.columns
        ]
    ].copy()
    predictions_frame["actual_price"] = test_frame["resale_price"].astype(float)
    predictions_frame["predicted_price"] = predictions
    predictions_frame["absolute_error"] = (predictions_frame["predicted_price"] - predictions_frame["actual_price"]).abs()
    predictions_frame["absolute_percentage_error"] = np.where(
        predictions_frame["actual_price"].astype(float) > 0,
        predictions_frame["absolute_error"] / predictions_frame["actual_price"].astype(float),
        np.nan,
    )
    return predictions_frame


def _build_feature_importance_frame(pipeline: Pipeline) -> pd.DataFrame:
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    if not hasattr(preprocessor, "get_feature_names_out") or not hasattr(model, "feature_importances_"):
        return pd.DataFrame(columns=["feature", "importance"])
    feature_names = [str(name) for name in preprocessor.get_feature_names_out()]
    importances = np.asarray(model.feature_importances_, dtype=float)
    if len(feature_names) != len(importances):
        return pd.DataFrame(columns=["feature", "importance"])
    importance_frame = pd.DataFrame({"feature": feature_names, "importance": importances})
    return importance_frame.sort_values("importance", ascending=False).reset_index(drop=True)


def run_extended_holdout_workflow(
    *,
    cutoff: pd.Timestamp = ROLLING_EVAL_START,
    min_month: pd.Timestamp = EXTENDED_HOLDOUT_MIN_MONTH,
    lookback_months: int = EXTENDED_HOLDOUT_LOOKBACK_MONTHS,
    tune_xgboost: bool = False,
    xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
    rolling_tuning_mode: str = "off",
) -> dict[str, object]:
    frame = _load_frame()
    enriched = _augment_regression_features(frame)
    enriched["transaction_month"] = pd.to_datetime(enriched["transaction_month"]).dt.to_period("M").dt.to_timestamp()
    enriched = _build_extended_holdout_history_features(enriched, lookback_months=lookback_months)
    enriched = _with_log_price_target(enriched)
    features, categorical, numeric = get_extended_holdout_features(enriched)
    evaluation_start_month = pd.Timestamp(cutoff).to_period("M").to_timestamp()
    rolling_window_months = max(1, int(lookback_months))
    candidate_months = sorted(pd.Series(enriched["transaction_month"].dropna().unique()).tolist())
    evaluation_months = [month for month in candidate_months if pd.Timestamp(month) > evaluation_start_month]
    if not evaluation_months:
        raise ValueError("No evaluation months found after the rolling evaluation start month.")

    LOGGER.info(
        "Section 2 rolling holdout run | eval_start=%s rolling_window_months=%d eval_months=%d features=%d tuning_mode=%s",
        evaluation_start_month.strftime("%Y-%m"),
        rolling_window_months,
        len(evaluation_months),
        len(features),
        rolling_tuning_mode,
    )

    estimator = XGBRegressor(
        objective="reg:squarederror",
        **QUESTION_B_XGBOOST_BEST_PARAMS,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        tree_method="hist",
    )
    tuned_params: dict[str, float | int] = {}
    monthly_prediction_frames: list[pd.DataFrame] = []
    latest_pipeline: Pipeline | None = None
    monthly_summary_rows: list[dict[str, object]] = []
    active_estimator = estimator
    active_tuned_params: dict[str, float | int] = {}

    for month_index, evaluation_month in enumerate(evaluation_months):
        evaluation_month = pd.Timestamp(evaluation_month).to_period("M").to_timestamp()
        train_start_month = evaluation_month - pd.DateOffset(months=rolling_window_months)
        train_frame = enriched.loc[
            (enriched["transaction_month"] >= train_start_month) &
            (enriched["transaction_month"] < evaluation_month)
        ].copy()
        test_frame = enriched.loc[enriched["transaction_month"] == evaluation_month].copy()
        if train_frame.empty or test_frame.empty:
            LOGGER.info(
                "Skipping rolling month %s because train=%d test=%d",
                evaluation_month.strftime("%Y-%m"),
                len(train_frame),
                len(test_frame),
            )
            continue

        should_tune = False
        tuning_iterations = 0
        tuning_folds = DEFAULT_XGBOOST_TUNING_FOLDS
        tuning_grid = None
        if rolling_tuning_mode == "first":
            should_tune = month_index == 0
            tuning_iterations = xgboost_tuning_iterations
        elif rolling_tuning_mode == "quarterly":
            should_tune = month_index % 3 == 0
            tuning_iterations = xgboost_tuning_iterations
        elif rolling_tuning_mode == "monthly_light":
            should_tune = True
            tuning_iterations = min(4, max(1, xgboost_tuning_iterations))
            tuning_folds = 1
            tuning_grid = ROLLING_LIGHT_TUNING_GRID

        if should_tune:
            LOGGER.info(
                "Rolling month %s tuning start | mode=%s iterations=%d folds=%d",
                evaluation_month.strftime("%Y-%m"),
                rolling_tuning_mode,
                tuning_iterations,
                tuning_folds,
            )
            active_estimator, active_tuned_params = _tune_xgboost_estimator(
                estimator,
                train_frame,
                features=features,
                categorical=categorical,
                numeric=numeric,
                tune_enabled=True,
                tuning_iterations=tuning_iterations,
                tuning_folds=tuning_folds,
                tuning_grid=tuning_grid,
            )
            tuned_params = dict(active_tuned_params)

        LOGGER.info(
            "Rolling month %s | train_start=%s train_rows=%d test_rows=%d tuned=%s",
            evaluation_month.strftime("%Y-%m"),
            train_start_month.strftime("%Y-%m"),
            len(train_frame),
            len(test_frame),
            bool(active_tuned_params),
        )
        pipeline = Pipeline(
            [
                ("preprocessor", _price_preprocessor(categorical, numeric)),
                ("model", _estimator_for_refit(active_estimator)),
            ]
        )
        pipeline.fit(train_frame[features], train_frame["log_price_per_sqm"])
        log_predictions = pipeline.predict(test_frame[features])
        predictions = _recover_resale_price(
            log_predictions,
            test_frame["floor_area_sqm"],
            test_frame["time_rebase_factor_1990"] if "time_rebase_factor_1990" in test_frame.columns else None,
        )
        monthly_prediction_frame = _build_prediction_frame(test_frame, predictions)
        monthly_prediction_frames.append(monthly_prediction_frame)
        monthly_metrics = evaluate_predictions(test_frame["resale_price"], predictions)
        monthly_summary_rows.append(
            {
                "transaction_month": evaluation_month.strftime("%Y-%m"),
                "train_start_month": train_start_month.strftime("%Y-%m"),
                "train_rows": int(len(train_frame)),
                "test_rows": int(len(test_frame)),
                "mae": float(monthly_metrics["mae"]),
                "rmse": float(monthly_metrics["rmse"]),
                "mape": float(monthly_metrics["mape"]),
                "r2": float(monthly_metrics["r2"]),
                "tuned_for_month": bool(should_tune),
                "tuned_params": json.dumps(active_tuned_params, sort_keys=True) if active_tuned_params else "",
            }
        )
        latest_pipeline = pipeline

    if not monthly_prediction_frames or latest_pipeline is None:
        raise ValueError("Rolling evaluation produced no monthly predictions.")

    predictions_frame = pd.concat(monthly_prediction_frames, ignore_index=True)
    metrics = evaluate_predictions(predictions_frame["actual_price"], predictions_frame["predicted_price"])
    feature_importance = _build_feature_importance_frame(latest_pipeline)

    summary = {
        "model": "xgboost",
        "evaluation_start_month": evaluation_start_month.strftime("%Y-%m"),
        "rolling_train_window_months": int(rolling_window_months),
        "history_feature_lookback_months": int(lookback_months),
        "evaluation_month_count": int(len(monthly_summary_rows)),
        "train_rows_last_month": int(monthly_summary_rows[-1]["train_rows"]),
        "test_rows_total": int(len(predictions_frame)),
        "feature_count": int(len(features)),
        "categorical_feature_count": int(len(categorical)),
        "numeric_feature_count": int(len(numeric)),
        "tuned_xgboost": rolling_tuning_mode != "off",
        "rolling_tuning_mode": rolling_tuning_mode,
        "xgboost_tuning_iterations": int(0 if rolling_tuning_mode == "off" else xgboost_tuning_iterations),
        "tuned_params": tuned_params,
        "mae": float(metrics["mae"]),
        "rmse": float(metrics["rmse"]),
        "mape": float(metrics["mape"]),
        "r2": float(metrics["r2"]),
    }
    return {
        "summary": summary,
        "features": features,
        "categorical": categorical,
        "numeric": numeric,
        "predictions_frame": predictions_frame,
        "feature_importance": feature_importance,
        "monthly_summary": pd.DataFrame(monthly_summary_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Section 2 rolling monthly XGBoost benchmark.")
    parser.add_argument(
        "--cutoff",
        default="2025-06-30",
        help="Evaluate months strictly after this date using a rolling 3-year training window.",
    )
    parser.add_argument(
        "--min-month",
        default="2022-06-01",
        help="Deprecated for rolling evaluation; retained for CLI compatibility.",
    )
    parser.add_argument(
        "--lookback-months",
        type=int,
        default=EXTENDED_HOLDOUT_LOOKBACK_MONTHS,
        help="Lookback window for street/block/flat-type/storey history features.",
    )
    parser.add_argument("--tune-xgboost", action="store_true", help="Enable XGBoost tuning before the final fit.")
    parser.add_argument(
        "--xgboost-tuning-iterations",
        type=int,
        default=DEFAULT_XGBOOST_TUNING_ITERATIONS,
        help="Base number of sampled parameter sets when rolling tuning is enabled.",
    )
    parser.add_argument(
        "--rolling-tuning-mode",
        default="off",
        choices=ROLLING_TUNING_MODES,
        help="Rolling tuning strategy: off, first, quarterly, or monthly_light.",
    )
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    _configure_logging(args.log_level)
    REPORTS.mkdir(parents=True, exist_ok=True)

    workflow = run_extended_holdout_workflow(
        cutoff=pd.Timestamp(args.cutoff),
        min_month=pd.Timestamp(args.min_month),
        lookback_months=args.lookback_months,
        tune_xgboost=args.rolling_tuning_mode != "off",
        xgboost_tuning_iterations=args.xgboost_tuning_iterations,
        rolling_tuning_mode=args.rolling_tuning_mode,
    )
    summary = workflow["summary"]

    pd.DataFrame([summary]).to_csv(REPORTS / "S2ExtendedHoldout_accuracy_summary.csv", index=False)
    pd.DataFrame({"feature": workflow["features"]}).to_csv(REPORTS / "S2ExtendedHoldout_feature_list.csv", index=False)
    workflow["predictions_frame"].to_csv(REPORTS / "S2ExtendedHoldout_predictions.csv", index=False)
    workflow["monthly_summary"].to_csv(REPORTS / "S2ExtendedHoldout_monthly_accuracy_summary.csv", index=False)
    workflow["feature_importance"].to_csv(REPORTS / "S2ExtendedHoldout_feature_importance.csv", index=False)
    (REPORTS / "S2ExtendedHoldout_accuracy_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    LOGGER.info(
        "Section 2 extended holdout complete | RMSE=%.0f MAE=%.0f MAPE=%.2f%% R2=%.3f",
        float(summary["rmse"]),
        float(summary["mae"]),
        float(summary["mape"]) * 100.0,
        float(summary["r2"]),
    )


if __name__ == "__main__":
    main()
