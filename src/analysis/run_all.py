from __future__ import annotations

import argparse
import json

import pandas as pd

from src.analysis.deck import build_deck_artifacts
from src.analysis.section2.S2_models import run_modeling_section
from src.analysis.section3.S3_policy import run_policy_section
from src.analysis.section1.tableau_export import export_tableau_assets
from src.common.config import DATA_PROCESSED, REPORTS, ensure_directories
from src.common.utils import write_markdown
from src.pipeline.build_resale_analysis_dataset import build_resale_analysis_dataset


def run_all(refresh: bool = False, skip_dataset: bool = False) -> dict[str, object]:
    ensure_directories()
    if not skip_dataset or not (DATA_PROCESSED / "hdb_resale_processed.parquet").exists():
        build_resale_analysis_dataset(refresh=refresh)

    frame = pd.read_parquet(DATA_PROCESSED / "hdb_resale_processed.parquet")
    export_tableau_assets(frame)
    modeling = run_modeling_section()
    policy = run_policy_section(refresh=refresh)
    deck = build_deck_artifacts()

    summary = {
        "rows": int(len(frame)),
        "years": [int(frame["transaction_year"].min()), int(frame["transaction_year"].max())],
        "modeling": modeling,
        "policy": policy,
        "deck": deck,
    }
    with (REPORTS / "run_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    write_markdown(
        REPORTS / "run_summary.md",
        [
            "# Run Summary",
            "",
            f"- Rows in processed dataset: {summary['rows']:,}",
            f"- Year coverage: {summary['years'][0]} to {summary['years'][1]}",
            f"- Best price model: {modeling['best_model']}",
            f"- Deck output: `{deck['pptx']}`",
        ],
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full case-study workflow.")
    parser.add_argument("--refresh", action="store_true", help="Re-download external sources.")
    parser.add_argument("--skip-dataset", action="store_true", help="Reuse existing processed dataset.")
    args = parser.parse_args()
    run_all(refresh=args.refresh, skip_dataset=args.skip_dataset)


if __name__ == "__main__":
    main()
