from __future__ import annotations

import argparse
import json

from src.analysis.section3.section3_question_a import analyze_town_value
from src.analysis.section3.section3_question_a import rebuild_question_a_figures
from src.analysis.section3.section3_question_b import analyze_flat_sizes
from src.analysis.section3.section3_question_b import rebuild_question_b_figures
from src.analysis.section3.section3_question_c import analyze_dtl2
from src.analysis.section3.section3_question_c import rebuild_question_c_figures
from src.analysis.section3.section3_question_d import analyze_coe_link
from src.analysis.section3.section3_question_d import rebuild_question_d_figures
from src.analysis.section3.S3_helpers import (
    CHARTS,
    LOGGER,
    REPORTS,
    SECTION3_FIGURE_REPORTS,
    configure_logging,
    display_town_name,
    format_chart_list,
    load_frame,
    load_saved_policy_summary,
    set_write_html,
)
from src.common.utils import write_markdown


def rebuild_policy_figures() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    SECTION3_FIGURE_REPORTS.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Rebuilding Section 3 figures from saved CSV reports")
    rebuild_question_a_figures()
    rebuild_question_b_figures()
    rebuild_question_c_figures()
    rebuild_question_d_figures()


def build_policy_section_lines(summary: dict[str, object]) -> list[str]:
    question_a = summary.get("question_a", summary.get("yishun"))
    sizes = summary["flat_sizes"]
    dtl2 = summary["dtl2"]
    coe = summary["coe"]
    target_town = question_a["target_town"]
    display_town = display_town_name(target_town)
    return [
        "# Section 3: Policy Analysis",
        "",
        f"## A. Is {display_town} the cheapest?",
        f"Banner statement: {question_a['banner_statement']}",
        "Question framing: 'Cheapest' can mean the lowest total ticket price or the lowest price per sqm after accounting for flat size.",
        f"Hypothesis: {question_a['hypothesis']}",
        f"Method: {question_a['method']}",
        f"Charts to show: {format_chart_list(question_a['charts'])}.",
        f"How to present the charts: {' '.join(question_a['chart_commentary'])}",
        f"Controls/confounders addressed: {', '.join(question_a['controls'])}.",
        f"Result: weighted gap versus peer median is **{question_a['weighted_gap_vs_peer_median_psm']:.1f} SGD/sqm**; the adjusted {display_town} effect is **{question_a['target_effect_pct']:.1f}%** (95% CI {question_a['target_effect_pct_ci_low']:.1f}% to {question_a['target_effect_pct_ci_high']:.1f}%, p-value {question_a['target_coef_pvalue']:.4f}); and the adjusted town-effect rank is **#{question_a['adjusted_rank_by_town_effect']}**.",
        f"Interpretation: {question_a['interpretation']}",
        f"Limitations: {' '.join(question_a['limitations'])}",
        "",
        "## B. Are flats getting smaller?",
        f"Banner statement: {sizes['banner_statement']}",
        "Question framing: a falling national average can come either from genuine shrinkage within flat types or from a changing mix of flat types being sold.",
        f"Hypothesis: {sizes['hypothesis']}",
        f"Method: {sizes['method']}",
        f"Charts to show: {format_chart_list(sizes['charts'])}.",
        f"How to present the charts: {' '.join(sizes['chart_commentary'])}",
        f"Controls/confounders addressed: {', '.join(sizes['controls'])}.",
        f"Result: raw slope is **{sizes['overall_slope_sqm_per_completion_year']:.3f} sqm/year**, average within-type slope is **{sizes['average_within_type_slope_sqm_per_completion_year']:.3f} sqm/year**, and the controlled year coefficient is **{sizes['controlled_completion_year_trend_coef']:.3f}** (p-value {sizes['controlled_completion_year_trend_pvalue']:.4f}).",
        f"Interpretation: {sizes['interpretation']}",
        f"Limitations: {' '.join(sizes['limitations'])}",
        "",
        "## C. Did Downtown Line Stage 2 raise prices?",
        f"Banner statement: {dtl2['banner_statement']}",
        "Question framing: we need a before-vs-after comparison against a credible control group, and the parallel-trends check matters as much as the treatment effect.",
        f"Hypothesis: {dtl2['hypothesis']}",
        f"Method: {dtl2['method']}",
        f"Charts to show: {format_chart_list(dtl2['charts'])}.",
        f"How to present the charts: {' '.join(dtl2['chart_commentary'])}",
        f"Controls/confounders addressed: {', '.join(dtl2['controls'])}.",
        f"Result: DiD interaction is **{dtl2['did_effect_pct']:.1%}** (p-value {dtl2['did_pvalue']:.4f}); pre-trend differential is **{dtl2['pretrend_effect_log_points_per_year']:.4f} log points/year** (p-value {dtl2['pretrend_pvalue']:.4f}).",
        f"Interpretation: {dtl2['interpretation']}",
        f"Limitations: {' '.join(dtl2['limitations'])}",
        "",
        "## D. Are Sengkang and Punggol unusually sensitive to COE prices?",
        f"Banner statement: {coe['banner_statement']}",
        "Question framing: the online claim is that buyers choose farther-out towns partly because lower housing costs support car ownership, so the real test is whether Sengkang and Punggol respond more to COE than central towns do.",
        f"Hypothesis: {coe['hypothesis']}",
        f"Method: {coe['method']}",
        f"Charts to show: {format_chart_list(coe['charts'])}.",
        f"How to present the charts: {' '.join(coe['chart_commentary'])}",
        f"Controls/confounders addressed: {', '.join(coe['controls'])}.",
        f"Result: central-town COE elasticity is **{coe['central_town_coe_elasticity']:.4f}**, the extra Sengkang/Punggol sensitivity is **{coe['relative_far_town_coe_effect']:.4f}** (p-value {coe['relative_far_town_coe_effect_pvalue']:.4f}), and the implied total Sengkang/Punggol elasticity is **{coe['far_town_total_coe_elasticity']:.4f}** using COE data sourced from **{coe['source']}**.",
        f"Coefficient explanation: {coe['coefficient_explanations'][0]['plain_label']} means {coe['coefficient_explanations'][0]['plain_english']} {coe['coefficient_explanations'][1]['plain_label']} means {coe['coefficient_explanations'][1]['plain_english']} {coe['coefficient_explanations'][2]['plain_label']} means {coe['coefficient_explanations'][2]['plain_english']}",
        f"Interpretation: {coe['interpretation']}",
        f"Limitations: {' '.join(coe['limitations'])}",
    ]


def run_policy_section(
        refresh: bool = False,
        *,
        reuse_reports: bool = False,
        figures_only: bool = False,
        skip_html: bool = False,
) -> dict[str, object]:
    set_write_html(not skip_html)
    CHARTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    if figures_only:
        rebuild_policy_figures()
        return load_saved_policy_summary() if (REPORTS / "policy_summary.json").exists() else {}

    if reuse_reports:
        summary = load_saved_policy_summary()
        rebuild_policy_figures()
        write_markdown(REPORTS / "policy_summary.md", build_policy_section_lines(summary))
        return summary

    frame = load_frame()
    question_a = analyze_town_value(frame, target_town="YISHUN")
    flat_sizes = analyze_flat_sizes(frame)
    dtl2 = analyze_dtl2(frame)
    coe = analyze_coe_link(frame, refresh=refresh)

    summary = {"question_a": question_a, "flat_sizes": flat_sizes, "dtl2": dtl2, "coe": coe}
    with (REPORTS / "policy_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    write_markdown(REPORTS / "policy_summary.md", build_policy_section_lines(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Section 3 policy analysis only.")
    parser.add_argument("--refresh", action="store_true", help="Refresh COE source data before rebuilding Section 3 outputs.")
    parser.add_argument("--skip-html", action="store_true", help="Skip writing HTML wrappers for Section 3 charts.")
    parser.add_argument("--reuse-reports", action="store_true", help="Reuse saved Section 3 reports and figure CSVs to rebuild outputs without rerunning the analysis.")
    parser.add_argument("--figures-only", action="store_true", help="Rebuild Section 3 figures from saved figure CSVs only.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()
    configure_logging(args.log_level)
    run_policy_section(
        refresh=args.refresh,
        reuse_reports=args.reuse_reports,
        figures_only=args.figures_only,
        skip_html=args.skip_html,
    )


if __name__ == "__main__":
    main()
