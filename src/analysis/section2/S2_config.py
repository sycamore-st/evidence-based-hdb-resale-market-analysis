from __future__ import annotations

import pandas as pd

TARGET_TRANSACTION = {
    "month": "2017-11",
    "transaction_month": pd.Timestamp("2017-11-01"),
    "flat_type": "4 ROOM",
    "town": "YISHUN",
    "flat_model": "NEW GENERATION",
    "storey_range": "10 TO 12",
    "floor_area_sqm": 91.0,
    "lease_commence_date": 1984,
    "resale_price": 550_800.0,
}

QUESTION_A_FEATURES = ["flat_type", "flat_age", "town"]
QUESTION_B_BASE_FEATURES = [
    "flat_type",
    "town",
    "flat_model",
    "floor_area_sqm",
    "year",
    "age",
    "remaining_lease_years",
    "min_floor_level",
    "max_floor_level",
]
QUESTION_B_OPTIONAL_FEATURES = [
    "distance_to_cbd_km",
    "nearest_mrt_distance_km",
    "nearest_bus_stop_distance_km",
    "nearest_school_distance_km",
    "bus_stop_count_within_1km",
    "school_count_within_1km",
]
QUESTION_C_FEATURES = [
    "town",
    "flat_model",
    "floor_area_sqm",
    "year",
    "age",
    "remaining_lease_years",
    "min_floor_level",
    "max_floor_level",
    "resale_price",
]
QUESTION_B_CONTEXT_FIELDS = [
    "block",
    "street_name",
    "building_key",
    "building_latitude",
    "building_longitude",
]

MAX_CLASSIFIER_SAMPLE = 12_000
MAX_Q3_PRICING_SAMPLE = 15_000
RANDOM_STATE = 42
DEFAULT_BLEND_WEIGHTS = {"ml": 0.6, "comps": 0.4}
DEFAULT_TEMPORAL_HOLDOUT_MONTHS = ("2014-12", "2017-11", "2026-02", "2026-03")
DEFAULT_QUESTION_B_MIN_YEAR = 2012
DEFAULT_COMPARABLE_EVAL_WORKERS = 1
DEFAULT_HDB_COMPARABLE_AREA_MAX_DIFF = 0.05
DEFAULT_HDB_COMPARABLE_AGE_YEAR_GAP = 1
DEFAULT_HDB_COMPARABLE_BUILDING_DISTANCE_KM = 0
DEFAULT_QB_LOCAL_WINDOW_MONTHS = 6
DEFAULT_QB_LOCAL_AREA_MAX_DIFF = 0.18
DEFAULT_QB_LOCAL_AGE_YEAR_GAP = 2
DEFAULT_COMPARABLE_ADJUSTMENT_MAX_MONTH_GAP = 6
QUESTION_B_XGBOOST_BEST_PARAMS = {
    "subsample": 0.75,
    "n_estimators": 340,
    "min_child_weight": 5,
    "max_depth": 8,
    "learning_rate": 0.1,
    "colsample_bytree": 1.0,
}
XGBOOST_TUNING_GRID = {
    "n_estimators": [260, 340, 420],
    "max_depth": [6, 8, 10],
    "learning_rate": [0.08, 0.1, 0.12],
    "min_child_weight": [1, 3, 5],
    "subsample": [0.75, 0.9, 1.0],
    "colsample_bytree": [0.85, 1.0],
}
DEFAULT_XGBOOST_TUNING_ITERATIONS = 12
DEFAULT_XGBOOST_TUNING_FOLDS = 3
CATBOOST_TUNING_GRID = {
    "iterations": [250, 400, 600],
    "depth": [4, 6, 8, 10],
    "learning_rate": [0.03, 0.05, 0.08, 0.1],
    "l2_leaf_reg": [1.0, 3.0, 5.0, 7.0],
}
DEFAULT_CATBOOST_TUNING_ITERATIONS = 12
QUESTION_A_TRAINING_WINDOWS = (
    ("full_history", None),
    ("recent_5y", 5),
    ("recent_3y", 3),
    ("recent_1y", 1),
)
QUESTION_A_MAIN_TRAINING_WINDOW = "recent_3y"
QUESTION_C_HOLDOUT_MONTH_COUNT = 9
QUESTION_C_TRAIN_WINDOW_MIN_YEARS = 3
QUESTION_C_TRAIN_WINDOW_MAX_YEARS = 5
QUESTION_C_UNSUPERVISED_CLUSTER_COUNT = 7
QUESTION_C_CLUSTER_K_VALUES = (2, 3, 4, 5, 6, 7, 8, 9, 10)

MAX_REGRESSION_SAMPLE: int | None = None
QUESTION_A_OFFICIAL_FEATURES = QUESTION_A_FEATURES.copy()
QUESTION_A_DIAGNOSTIC_FEATURES = [
    "year",
    "town",
    "flat_type",
    "flat_age",
    "floor_area_sqm",
    "min_floor_level",
    "max_floor_level",
]
QUESTION_A_IMPUTATION_FEATURES = ["floor_area_sqm", "min_floor_level", "max_floor_level"]
QUESTION_A_IMPUTATION_METHODS = ("avg", "p25", "p75", "most_frequent", "null")
QUESTION_A_IMPUTATION_MIN_GROUP_SIZE = 5
