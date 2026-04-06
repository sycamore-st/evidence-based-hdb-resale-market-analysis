from __future__ import annotations

import argparse
import gc
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.cluster import AgglomerativeClustering, Birch, MiniBatchKMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    davies_bouldin_score,
    mean_squared_error,
    silhouette_score,
)
from sklearn.metrics.pairwise import pairwise_distances_argmin
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import Pipeline

from src.analysis.common.plotly_standard import apply_standard_theme, load_plotly_theme
from src.analysis.section2.S2_config import (
    DEFAULT_XGBOOST_TUNING_ITERATIONS,
    QUESTION_C_HOLDOUT_MONTH_COUNT,
    QUESTION_C_FEATURES,
    QUESTION_C_TRAIN_WINDOW_MAX_YEARS,
    QUESTION_C_TRAIN_WINDOW_MIN_YEARS,
    QUESTION_C_UNSUPERVISED_CLUSTER_COUNT,
    RANDOM_STATE,
)
from src.analysis.section2.S2_helpers import (
    LOGGER,
    _augment_regression_features,
    _classifier_preprocessor,
    _configure_logging,
    _estimator_for_refit,
    _fit_classifier_models,
    _load_frame,
    _price_preprocessor,
    _recover_resale_price,
    _tune_xgboost_estimator,
    _with_log_price_target,
    _write_plotly_assets,
)
from src.analysis.section2.section2_question_b import (
    _build_question_b_candidates,
    build_question_b_training_frame,
    get_question_b_features,
)
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS
QUESTION_C_UNSUPERVISED_MAX_TRAIN_SAMPLE = None
QUESTION_C_UNSUPERVISED_METHOD_TRAIN_SAMPLE = {
    "kmeans": None,
    "gaussian_mixture": 5_000,
    "agglomerative": 2_000,
    "birch": 5_000,
}
QUESTION_C_UNSUPERVISED_METHODS = (
    "kmeans",
    # "gaussian_mixture",
    # "agglomerative",
    # "birch",
)
QUESTION_C_UNSUPERVISED_METRIC_SAMPLE = 5_000
QUESTION_C_UNSUPERVISED_CATEGORICAL_FEATURES = [
    # "town",
    # "block",
    # "street_name",
    # "storey_range",
    # "flat_model",
    # "remaining_lease",
    # "transaction_quarter",
    # "nearest_mrt_station",
    # "nearest_mrt_line",
    # "nearest_school_name",
    # "building_match_status",
]
QUESTION_C_UNSUPERVISED_NUMERIC_FEATURES = [
    "resale_price",
    # "year",
    # "age",
    # "lease_commence_date",
    "floor_area_sqm",
    # "remaining_lease_years",
    # "remaining_lease_proxy",
    # "remaining_lease_effective",
    # "min_floor_level",
    # "max_floor_level",
    # "town_latitude",
    # "town_longitude",
    # "distance_to_cbd_km",
    # "nearest_mrt_distance_km",
    # "nearest_bus_stop_distance_km",
    # "nearest_school_distance_km",
    # "building_latitude",
    # "building_longitude",
    # "bus_stop_count_within_1km",
    # "school_count_within_1km",
]
QUESTION_C_UNSUPERVISED_REQUIRED_COLUMNS = [
    "transaction_month",
    "flat_type",
    "resale_price",
    "floor_area_sqm",
]
QUESTION_C_UNSUPERVISED_DISPLAY_COLUMNS = [
    "transaction_month",
    "town",
    "flat_model",
    "flat_type",
    "floor_area_sqm",
    "resale_price",
]


def _compact_metric_label(value: float, *, currency: bool = False) -> str:
    if currency:
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.0f}K"
        return f"{value:.0f}"
    return f"{value:.0f}"


def _build_question_c_candidates() -> dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(max_iter=2000, solver="saga"),
    }


def _prepare_question_c_frame(frame: pd.DataFrame, *, subject_month: pd.Timestamp | None = None) -> pd.DataFrame:
    pricing_frame = build_question_b_training_frame(frame, subject_month=subject_month)
    return pricing_frame.dropna(subset=QUESTION_C_FEATURES + ["flat_type"]).copy()


def _build_question_c_split(frame: pd.DataFrame) -> dict[str, object]:
    if "transaction_month" not in frame.columns:
        raise KeyError("transaction_month is required for Question C temporal splitting.")

    months = sorted(pd.Series(frame["transaction_month"].dropna().unique()).tolist())
    if len(months) < 2:
        raise ValueError("Question C temporal split requires at least two distinct months.")

    holdout_count = min(QUESTION_C_HOLDOUT_MONTH_COUNT, max(1, len(months) - 1))
    holdout_months = months[-holdout_count:]
    holdout_start = pd.Timestamp(holdout_months[0])
    max_train_start = holdout_start - pd.DateOffset(years=QUESTION_C_TRAIN_WINDOW_MAX_YEARS)
    train_months = [
        month for month in months
        if pd.Timestamp(month) < holdout_start and pd.Timestamp(month) >= max_train_start
    ]
    if not train_months:
        raise ValueError("Question C temporal split could not find any training months before the holdout window.")

    train_frame = frame.loc[frame["transaction_month"].isin(train_months)].copy()
    test_frame = frame.loc[frame["transaction_month"].isin(holdout_months)].copy()
    if train_frame.empty or test_frame.empty:
        raise ValueError("Question C temporal split produced an empty train or test frame.")

    observed_train_months = sorted(pd.Series(train_frame["transaction_month"].dropna().unique()).tolist())
    observed_holdout_months = sorted(pd.Series(test_frame["transaction_month"].dropna().unique()).tolist())
    observed_train_start = pd.Timestamp(observed_train_months[0])
    actual_train_window_years = round((holdout_start - observed_train_start).days / 365.25, 2)
    return {
        "train_mask": frame["transaction_month"].isin(train_months),
        "test_mask": frame["transaction_month"].isin(holdout_months),
        "train_months": [pd.Timestamp(month) for month in observed_train_months],
        "holdout_months": [pd.Timestamp(month) for month in observed_holdout_months],
        "train_frame": train_frame,
        "test_frame": test_frame,
        "train_period_start": observed_train_start,
        "train_period_end": pd.Timestamp(observed_train_months[-1]),
        "holdout_period_start": holdout_start,
        "holdout_period_end": pd.Timestamp(observed_holdout_months[-1]),
        "holdout_month_count": len(observed_holdout_months),
        "configured_train_window_years": {
            "min": QUESTION_C_TRAIN_WINDOW_MIN_YEARS,
            "max": QUESTION_C_TRAIN_WINDOW_MAX_YEARS,
        },
        "actual_train_window_years": actual_train_window_years,
    }


def _build_question_c_flat_type_distribution(
        frame: pd.DataFrame,
        *,
        subject_month: pd.Timestamp | None = None,
) -> dict[str, pd.DataFrame]:
    sample = _prepare_question_c_frame(frame, subject_month=subject_month)
    distribution_columns = [
        column for column in ["flat_type", "floor_area_sqm", "resale_price", "town", "flat_model"]
        if column in sample.columns
    ]
    distribution_frame = sample[distribution_columns].copy()
    summary = (
        distribution_frame.groupby("flat_type", dropna=False)
        .agg(
            transaction_count=("flat_type", "size"),
            floor_area_min=("floor_area_sqm", "min"),
            floor_area_p25=("floor_area_sqm", lambda values: float(values.quantile(0.25))),
            floor_area_avg=("floor_area_sqm", "mean"),
            floor_area_p50=("floor_area_sqm", "median"),
            floor_area_p75=("floor_area_sqm", lambda values: float(values.quantile(0.75))),
            floor_area_max=("floor_area_sqm", "max"),
            resale_price_min=("resale_price", "min"),
            resale_price_p25=("resale_price", lambda values: float(values.quantile(0.25))),
            resale_price_avg=("resale_price", "mean"),
            resale_price_p50=("resale_price", "median"),
            resale_price_p75=("resale_price", lambda values: float(values.quantile(0.75))),
            resale_price_max=("resale_price", "max"),
        )
        .reset_index()
        .sort_values("flat_type")
    )
    return {
        "distribution_frame": distribution_frame,
        "distribution_summary": summary,
    }


def _prepare_question_c_unsupervised_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = _augment_regression_features(frame)
    keep_columns = [
        *QUESTION_C_UNSUPERVISED_REQUIRED_COLUMNS,
        *QUESTION_C_UNSUPERVISED_DISPLAY_COLUMNS,
        *QUESTION_C_UNSUPERVISED_CATEGORICAL_FEATURES,
        *QUESTION_C_UNSUPERVISED_NUMERIC_FEATURES,
    ]
    existing = [column for column in dict.fromkeys(keep_columns) if column in enriched.columns]
    sample = enriched[existing].dropna(subset=QUESTION_C_UNSUPERVISED_REQUIRED_COLUMNS).copy()
    return _with_log_price_target(sample)


def _columns_present_with_values(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [
        column for column in columns
        if column in frame.columns and frame[column].notna().any()
    ]


def _existing_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    return [column for column in columns if column in frame.columns]


def _get_question_c_unsupervised_clustering_features(frame: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    categorical = [
        column for column in QUESTION_C_UNSUPERVISED_CATEGORICAL_FEATURES
        if column in frame.columns and frame[column].notna().any()
    ]
    numeric = _columns_present_with_values(frame, QUESTION_C_UNSUPERVISED_NUMERIC_FEATURES)
    return categorical + numeric, categorical, numeric


def _get_question_c_unsupervised_pricing_features(
        frame: pd.DataFrame,
        *,
        segment_feature: str,
) -> tuple[list[str], list[str], list[str]]:
    base_categorical = _columns_present_with_values(frame, QUESTION_C_UNSUPERVISED_CATEGORICAL_FEATURES)
    base_numeric = _columns_present_with_values(frame, QUESTION_C_UNSUPERVISED_NUMERIC_FEATURES)
    categorical = [segment_feature, *[column for column in base_categorical if column != segment_feature and column != "flat_type"]]
    numeric = [column for column in base_numeric if column != "resale_price"]
    return categorical + numeric, categorical, numeric


def _sample_question_c_unsupervised_train(
        frame: pd.DataFrame,
        *,
        max_sample: int | None = QUESTION_C_UNSUPERVISED_MAX_TRAIN_SAMPLE,
) -> pd.DataFrame:
    if max_sample is None:
        return frame.copy()
    if len(frame) <= max_sample:
        return frame.copy()
    return frame.sample(max_sample, random_state=RANDOM_STATE)


def _sample_cluster_metric_inputs(
        transformed_features,
        labels: np.ndarray,
        *,
        max_sample: int = QUESTION_C_UNSUPERVISED_METRIC_SAMPLE,
) -> tuple[object, np.ndarray]:
    if transformed_features.shape[0] <= max_sample:
        return transformed_features, labels
    sampled_indices = np.random.default_rng(RANDOM_STATE).choice(
        transformed_features.shape[0],
        size=max_sample,
        replace=False,
    )
    return transformed_features[sampled_indices], labels[sampled_indices]


def _assign_clusters_by_centroid(
        train_features: np.ndarray,
        train_labels: np.ndarray,
        target_features: np.ndarray,
) -> np.ndarray:
    unique_labels = np.unique(train_labels)
    centroids = np.vstack([train_features[train_labels == label].mean(axis=0) for label in unique_labels])
    nearest = pairwise_distances_argmin(target_features, centroids)
    return unique_labels[nearest]


def _predict_clusters_in_chunks(
        transformed_features,
        predict_fn,
        *,
        chunk_size: int = 50_000,
        densify: bool = False,
) -> np.ndarray:
    labels: list[np.ndarray] = []
    total_rows = transformed_features.shape[0]

    for start in range(0, total_rows, chunk_size):
        stop = min(start + chunk_size, total_rows)
        chunk = transformed_features[start:stop]
        if densify:
            chunk = chunk.toarray() if hasattr(chunk, "toarray") else np.asarray(chunk)
        labels.append(np.asarray(predict_fn(chunk)))
    return np.concatenate(labels, axis=0) if labels else np.array([], dtype=int)


def _map_segments_to_flat_type_by_median_area(
        frame: pd.DataFrame,
        *,
        segment_column: str,
) -> tuple[dict[str, str], pd.DataFrame]:
    summary_aggregations: dict[str, tuple[str, str]] = {
        "transactions": (segment_column, "size"),
        "median_price": ("resale_price", "median"),
        "median_floor_area": ("floor_area_sqm", "median"),
    }
    if "age" in frame.columns:
        summary_aggregations["median_flat_age"] = ("age", "median")
    segment_summary = (
        frame.groupby(segment_column, dropna=False)
        .agg(**summary_aggregations)
        .reset_index()
        .sort_values(["median_floor_area", segment_column], ascending=[False, True], na_position="last")
        .reset_index(drop=True)
    )
    ordered_flat_types = (
        frame.groupby("flat_type", dropna=False)["floor_area_sqm"]
        .median()
        .sort_values(ascending=False)
        .index.astype(str)
        .tolist()
    )
    if not ordered_flat_types:
        return {}, segment_summary

    mapping: dict[str, str] = {}
    flat_type_count = len(ordered_flat_types)
    for index, segment in enumerate(segment_summary[segment_column].astype(str)):
        flat_type_index = min(index, flat_type_count - 1)
        mapping[str(segment)] = ordered_flat_types[flat_type_index]
    return mapping, segment_summary


def _build_segment_flat_type_crosstab(
        frame: pd.DataFrame,
        *,
        segment_column: str,
) -> pd.DataFrame:
    crosstab = pd.crosstab(
        frame[segment_column].astype(str),
        frame["flat_type"].astype(str),
        dropna=False,
    )
    crosstab.index.name = segment_column
    return crosstab.reset_index()


def _map_segments_to_flat_type_by_majority_vote(
        frame: pd.DataFrame,
        *,
        segment_column: str,
) -> dict[str, str]:
    majority = (
        frame.groupby(segment_column, dropna=False)["flat_type"]
        .agg(
            lambda values: values.astype(str).mode(dropna=True).sort_values().iloc[0]
            if not values.dropna().empty else np.nan
        )
        .to_dict()
    )
    return {str(key): str(value) for key, value in majority.items() if pd.notna(value)}


def _fit_question_c_pricing_xgboost_full_sample(
        frame: pd.DataFrame,
        *,
        segment_feature: str,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    model_frame = frame.copy()
    features, categorical, numeric = _get_question_c_unsupervised_pricing_features(
        model_frame,
        segment_feature=segment_feature,
    )
    candidate_model = _build_question_b_candidates()["xgboost"]
    tuned_params: dict[str, float | int] = {}
    candidate_model, tuned_params = _tune_xgboost_estimator(
        candidate_model,
        model_frame,
        features=features,
        categorical=categorical,
        numeric=numeric,
        tune_enabled=tune_xgboost,
        tuning_iterations=xgboost_tuning_iterations,
    )
    pipeline = Pipeline(
        [
            ("preprocessor", _price_preprocessor(categorical, numeric)),
            ("model", _estimator_for_refit(candidate_model)),
        ]
    )
    pipeline.fit(model_frame[features], model_frame["log_price_per_sqm"])
    log_predictions = pipeline.predict(model_frame[features])
    predictions = _recover_resale_price(log_predictions, model_frame["floor_area_sqm"])
    rmse = float(np.sqrt(mean_squared_error(model_frame["resale_price"], predictions)))
    return {
        "features": features,
        "categorical": categorical,
        "numeric": numeric,
        "pipeline": pipeline,
        "rmse": rmse,
        "tuned_params": tuned_params,
        "predictions": predictions,
    }


def _per_class_accuracy_table(confusion: np.ndarray, labels: list[str]) -> pd.DataFrame:
    row_totals = confusion.sum(axis=1)
    diagonal = confusion.diagonal() if confusion.size else np.array([], dtype=float)
    accuracy = np.divide(
        diagonal,
        row_totals,
        out=np.full(len(labels), np.nan, dtype=float),
        where=row_totals > 0,
    )
    return pd.DataFrame(
        {
            "flat_type": labels,
            "correct_predictions": diagonal.astype(int),
            "actual_count": row_totals.astype(int),
            "per_class_accuracy": accuracy.astype(float),
        }
    )


def _fit_known_flat_type_pricing_on_split(
        frame: pd.DataFrame,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    features, categorical, numeric = get_question_b_features(frame)
    split = _build_question_c_split(frame)
    candidate_model = _build_question_b_candidates()["xgboost"]
    tuned_params: dict[str, float | int] = {}
    candidate_model, tuned_params = _tune_xgboost_estimator(
        candidate_model,
        split["train_frame"],
        features=features,
        categorical=categorical,
        numeric=numeric,
        tune_enabled=tune_xgboost,
        tuning_iterations=xgboost_tuning_iterations,
    )
    best_name = "xgboost"
    pipeline = Pipeline(
        [
            ("preprocessor", _price_preprocessor(categorical, numeric)),
            ("model", candidate_model),
        ]
    )
    pipeline.fit(split["train_frame"][features], split["train_frame"]["log_price_per_sqm"])
    known_log_predictions = pipeline.predict(split["test_frame"][features])
    known_predictions = _recover_resale_price(known_log_predictions, split["test_frame"]["floor_area_sqm"])
    rmse = float(np.sqrt(mean_squared_error(split["test_frame"]["resale_price"], known_predictions)))
    return {
        "features": features,
        "categorical": categorical,
        "numeric": numeric,
        "split": split,
        "pipeline": pipeline,
        "best_model": best_name,
        "known_flat_type_rmse": rmse,
        "known_predictions": known_predictions,
        "candidate_metrics": [{"name": best_name, "tuned_params": tuned_params}] if tuned_params else [],
    }


def predict_flat_type_supervised(
        frame: pd.DataFrame,
        *,
        subject_month: pd.Timestamp | None = None,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    LOGGER.info("Question C supervised track start")
    sample = _prepare_question_c_frame(frame, subject_month=subject_month)
    LOGGER.info("Question C supervised sample prepared with %d rows", len(sample))
    split = _build_question_c_split(sample)
    categorical = ["town", "flat_model"]
    numeric = [column for column in QUESTION_C_FEATURES if column not in categorical]
    classifier_fit = _fit_classifier_models(
        split["train_frame"],
        split["test_frame"],
        features=QUESTION_C_FEATURES,
        target="flat_type",
        categorical=categorical,
        numeric=numeric,
        candidates=_build_question_c_candidates(),
    )

    pricing = _fit_known_flat_type_pricing_on_split(
        sample,
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )
    recovered_test = pricing["split"]["test_frame"].copy()
    recovered_test["flat_type"] = classifier_fit["test_predictions"]
    recovered_log_predictions = pricing["pipeline"].predict(recovered_test[pricing["features"]])
    recovered_predictions = _recover_resale_price(
        recovered_log_predictions,
        recovered_test["floor_area_sqm"],
    )
    recovered_rmse = float(np.sqrt(mean_squared_error(recovered_test["resale_price"], recovered_predictions)))
    best_summary = classifier_fit["best_summary"]
    confusion_labels = sorted(sample["flat_type"].dropna().astype(str).unique().tolist())
    confusion = confusion_matrix(
        split["test_frame"]["flat_type"].astype(str),
        pd.Series(classifier_fit["test_predictions"]).astype(str),
        labels=confusion_labels,
    )
    per_class_accuracy = _per_class_accuracy_table(confusion, confusion_labels)
    LOGGER.info(
        "Question C supervised complete | best_model=%s weighted_f1=%.3f pricing_rmse_delta=%.0f",
        classifier_fit["best_model"],
        best_summary["weighted_f1"],
        recovered_rmse - pricing["known_flat_type_rmse"],
    )
    return {
        "features": QUESTION_C_FEATURES,
        "candidate_metrics": [
            {
                "name": candidate["name"],
                "accuracy": candidate["accuracy"],
                "weighted_precision": candidate["weighted_precision"],
                "weighted_recall": candidate["weighted_recall"],
                "weighted_f1": candidate["weighted_f1"],
            }
            for candidate in classifier_fit["candidate_metrics"]
        ],
        "best_model": classifier_fit["best_model"],
        "accuracy": best_summary["accuracy"],
        "weighted_precision": best_summary["weighted_precision"],
        "weighted_recall": best_summary["weighted_recall"],
        "weighted_f1": best_summary["weighted_f1"],
        "report": best_summary["report"],
        "confusion_labels": confusion_labels,
        "confusion_matrix": confusion.tolist(),
        "per_class_accuracy": per_class_accuracy,
        "split_method": "latest_9_month_holdout_with_prior_5y_training_window",
        "train_period_start": split["train_period_start"].strftime("%Y-%m"),
        "train_period_end": split["train_period_end"].strftime("%Y-%m"),
        "holdout_period_start": split["holdout_period_start"].strftime("%Y-%m"),
        "holdout_period_end": split["holdout_period_end"].strftime("%Y-%m"),
        "holdout_month_count": split["holdout_month_count"],
        "configured_train_window_years": split["configured_train_window_years"],
        "actual_train_window_years": split["actual_train_window_years"],
        "split_holdout_months": [month.strftime("%Y-%m") for month in split["holdout_months"]],
        "pricing_with_known_flat_type_rmse": pricing["known_flat_type_rmse"],
        "pricing_with_recovered_flat_type_rmse": recovered_rmse,
        "pricing_rmse_delta": recovered_rmse - pricing["known_flat_type_rmse"],
        "test_predictions": recovered_test[["transaction_month", "town", "flat_model", "flat_type"]].assign(
            predicted_flat_type=classifier_fit["test_predictions"]
        ),
    }


def predict_flat_type(frame: pd.DataFrame) -> dict[str, object]:
    return predict_flat_type_supervised(frame)


def recover_flat_type_segments_unsupervised(
        frame: pd.DataFrame,
        *,
        subject_month: pd.Timestamp | None = None,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    LOGGER.info("Question C unsupervised track start")
    sample = _prepare_question_c_unsupervised_frame(frame)

    LOGGER.info("Question C unsupervised sample prepared with %d rows", len(sample))
    analysis_frame = sample.sort_values("transaction_month").reset_index(drop=True)
    features, categorical, numeric = _get_question_c_unsupervised_clustering_features(analysis_frame)

    preprocessor = _classifier_preprocessor(categorical, numeric)
    transformed_full = preprocessor.fit_transform(analysis_frame[features])
    to_dense = lambda values: values.toarray() if hasattr(values, "toarray") else np.asarray(values)
    base_cluster_limit = len(analysis_frame["flat_type"].dropna().astype(str).unique().tolist())
    _ = (tune_xgboost, xgboost_tuning_iterations)
    confusion_labels = sorted(sample["flat_type"].dropna().astype(str).unique().tolist())
    method_rows: list[dict[str, object]] = []
    best_result: dict[str, object] | None = None
    best_sort_key: tuple[float, float, float] | None = None

    for method_name in QUESTION_C_UNSUPERVISED_METHODS:
        method_fit_frame = _sample_question_c_unsupervised_train(
            analysis_frame,
            max_sample=QUESTION_C_UNSUPERVISED_METHOD_TRAIN_SAMPLE.get(
                method_name,
                QUESTION_C_UNSUPERVISED_MAX_TRAIN_SAMPLE,
            ),
        )
        transformed_fit = preprocessor.transform(method_fit_frame[features])
        fit_on_full_data = len(method_fit_frame) == len(analysis_frame)
        max_feasible_clusters = max(
            2,
            min(
                int(len(method_fit_frame) - 1),
                base_cluster_limit,
            ),
        )
        n_clusters = min(QUESTION_C_UNSUPERVISED_CLUSTER_COUNT, max_feasible_clusters)
        LOGGER.info("Question C unsupervised fitting %s with %d clusters", method_name, n_clusters)
        if method_name == "kmeans":
            model = MiniBatchKMeans(
                n_clusters=n_clusters,
                n_init=5,
                random_state=RANDOM_STATE,
                batch_size=2048,
            )
            fit_labels = model.fit_predict(transformed_fit)
            full_labels = fit_labels if fit_on_full_data else _predict_clusters_in_chunks(
                transformed_full,
                model.predict,
                densify=False,
            )
        elif method_name == "gaussian_mixture":
            transformed_fit_dense = to_dense(transformed_fit)
            model = GaussianMixture(
                n_components=n_clusters,
                covariance_type="diag",
                random_state=RANDOM_STATE,
            )
            fit_labels = model.fit_predict(transformed_fit_dense)
            full_labels = fit_labels if fit_on_full_data else _predict_clusters_in_chunks(
                transformed_full,
                model.predict,
                densify=True,
            )
        elif method_name == "agglomerative":
            transformed_fit_dense = to_dense(transformed_fit)
            model = AgglomerativeClustering(n_clusters=n_clusters, linkage="ward")
            fit_labels = model.fit_predict(transformed_fit_dense)
            full_labels = fit_labels if fit_on_full_data else _predict_clusters_in_chunks(
                transformed_full,
                lambda chunk: _assign_clusters_by_centroid(transformed_fit_dense, fit_labels, to_dense(chunk)),
                densify=False,
            )
        elif method_name == "birch":
            transformed_fit_dense = to_dense(transformed_fit)
            model = Birch(n_clusters=n_clusters)
            fit_labels = model.fit_predict(transformed_fit_dense)
            full_labels = fit_labels if fit_on_full_data else _predict_clusters_in_chunks(
                transformed_full,
                model.predict,
                densify=True,
            )
        else:
            continue

        metric_features, metric_labels = _sample_cluster_metric_inputs(transformed_fit, np.asarray(fit_labels))
        metric_features_dense = to_dense(metric_features)
        silhouette = float(silhouette_score(metric_features_dense, metric_labels)) if len(np.unique(metric_labels)) > 1 else np.nan
        dbi = float(davies_bouldin_score(metric_features_dense, metric_labels)) if len(np.unique(metric_labels)) > 1 else np.nan
        full_segmented = analysis_frame.copy()
        full_segmented["recovered_segment"] = pd.Series(full_labels, index=full_segmented.index).map(lambda value: f"SEGMENT_{value}")
        area_order_mapping, segment_summary = _map_segments_to_flat_type_by_median_area(
            full_segmented,
            segment_column="recovered_segment",
        )
        segment_crosstab = _build_segment_flat_type_crosstab(
            full_segmented,
            segment_column="recovered_segment",
        )
        segment_to_flat_type = _map_segments_to_flat_type_by_majority_vote(
            full_segmented,
            segment_column="recovered_segment",
        )
        full_segmented["predicted_flat_type"] = full_segmented["recovered_segment"].map(segment_to_flat_type)
        valid_unsupervised = full_segmented["predicted_flat_type"].notna()
        unsupervised_accuracy = (
            float(
                accuracy_score(
                    full_segmented.loc[valid_unsupervised, "flat_type"].astype(str),
                    full_segmented.loc[valid_unsupervised, "predicted_flat_type"].astype(str),
                )
            )
            if valid_unsupervised.any()
            else np.nan
        )
        unsupervised_report = (
            classification_report(
                full_segmented.loc[valid_unsupervised, "flat_type"].astype(str),
                full_segmented.loc[valid_unsupervised, "predicted_flat_type"].astype(str),
                labels=confusion_labels,
                output_dict=True,
                zero_division=0,
            )
            if valid_unsupervised.any()
            else {}
        )
        unsupervised_confusion = (
            confusion_matrix(
                full_segmented.loc[valid_unsupervised, "flat_type"].astype(str),
                full_segmented.loc[valid_unsupervised, "predicted_flat_type"].astype(str),
                labels=confusion_labels,
            )
            if valid_unsupervised.any()
            else np.zeros((len(confusion_labels), len(confusion_labels)), dtype=int)
        )
        unsupervised_per_class_accuracy = _per_class_accuracy_table(unsupervised_confusion, confusion_labels)
        method_row = {
            "method_name": method_name,
            "cluster_count": n_clusters,
            "fit_sample_size": int(len(method_fit_frame)),
            "metric_sample_size": int(len(metric_labels)),
            "accuracy": unsupervised_accuracy,
            "silhouette_score": silhouette,
            "davies_bouldin_score": dbi,
        }
        method_rows.append(method_row)
        accuracy_for_sort = -np.inf if pd.isna(unsupervised_accuracy) else float(unsupervised_accuracy)
        silhouette_for_sort = -np.inf if pd.isna(silhouette) else float(silhouette)
        dbi_for_sort = np.inf if pd.isna(dbi) else float(dbi)
        sort_key = (
            -accuracy_for_sort,
            -silhouette_for_sort,
            dbi_for_sort,
        )
        if best_sort_key is None or sort_key < best_sort_key:
            best_sort_key = sort_key
            best_result = {
                "method_name": method_name,
                "cluster_count": n_clusters,
                "fit_sample_size": int(len(method_fit_frame)),
                "metric_sample_size": int(len(metric_labels)),
                "accuracy": unsupervised_accuracy,
                "silhouette_score": silhouette,
                "davies_bouldin_score": dbi,
                "segment_to_flat_type_mapping": segment_to_flat_type,
                "segment_area_order_mapping": area_order_mapping,
                "report": unsupervised_report,
                "confusion_matrix": unsupervised_confusion.tolist(),
                "per_class_accuracy": unsupervised_per_class_accuracy,
                "segment_summary": segment_summary,
                "segment_flat_type_crosstab": segment_crosstab,
                "assignments": full_segmented[
                    _existing_columns(
                        full_segmented,
                        [
                            *QUESTION_C_UNSUPERVISED_DISPLAY_COLUMNS,
                            "recovered_segment",
                            "predicted_flat_type",
                        ],
                    )
                ].copy(),
            }
        del full_segmented, unsupervised_report, unsupervised_per_class_accuracy, segment_summary
        gc.collect()

    if not method_rows or best_result is None:
        raise ValueError("Question C unsupervised comparison produced no method results.")

    method_comparison = (
        pd.DataFrame(method_rows)
        .sort_values(["accuracy", "silhouette_score", "davies_bouldin_score"], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    best_method_name = str(best_result["method_name"])
    LOGGER.info(
        "Question C unsupervised complete | best_method=%s mapped_accuracy=%.3f silhouette=%.3f dbi=%.3f",
        best_method_name,
        float(best_result["accuracy"]),
        float(best_result["silhouette_score"]),
        float(best_result["davies_bouldin_score"]),
    )
    return {
        "segment_feature": "recovered_segment",
        "method_name": best_method_name,
        "cluster_count": int(best_result["cluster_count"]),
        "fit_sample_size": int(best_result["fit_sample_size"]),
        "metric_sample_size": int(best_result["metric_sample_size"]),
        "segment_to_flat_type_mapping": best_result["segment_to_flat_type_mapping"],
        "segment_area_order_mapping": best_result["segment_area_order_mapping"],
        "accuracy": best_result["accuracy"],
        "report": best_result["report"],
        "confusion_labels": confusion_labels,
        "confusion_matrix": best_result["confusion_matrix"],
        "per_class_accuracy": best_result["per_class_accuracy"],
        "segment_summary": best_result["segment_summary"],
        "segment_flat_type_crosstab": best_result["segment_flat_type_crosstab"],
        "method_comparison": method_comparison,
        "evaluation_scope": "full_sample_cluster_recovery",
        "sample_size": int(len(sample)),
        "assignments": best_result["assignments"],
    }


def evaluate_question3_pricing_impact(
        frame: pd.DataFrame,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    LOGGER.info("Question C combined evaluation start")
    distribution = _build_question_c_flat_type_distribution(frame)
    return {
        "supervised": predict_flat_type_supervised(
            frame,
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
        ),
        "unsupervised": recover_flat_type_segments_unsupervised(
            frame,
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
        ),
        "flat_type_distribution_frame": distribution["distribution_frame"],
        "flat_type_distribution_summary": distribution["distribution_summary"],
    }


def build_question_c_figures(result: dict[str, object]) -> dict[str, go.Figure]:
    question_c_supervised = pd.DataFrame(result["supervised"]["candidate_metrics"]).sort_values("weighted_f1", ascending=True)
    theme = load_plotly_theme()
    fig_c_supervised = go.Figure()
    fig_c_supervised.add_bar(
        x=question_c_supervised["weighted_f1"],
        y=question_c_supervised["name"],
        orientation="h",
        name="Weighted F1",
        marker_color=[theme.blue] * len(question_c_supervised),
        marker_line={"color": theme.blue, "width": 1.2},
        text=[f"{value:.3f}" for value in question_c_supervised["weighted_f1"]],
        textposition="outside",
        cliponaxis=False,
    )
    apply_standard_theme(
        fig_c_supervised,
        title="Question 3 Supervised Recovery",
        xaxis_title="Weighted F1",
        yaxis_title=None,
    )
    fig_c_supervised.update_traces(textfont={"size": 18, "color": "#000000"})
    fig_c_supervised.update_layout(bargap=0.62, showlegend=True)
    fig_c_supervised.update_xaxes(range=[0, min(1.08, question_c_supervised["weighted_f1"].max() * 1.16)])

    supervised_labels = result["supervised"]["confusion_labels"]
    fig_c_supervised_confusion = go.Figure(
        data=go.Heatmap(
            z=result["supervised"]["confusion_matrix"],
            x=supervised_labels,
            y=supervised_labels,
            colorscale=theme.heatmap_primary_scale,
            colorbar_title="Count",
            text=result["supervised"]["confusion_matrix"],
            texttemplate="%{text}",
            xgap=3,
            ygap=3,
        )
    )
    apply_standard_theme(
        fig_c_supervised_confusion,
        title="Question 3 Supervised Confusion Matrix",
        xaxis_title="Predicted Flat Type",
        yaxis_title="Actual Flat Type",
    )

    question_c_unsupervised = result["unsupervised"]["segment_summary"].sort_values("median_price", ascending=True)
    fig_c_unsupervised = go.Figure()
    fig_c_unsupervised.add_bar(
        x=question_c_unsupervised["median_price"],
        y=question_c_unsupervised["recovered_segment"],
        orientation="h",
        name="Median Price",
        marker_color=[theme.green] * len(question_c_unsupervised),
        marker_line={"color": theme.green, "width": 1.2},
        text=[f"SGD {value:,.0f}" for value in question_c_unsupervised["median_price"]],
        textposition="outside",
        cliponaxis=False,
    )
    apply_standard_theme(
        fig_c_unsupervised,
        title="Question 3 Unsupervised Segment Profiles",
        xaxis_title="Median Price (SGD)",
        yaxis_title=None,
    )
    fig_c_unsupervised.update_traces(textfont={"size": 18, "color": "#000000"})
    fig_c_unsupervised.update_layout(bargap=0.62, showlegend=True)
    fig_c_unsupervised.update_xaxes(range=[0, question_c_unsupervised["median_price"].max() * 1.22])

    unsupervised_labels = result["unsupervised"]["confusion_labels"]
    fig_c_unsupervised_confusion = go.Figure(
        data=go.Heatmap(
            z=result["unsupervised"]["confusion_matrix"],
            x=unsupervised_labels,
            y=unsupervised_labels,
            colorscale=theme.heatmap_secondary_scale,
            colorbar_title="Count",
            text=result["unsupervised"]["confusion_matrix"],
            texttemplate="%{text}",
            xgap=3,
            ygap=3,
        )
    )
    apply_standard_theme(
        fig_c_unsupervised_confusion,
        title="Question 3 Unsupervised Full-Sample Mapped Confusion Matrix",
        xaxis_title="Mapped Predicted Flat Type",
        yaxis_title="Actual Flat Type",
    )

    method_comparison = result["unsupervised"]["method_comparison"].copy()
    fig_c_unsupervised_k = go.Figure()
    if not method_comparison.empty:
        fig_c_unsupervised_k.add_bar(
            x=method_comparison["method_name"],
            y=method_comparison["silhouette_score"],
            name="Silhouette Score",
            marker_color=theme.alpha(theme.secondary, 0.58),
            marker_line={"color": theme.secondary, "width": 1.2},
            text=[f"{value:.3f}" for value in method_comparison["silhouette_score"]],
            textposition="outside",
            cliponaxis=False,
            customdata=method_comparison[["accuracy", "davies_bouldin_score", "metric_sample_size"]].to_numpy(),
            hovertemplate=(
                "Method: %{x}<br>Silhouette score: %{y:.3f}<br>Mapped full-sample accuracy: %{customdata[0]:.3f}"
                "<br>Davies-Bouldin: %{customdata[1]:.3f}<br>Metric sample size: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
        fig_c_unsupervised_k.add_scatter(
            x=method_comparison["method_name"],
            y=method_comparison["accuracy"],
            mode="lines+markers",
            name="Mapped Full-Sample Accuracy",
            line={"color": theme.blue, "width": 2, "dash": "dot"},
            marker={"size": 8, "color": theme.alpha(theme.blue, 0.38), "line": {"color": theme.blue, "width": 1.1}},
            yaxis="y2",
            hovertemplate="Method: %{x}<br>Mapped full-sample accuracy: %{y:.3f}<extra></extra>",
        )
        selected_method = str(result["unsupervised"]["method_name"])
        selected_row = method_comparison.loc[method_comparison["method_name"].eq(selected_method)]
        if not selected_row.empty:
            fig_c_unsupervised_k.add_annotation(
                x=selected_method,
                y=float(selected_row["silhouette_score"].iloc[0]),
                text=f"Selected: {selected_method}",
                showarrow=True,
                arrowhead=2,
                ax=84,
                ay=-48,
                font={"size": 13, "color": "#000000"},
                bgcolor=theme.alpha(theme.surface, 0.94),
                bordercolor=theme.alpha(theme.accent, 0.55),
            )
    apply_standard_theme(
        fig_c_unsupervised_k,
        title="Question 3 Unsupervised Method Comparison",
        xaxis_title="Unsupervised Method",
        yaxis_title="Silhouette Score",
    )
    fig_c_unsupervised_k.update_layout(
        margin={"l": 72, "r": 96, "t": 112, "b": 96},
        bargap=0.36,
        yaxis2={
            "title": "Mapped Full-Sample Accuracy",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        }
    )

    unsupervised_assignments = result["unsupervised"]["assignments"].copy()
    unsupervised_assignments["floor_area_sqft"] = unsupervised_assignments["floor_area_sqm"] * 10.7639
    fig_c_unsupervised_scatter = go.Figure()
    color_sequence = theme.color_sequence
    predicted_labels = sorted(
        unsupervised_assignments["predicted_flat_type"].dropna().astype(str).unique().tolist()
    )
    hover_columns = _existing_columns(
        unsupervised_assignments,
        ["town", "flat_model", "recovered_segment"],
    )
    for index, predicted_label in enumerate(predicted_labels):
        label_frame = unsupervised_assignments.loc[
            unsupervised_assignments["predicted_flat_type"].astype(str).eq(predicted_label)
        ]
        base_color = color_sequence[index % len(color_sequence)]
        customdata = label_frame[hover_columns].to_numpy() if hover_columns else None
        hover_lines = [
            f"Predicted flat type: {predicted_label}",
            "Floor area: %{x:.1f} sqft",
            "Resale price: SGD %{y:,.0f}",
        ]
        if "town" in hover_columns:
            hover_lines.append(f"Town: %{{customdata[{hover_columns.index('town')}]}}")
        if "flat_model" in hover_columns:
            hover_lines.append(f"Flat model: %{{customdata[{hover_columns.index('flat_model')}]}}")
        if "recovered_segment" in hover_columns:
            hover_lines.append(f"Recovered segment: %{{customdata[{hover_columns.index('recovered_segment')}]}}")
        fig_c_unsupervised_scatter.add_scatter(
            x=label_frame["floor_area_sqft"],
            y=label_frame["resale_price"],
            mode="markers",
            name=predicted_label,
            marker={
                "size": 6,
                "color": theme.alpha(base_color, 0.48),
                "line": {"color": base_color, "width": 0.6},
            },
            customdata=customdata,
            hovertemplate="<br>".join(hover_lines) + "<extra></extra>",
        )
    apply_standard_theme(
        fig_c_unsupervised_scatter,
        title="Question 3 Predicted Flat Type: Floor Area vs Resale Price",
        xaxis_title="Floor Area (sqft)",
        yaxis_title="Resale Price (SGD)",
    )
    fig_c_unsupervised_scatter.update_layout(showlegend=True)

    distribution = result["flat_type_distribution_frame"].copy()
    fig_c_floor_area = go.Figure()
    fig_c_resale_price = go.Figure()
    flat_type_counts = (
        distribution.groupby("flat_type", dropna=False)
        .size()
        .reset_index(name="transaction_count")
        .sort_values("transaction_count", ascending=True)
    )
    fig_c_flat_type_count = go.Figure()
    for index, (flat_type, group) in enumerate(distribution.groupby("flat_type", dropna=False)):
        base_color = [theme.blue, theme.primary, theme.secondary, theme.accent, theme.primary_dark][index % 5]
        fill_color = theme.alpha(base_color, 0.16)
        floor_area_median = float(group["floor_area_sqm"].median())
        resale_price_median = float(group["resale_price"].median())
        fig_c_floor_area.add_box(
            y=group["floor_area_sqm"],
            name=str(flat_type),
            boxmean=True,
            boxpoints=False,
            quartilemethod="inclusive",
            marker_color=base_color,
            line={"color": base_color},
            fillcolor=fill_color,
            opacity=1.0,
        )
        fig_c_floor_area.add_annotation(
            x=str(flat_type),
            y=floor_area_median,
            text=_compact_metric_label(floor_area_median),
            showarrow=False,
            yshift=22,
            font={"color": "#000000", "size": 14},
            bgcolor=theme.alpha(theme.surface, 0.92),
            bordercolor="rgba(0,0,0,0)",
        )
        fig_c_resale_price.add_box(
            y=group["resale_price"],
            name=str(flat_type),
            boxmean=True,
            boxpoints=False,
            quartilemethod="inclusive",
            marker_color=base_color,
            line={"color": base_color},
            fillcolor=fill_color,
            opacity=1.0,
        )
        fig_c_resale_price.add_annotation(
            x=str(flat_type),
            y=resale_price_median,
            text=_compact_metric_label(resale_price_median, currency=True),
            showarrow=False,
            yshift=22,
            font={"color": "#000000", "size": 14},
            bgcolor=theme.alpha(theme.surface, 0.92),
            bordercolor="rgba(0,0,0,0)",
        )
    fig_c_flat_type_count.add_bar(
        x=flat_type_counts["flat_type"].astype(str),
        y=flat_type_counts["transaction_count"],
        marker_color=theme.blue,
        marker_line={"color": theme.primary_dark, "width": 1},
        text=[f"{int(value):,}" for value in flat_type_counts["transaction_count"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="Flat type: %{x}<br>Transactions: %{y:,}<extra></extra>",
        showlegend=False,
    )
    apply_standard_theme(
        fig_c_floor_area,
        title="Question 3 Floor Area Distribution by Flat Type",
        xaxis_title="Flat Type",
        yaxis_title="Floor Area (sqm)",
    )
    apply_standard_theme(
        fig_c_resale_price,
        title="Question 3 Resale Price Distribution by Flat Type",
        xaxis_title="Flat Type",
        yaxis_title="Resale Price (SGD)",
    )
    apply_standard_theme(
        fig_c_flat_type_count,
        title="Question 3 Flat Type Counts",
        xaxis_title="Flat Type",
        yaxis_title="Transaction Count",
    )
    fig_c_flat_type_count.update_layout(bargap=0.28)
    return {
        "S2QcF1_unsupervised_confusion": fig_c_unsupervised_confusion,
        "S2QcF2_unsupervised_k_comparison": fig_c_unsupervised_k,
        "S2QcF3_unsupervised_segment_profile": fig_c_unsupervised,
        "S2QcF4_unsupervised_floor_area_price_scatter": fig_c_unsupervised_scatter,
        "S2QcF5_flat_type_count": fig_c_flat_type_count,
        "S2QcF6_flat_type_floor_area_distribution": fig_c_floor_area,
        "S2QcF7_flat_type_resale_price_distribution": fig_c_resale_price,
        "S2QcF8_supervised_model_summary": fig_c_supervised,
        "S2QcF9_supervised_confusion": fig_c_supervised_confusion,
    }


def build_question_c_summary_lines(result: dict[str, object]) -> list[str]:
    return [
        "## Question C: Dual Flat-Type Recovery Tracks",
        "A flat-type distribution summary is exported first so the presentation can open with descriptive box charts for floor area and transaction amount by flat type.",
        f"Flat-type descriptive summary rows: **{len(result['flat_type_distribution_summary'])}**.",
        (
            "Evaluation split: latest "
            f"**{result['supervised']['holdout_month_count']} months** "
            f"({result['supervised']['holdout_period_start']} to {result['supervised']['holdout_period_end']}) "
            "for testing, with the prior rolling training window "
            f"({result['supervised']['train_period_start']} to {result['supervised']['train_period_end']}, "
            f"**{result['supervised']['actual_train_window_years']:.2f} years** of history)."
        ),
        "",
        "### Unsupervised Track",
        f"Recovered segments per method: **{result['unsupervised']['cluster_count']}**.",
        f"Unsupervised methods evaluated: **{len(result['unsupervised']['method_comparison'])}**.",
        f"Selected unsupervised method: **{result['unsupervised']['method_name']}**.",
        f"Cluster fit sample size: **{result['unsupervised']['fit_sample_size']:,}**.",
        f"Silhouette / Davies-Bouldin metric sample size: **{result['unsupervised']['metric_sample_size']:,}**.",
        (
            f"Mapped full-sample accuracy for the selected **{result['unsupervised']['method_name']}** solution after majority-vote cluster-to-flat-type assignment: **{result['unsupervised']['accuracy']:.3f}**."
            if not pd.isna(result['unsupervised']['accuracy'])
            else "Mapped full-sample accuracy is unavailable because no segment could be assigned to a flat type."
        ),
        "A segment-by-flat-type crosstab is exported so cluster purity can be inspected directly, separate from the majority-vote mapping used for accuracy.",
        "The method comparison chart is exported so KMeans, Gaussian mixture, agglomerative clustering, and Birch can be compared directly on full-sample mapped accuracy, silhouette score, and Davies-Bouldin score.",
        "",
        "### Supervised Track",
        f"Selected classifier: **{result['supervised']['best_model']}**.",
        f"Holdout accuracy: **{result['supervised']['accuracy']:.3f}**.",
        f"Weighted precision / recall / f1: **{result['supervised']['weighted_precision']:.3f} / {result['supervised']['weighted_recall']:.3f} / {result['supervised']['weighted_f1']:.3f}**.",
        f"Downstream pricing RMSE with known flat type vs recovered flat type: **{result['supervised']['pricing_with_known_flat_type_rmse']:,.0f} vs {result['supervised']['pricing_with_recovered_flat_type_rmse']:,.0f}**.",
        "",
    ]


def run_question_c_workflow(
        frame: pd.DataFrame,
        *,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
        artifact_suffix: str = "",
) -> dict[str, object]:
    result = evaluate_question3_pricing_impact(
        frame,
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )
    with (REPORTS / f"S2Qc_flat_type_classifier{artifact_suffix}.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                **{key: value for key, value in result["supervised"].items() if key not in {"per_class_accuracy", "test_predictions"}},
                "per_class_accuracy": result["supervised"]["per_class_accuracy"].to_dict("records"),
                "test_predictions": result["supervised"]["test_predictions"].to_dict("records"),
            },
            handle,
            indent=2,
            default=str,
        )
    with (REPORTS / f"S2Qc_flat_type_unsupervised{artifact_suffix}.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                **{key: value for key, value in result['unsupervised'].items() if
                   key not in {'segment_summary', 'segment_flat_type_crosstab', 'assignments', 'per_class_accuracy', 'method_comparison'}},
                'segment_summary': result['unsupervised']['segment_summary'].to_dict('records'),
                'segment_flat_type_crosstab': result['unsupervised']['segment_flat_type_crosstab'].to_dict('records'),
                'assignments': result['unsupervised']['assignments'].to_dict('records'),
                'per_class_accuracy': result['unsupervised']['per_class_accuracy'].to_dict('records'),
                'method_comparison': result['unsupervised']['method_comparison'].to_dict('records'),
            },
            handle,
            indent=2,
            default=str,
        )
    result['flat_type_distribution_summary'].to_csv(
        REPORTS / f"S2Qc_flat_type_distribution_summary{artifact_suffix}.csv", index=False)
    result["supervised"]["per_class_accuracy"].to_csv(
        REPORTS / f"S2Qc_supervised_per_class_accuracy{artifact_suffix}.csv",
        index=False,
    )
    result["unsupervised"]["per_class_accuracy"].to_csv(
        REPORTS / f"S2Qc_unsupervised_per_class_accuracy{artifact_suffix}.csv",
        index=False,
    )
    result["unsupervised"]["segment_flat_type_crosstab"].to_csv(
        REPORTS / f"S2Qc_unsupervised_segment_flat_type_crosstab{artifact_suffix}.csv",
        index=False,
    )
    result["unsupervised"]["method_comparison"].to_csv(
        REPORTS / f"S2Qc_unsupervised_method_comparison{artifact_suffix}.csv",
        index=False,
    )
    return {
        "result": result,
        "summary_lines": build_question_c_summary_lines(result),
        "figures": build_question_c_figures(result),
        "supporting_outputs": [
            f"- `reports/S2Qc_flat_type_classifier{artifact_suffix}.json`, `reports/S2Qc_flat_type_unsupervised{artifact_suffix}.json`, and `reports/S2Qc_flat_type_distribution_summary{artifact_suffix}.csv` for S2Qc.",
        ],
    }


__all__ = [
    "_build_question_c_flat_type_distribution",
    "_fit_known_flat_type_pricing_on_split",
    "_prepare_question_c_frame",
    "build_question_c_figures",
    "build_question_c_summary_lines",
    "evaluate_question3_pricing_impact",
    "main",
    "predict_flat_type",
    "predict_flat_type_supervised",
    "recover_flat_type_segments_unsupervised",
    "run_question_c_workflow",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 2 Question C only.")
    parser.add_argument("--skip-plotly", action="store_true", help="Skip writing Plotly HTML artifacts.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    _configure_logging(args.log_level)
    REPORTS.mkdir(parents=True, exist_ok=True)
    frame = _load_frame()
    result = evaluate_question3_pricing_impact(frame)

    result["supervised"]["test_predictions"].to_csv(REPORTS / "S2Qc_supervised_eval_predictions.csv", index=False)
    result["unsupervised"]["assignments"].to_csv(REPORTS / "S2Qc_unsupervised_eval_predictions.csv", index=False)
    result["supervised"]["per_class_accuracy"].to_csv(
        REPORTS / "S2Qc_supervised_per_class_accuracy.csv",
        index=False,
    )
    result["unsupervised"]["per_class_accuracy"].to_csv(
        REPORTS / "S2Qc_unsupervised_per_class_accuracy.csv",
        index=False,
    )
    result["unsupervised"]["segment_flat_type_crosstab"].to_csv(
        REPORTS / "S2Qc_unsupervised_segment_flat_type_crosstab.csv",
        index=False,
    )
    result["unsupervised"]["method_comparison"].to_csv(
        REPORTS / "S2Qc_unsupervised_method_comparison.csv",
        index=False,
    )
    result["flat_type_distribution_summary"].to_csv(
        REPORTS / "S2Qc_flat_type_distribution_summary.csv",
        index=False,
    )
    if not args.skip_plotly:
        _write_plotly_assets(build_question_c_figures(result))


if __name__ == "__main__":
    main()
