from __future__ import annotations

import json
from pathlib import Path

from src.common.config import ensure_directories
from src.pipeline.web_artifacts import REQUIRED_FILES, artifact_directory, build_web_artifact_bundle


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def publish_web_artifacts() -> None:
    ensure_directories()
    bundle = build_web_artifact_bundle()

    for section, payloads in bundle.items():
        target = artifact_directory(section)
        for filename, payload in zip(REQUIRED_FILES, payloads, strict=True):
            _write_json(target / f"{filename}.json", payload)
            print(f"Wrote {target / f'{filename}.json'}", flush=True)



def main() -> None:
    publish_web_artifacts()


if __name__ == "__main__":
    main()
