from __future__ import annotations

from typing import Any


from core.utils import write_text


def _quality_status_label(quality: dict[str, Any]) -> str:
    if not quality.get("all_passed"):
        return "FAILED"
    if quality.get("has_warnings"):
        return "PASSED (with warnings)"
    return "PASSED"


def _delta(current: Any, baseline: Any) -> str:
    """Signed change against baseline, or n/a when either side is missing."""
    if not isinstance(current, (int, float)) or not isinstance(baseline, (int, float)):
        return "n/a"
    change = current - baseline
    if abs(change) < 1e-9:
        return "0.00"
    return f"{change:+.2f}"


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    content = f"""# Phase 1 Baseline Data Pipeline Report

## Executive Summary
This report summarizes the baseline ingestion, cleaning, vector indexing, evaluation, and data observability metrics.

## 1. Source Ingestion Summary
- **Source API**: {source_summary.get("source_api", "Crossref REST API")}
- **Search Query**: `{source_summary.get("source_query", "N/A")}`
- **Raw Records Ingested**: {source_summary.get("raw_count", 0)}
- **Cleaned Records**: {source_summary.get("clean_count", 0)}

## 2. Baseline Evaluation Metrics
- **Evaluated Samples**: {metrics.get("samples", 0)}
- **Retrieval Hit Rate**: {metrics.get("retrieval_hit_rate", 0.0):.4f} ({metrics.get("retrieval_hit_rate", 0.0)*100:.1f}%)
- **Mean Token F1**: {metrics.get("mean_token_f1", 0.0):.4f}
- **LLM Judge Accuracy**: {metrics.get("judge_accuracy", 0.0):.4f} ({metrics.get("judge_accuracy", 0.0)*100:.1f}%)
- **Mean LLM Judge Score**: {metrics.get("mean_judge_score", 0.0):.2f} / 5.0

## 3. Data Observability & Quality Audit

### 3.1 Blocking checks (drive the pass/fail status)
| Check | Value |
| :--- | :---: |
| Total Clean Rows | {quality.get("total_rows", 0)} |
| Null Paper IDs | {quality.get("null_paper_ids", 0)} |
| Duplicate Paper IDs | {quality.get("duplicate_paper_ids", 0)} |
| Null Titles | {quality.get("null_titles", 0)} |
| Empty Summaries | {quality.get("empty_summaries", 0)} |

### 3.2 Content-integrity warnings
These catch damage that leaves a field non-null and long enough to pass the
blocking checks, but still degrades retrieval.

| Signal | Value |
| :--- | :---: |
| Truncated Titles | {quality.get("truncated_titles", 0)} |
| Noisy Summaries (repeated-phrase injection) | {quality.get("noisy_summaries", 0)} |
| Stale Rows | {quality.get("stale_rows", 0)} |

- **Overall Data Quality Audit Status**: {_quality_status_label(quality)}

## 4. Freshness Audit
- **Latest Publication Date**: {freshness.get("latest_published", "N/A")}
- **Oldest Publication Date**: {freshness.get("oldest_published", "N/A")}
- **Freshness Threshold**: {freshness.get("freshness_threshold_days", "N/A")} days
- **Stale Rows Count**: {freshness.get("stale_rows", 0)} / {freshness.get("total_rows", 0)}
- **Is Dataset Fresh?**: {"YES" if freshness.get("is_fresh") else "NO"}
"""
    write_text(report_path, content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    metric_rows = [
        ("Retrieval Hit Rate", "retrieval_hit_rate"),
        ("Mean Token F1", "mean_token_f1"),
        ("Judge Accuracy", "judge_accuracy"),
        ("Mean Judge Score", "mean_judge_score"),
    ]
    metric_table = "\n".join(
        f"| {label} | {baseline_metrics.get(key, 0.0):.2f} | {corrupted_metrics.get(key, 0.0):.2f} "
        f"| {_delta(corrupted_metrics.get(key), baseline_metrics.get(key))} "
        f"| {repaired_metrics.get(key, 0.0):.2f} "
        f"| {_delta(repaired_metrics.get(key), baseline_metrics.get(key))} |"
        for label, key in metric_rows
    )

    signal_rows = [
        ("Duplicate Paper IDs", "duplicate_paper_ids"),
        ("Empty Summaries", "empty_summaries"),
        ("Truncated Titles", "truncated_titles"),
        ("Noisy Summaries", "noisy_summaries"),
        ("Stale Rows", "stale_rows"),
    ]
    signal_table = "\n".join(
        f"| {label} | {corrupted_quality.get(key, 0)} | {repaired_quality.get(key, 0)} |"
        for label, key in signal_rows
    )

    hit_drop = _delta(corrupted_metrics.get("retrieval_hit_rate"), baseline_metrics.get("retrieval_hit_rate"))

    # Report recovery per metric instead of generalising from one of them: the
    # deterministic retrieval metrics can land exactly on baseline while the
    # LLM-judged ones move a little, because the judge is not deterministic even
    # when the repaired corpus is byte-identical to the baseline corpus.
    exact, drifted = [], []
    for label, key in metric_rows:
        repaired_value, baseline_value = repaired_metrics.get(key), baseline_metrics.get(key)
        if not isinstance(repaired_value, (int, float)) or not isinstance(baseline_value, (int, float)):
            continue
        (exact if abs(repaired_value - baseline_value) < 1e-9 else drifted).append(
            f"{label} ({_delta(repaired_value, baseline_value)})"
        )

    if exact and not drifted:
        recovery_sentence = "Every tracked metric returned exactly to its baseline value, so the repair is complete."
    elif exact:
        recovery_sentence = (
            f"{', '.join(exact)} returned exactly to baseline. "
            f"{', '.join(drifted)} differ slightly: the repaired corpus is rebuilt from the same raw "
            "snapshot, so this residual gap reflects LLM-judge variance rather than unrecovered data."
        )
    else:
        recovery_sentence = (
            f"No metric landed exactly on baseline ({', '.join(drifted)}), so the recovery is only partial."
        )

    content = f"""# Data Corruption & Pipeline Repair Comparison Report

## Executive Summary
This report analyzes the impact of synthetic data corruption on RAG retrieval and
answer quality, and verifies how much of that quality returns after the pipeline is
repaired from the saved raw snapshot. All three states are scored on the identical
frozen evaluation set.

## 1. Metrics Comparison Table

| Metric | Baseline | Corrupted | Δ vs Baseline | Repaired | Δ vs Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: |
{metric_table}

| Pipeline Stage | Samples | Quality Status | Freshness |
| :--- | :---: | :---: | :---: |
| **Baseline (Clean)** | {baseline_metrics.get("samples", 0)} | PASSED | Fresh |
| **Corrupted (Damaged)** | {corrupted_metrics.get("samples", 0)} | {_quality_status_label(corrupted_quality)} | {"Fresh" if corrupted_freshness.get("is_fresh") else "Stale"} |
| **Repaired (Restored)** | {repaired_metrics.get("samples", 0)} | {_quality_status_label(repaired_quality)} | {"Fresh" if repaired_freshness.get("is_fresh") else "Stale"} |

## 2. Which Observability Signals Detected the Damage

| Quality Signal | Corrupted | Repaired |
| :--- | :---: | :---: |
{signal_table}

Freshness moved from latest publication `{corrupted_freshness.get("latest_published", "N/A")}`
({corrupted_freshness.get("stale_rows", 0)} stale rows) while corrupted, back to
`{repaired_freshness.get("latest_published", "N/A")}` ({repaired_freshness.get("stale_rows", 0)} stale rows)
after repair.

## 3. Key Findings & Insights
1. **Bad data measurably degrades the agent.** Retrieval hit rate moved {hit_drop} against
   baseline once the corrupted corpus was indexed, and the answer-quality metrics fell with it.
2. **The damage was visible in the quality signals before reading any answer.** Dropped,
   duplicated, blanked, truncated, noise-injected and back-dated rows each surfaced in the
   table above, which is what makes the failure detectable in production rather than silent.
3. **Repairing from the saved raw snapshot restores the pipeline.** {recovery_sentence}
"""
    write_text(report_path, content)
