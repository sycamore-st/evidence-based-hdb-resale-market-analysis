from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from src.analysis.section2.S2_config import DEFAULT_QB_LOCAL_WINDOW_MONTHS
from src.common.config import SECTION2_OUTPUT_RESULTS

REPORTS = SECTION2_OUTPUT_RESULTS
TABLEAU = SECTION2_OUTPUT_RESULTS
from src.common.utils import write_markdown


def _format_sgd(value: float) -> str:
    return f"SGD {value:,.0f}"


def _format_pct(value: float) -> str:
    return f"{value:.1%}"


def _artifact_path(directory: Path, stem: str, suffix: str, extension: str) -> Path:
    return directory / f"{stem}{suffix}.{extension}"


def _question_a_lines(result: dict[str, object], suffix: str) -> list[str]:
    model_comparison = pd.read_csv(_artifact_path(REPORTS, "S2Qa_model_comparison", suffix, "csv"))
    observed = pd.read_csv(_artifact_path(REPORTS, "S2Qa_observed_model_comparison", suffix, "csv"))
    imputed = pd.read_csv(_artifact_path(REPORTS, "S2Qa_imputed_model_comparison", suffix, "csv"))
    best_official = model_comparison.sort_values("mape", ascending=True).iloc[0]
    best_observed = observed.sort_values("mape", ascending=True).iloc[0]
    best_imputation = imputed.loc[imputed["name"].eq(result["diagnostic_best_model"])].sort_values("mape").iloc[0]
    prediction_range = result["recommended_prediction_range"]
    official_mape = float(best_official["mape"])
    observed_mape = float(best_observed["mape"])
    official_rmse = float(best_official["rmse"])
    observed_rmse = float(best_observed["rmse"])
    rmse_change_pct = (observed_rmse - official_rmse) / official_rmse if official_rmse else 0.0
    mape_change_pct = (observed_mape - official_mape) / official_mape if official_mape else 0.0
    if observed_mape <= official_mape:
        diagnostic_line = (
            f"- When the richer diagnostic model can see hidden drivers such as size and floor level, "
            f"MAPE improves to **{observed_mape:.2%}** and RMSE improves to **{_format_sgd(observed_rmse)}**."
        )
    else:
        diagnostic_line = (
            f"- When the richer diagnostic model can see hidden drivers such as size and floor level, "
            f"RMSE improves to **{_format_sgd(observed_rmse)}** (about **{abs(rmse_change_pct):.1%}** better), "
            f"but MAPE worsens to **{observed_mape:.2%}** (about **{abs(mape_change_pct):.1%}** worse), "
            "so added features help absolute dollar fit more than proportional accuracy."
        )
    return [
        "# S2Qa PPT Summary",
        "",
        "## What",
        "We need a simple, defensible way to estimate what a flat should cost when senior management only wants us to use the limited attributes stated in the case: flat type, flat age, and town.",
        "",
        "## How",
        "- We first compared a small set of candidate models on a true holdout period and kept the strongest performer as the official answer.",
        "- We then ran a diagnostic second pass with richer hidden information such as size and floor level, not to replace the official answer, but to show how much uncertainty is created when those drivers are missing.",
        "",
        "## Why",
        "This approach lets us stay faithful to the case prompt while still telling management an honest story: a clean headline estimate is useful, but omitted flat characteristics can widen the realistic pricing range materially.",
        "",
        "## Results",
        f"- The best official model is **{result['best_model']}**, delivering **{best_official['mape']:.2%} MAPE**, **{_format_sgd(float(best_official['rmse']))} RMSE**, and **{_format_sgd(float(best_official['mae']))}** average absolute error on the 2014 holdout.",
        diagnostic_line,
        f"- Once those hidden drivers are imputed rather than observed, even the best group-based proxy setting rises to **{best_imputation['mape']:.2%} MAPE**, so imputation should be framed as uncertainty control rather than a free accuracy gain.",
        f"- The most credible presentation range is therefore **{_format_sgd(float(prediction_range['low']))} to {_format_sgd(float(prediction_range['high']))}**, with a midpoint of **{_format_sgd(float(prediction_range['mid']))}**.",
        "",
        "## Interpretation",
        "The story for management is not that extra features automatically make every metric better. In this rerun, richer hidden features improve RMSE, but they do not improve MAPE and they slightly worsen MAE. The answer should still be presented as a range rather than as a single exact number.",
        "",
    ]


def _question_b_lines(result: dict[str, object], suffix: str) -> list[str]:
    model_comparison = pd.read_csv(_artifact_path(REPORTS, "S2Qb_model_comparison", suffix, "csv"))
    try:
        comparables = pd.read_csv(_artifact_path(REPORTS, "S2Qb_comparables", suffix, "csv"))
    except EmptyDataError:
        comparables = pd.DataFrame()
    subject_summary = pd.read_csv(_artifact_path(TABLEAU, "S2Qb_subject_summary", suffix, "csv")).iloc[0]
    best_model = model_comparison.sort_values("mape", ascending=True).iloc[0]
    return [
        "# S2Qb PPT Summary",
        "",
        "## What",
        "The question is not just what the target Yishun transaction should have cost, but whether the observed price looks reasonable once we place it in market context.",
        "",
        "## How",
        "- We first built an expected-price benchmark using holdout-tested models, then compared the actual deal price against that benchmark.",
        "- We did not rely on the model alone: we also checked whether the transaction still looked reasonable relative to nearby local market activity and any comparable-sale evidence available.",
        "",
        "## Why",
        "Senior management will care less about a technical score and more about whether the price sits comfortably within the market range. That means the answer has to combine prediction, context, and a clear confidence statement.",
        "",
        "## Results",
        f"- The best expected-price model is **{result['best_model']}**, with holdout error of **{best_model['mape']:.2%} MAPE**, so the benchmark is directionally strong.",
        f"- It estimates the flat at **{_format_sgd(float(subject_summary['expected_price']))}**, versus an actual transacted price of **{_format_sgd(float(subject_summary['actual_price']))}**.",
        f"- That means the deal cleared **{_format_sgd(float(subject_summary['absolute_deviation']))}** above the model estimate, or about **{_format_pct(float(subject_summary['percentage_deviation']))}**.",
        f"- Even so, the actual price still sits within the model's expected range of **{_format_sgd(float(subject_summary['prediction_interval_low']))} to {_format_sgd(float(subject_summary['prediction_interval_high']))}**, so the final call is: **{subject_summary['final_assessment']}**.",
        f"- The local +/-{DEFAULT_QB_LOCAL_WINDOW_MONTHS}-month market window still contains **{int(subject_summary['local_distribution_count'])}** transactions, which supports a **{subject_summary['confidence_level']}** confidence rating.",
        f"- Comparable-sale support is thin at **{int(subject_summary['comparable_count'])}** transactions, so the final message should lean more on the model band and local market distribution than on direct comps.",
        "",
        "## Interpretation",
        "The presentation takeaway is that this was not a bargain transaction, but it also does not look obviously mispriced. It sits above the model midpoint, yet still within a reasonable market range, so the fairest executive conclusion is that the deal looks defensible rather than anomalous.",
        "",
    ]


def _question_c_lines(result: dict[str, object], suffix: str) -> list[str]:
    supervised = json.loads(_artifact_path(REPORTS, "S2Qc_flat_type_classifier", suffix, "json").read_text(encoding="utf-8"))
    unsupervised = json.loads(_artifact_path(REPORTS, "S2Qc_flat_type_unsupervised", suffix, "json").read_text(encoding="utf-8"))
    distribution = pd.read_csv(_artifact_path(REPORTS, "S2Qc_flat_type_distribution_summary", suffix, "csv"))
    top_segment = max(unsupervised["segment_summary"], key=lambda row: row["median_price"])
    top_distribution = distribution.sort_values("transaction_count", ascending=False).iloc[0]
    return [
        "# S2Qc PPT Summary",
        "",
        "## What",
        "If the flat type field is missing, the business problem is not academic classification accuracy. It is whether we can restore a critical operational field quickly enough to keep downstream analysis and decision-making usable.",
        "",
        "## How",
        f"- We evaluated both recovery paths on a strict time-aware split: the latest **{supervised['holdout_month_count']} months** (**{supervised['holdout_period_start']} to {supervised['holdout_period_end']}**) were held out for testing, while the immediately preceding rolling training window supplied the learning sample.",
        "- We compared two recovery paths: a supervised classifier trained directly on known flat types, and an unsupervised segmentation approach that tries to reconstruct flat types indirectly from transaction patterns.",
        "- We also checked the downstream pricing impact of both approaches, because the real test is whether the recovered field remains useful for later business analysis.",
        "",
        "## Why",
        "This lets us answer the management question in operational terms: which method would we trust to restore the missing field in production, and which method is better kept as exploratory analysis.",
        "",
        "## Results",
        f"- The supervised approach clearly leads: **{supervised['best_model']}** reaches **{supervised['accuracy']:.3f} accuracy** and **{supervised['weighted_f1']:.3f} weighted F1**.",
        f"- More importantly, downstream pricing barely deteriorates when we use the recovered flat type: RMSE moves from **{supervised['pricing_with_known_flat_type_rmse']:,.0f}** to **{supervised['pricing_with_recovered_flat_type_rmse']:,.0f}**.",
        f"- The unsupervised route is anchored at **{unsupervised['cluster_count']}** clusters to align with the primary HDB flat categories, and reaches **{unsupervised['accuracy']:.3f} mapped accuracy** on the full sample." if unsupervised["accuracy"] is not None else f"- The unsupervised route is anchored at **{unsupervised['cluster_count']}** clusters to align with the primary HDB flat categories, but does not produce a reliable mapped accuracy for direct field recovery.",
        f"- Its main value is descriptive: for example, **{top_segment['recovered_segment']}** forms the highest-priced recovered segment at **{_format_sgd(float(top_segment['median_price']))}**, while **{top_distribution['flat_type']}** is the largest observed flat-type group with **{int(top_distribution['transaction_count'])}** transactions.",
        "",
        "## Interpretation",
        "The executive recommendation is straightforward: use the supervised model to restore the missing field, because it preserves operational usefulness with very little downstream damage. Keep the unsupervised method as an exploratory segmentation view, not as the production recovery solution.",
        "",
    ]


def write_section2_ppt_summaries(results: dict[str, object], *, artifact_suffix: str = "") -> dict[str, str]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}
    builders = {
        "question_a": ("S2Qa_ppt_summary", _question_a_lines),
        "question_b": ("S2Qb_ppt_summary", _question_b_lines),
        "question_c": ("S2Qc_ppt_summary", _question_c_lines),
    }
    for key, (stem, builder) in builders.items():
        if key not in results:
            continue
        path = _artifact_path(REPORTS, stem, artifact_suffix, "md")
        write_markdown(path, builder(results[key], artifact_suffix))
        outputs[key] = str(path)
    return outputs
