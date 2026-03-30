from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.analysis.section2.S2_config import DEFAULT_XGBOOST_TUNING_ITERATIONS
from src.analysis.section2.S2_helpers import _configure_logging, _load_frame, _write_plotly_assets
from src.analysis.section2.S2_ppt_summary import write_section2_ppt_summaries
from src.analysis.section2.section2_question_a import run_question_a_workflow
from src.analysis.section2.section2_question_b import run_question_b_workflow
from src.analysis.section2.section2_question_c import run_question_c_workflow
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS
from src.common.utils import write_markdown


def run_modeling_section(
        *,
        question_b_options: dict[str, object] | None = None,
        question: str = "all",
        skip_plotly: bool = False,
        tune_xgboost: bool = False,
        xgboost_tuning_iterations: int = DEFAULT_XGBOOST_TUNING_ITERATIONS,
) -> dict[str, object]:
    _configure_logging()
    REPORTS.mkdir(parents=True, exist_ok=True)
    overall_start = time.perf_counter()
    frame = _load_frame()
    question_b_options = question_b_options or {}
    artifact_suffix = "_baseline" if question_b_options.get("baseline_only") else ""
    selected_questions = {"a", "b", "c"} if question == "all" else {question}

    results: dict[str, object] = {}
    plotly_figures: dict[str, object] = {}
    summary_lines = ["# Section 2: Data Modeling", ""]
    supporting_outputs = ["Supporting outputs:"]

    if "a" in selected_questions:
        question_a = run_question_a_workflow(
            frame,
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
            artifact_suffix=artifact_suffix,
        )
        results["question_a"] = question_a["result"]
        plotly_figures.update(question_a["figures"])
        summary_lines.extend(question_a["summary_lines"])
        supporting_outputs.extend(question_a["supporting_outputs"])

    if "b" in selected_questions:
        question_b = run_question_b_workflow(
            frame,
            question_b_options=question_b_options,
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
            artifact_suffix=artifact_suffix,
        )
        results["question_b"] = question_b["result"]
        plotly_figures.update(question_b["figures"])
        summary_lines.extend(question_b["summary_lines"])
        supporting_outputs.extend(question_b["supporting_outputs"])

    if "c" in selected_questions:
        question_c = run_question_c_workflow(
            frame,
            tune_xgboost=tune_xgboost,
            xgboost_tuning_iterations=xgboost_tuning_iterations,
            artifact_suffix=artifact_suffix,
        )
        results["question_c"] = question_c["result"]
        plotly_figures.update(question_c["figures"])
        summary_lines.extend(question_c["summary_lines"])
        supporting_outputs.extend(question_c["supporting_outputs"])

    plotly_paths: dict[str, dict[str, str]] = {}
    if not skip_plotly and plotly_figures:
        plotly_paths = _write_plotly_assets(plotly_figures, suffix=artifact_suffix)
        summary_lines.append("Plotly chart outputs:")
        for paths in plotly_paths.values():
            summary_lines.append(f"- `{Path(paths['html']).name}` and `{Path(paths['svg']).name}`")
        summary_lines.append("")
    elif skip_plotly:
        summary_lines.extend(["Plotly chart outputs were skipped for this run.", ""])

    ppt_summary_paths = write_section2_ppt_summaries(results, artifact_suffix=artifact_suffix)
    if ppt_summary_paths:
        summary_lines.extend(["PPT-ready markdown summaries:", *[f"- `{Path(path).name}`" for path in ppt_summary_paths.values()], ""])

    summary_lines.extend(supporting_outputs)
    write_markdown(REPORTS / f"S2_modeling_summary{artifact_suffix}.md", summary_lines)

    response: dict[str, object] = {
        "plotly_outputs": plotly_paths,
        "ppt_summary_outputs": ppt_summary_paths,
        "artifact_suffix": artifact_suffix,
        "question": question,
        "skip_plotly": skip_plotly,
        "tune_xgboost": tune_xgboost,
        "xgboost_tuning_iterations": xgboost_tuning_iterations,
    }
    if "question_a" in results:
        response["question_a"] = {key: value for key, value in results["question_a"].items() if key not in {"model_pipeline", "diagnostic_model_pipeline"}}
        response["best_model"] = results["question_a"]["best_model"]
    if "question_b" in results:
        response["question_b"] = {key: value for key, value in results["question_b"].items() if key not in {"comparables_frame", "explorer_frame"}}
        response.setdefault("best_model", results["question_b"]["best_model"])
    if "question_c" in results:
        response["question_c"] = {
            "supervised": {key: value for key, value in results["question_c"]["supervised"].items() if key != "test_predictions"},
            "unsupervised": {
                **{key: value for key, value in results["question_c"]["unsupervised"].items() if key not in {"segment_summary", "test_assignments"}},
                "segment_summary": results["question_c"]["unsupervised"]["segment_summary"].to_dict("records"),
            },
            "flat_type_distribution_summary": results["question_c"]["flat_type_distribution_summary"].to_dict("records"),
        }
        response.setdefault("best_model", results["question_c"]["supervised"]["best_model"])
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run Section 2 modeling outputs.")
    comparable_group = parser.add_mutually_exclusive_group()
    comparable_group.add_argument("--baseline-only", action="store_true", help="Run Question 2 without comparables or optional POI/location features.")
    comparable_group.add_argument("--with-comparables", action="store_true", help="Enable the slower comparable-sales workflow for Question 2.")
    parser.add_argument("--question", choices=["all", "a", "b", "c"], default="all", help="Run all of Section 2 or only a single question workflow.")
    parser.add_argument("--skip-plotly", action="store_true", help="Skip writing Plotly HTML artifacts.")
    parser.add_argument("--tune-xgboost", action="store_true", help="Enable lightweight XGBoost tuning for Questions 2 and 3.")
    parser.add_argument("--xgboost-tuning-iterations", type=int, default=DEFAULT_XGBOOST_TUNING_ITERATIONS, help="Number of sampled parameter sets when XGBoost tuning is enabled.")
    args = parser.parse_args()
    question_b_options = {
        "baseline_only": bool(args.baseline_only),
        "use_comparables": bool(args.with_comparables),
    }
    response = run_modeling_section(
        question_b_options=question_b_options,
        question=args.question,
        skip_plotly=args.skip_plotly,
        tune_xgboost=args.tune_xgboost,
        xgboost_tuning_iterations=args.xgboost_tuning_iterations,
    )
    with (REPORTS / "S2_response.json").open("w", encoding="utf-8") as handle:
        json.dump(response, handle, indent=2, default=str)
