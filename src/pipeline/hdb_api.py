from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.common.config import (
    BUS_STOP_DATASET_ID,
    COE_DATASET_ID,
    DATA_RAW,
    HDB_API_PAGE_SIZE,
    HDB_ARTIFACTS,
    HDB_BUILDING_DATASET_ID,
    HDB_COLLECTION_ID,
    MRT_DATASET_ID,
    PLANNING_AREA_DATASET_ID,
    SCHOOL_ZONE_DATASET_ID,
)

API_TIMEOUT = 60
MAX_RETRIES = 6


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "evidence-based-hdb-resale-market-analysis/0.1"})
    return session


def _get_with_backoff(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    session: requests.Session | None = None,
) -> requests.Response:
    active_session = session or _session()
    response = None
    for attempt in range(MAX_RETRIES):
        response = active_session.get(url, params=params, timeout=API_TIMEOUT)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        retry_after = float(response.headers.get("Retry-After", "0") or 0)
        sleep_seconds = retry_after if retry_after > 0 else min(2**attempt, 30)
        time.sleep(sleep_seconds)
    raise RuntimeError(f"Exceeded retry budget for {url} with params={params}.")


def fetch_collection_metadata(refresh: bool = False) -> dict[str, Any]:
    cache_path = DATA_RAW / "collection_189_metadata.json"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    url = f"https://api-production.data.gov.sg/v2/public/api/collections/{HDB_COLLECTION_ID}/metadata"
    response = _session().get(url, timeout=API_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def fetch_dataset_metadata(dataset_id: str, refresh: bool = False) -> dict[str, Any]:
    cache_path = DATA_RAW / f"{dataset_id}_metadata.json"
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    url = f"https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/metadata"
    response = _session().get(url, timeout=API_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def fetch_datastore_dataset(dataset_id: str, refresh: bool = False) -> pd.DataFrame:
    cache_path = DATA_RAW / f"{dataset_id}.csv"
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path)

    session = _session()
    open_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    try:
        poll_response = _get_with_backoff(open_url, session=session)
        poll_payload = poll_response.json()
        if poll_payload.get("code") == 0 and poll_payload.get("data", {}).get("url"):
            download_url = poll_payload["data"]["url"]
            download_response = _get_with_backoff(download_url, session=session)
            cache_path.write_bytes(download_response.content)
            return pd.read_csv(cache_path)
    except Exception:
        pass

    url = "https://data.gov.sg/api/action/datastore_search"
    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "resource_id": dataset_id,
            "limit": HDB_API_PAGE_SIZE,
            "offset": offset,
        }
        response = _get_with_backoff(url, params=params, session=session)
        payload = response.json()
        result = payload["result"]
        batch = result["records"]
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        if offset >= result["total"]:
            break
        time.sleep(0.2)

    frame = pd.DataFrame(rows).drop(columns=["_id"], errors="ignore")
    frame.to_csv(cache_path, index=False)
    return frame


def fetch_open_dataset_file(dataset_id: str, refresh: bool = False) -> Path:
    cache_dir = DATA_RAW / dataset_id
    extracted_dir = cache_dir / "extracted"
    if extracted_dir.exists() and any(extracted_dir.iterdir()) and not refresh:
        return extracted_dir

    cache_dir.mkdir(parents=True, exist_ok=True)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    poll_url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
    response = _get_with_backoff(poll_url)
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"Open dataset poll failed for {dataset_id}: {payload}")

    download_url = payload["data"]["url"]
    download_response = _get_with_backoff(download_url)
    content = download_response.content

    archive_path = cache_dir / "download.bin"
    archive_path.write_bytes(content)
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            archive.extractall(extracted_dir)
    else:
        target = extracted_dir / "dataset.geojson"
        target.write_bytes(content)
    return extracted_dir


def fetch_all_hdb_raw(refresh: bool = False) -> dict[str, pd.DataFrame]:
    fetch_collection_metadata(refresh=refresh)
    frames: dict[str, pd.DataFrame] = {}
    for artifact in HDB_ARTIFACTS:
        fetch_dataset_metadata(artifact.dataset_id, refresh=refresh)
        frames[artifact.slug] = fetch_datastore_dataset(artifact.dataset_id, refresh=refresh)
    return frames


def fetch_coe_raw(refresh: bool = False) -> pd.DataFrame:
    return fetch_datastore_dataset(COE_DATASET_ID, refresh=refresh)


def fetch_mrt_dataset_dir(refresh: bool = False) -> Path:
    return fetch_open_dataset_file(MRT_DATASET_ID, refresh=refresh)


def fetch_bus_stop_dataset_dir(refresh: bool = False) -> Path:
    return fetch_open_dataset_file(BUS_STOP_DATASET_ID, refresh=refresh)


def fetch_school_zone_dataset_dir(refresh: bool = False) -> Path:
    return fetch_open_dataset_file(SCHOOL_ZONE_DATASET_ID, refresh=refresh)


def fetch_hdb_building_dataset_dir(refresh: bool = False) -> Path:
    return fetch_open_dataset_file(HDB_BUILDING_DATASET_ID, refresh=refresh)


def fetch_planning_area_dataset_dir(refresh: bool = False) -> Path:
    return fetch_open_dataset_file(PLANNING_AREA_DATASET_ID, refresh=refresh)
