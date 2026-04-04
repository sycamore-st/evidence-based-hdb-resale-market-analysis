from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - fallback for minimal environments
    def tqdm(iterable=None, *args, **kwargs):
        return iterable

from src.common.config import SECTION1_OUTPUT_FINAL, WEB_OVERVIEW_ARTIFACTS, ensure_directories
from src.common.utils import slugify


DASHBOARD3_OUTPUT_DIR = WEB_OVERVIEW_ARTIFACTS / "dashboard3"
TOWNS_OUTPUT_DIR = DASHBOARD3_OUTPUT_DIR / "towns"

BUILDING_OPTIMIZER_CSV = SECTION1_OUTPUT_FINAL / "building_optimizer.csv"
BUILDING_CANONICAL_CSV = SECTION1_OUTPUT_FINAL / "building_canonical_lookup.csv"
LOCATION_QUALITY_CSV = SECTION1_OUTPUT_FINAL / "location_quality.csv"
LOCATION_POI_POINTS_CSV = SECTION1_OUTPUT_FINAL / "location_poi_points.csv"
LOCATION_POI_SUMMARY_CSV = SECTION1_OUTPUT_FINAL / "location_poi_summary.csv"
HDB_BUILDINGS_GEOJSON = SECTION1_OUTPUT_FINAL / "hdb_existing_buildings.geojson"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def _normalize_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _normalize_value(value) for key, value in record.items()}


def _canonicalize_column_name(value: str) -> str:
    return slugify(value).replace("-", "_")


def _canonicalize_frame_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns={column: _canonicalize_column_name(str(column)) for column in frame.columns})


def _town_slug(town: str) -> str:
    return slugify(town)


@dataclass
class TownJsonArrayWriter:
    path: Path
    handle: Any
    is_first: bool = True

    @classmethod
    def create(cls, path: Path) -> "TownJsonArrayWriter":
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("w", encoding="utf-8")
        handle.write("[\n")
        return cls(path=path, handle=handle)

    def write(self, payload: dict[str, Any]) -> None:
        if not self.is_first:
            self.handle.write(",\n")
        json.dump(payload, self.handle, ensure_ascii=True)
        self.is_first = False

    def close(self) -> None:
        self.handle.write("\n]\n")
        self.handle.close()


def _town_paths(town_slug: str) -> dict[str, str]:
    return {
        "summary": f"towns/{town_slug}/summary.json",
        "buildings": f"towns/{town_slug}/buildings.json",
        "transactions": f"towns/{town_slug}/transactions.json",
        "location": f"towns/{town_slug}/location.json",
        "poi_points": f"towns/{town_slug}/poi_points.json",
        "poi_summary": f"towns/{town_slug}/poi_summary.json",
        "geometry": f"towns/{town_slug}/geometry.json",
    }


def _ensure_town_meta(
    metadata: dict[str, dict[str, Any]],
    town: str,
) -> dict[str, Any]:
    town_slug = _town_slug(town)
    if town_slug not in metadata:
        metadata[town_slug] = {
            "town": town,
            "slug": town_slug,
            "counts": {
                "building_rows": 0,
                "transaction_rows": 0,
                "location_rows": 0,
                "poi_point_rows": 0,
                "poi_summary_rows": 0,
                "geometry_features": 0,
            },
            "filters": {
                "transaction_years": set(),
                "budgets": set(),
                "flat_types": set(),
            },
            "files": _town_paths(town_slug),
        }
    return metadata[town_slug]


def _write_streamed_town_rows(
    source_csv: Path,
    *,
    dataset_name: str,
    count_key: str,
    metadata: dict[str, dict[str, Any]],
    chunk_size: int,
) -> None:
    writers: dict[str, TownJsonArrayWriter] = {}
    total_rows = sum(1 for _ in source_csv.open("r", encoding="utf-8")) - 1
    try:
        chunk_iter = pd.read_csv(source_csv, chunksize=chunk_size, low_memory=False)
        progress = tqdm(
            chunk_iter,
            total=max(1, (total_rows + chunk_size - 1) // chunk_size),
            desc=f"Dashboard 3 {dataset_name} chunks",
            unit="chunk",
        )
        for chunk in progress:
            chunk = _canonicalize_frame_columns(chunk)
            if "town" not in chunk.columns:
                raise ValueError(f"{source_csv} is missing a 'town' column")
            chunk = chunk.dropna(subset=["town"]).copy()
            if chunk.empty:
                continue
            chunk["town"] = chunk["town"].astype(str).str.strip()
            progress.set_postfix(rows=f"{min(total_rows, sum(meta['counts'][count_key] for meta in metadata.values()) + len(chunk)):,}")
            for town, group in chunk.groupby("town", dropna=False, sort=False):
                town_meta = _ensure_town_meta(metadata, town)
                writer = writers.get(town_meta["slug"])
                if writer is None:
                    writer = TownJsonArrayWriter.create(TOWNS_OUTPUT_DIR / town_meta["slug"] / f"{dataset_name}.json")
                    writers[town_meta["slug"]] = writer
                rows = [_normalize_record(record) for record in group.to_dict("records")]
                for row in rows:
                    writer.write(row)
                    town_meta["counts"][count_key] += 1
                    if dataset_name == "transactions":
                        year = row.get("transaction_year")
                        budget = row.get("budget")
                        flat_type = row.get("flat_type")
                        if year is not None:
                            town_meta["filters"]["transaction_years"].add(int(year))
                        if budget is not None:
                            town_meta["filters"]["budgets"].add(int(budget))
                        if flat_type:
                            town_meta["filters"]["flat_types"].add(str(flat_type))
    finally:
        for writer in writers.values():
            writer.close()


def _write_town_small_json_files(
    source_csv: Path,
    *,
    dataset_name: str,
    count_key: str,
    metadata: dict[str, dict[str, Any]],
) -> None:
    frame = _canonicalize_frame_columns(pd.read_csv(source_csv, low_memory=False))
    if frame.empty or "town" not in frame.columns:
        return
    frame = frame.dropna(subset=["town"]).copy()
    frame["town"] = frame["town"].astype(str).str.strip()
    for town, group in frame.groupby("town", dropna=False, sort=True):
        town_meta = _ensure_town_meta(metadata, town)
        payload = [_normalize_record(record) for record in group.to_dict("records")]
        town_meta["counts"][count_key] = len(payload)
        _write_json(TOWNS_OUTPUT_DIR / town_meta["slug"] / f"{dataset_name}.json", payload)


def _load_canonical_buildings_by_town() -> dict[str, dict[str, dict[str, Any]]]:
    if not BUILDING_CANONICAL_CSV.exists():
        return {}
    frame = _canonicalize_frame_columns(pd.read_csv(BUILDING_CANONICAL_CSV, low_memory=False))
    if frame.empty or "town" not in frame.columns or "building_key" not in frame.columns:
        return {}
    frame = frame.dropna(subset=["town", "building_key"]).copy()
    frame["town"] = frame["town"].astype(str).str.strip()
    by_town: dict[str, dict[str, dict[str, Any]]] = {}
    for town, group in frame.groupby("town", dropna=False, sort=True):
        by_town[town] = {
            str(record["building_key"]): _normalize_record(record)
            for record in group.to_dict("records")
            if record.get("building_key")
        }
    return by_town


def _write_town_geometry_files(metadata: dict[str, dict[str, Any]]) -> None:
    if not HDB_BUILDINGS_GEOJSON.exists():
        return
    payload = json.loads(HDB_BUILDINGS_GEOJSON.read_text(encoding="utf-8"))
    canonical_by_town = _load_canonical_buildings_by_town()
    features_by_town: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        town = props.get("Town")
        if not town:
            continue
        town_name = str(town).strip()
        building_key = props.get("Building Key")
        canonical = canonical_by_town.get(town_name, {}).get(str(building_key), {})
        enriched_feature = {
            **feature,
            "properties": {
                **props,
                "Street Name": canonical.get("street_name", props.get("Street Name")),
                "Latest Transaction Month": canonical.get("latest_transaction_month", props.get("Latest Transaction Month")),
                "Latest Transaction Year": canonical.get("latest_transaction_year", props.get("Latest Transaction Year")),
                "Latest Transaction Price": canonical.get("latest_transaction_price", props.get("Latest Transaction Price")),
                "Has Transaction Data": canonical.get("has_transaction_data", props.get("Has Transaction Data")),
                "Has Building Geometry": canonical.get("has_building_geometry", props.get("Has Building Geometry")),
            },
        }
        features_by_town[town_name].append(enriched_feature)

    for town, features in features_by_town.items():
        town_meta = _ensure_town_meta(metadata, town)
        town_meta["counts"]["geometry_features"] = len(features)
        town_payload = {
            "type": "FeatureCollection",
            "features": features,
        }
        _write_json(TOWNS_OUTPUT_DIR / town_meta["slug"] / "geometry.json", town_payload)


def _build_manifest(metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    towns = []
    all_years: set[int] = set()
    all_budgets: set[int] = set()
    all_flat_types: set[str] = set()

    for town_meta in sorted(metadata.values(), key=lambda item: item["town"]):
        years = sorted(town_meta["filters"]["transaction_years"])
        budgets = sorted(town_meta["filters"]["budgets"])
        flat_types = sorted(town_meta["filters"]["flat_types"])
        all_years.update(years)
        all_budgets.update(budgets)
        all_flat_types.update(flat_types)
        towns.append(
            {
                "town": town_meta["town"],
                "slug": town_meta["slug"],
                "counts": town_meta["counts"],
                "filters": {
                    "transaction_years": years,
                    "budgets": budgets,
                    "flat_types": flat_types,
                },
                "files": town_meta["files"],
            }
        )

    return {
        "dataset_version": f"dashboard3-web-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": _utc_now_iso(),
        "artifact_root": "artifacts/web/overview/dashboard3",
        "source_files": {
            "building_canonical_lookup": str(BUILDING_CANONICAL_CSV),
            "building_optimizer": str(BUILDING_OPTIMIZER_CSV),
            "location_quality": str(LOCATION_QUALITY_CSV),
            "location_poi_points": str(LOCATION_POI_POINTS_CSV),
            "location_poi_summary": str(LOCATION_POI_SUMMARY_CSV),
            "hdb_existing_buildings": str(HDB_BUILDINGS_GEOJSON),
        },
        "filters": {
            "towns": [town["town"] for town in towns],
            "transaction_years": sorted(all_years),
            "budgets": sorted(all_budgets),
            "flat_types": sorted(all_flat_types),
        },
        "towns": towns,
        "notes": [
            "Dashboard 3 web artifacts are sharded by town so the frontend can lazy-load only the selected town.",
            "Large CSV sources are streamed in chunks during publishing to avoid loading the full Tableau export into memory at once.",
        ],
    }


def _write_town_summaries(metadata: dict[str, dict[str, Any]]) -> None:
    for town_meta in metadata.values():
        payload = {
            "town": town_meta["town"],
            "slug": town_meta["slug"],
            "counts": town_meta["counts"],
            "filters": {
                "transaction_years": sorted(town_meta["filters"]["transaction_years"]),
                "budgets": sorted(town_meta["filters"]["budgets"]),
                "flat_types": sorted(town_meta["filters"]["flat_types"]),
            },
        }
        _write_json(TOWNS_OUTPUT_DIR / town_meta["slug"] / "summary.json", payload)


def publish_dashboard3_web_artifacts(*, chunk_size: int = 25_000) -> Path:
    ensure_directories()
    if DASHBOARD3_OUTPUT_DIR.exists():
        shutil.rmtree(DASHBOARD3_OUTPUT_DIR)
    TOWNS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    required_files = [
        BUILDING_CANONICAL_CSV,
        BUILDING_OPTIMIZER_CSV,
        LOCATION_QUALITY_CSV,
        LOCATION_POI_POINTS_CSV,
        LOCATION_POI_SUMMARY_CSV,
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        missing_joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Dashboard 3 source files are missing: {missing_joined}. "
            "Run the Section 1 dashboard exports first."
        )

    metadata: dict[str, dict[str, Any]] = {}
    _write_streamed_town_rows(
        BUILDING_CANONICAL_CSV,
        dataset_name="buildings",
        count_key="building_rows",
        metadata=metadata,
        chunk_size=chunk_size,
    )
    _write_streamed_town_rows(
        BUILDING_OPTIMIZER_CSV,
        dataset_name="transactions",
        count_key="transaction_rows",
        metadata=metadata,
        chunk_size=chunk_size,
    )
    _write_streamed_town_rows(
        LOCATION_QUALITY_CSV,
        dataset_name="location",
        count_key="location_rows",
        metadata=metadata,
        chunk_size=chunk_size,
    )
    _write_town_small_json_files(
        LOCATION_POI_POINTS_CSV,
        dataset_name="poi_points",
        count_key="poi_point_rows",
        metadata=metadata,
    )
    _write_town_small_json_files(
        LOCATION_POI_SUMMARY_CSV,
        dataset_name="poi_summary",
        count_key="poi_summary_rows",
        metadata=metadata,
    )
    _write_town_geometry_files(metadata)
    _write_town_summaries(metadata)

    manifest = _build_manifest(metadata)
    _write_json(DASHBOARD3_OUTPUT_DIR / "manifest.json", manifest)
    return DASHBOARD3_OUTPUT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish town-sharded Dashboard 3 web artifacts.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=25_000,
        help="CSV chunk size used when streaming the large Dashboard 3 exports.",
    )
    args = parser.parse_args()
    output_dir = publish_dashboard3_web_artifacts(chunk_size=args.chunk_size)
    print(f"Wrote Dashboard 3 web artifacts to {output_dir}", flush=True)


if __name__ == "__main__":
    main()
