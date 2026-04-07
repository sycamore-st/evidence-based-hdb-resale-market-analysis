from __future__ import annotations

import logging
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import ParameterSampler
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

try:
    from catboost import CatBoostRegressor
except ImportError:  # pragma: no cover - optional dependency
    CatBoostRegressor = None

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.analysis.common.plotly_standard import apply_standard_theme, configure_plotly_png_browser
from src.analysis.section2.S2_config import (
    CATBOOST_TUNING_GRID,
    DEFAULT_CATBOOST_TUNING_ITERATIONS,
    DEFAULT_TEMPORAL_HOLDOUT_MONTHS,
    DEFAULT_XGBOOST_TUNING_FOLDS,
    DEFAULT_XGBOOST_TUNING_ITERATIONS,
    QUESTION_A_IMPUTATION_FEATURES,
    QUESTION_B_XGBOOST_BEST_PARAMS,
    RANDOM_STATE,
    TARGET_TRANSACTION,
    XGBOOST_TUNING_GRID,
)
from src.common.config import DATA_PROCESSED, SECTION2_OUTPUT_CHARTS

CHARTS = SECTION2_OUTPUT_CHARTS

LOGGER = logging.getLogger(__name__)

@dataclass
class ModelResult:
    name: str
    mae: float
    rmse: float
    mape: float
    mdape: float
    r2: float
    fit_seconds: float = 0.0
    predict_seconds: float = 0.0
    total_seconds: float = 0.0

def _configure_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(message)s",
        )
    else:
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

def _load_frame() -> pd.DataFrame:

    path = DATA_PROCESSED / "hdb_resale_processed.parquet"
    if not path.exists():
        raise FileNotFoundError("Processed dataset missing. Run `python -m src.pipeline.build_resale_analysis_dataset` first.")

    LOGGER.info("Loading processed resale frame from %s", path)
    frame = pd.read_parquet(path)

    LOGGER.info("Loaded resale frame with %d rows and %d columns", len(frame), len(frame.columns))
    if "building_key" not in frame.columns:
        LOGGER.info("No building_key in resale frame; skipping building-level enrichment merge")
        return frame
    building_path = DATA_PROCESSED / "building_master_with_poi.parquet"
    if not building_path.exists():
        LOGGER.info("No building POI master found at %s; using resale frame only", building_path)
        return frame

    building_columns = [
        "building_key",
        "building_latitude",
        "building_longitude",
        "nearest_mrt_name",
        "nearest_mrt_distance_km",
        "nearest_bus_stop_num",
        "nearest_bus_stop_distance_km",
        "bus_stop_count_within_1km",
        "nearest_school_name",
        "nearest_school_distance_km",
        "school_count_within_1km",
        "distance_to_cbd_km",
        "building_match_status",
    ]

    building_master = pd.read_parquet(building_path, columns=building_columns)
    if "building_key" not in building_master.columns:
        LOGGER.warning("Building POI master is missing building_key; skipping enrichment merge")
        return frame

    building_master = building_master.drop_duplicates(subset=["building_key"])

    LOGGER.info("Merging building POI master with %d unique building rows", len(building_master))
    merged = frame.drop(
        columns=[column for column in building_columns if column != "building_key" and column in frame.columns],
        errors="ignore",
    ).merge(building_master, on="building_key", how="left")

    if "distance_to_cbd_km" not in merged.columns and "distance_to_cbd_km_x" in merged.columns:
        merged["distance_to_cbd_km"] = merged["distance_to_cbd_km_x"].where(
            merged["distance_to_cbd_km_x"].notna(),
            merged["distance_to_cbd_km_y"],
        )

    if "distance_to_cbd_km_y" in merged.columns:
        merged["distance_to_cbd_km"] = merged["distance_to_cbd_km"].where(
            merged["distance_to_cbd_km"].notna(),
            merged["distance_to_cbd_km_y"],
        )
    drop_columns = [column for column in merged.columns if column.endswith("_x") or column.endswith("_y")]

    if drop_columns:
        merged = merged.drop(columns=drop_columns)
    LOGGER.info("Finished building enrichment merge; frame now has %d columns", len(merged.columns))
    return merged

def _price_preprocessor(categorical: list[str], numeric: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                numeric,
            ),
        ]
    )

def _classifier_preprocessor(categorical: list[str], numeric: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
        ]
    )

def _sample_if_needed(frame: pd.DataFrame, sample_limit: int | None) -> pd.DataFrame:
    if sample_limit is None or sample_limit <= 0:
        return frame.copy()
    if len(frame) <= sample_limit:
        return frame.copy()
    return frame.sample(sample_limit, random_state=RANDOM_STATE)

def _with_log_resale_target(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    valid_price = enriched["resale_price"].astype(float) > 0
    enriched = enriched.loc[valid_price].copy()
    enriched["log_resale_price"] = np.log(enriched["resale_price"].astype(float))
    return enriched

def _recover_direct_resale_price(log_resale_price: np.ndarray) -> np.ndarray:
    return np.exp(np.asarray(log_resale_price, dtype=float))

def _direct_regression_metric_bundle(test_frame: pd.DataFrame, log_predictions: np.ndarray) -> dict[str, object]:
    predicted_resale_price = _recover_direct_resale_price(log_predictions)
    actual_resale_price = test_frame["resale_price"].astype(float).to_numpy()
    metrics = evaluate_predictions(actual_resale_price, predicted_resale_price)
    return {
        "predicted_resale_price": predicted_resale_price,
        **metrics,
    }


def _build_model_metric_row(
        *,
        name: str,
        metrics_bundle: dict[str, object],
        fit_seconds: float,
        predict_seconds: float,
        tuned_params: dict[str, float | int] | None = None,
) -> dict[str, float | str | dict[str, float | int]]:
    metric_row: dict[str, float | str | dict[str, float | int]] = {
        "name": name,
        "mae": float(metrics_bundle["mae"]),
        "mape": float(metrics_bundle["mape"]),
        "mdape": float(metrics_bundle["mdape"]),
        "rmse": float(metrics_bundle["rmse"]),
        "r2": float(metrics_bundle["r2"]),
        "fit_seconds": fit_seconds,
        "predict_seconds": predict_seconds,
        "total_seconds": fit_seconds + predict_seconds,
    }
    if tuned_params:
        metric_row["tuned_params"] = tuned_params
    return metric_row


def _record_model_metric_result(
        *,
        metrics: list[dict[str, float | str | dict[str, float | int]]],
        metric_row: dict[str, float | str | dict[str, float | int]],
        best_mape: float,
        best_name: str,
        best_pipeline: Pipeline | None,
        name: str,
        pipeline: Pipeline,
) -> tuple[float, str, Pipeline | None, float, float, float, float]:
    metrics.append(metric_row)
    mae = float(metric_row["mae"])
    mape = float(metric_row["mape"])
    rmse = float(metric_row["rmse"])
    r2 = float(metric_row["r2"])
    if mape < best_mape:
        best_mape = mape
        best_name = name
        best_pipeline = pipeline
    return best_mape, best_name, best_pipeline, mae, mape, rmse, r2

def make_temporal_split(
        frame: pd.DataFrame,
        *,
        month_column: str = "transaction_month",
        preferred_holdout_months: tuple[str, ...] = DEFAULT_TEMPORAL_HOLDOUT_MONTHS,
        latest_month_count: int = 1,
) -> dict[str, object]:
    if month_column not in frame.columns:
        raise KeyError(f"{month_column} is required for temporal splitting.")

    months = sorted(pd.Series(frame[month_column].dropna().unique()).tolist())
    if len(months) < 2:
        raise ValueError("Temporal split requires at least two distinct months.")

    preferred = {
        pd.Timestamp(f"{month}-01")
        for month in preferred_holdout_months
    }
    latest = set(months[-latest_month_count:]) if latest_month_count > 0 else set()
    holdout = sorted((preferred & set(months)) | latest)
    if len(holdout) >= len(months):
        holdout = [months[-1]]
    train_months = [month for month in months if month not in holdout]
    if not train_months:
        train_months = months[:-1]
        holdout = [months[-1]]

    train_mask = frame[month_column].isin(train_months)
    test_mask = frame[month_column].isin(holdout)
    return {
        "train_mask": train_mask,
        "test_mask": test_mask,
        "train_months": [pd.Timestamp(month) for month in train_months],
        "holdout_months": [pd.Timestamp(month) for month in holdout],
        "train_frame": frame.loc[train_mask].copy(),
        "test_frame": frame.loc[test_mask].copy(),
    }

def _tune_xgboost_estimator(
        estimator: XGBRegressor,
        train_frame: pd.DataFrame,
        *,
        features: list[str],
        categorical: list[str],
        numeric: list[str],
        tune_enabled: bool = False,
        tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        tuning_folds: int = DEFAULT_XGBOOST_TUNING_FOLDS,
        tuning_grid: dict[str, list[float | int]] | None = None,
) -> tuple[XGBRegressor, dict[str, float | int]]:
    if not tune_enabled:
        return estimator, {}
    if len(train_frame) < 500:
        return estimator, {}

    months = sorted(pd.Series(train_frame["transaction_month"].dropna().unique()).tolist())
    if len(months) < 3:
        return estimator, {}
    effective_tuning_folds = max(1, int(tuning_folds))
    holdout_months = months[-min(effective_tuning_folds, len(months) - 1):]
    cv_splits: list[dict[str, object]] = []
    for holdout_month in holdout_months:
        split = make_temporal_split(
            train_frame,
            preferred_holdout_months=(pd.Timestamp(holdout_month).strftime("%Y-%m"),),
            latest_month_count=0,
        )
        if split["train_frame"].empty or split["test_frame"].empty:
            continue
        cv_splits.append(split)
    if not cv_splits:
        return estimator, {}

    prepared_splits: list[dict[str, object]] = []
    for split in cv_splits:
        preprocessor = _price_preprocessor(categorical, numeric)
        fitted_preprocessor = clone(preprocessor).fit(split["train_frame"][features])
        prepared_splits.append(
            {
                "transformed_train": fitted_preprocessor.transform(split["train_frame"][features]),
                "transformed_test": fitted_preprocessor.transform(split["test_frame"][features]),
                "train_target": split["train_frame"]["log_price_per_sqm"],
                "test_target": split["test_frame"]["log_price_per_sqm"],
                "test_frame": split["test_frame"],
            }
        )

    best_params: dict[str, float | int] = {}
    best_score = np.inf

    parameter_grid = XGBOOST_TUNING_GRID if tuning_grid is None else tuning_grid
    sampled_params = list(
        ParameterSampler(
            parameter_grid,
            n_iter=max(1, tuning_iterations),
            random_state=RANDOM_STATE,
        )
    )
    LOGGER.info(
        "Tuning XGBoost over %d sampled parameter sets with %d temporal folds",
        len(sampled_params),
        len(cv_splits),
    )
    for params in sampled_params:
        trial_start = time.perf_counter()
        LOGGER.info("XGBoost tuning trial start: %s", params)
        fold_scores: list[float] = []
        for split in prepared_splits:
            candidate = clone(estimator).set_params(
                **params,
                early_stopping_rounds=20,
                eval_metric="mae",
            )
            candidate.fit(
                split["transformed_train"],
                split["train_target"],
                eval_set=[(split["transformed_test"], split["test_target"])],
                verbose=False,
            )
            log_predictions = candidate.predict(split["transformed_test"])
            fold_scores.append(float(_regression_metric_bundle(split["test_frame"], log_predictions)["mape"]))
        score = float(np.mean(fold_scores))
        LOGGER.info(
            "XGBoost tuning trial complete in %.1fs | avg_MAPE=%.2f%% | params=%s",
            time.perf_counter() - trial_start,
            score * 100,
            params,
        )
        if score < best_score:
            best_score = score
            best_params = dict(params)

    if not best_params:
        return estimator, {}
    LOGGER.info("Selected tuned XGBoost params: %s", best_params)
    return clone(estimator).set_params(**best_params), best_params

def _tune_catboost_estimator(
        estimator: CatBoostRegressor,
        train_frame: pd.DataFrame,
        *,
        features: list[str],
        categorical: list[str],
        numeric: list[str],
        tune_enabled: bool = False,
        tuning_iterations: int = DEFAULT_CATBOOST_TUNING_ITERATIONS,
) -> tuple[CatBoostRegressor, dict[str, float | int]]:
    if not tune_enabled:
        return estimator, {}
    if len(train_frame) < 500:
        return estimator, {}

    inner_split = make_temporal_split(
        train_frame,
        preferred_holdout_months=(),
        latest_month_count=1,
    )
    if inner_split["train_frame"].empty or inner_split["test_frame"].empty:
        return estimator, {}

    best_params: dict[str, float | int] = {}
    best_score = np.inf
    preprocessor = _price_preprocessor(categorical, numeric)
    fitted_preprocessor = clone(preprocessor).fit(inner_split["train_frame"][features])
    transformed_train = fitted_preprocessor.transform(inner_split["train_frame"][features])
    transformed_test = fitted_preprocessor.transform(inner_split["test_frame"][features])
    if hasattr(transformed_train, "toarray"):
        transformed_train = transformed_train.toarray()
    if hasattr(transformed_test, "toarray"):
        transformed_test = transformed_test.toarray()

    sampled_params = list(
        ParameterSampler(
            CATBOOST_TUNING_GRID,
            n_iter=max(1, tuning_iterations),
            random_state=RANDOM_STATE,
        )
    )
    LOGGER.info("Tuning CatBoost over %d sampled parameter sets", len(sampled_params))
    for params in sampled_params:
        trial_start = time.perf_counter()
        LOGGER.info("CatBoost tuning trial start: %s", params)
        candidate = clone(estimator).set_params(**params)
        candidate.fit(
            transformed_train,
            inner_split["train_frame"]["log_price_per_sqm"],
            eval_set=(transformed_test, inner_split["test_frame"]["log_price_per_sqm"]),
            verbose=False,
            use_best_model=True,
        )
        log_predictions = candidate.predict(transformed_test)
        score = float(_regression_metric_bundle(inner_split["test_frame"], log_predictions)["mape"])
        LOGGER.info(
            "CatBoost tuning trial complete in %.1fs | MAPE=%.2f%% | params=%s",
            time.perf_counter() - trial_start,
            score * 100,
            params,
        )
        if score < best_score:
            best_score = score
            best_params = dict(params)

    if not best_params:
        return estimator, {}
    LOGGER.info("Selected tuned CatBoost params: %s", best_params)
    return clone(estimator).set_params(**best_params), best_params

def _fit_regression_models(
        train_frame: pd.DataFrame,
        test_frame: pd.DataFrame,
        *,
        features: list[str],
        categorical: list[str],
        numeric: list[str],
        candidates: dict[str, object],
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        tune_catboost: bool = False,
        catboost_tuning_iterations: int = DEFAULT_CATBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    LOGGER.info(
        "Regression fit start: train=%d test=%d features=%d candidates=%s",
        len(train_frame),
        len(test_frame),
        len(features),
        ", ".join(candidates.keys()),
    )
    preprocessor = _price_preprocessor(categorical, numeric)
    metrics: list[dict[str, float | str]] = []
    best_name = ""
    best_mape = np.inf
    best_pipeline: Pipeline | None = None

    def fit_regression_pipeline(estimator: object) -> Pipeline:
        fitted_preprocessor = clone(preprocessor).fit(train_frame[features])
        if isinstance(estimator, XGBRegressor):
            transformed_train = fitted_preprocessor.transform(train_frame[features])
            transformed_test = fitted_preprocessor.transform(test_frame[features])
            fitted_model = clone(estimator).set_params(
                early_stopping_rounds=20,
                eval_metric="mae",
            )
            fitted_model.fit(
                transformed_train,
                train_frame["log_price_per_sqm"],
                eval_set=[(transformed_test, test_frame["log_price_per_sqm"])],
                verbose=False,
            )
            return Pipeline([("preprocessor", fitted_preprocessor), ("model", fitted_model)])
        if CatBoostRegressor is not None and isinstance(estimator, CatBoostRegressor):
            transformed_train = fitted_preprocessor.transform(train_frame[features])
            transformed_test = fitted_preprocessor.transform(test_frame[features])
            if hasattr(transformed_train, "toarray"):
                transformed_train = transformed_train.toarray()
            if hasattr(transformed_test, "toarray"):
                transformed_test = transformed_test.toarray()
            fitted_model = clone(estimator)
            fitted_model.fit(transformed_train, train_frame["log_price_per_sqm"])
            return Pipeline([("preprocessor", fitted_preprocessor), ("model", fitted_model)])

        pipeline = Pipeline([("preprocessor", clone(preprocessor)), ("model", estimator)])
        pipeline.fit(train_frame[features], train_frame["log_price_per_sqm"])
        return pipeline

    for name, estimator in candidates.items():
        start_time = time.perf_counter()
        LOGGER.info("Fitting regression candidate: %s", name)
        tuned_params: dict[str, float | int] = {}
        candidate_estimator = estimator
        if isinstance(estimator, XGBRegressor):
            candidate_estimator, tuned_params = _tune_xgboost_estimator(
                estimator,
                train_frame,
                features=features,
                categorical=categorical,
                numeric=numeric,
                tune_enabled=tune_xgboost,
                tuning_iterations=xgboost_tuning_iterations,
            )
        elif CatBoostRegressor is not None and isinstance(estimator, CatBoostRegressor):
            candidate_estimator, tuned_params = _tune_catboost_estimator(
                estimator,
                train_frame,
                features=features,
                categorical=categorical,
                numeric=numeric,
                tune_enabled=tune_catboost,
                tuning_iterations=catboost_tuning_iterations,
            )
        fit_start = time.perf_counter()
        pipeline = fit_regression_pipeline(candidate_estimator)
        fit_seconds = float(time.perf_counter() - fit_start)
        predict_start = time.perf_counter()
        log_predictions = pipeline.predict(test_frame[features])
        predict_seconds = float(time.perf_counter() - predict_start)
        metrics_bundle = _regression_metric_bundle(test_frame, log_predictions)
        metric_row = _build_model_metric_row(
            name=name,
            metrics_bundle=metrics_bundle,
            fit_seconds=fit_seconds,
            predict_seconds=predict_seconds,
            tuned_params=tuned_params,
        )
        best_mape, best_name, best_pipeline, mae, mape, rmse, r2 = _record_model_metric_result(
            metrics=metrics,
            metric_row=metric_row,
            best_mape=best_mape,
            best_name=best_name,
            best_pipeline=best_pipeline,
            name=name,
            pipeline=pipeline,
        )
        LOGGER.info(
            "Completed regression candidate: %s in %.1fs | MAE=%.0f RMSE=%.0f MAPE=%.2f%% R2=%.3f",
            name,
            time.perf_counter() - start_time,
            mae,
            rmse,
            mape * 100,
            r2,
        )

    assert best_pipeline is not None
    LOGGER.info("Best regression candidate: %s", best_name)
    return {
        "candidate_metrics": sorted(metrics, key=lambda item: item["mape"]),
        "best_model": best_name,
        "best_pipeline": best_pipeline,
        "best_estimator": clone(best_pipeline.named_steps["model"]),
    }

def _fit_direct_price_regression_models(
        train_frame: pd.DataFrame,
        test_frame: pd.DataFrame,
        *,
        features: list[str],
        categorical: list[str],
        numeric: list[str],
        candidates: dict[str, object],
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    LOGGER.info(
        "Direct-price regression fit start: train=%d test=%d features=%d candidates=%s",
        len(train_frame),
        len(test_frame),
        len(features),
        ", ".join(candidates.keys()),
    )
    preprocessor = _price_preprocessor(categorical, numeric)
    metrics: list[dict[str, float | str]] = []
    best_name = ""
    best_mape = np.inf
    best_pipeline: Pipeline | None = None

    def fit_regression_pipeline(estimator: object) -> Pipeline:
        fitted_preprocessor = clone(preprocessor).fit(train_frame[features])
        if isinstance(estimator, XGBRegressor):
            transformed_train = fitted_preprocessor.transform(train_frame[features])
            transformed_test = fitted_preprocessor.transform(test_frame[features])
            fitted_model = clone(estimator).set_params(
                early_stopping_rounds=20,
                eval_metric="mae",
            )
            fitted_model.fit(
                transformed_train,
                train_frame["log_resale_price"],
                eval_set=[(transformed_test, test_frame["log_resale_price"])],
                verbose=False,
            )
            return Pipeline([("preprocessor", fitted_preprocessor), ("model", fitted_model)])

        pipeline = Pipeline([("preprocessor", clone(preprocessor)), ("model", estimator)])
        pipeline.fit(train_frame[features], train_frame["log_resale_price"])
        return pipeline

    for name, estimator in candidates.items():
        start_time = time.perf_counter()
        LOGGER.info("Fitting direct-price regression candidate: %s", name)
        tuned_params: dict[str, float | int] = {}
        candidate_estimator = estimator
        fit_start = time.perf_counter()
        pipeline = fit_regression_pipeline(candidate_estimator)
        fit_seconds = float(time.perf_counter() - fit_start)
        predict_start = time.perf_counter()
        log_predictions = pipeline.predict(test_frame[features])
        predict_seconds = float(time.perf_counter() - predict_start)
        metrics_bundle = _direct_regression_metric_bundle(test_frame, log_predictions)
        metric_row = _build_model_metric_row(
            name=name,
            metrics_bundle=metrics_bundle,
            fit_seconds=fit_seconds,
            predict_seconds=predict_seconds,
            tuned_params=tuned_params,
        )
        best_mape, best_name, best_pipeline, mae, mape, rmse, r2 = _record_model_metric_result(
            metrics=metrics,
            metric_row=metric_row,
            best_mape=best_mape,
            best_name=best_name,
            best_pipeline=best_pipeline,
            name=name,
            pipeline=pipeline,
        )
        LOGGER.info(
            "Completed direct-price regression candidate: %s in %.1fs | MAE=%.0f RMSE=%.0f MAPE=%.2f%% R2=%.3f",
            name,
            time.perf_counter() - start_time,
            mae,
            rmse,
            mape * 100,
            r2,
        )

    assert best_pipeline is not None
    LOGGER.info("Best direct-price regression candidate: %s", best_name)
    return {
        "candidate_metrics": sorted(metrics, key=lambda item: item["mape"]),
        "best_model": best_name,
        "best_pipeline": best_pipeline,
        "best_estimator": clone(best_pipeline.named_steps["model"]),
    }

def _fit_classifier_models(
        train_frame: pd.DataFrame,
        test_frame: pd.DataFrame,
        *,
        features: list[str],
        target: str,
        categorical: list[str],
        numeric: list[str],
        candidates: dict[str, object],
) -> dict[str, object]:
    LOGGER.info(
        "Classifier fit start: train=%d test=%d features=%d candidates=%s",
        len(train_frame),
        len(test_frame),
        len(features),
        ", ".join(candidates.keys()),
    )
    preprocessor = _classifier_preprocessor(categorical, numeric)
    summaries: list[dict[str, object]] = []
    best_name = ""
    best_weighted_f1 = -np.inf
    best_pipeline: Pipeline | None = None
    best_summary: dict[str, object] = {}
    best_predictions: np.ndarray | None = None

    for name, estimator in candidates.items():
        start_time = time.perf_counter()
        LOGGER.info("Fitting classifier candidate: %s", name)
        pipeline = Pipeline([("preprocessor", clone(preprocessor)), ("model", estimator)])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            pipeline.fit(train_frame[features], train_frame[target])
        preds = pipeline.predict(test_frame[features])
        precision, recall, f1, _ = precision_recall_fscore_support(
            test_frame[target],
            preds,
            average="weighted",
            zero_division=0,
        )
        summary = {
            "name": name,
            "accuracy": float(accuracy_score(test_frame[target], preds)),
            "weighted_precision": float(precision),
            "weighted_recall": float(recall),
            "weighted_f1": float(f1),
            "report": classification_report(test_frame[target], preds, output_dict=True, zero_division=0),
        }
        summaries.append(summary)
        if float(f1) > best_weighted_f1:
            best_weighted_f1 = float(f1)
            best_name = name
            best_pipeline = pipeline
            best_summary = summary
            best_predictions = preds
        LOGGER.info(
            "Completed classifier candidate: %s in %.1fs | accuracy=%.3f weighted_f1=%.3f",
            name,
            time.perf_counter() - start_time,
            summary["accuracy"],
            summary["weighted_f1"],
        )

    assert best_pipeline is not None
    assert best_predictions is not None
    LOGGER.info("Best classifier candidate: %s", best_name)
    return {
        "candidate_metrics": sorted(summaries, key=lambda item: item["weighted_f1"], reverse=True),
        "best_model": best_name,
        "best_pipeline": best_pipeline,
        "best_summary": best_summary,
        "test_predictions": best_predictions,
    }

def _normalize_subject(subject: dict[str, object]) -> dict[str, object]:
    normalized = dict(subject)
    month_value = normalized.get("transaction_month") or normalized.get("month") or TARGET_TRANSACTION[
        "transaction_month"]
    timestamp = pd.Timestamp(month_value)
    normalized["transaction_month"] = timestamp
    normalized["month"] = timestamp.strftime("%Y-%m")
    normalized.setdefault("year", float(timestamp.year))
    lease_year = normalized.get("lease_commence_date")
    if lease_year is not None and not pd.isna(lease_year):
        flat_age = float(timestamp.year - float(lease_year))
        normalized.setdefault("flat_age", flat_age)
        normalized.setdefault("age", flat_age)
        normalized.setdefault("remaining_lease_effective", float(99 - flat_age))
        normalized.setdefault("remaining_lease_years", float(99 - flat_age))
    storey_range = normalized.get("storey_range")
    if storey_range is not None and not pd.isna(storey_range):
        min_floor, max_floor = _parse_storey_bounds(storey_range)
        normalized.setdefault("min_floor_level", min_floor)
        normalized.setdefault("max_floor_level", max_floor)
    return normalized

def _subject_frame(subject: dict[str, object], features: list[str]) -> pd.DataFrame:
    normalized = _normalize_subject(subject)
    return pd.DataFrame([{feature: normalized.get(feature, np.nan) for feature in features}])

def _parse_storey_bounds(value: object) -> tuple[float, float]:
    if value is None or pd.isna(value):
        return np.nan, np.nan
    text = str(value).strip().upper()
    if " TO " not in text:
        return np.nan, np.nan
    lower, upper = text.split(" TO ", 1)
    try:
        return float(lower), float(upper)
    except ValueError:
        return np.nan, np.nan

def _augment_regression_features(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()

    if "transaction_month" in enriched.columns and "year" not in enriched.columns:
        enriched["year"] = pd.to_datetime(enriched["transaction_month"]).dt.year.astype(float)
    elif "transaction_year" in enriched.columns and "year" not in enriched.columns:
        enriched["year"] = enriched["transaction_year"].astype(float)

    if "flat_age" in enriched.columns and "age" not in enriched.columns:
        enriched["age"] = enriched["flat_age"].astype(float)

    if "remaining_lease_effective" in enriched.columns and "remaining_lease_years" not in enriched.columns:
        enriched["remaining_lease_years"] = enriched["remaining_lease_effective"].astype(float)
    if "storey_range" in enriched.columns and (
            "min_floor_level" not in enriched.columns or "max_floor_level" not in enriched.columns
    ):
        bounds = enriched["storey_range"].map(_parse_storey_bounds)
        enriched["min_floor_level"] = [bound[0] for bound in bounds]
        enriched["max_floor_level"] = [bound[1] for bound in bounds]
    return enriched

def _build_time_rebase_lookup(frame: pd.DataFrame) -> dict[pd.Timestamp, float]:
    enriched = _augment_regression_features(frame)
    valid = enriched.loc[
        enriched["floor_area_sqm"].astype(float).gt(0) & enriched["resale_price"].astype(float).gt(0),
        ["transaction_month", "resale_price", "floor_area_sqm"],
    ].copy()
    valid["transaction_month"] = pd.to_datetime(valid["transaction_month"])
    valid["price_per_sqm"] = valid["resale_price"].astype(float) / valid["floor_area_sqm"].astype(float)
    monthly = valid.groupby("transaction_month", dropna=False)["price_per_sqm"].median().sort_index()
    base_month = pd.Timestamp("1990-01-01")
    if base_month not in monthly.index:
        base_month = monthly.index.min()
    base_value = float(monthly.loc[base_month])
    if not np.isfinite(base_value) or base_value <= 0:
        base_value = float(monthly.iloc[0])
    factors = (monthly / base_value).astype(float)
    return {pd.Timestamp(month): float(value) for month, value in factors.items()}

def _attach_time_rebase_factor(frame: pd.DataFrame, time_rebase_lookup: dict[pd.Timestamp, float] | None) -> pd.DataFrame:
    enriched = frame.copy()
    if not time_rebase_lookup:
        enriched["time_rebase_factor_1990"] = 1.0
        return enriched
    transaction_month = pd.to_datetime(enriched["transaction_month"])
    mapped = transaction_month.map(lambda value: time_rebase_lookup.get(pd.Timestamp(value), np.nan))
    fallback = float(np.nanmedian(list(time_rebase_lookup.values()))) if time_rebase_lookup else 1.0
    enriched["time_rebase_factor_1990"] = mapped.fillna(fallback).astype(float)
    return enriched

def _time_rebase_factor_for_timestamp(
        timestamp: pd.Timestamp,
        time_rebase_lookup: dict[pd.Timestamp, float] | None,
) -> float:
    if not time_rebase_lookup:
        return 1.0
    return float(time_rebase_lookup.get(pd.Timestamp(timestamp), np.nanmedian(list(time_rebase_lookup.values()))))

def _with_log_price_target(
        frame: pd.DataFrame,
        *,
        time_rebase_lookup: dict[pd.Timestamp, float] | None = None,
) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    valid_area = enriched["floor_area_sqm"].astype(float) > 0
    valid_price = enriched["resale_price"].astype(float) > 0
    enriched = enriched.loc[valid_area & valid_price].copy()
    enriched["price_per_sqm"] = enriched["resale_price"].astype(float) / enriched["floor_area_sqm"].astype(float)
    enriched = _attach_time_rebase_factor(enriched, time_rebase_lookup)
    enriched["rebased_price_per_sqm_1990"] = (
        enriched["price_per_sqm"] / enriched["time_rebase_factor_1990"].astype(float)
    )
    enriched["log_price_per_sqm"] = np.log(enriched["rebased_price_per_sqm_1990"])
    return enriched

def _recover_resale_price(
        log_price_per_sqm: np.ndarray,
        floor_area_sqm: pd.Series | np.ndarray,
        time_rebase_factor: pd.Series | np.ndarray | None = None,
) -> np.ndarray:
    factor = 1.0 if time_rebase_factor is None else np.asarray(time_rebase_factor, dtype=float)
    return (
        np.exp(np.asarray(log_price_per_sqm, dtype=float))
        * factor
        * np.asarray(floor_area_sqm, dtype=float)
    )

def _recover_price_per_sqm(
        log_price_per_sqm: np.ndarray,
        time_rebase_factor: pd.Series | np.ndarray | None = None,
) -> np.ndarray:
    factor = 1.0 if time_rebase_factor is None else np.asarray(time_rebase_factor, dtype=float)
    return np.exp(np.asarray(log_price_per_sqm, dtype=float)) * factor

def _subject_floor_area_for_recovery(subject: dict[str, object], frame: pd.DataFrame) -> float:
    provided = subject.get("floor_area_sqm")
    if provided is not None and not pd.isna(provided):
        return float(provided)

    candidate = frame.loc[
        frame["flat_type"].eq(subject.get("flat_type")) & frame["town"].eq(subject.get("town")),
        "floor_area_sqm",
    ].median()
    if pd.isna(candidate):
        candidate = frame.loc[frame["flat_type"].eq(subject.get("flat_type")), "floor_area_sqm"].median()
    if pd.isna(candidate):
        candidate = frame["floor_area_sqm"].median()
    return float(candidate)

def evaluate_predictions(actual: np.ndarray | pd.Series, predicted: np.ndarray | pd.Series) -> dict[str, float | int]:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    valid_mask = np.isfinite(actual_array) & np.isfinite(predicted_array)
    if not np.all(valid_mask):
        dropped = int((~valid_mask).sum())
        LOGGER.warning("Dropping %d rows with non-finite values before scoring predictions.", dropped)
    actual_array = actual_array[valid_mask]
    predicted_array = predicted_array[valid_mask]
    if len(actual_array) == 0:
        raise ValueError("No valid prediction rows remain after removing NaN/inf values.")
    ape = np.where(
        actual_array != 0.0,
        np.abs((actual_array - predicted_array) / actual_array),
        np.nan,
    )
    return {
        "mae": float(mean_absolute_error(actual_array, predicted_array)),
        "mape": float(mean_absolute_percentage_error(actual_array, predicted_array)),
        "mdape": float(np.nanmedian(ape)) if np.isfinite(ape).any() else np.nan,
        "rmse": float(np.sqrt(mean_squared_error(actual_array, predicted_array))),
        "r2": float(r2_score(actual_array, predicted_array)),
        "sample_count": int(len(actual_array)),
    }

def _regression_metric_bundle(test_frame: pd.DataFrame, log_predictions: np.ndarray) -> dict[str, object]:
    time_rebase_factor = (
        test_frame["time_rebase_factor_1990"].astype(float).to_numpy()
        if "time_rebase_factor_1990" in test_frame.columns
        else None
    )
    recovery_floor_area = (
        test_frame["recovery_floor_area_sqm"].astype(float).to_numpy()
        if "recovery_floor_area_sqm" in test_frame.columns
        else test_frame["floor_area_sqm"].astype(float).to_numpy()
    )
    predicted_price_per_sqm = _recover_price_per_sqm(log_predictions, time_rebase_factor=time_rebase_factor)
    predicted_resale_price = predicted_price_per_sqm * recovery_floor_area
    actual_resale_price = test_frame["resale_price"].astype(float).to_numpy()
    metrics = evaluate_predictions(actual_resale_price, predicted_resale_price)
    return {
        "predicted_price_per_sqm": predicted_price_per_sqm,
        "predicted_resale_price": predicted_resale_price,
        **metrics,
    }

def _estimator_for_refit(estimator: object) -> object:
    cloned = clone(estimator)
    if isinstance(cloned, XGBRegressor):
        cloned.set_params(early_stopping_rounds=None)
    return cloned

def _write_plotly_assets(figures: dict[str, go.Figure], *, suffix: str = "") -> dict[str, dict[str, str]]:
    CHARTS.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict[str, str]] = {}
    configure_plotly_png_browser()
    for name, figure in figures.items():
        html_path = CHARTS / f"{name}{suffix}.html"
        svg_path = CHARTS / f"{name}{suffix}.svg"
        png_path = CHARTS / f"{name}{suffix}.png"
        LOGGER.info("Writing Plotly figure: %s and %s", html_path.name, svg_path.name)
        apply_standard_theme(figure)
        figure.write_html(html_path, include_plotlyjs="cdn")
        try:
            figure.write_image(svg_path, format="svg")
        except Exception:
            figure.write_image(png_path, format="png", scale=3)
        outputs[name] = {"html": str(html_path), "svg": str(svg_path), "png": str(png_path)}
    return outputs

__all__ = [
    "ModelResult",
    "_configure_logging",
    "_load_frame",
    "_price_preprocessor",
    "_classifier_preprocessor",
    "_sample_if_needed",
    "_with_log_resale_target",
    "_recover_direct_resale_price",
    "_direct_regression_metric_bundle",
    "make_temporal_split",
    "_tune_catboost_estimator",
    "_tune_xgboost_estimator",
    "_fit_regression_models",
    "_fit_direct_price_regression_models",
    "_fit_classifier_models",
    "_normalize_subject",
    "_subject_frame",
    "_parse_storey_bounds",
    "_augment_regression_features",
    "_build_time_rebase_lookup",
    "_attach_time_rebase_factor",
    "_time_rebase_factor_for_timestamp",
    "_with_log_price_target",
    "_recover_resale_price",
    "_recover_price_per_sqm",
    "_subject_floor_area_for_recovery",
    "evaluate_predictions",
    "_regression_metric_bundle",
    "_estimator_for_refit",
    "_write_plotly_assets",
]
