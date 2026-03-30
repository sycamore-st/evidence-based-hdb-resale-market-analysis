from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.cluster import MiniBatchKMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    davies_bouldin_score,
    mean_squared_error,
    silhouette_score,
)
from sklearn.pipeline import Pipeline

from src.analysis.common.plotly_standard import apply_standard_theme, load_plotly_theme
from src.analysis.section2.S2_config import (
    DEFAULT_XGBOOST_TUNING_ITERATIONS,
    QUESTION_C_HOLDOUT_MONTH_COUNT,
    QUESTION_B_OPTIONAL_FEATURES,
    QUESTION_C_CLUSTER_K_VALUES,
    QUESTION_C_FEATURES,
    QUESTION_C_TRAIN_WINDOW_MAX_YEARS,
    QUESTION_C_TRAIN_WINDOW_MIN_YEARS,
    QUESTION_C_UNSUPERVISED_CLUSTER_COUNT,
    RANDOM_STATE,
)
from src.analysis.section2.S2_helpers import (
    LOGGER,
    _classifier_preprocessor,
    _configure_logging,
    _estimator_for_refit,
    _fit_classifier_models,
    _fit_regression_models,
    _load_frame,
    _price_preprocessor,
    _recover_resale_price,
    _tune_xgboost_estimator,
    _write_plotly_assets,
)
from src.analysis.section2.section2_question_b import (
    _build_question_b_candidates,
    build_question_b_training_frame,
    get_question_b_features,
)
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS


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
    distribution_frame = sample[["flat_type", "floor_area_sqm", "resale_price"]].copy()
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


def _build_unsupervised_k_comparison(
        transformed_full: np.ndarray,
        labels_full: pd.Series,
) -> pd.DataFrame:
    max_allowed = min(int(len(transformed_full) - 1), max(QUESTION_C_CLUSTER_K_VALUES))
    k_values = [k for k in QUESTION_C_CLUSTER_K_VALUES if 2 <= k <= max_allowed]
    if not k_values:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for k in k_values:
        model = MiniBatchKMeans(n_clusters=k, n_init=5, random_state=RANDOM_STATE, batch_size=2048)
        full_clusters = model.fit_predict(transformed_full)
        cluster_names = pd.Series(full_clusters).map(lambda value: f"SEGMENT_{value}")
        mapping = (
            pd.DataFrame({"segment": cluster_names, "flat_type": labels_full.astype(str).to_numpy()})
            .groupby("segment", dropna=False)["flat_type"]
            .agg(lambda values: values.mode(dropna=True).sort_values().iloc[0] if not values.mode(dropna=True).empty else np.nan)
            .to_dict()
        )
        predicted = pd.Series(full_clusters).map(lambda value: mapping.get(f"SEGMENT_{value}", np.nan))
        valid = predicted.notna()
        accuracy = (
            float(accuracy_score(labels_full.reset_index(drop=True).loc[valid].astype(str), predicted.loc[valid].astype(str)))
            if valid.any()
            else np.nan
        )
        silhouette = float(silhouette_score(transformed_full, full_clusters)) if len(np.unique(full_clusters)) > 1 else np.nan
        dbi = float(davies_bouldin_score(transformed_full, full_clusters)) if len(np.unique(full_clusters)) > 1 else np.nan
        rows.append(
            {
                "k": int(k),
                "mapped_accuracy": accuracy,
                "inertia": float(model.inertia_),
                "silhouette_score": silhouette,
                "davies_bouldin_score": dbi,
                "matches_hdb_flat_categories": bool(int(k) == QUESTION_C_UNSUPERVISED_CLUSTER_COUNT),
            }
        )
    return pd.DataFrame(rows)


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
    sample = _prepare_question_c_frame(frame, subject_month=subject_month)
    LOGGER.info("Question C unsupervised sample prepared with %d rows", len(sample))
    categorical = ["town", "flat_model"]
    numeric = [column for column in QUESTION_C_FEATURES if column not in categorical]
    preprocessor = _classifier_preprocessor(categorical, numeric)
    transformed_full = preprocessor.fit_transform(sample[QUESTION_C_FEATURES])
    if hasattr(transformed_full, "toarray"):
        transformed_full_dense = transformed_full.toarray()
    else:
        transformed_full_dense = np.asarray(transformed_full)
    k_comparison = _build_unsupervised_k_comparison(
        transformed_full_dense,
        sample["flat_type"],
    )
    max_feasible_clusters = max(2, min(int(len(transformed_full_dense) - 1), len(sample["flat_type"].dropna().unique())))
    n_clusters = min(QUESTION_C_UNSUPERVISED_CLUSTER_COUNT, max_feasible_clusters)
    LOGGER.info("Question C unsupervised fitting MiniBatchKMeans with %d clusters", n_clusters)
    kmeans = MiniBatchKMeans(n_clusters=n_clusters, n_init=5, random_state=RANDOM_STATE, batch_size=2048)
    full_clusters = kmeans.fit_predict(transformed_full_dense)

    full_segmented = sample.copy()
    full_segmented["recovered_segment"] = pd.Series(full_clusters, index=full_segmented.index).map(
        lambda value: f"SEGMENT_{value}")
    segment_to_flat_type = (
        full_segmented.groupby("recovered_segment", dropna=False)["flat_type"]
        .agg(lambda values: values.mode(dropna=True).sort_values().iloc[0] if not values.mode(dropna=True).empty else np.nan)
        .to_dict()
    )
    full_segmented["predicted_flat_type"] = full_segmented["recovered_segment"].map(segment_to_flat_type)
    confusion_labels = sorted(sample["flat_type"].dropna().astype(str).unique().tolist())
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

    optional_features = [feature for feature in QUESTION_B_OPTIONAL_FEATURES if
                         feature in sample.columns and sample[feature].notna().any()]
    unsupervised_features = [
        "recovered_segment",
        "town",
        "flat_model",
        "floor_area_sqm",
        "year",
        "age",
        "remaining_lease_years",
        "min_floor_level",
        "max_floor_level",
        *optional_features,
    ]
    categorical_pricing = ["recovered_segment", "town", "flat_model"]
    numeric_pricing = [feature for feature in unsupervised_features if feature not in categorical_pricing]
    pricing_split = _build_question_c_split(full_segmented)
    pricing_fit = _fit_regression_models(
        pricing_split["train_frame"].assign(resale_price=pricing_split["train_frame"]["resale_price"]),
        pricing_split["test_frame"].assign(resale_price=pricing_split["test_frame"]["resale_price"]),
        features=unsupervised_features,
        categorical=categorical_pricing,
        numeric=numeric_pricing,
        candidates=_build_question_b_candidates(),
        tune_xgboost=tune_xgboost,
        xgboost_tuning_iterations=xgboost_tuning_iterations,
    )
    best_name = str(pricing_fit["best_model"])
    pricing_pipeline = Pipeline(
        [
            ("preprocessor", _price_preprocessor(categorical_pricing, numeric_pricing)),
            ("model", _estimator_for_refit(pricing_fit["best_estimator"])),
        ]
    )
    pricing_pipeline.fit(pricing_split["train_frame"][unsupervised_features], pricing_split["train_frame"]["log_price_per_sqm"])
    segment_log_predictions = pricing_pipeline.predict(pricing_split["test_frame"][unsupervised_features])
    segment_predictions = _recover_resale_price(
        segment_log_predictions,
        pricing_split["test_frame"]["floor_area_sqm"],
    )
    segment_rmse = float(np.sqrt(mean_squared_error(pricing_split["test_frame"]["resale_price"], segment_predictions)))
    known_pricing = _fit_known_flat_type_pricing_on_split(sample)

    segment_summary = (
        full_segmented
        .groupby("recovered_segment", dropna=False)
        .agg(
            transactions=("recovered_segment", "size"),
            median_price=("resale_price", "median"),
            median_floor_area=("floor_area_sqm", "median"),
            median_flat_age=("age", "median"),
        )
        .reset_index()
        .sort_values("recovered_segment")
    )
    LOGGER.info(
        "Question C unsupervised complete | pricing_model=%s pricing_rmse_delta=%.0f",
        best_name,
        segment_rmse - known_pricing["known_flat_type_rmse"],
    )
    return {
        "segment_feature": "recovered_segment",
        "cluster_count": n_clusters,
        "segment_to_flat_type_mapping": segment_to_flat_type,
        "accuracy": unsupervised_accuracy,
        "report": unsupervised_report,
        "confusion_labels": confusion_labels,
        "confusion_matrix": unsupervised_confusion.tolist(),
        "per_class_accuracy": unsupervised_per_class_accuracy,
        "pricing_model": best_name,
        "segment_summary": segment_summary,
        "k_comparison": k_comparison,
        "evaluation_scope": "full_sample_mapped_accuracy",
        "pricing_split_method": "latest_9_month_holdout_with_prior_5y_training_window",
        "train_period_start": pricing_split["train_period_start"].strftime("%Y-%m"),
        "train_period_end": pricing_split["train_period_end"].strftime("%Y-%m"),
        "holdout_period_start": pricing_split["holdout_period_start"].strftime("%Y-%m"),
        "holdout_period_end": pricing_split["holdout_period_end"].strftime("%Y-%m"),
        "holdout_month_count": pricing_split["holdout_month_count"],
        "configured_train_window_years": pricing_split["configured_train_window_years"],
        "actual_train_window_years": pricing_split["actual_train_window_years"],
        "split_holdout_months": [month.strftime("%Y-%m") for month in pricing_split["holdout_months"]],
        "pricing_with_known_flat_type_rmse": known_pricing["known_flat_type_rmse"],
        "pricing_with_recovered_segment_rmse": segment_rmse,
        "pricing_rmse_delta": segment_rmse - known_pricing["known_flat_type_rmse"],
        "test_assignments": full_segmented[
            ["transaction_month", "town", "flat_model", "flat_type", "recovered_segment", "predicted_flat_type"]
        ].copy(),
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
        title="Question 3 Unsupervised Mapped Confusion Matrix",
        xaxis_title="Mapped Predicted Flat Type",
        yaxis_title="Actual Flat Type",
    )

    k_comparison = result["unsupervised"]["k_comparison"].copy()
    fig_c_unsupervised_k = go.Figure()
    if not k_comparison.empty:
        fig_c_unsupervised_k.add_scatter(
            x=k_comparison["k"],
            y=k_comparison["inertia"],
            mode="lines+markers",
            name="Inertia",
            line={"color": theme.secondary, "width": 3},
            marker={"size": 9, "color": theme.alpha(theme.secondary, 0.42), "line": {"color": theme.secondary, "width": 1.2}},
            yaxis="y",
            hovertemplate="k=%{x}<br>Inertia=%{y:,.0f}<extra></extra>",
        )
        fig_c_unsupervised_k.add_scatter(
            x=k_comparison["k"],
            y=k_comparison["mapped_accuracy"],
            mode="lines+markers",
            name="Mapped Accuracy",
            line={"color": theme.blue, "width": 2, "dash": "dot"},
            marker={"size": 8, "color": theme.alpha(theme.blue, 0.38), "line": {"color": theme.blue, "width": 1.1}},
            yaxis="y2",
            hovertemplate="k=%{x}<br>Mapped accuracy=%{y:.3f}<extra></extra>",
        )
        for index, row in enumerate(k_comparison.itertuples()):
            fig_c_unsupervised_k.add_annotation(
                x=float(row.k),
                y=float(row.inertia),
                text=f"{float(row.inertia):,.0f}",
                showarrow=False,
                yshift=-18 if index % 2 == 0 else -34,
                font={"size": 13, "color": "#000000"},
                bgcolor="rgba(0,0,0,0)",
            )
            fig_c_unsupervised_k.add_annotation(
                x=float(row.k),
                y=float(row.mapped_accuracy),
                yref="y2",
                text=f"{float(row.mapped_accuracy):.3f}",
                showarrow=False,
                yshift=16 if index % 2 == 0 else 30,
                font={"size": 13, "color": "#000000"},
                bgcolor="rgba(0,0,0,0)",
            )
        selected_row = k_comparison.loc[k_comparison["k"].eq(result["unsupervised"]["cluster_count"])]
        if not selected_row.empty:
            selected_k = int(selected_row["k"].iloc[0])
            fig_c_unsupervised_k.add_vline(
                x=selected_k,
                line={"color": theme.accent, "width": 2, "dash": "dash"},
            )
            fig_c_unsupervised_k.add_annotation(
                x=selected_k,
                y=float(selected_row["inertia"].iloc[0]),
                text=f"k={selected_k} aligns with primary HDB flat categories",
                showarrow=True,
                arrowhead=2,
                ax=88,
                ay=-56,
                font={"size": 13, "color": "#000000"},
                bgcolor=theme.alpha(theme.surface, 0.94),
                bordercolor=theme.alpha(theme.accent, 0.55),
            )
    apply_standard_theme(
        fig_c_unsupervised_k,
        title="Question 3 Unsupervised Elbow Plot",
        xaxis_title="Cluster Count (k)",
        yaxis_title="Inertia",
    )
    fig_c_unsupervised_k.update_layout(
        margin={"l": 72, "r": 96, "t": 112, "b": 96},
        yaxis2={
            "title": "Mapped Accuracy",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        }
    )

    distribution = result["flat_type_distribution_frame"].copy()
    fig_c_floor_area = go.Figure()
    fig_c_resale_price = go.Figure()
    flat_type_counts = (
        distribution.groupby("flat_type", dropna=False)
        .size()
        .reset_index(name="transaction_count")
        .sort_values("transaction_count", ascending=False)
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
        "S2QcF4_flat_type_count": fig_c_flat_type_count,
        "S2QcF5_flat_type_floor_area_distribution": fig_c_floor_area,
        "S2QcF6_flat_type_resale_price_distribution": fig_c_resale_price,
        "S2QcF7_supervised_model_summary": fig_c_supervised,
        "S2QcF8_supervised_confusion": fig_c_supervised_confusion,
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
        f"Recovered segments: **{result['unsupervised']['cluster_count']}** to align with the primary HDB flat categories.",
        f"Unsupervised k candidates evaluated: **{len(result['unsupervised']['k_comparison'])}**.",
        (
            f"Mapped full-sample accuracy for the fixed **{result['unsupervised']['cluster_count']}-cluster** solution after segment-to-flat-type assignment: **{result['unsupervised']['accuracy']:.3f}**."
            if not pd.isna(result['unsupervised']['accuracy'])
            else "Mapped full-sample accuracy is unavailable because no segment could be assigned to a flat type."
        ),
        "The elbow plot is exported as a supporting diagnostic so the fixed 7-cluster choice can be compared against nearby k values.",
        f"Downstream pricing still uses the time-aware holdout ({result['unsupervised']['holdout_period_start']} to {result['unsupervised']['holdout_period_end']}): RMSE with known flat type vs recovered segment is **{result['unsupervised']['pricing_with_known_flat_type_rmse']:,.0f} vs {result['unsupervised']['pricing_with_recovered_segment_rmse']:,.0f}**.",
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
                   key not in {'segment_summary', 'test_assignments', 'per_class_accuracy', 'k_comparison'}},
                'segment_summary': result['unsupervised']['segment_summary'].to_dict('records'),
                'test_assignments': result['unsupervised']['test_assignments'].to_dict('records'),
                'per_class_accuracy': result['unsupervised']['per_class_accuracy'].to_dict('records'),
                'k_comparison': result['unsupervised']['k_comparison'].to_dict('records'),
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
    result["unsupervised"]["k_comparison"].to_csv(
        REPORTS / f"S2Qc_unsupervised_k_comparison{artifact_suffix}.csv",
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
    result["unsupervised"]["test_assignments"].to_csv(REPORTS / "S2Qc_unsupervised_eval_predictions.csv",
                                                      index=False)
    result["supervised"]["per_class_accuracy"].to_csv(
        REPORTS / "S2Qc_supervised_per_class_accuracy.csv",
        index=False,
    )
    result["unsupervised"]["per_class_accuracy"].to_csv(
        REPORTS / "S2Qc_unsupervised_per_class_accuracy.csv",
        index=False,
    )
    result["unsupervised"]["k_comparison"].to_csv(
        REPORTS / "S2Qc_unsupervised_k_comparison.csv",
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
