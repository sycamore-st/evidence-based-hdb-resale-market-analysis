from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.common.config import DATA_PROCESSED, SECTION1_OUTPUT_RESULTS, ensure_directories

TABLEAU = SECTION1_OUTPUT_RESULTS


BUILDING_PIPELINE_STAGE_FILES = {
    "transactions_base": DATA_PROCESSED / "hdb_transactions_base.parquet",
    "town_city_area_lookup": DATA_PROCESSED / "town_city_area_lookup.parquet",
    "building_master_base": DATA_PROCESSED / "building_master_base.parquet",
    "building_master_with_poi": DATA_PROCESSED / "building_master_with_poi.parquet",
    "transaction_building_matches": DATA_PROCESSED / "transaction_building_matches.parquet",
    "building_poi_summary": DATA_PROCESSED / "building_poi_summary.parquet",
}


def log_step(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def ensure_pipeline_directories() -> None:
    ensure_directories()
    TABLEAU.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)


def save_stage(frame: pd.DataFrame, key: str) -> Path:
    path = BUILDING_PIPELINE_STAGE_FILES[key]
    frame.to_parquet(path, index=False)
    log_step(f"Saved stage `{key}` to {path}.")
    return path


def load_stage(key: str) -> pd.DataFrame:
    path = BUILDING_PIPELINE_STAGE_FILES[key]
    if not path.exists():
        raise FileNotFoundError(f"Missing stage file: {path}")
    log_step(f"Loading stage `{key}` from {path}.")
    return pd.read_parquet(path)


def write_labeled_csv(frame: pd.DataFrame, path: Path, labeler) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    labeler(frame).to_csv(path, index=False)
    log_step(f"Wrote {path}")
    return path
