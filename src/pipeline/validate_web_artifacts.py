from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.config import WEB_MODEL_ARTIFACTS, WEB_OVERVIEW_ARTIFACTS, WEB_POLICY_ARTIFACTS
from src.pipeline.web_artifacts import REQUIRED_FILES, WEB_SECTIONS


SECTION_DIRS = {
    "overview": WEB_OVERVIEW_ARTIFACTS,
    "policy": WEB_POLICY_ARTIFACTS,
    "model": WEB_MODEL_ARTIFACTS,
}

BASE_KEYS = {"dataset_version", "generated_at", "source_coverage_end"}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_web_artifacts() -> None:
    for section in WEB_SECTIONS:
        section_dir = SECTION_DIRS[section]
        for filename in REQUIRED_FILES:
            path = section_dir / f"{filename}.json"
            _require(path.exists(), f"Missing required artifact: {path}")
            payload = _read_json(path)
            _require(BASE_KEYS.issubset(payload.keys()), f"{path} is missing required metadata keys.")

            if filename == "summary":
                _require("cards" in payload and isinstance(payload["cards"], list), f"{path} must contain a cards list.")
                _require("headline" in payload and payload["headline"], f"{path} must contain a headline.")
            elif filename == "timeseries":
                _require("series" in payload and isinstance(payload["series"], list), f"{path} must contain a series list.")
            elif filename == "filters":
                _require("filters" in payload and isinstance(payload["filters"], list), f"{path} must contain a filters list.")
            elif filename == "metadata":
                _require(payload.get("section") == section, f"{path} section must be `{section}`.")
                _require("record_count" in payload, f"{path} must contain record_count.")

    print("Web artifacts validated successfully.", flush=True)


def main() -> None:
    validate_web_artifacts()


if __name__ == "__main__":
    main()
