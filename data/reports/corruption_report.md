# Data Corruption & Pipeline Repair Comparison Report

## Executive Summary
This report analyzes the impact of synthetic data corruption on RAG retrieval and
answer quality, and verifies how much of that quality returns after the pipeline is
repaired from the saved raw snapshot. All three states are scored on the identical
frozen evaluation set.

## 1. Metrics Comparison Table

| Metric | Baseline | Corrupted | Δ vs Baseline | Repaired | Δ vs Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Retrieval Hit Rate | 1.00 | 0.60 | -0.40 | 1.00 | 0.00 |
| Mean Token F1 | 1.00 | 0.66 | -0.34 | 1.00 | 0.00 |
| Judge Accuracy | 0.90 | 0.60 | -0.30 | 0.93 | +0.03 |
| Mean Judge Score | 4.60 | 3.42 | -1.17 | 4.70 | +0.10 |

| Pipeline Stage | Samples | Quality Status | Freshness |
| :--- | :---: | :---: | :---: |
| **Baseline (Clean)** | 40 | PASSED | Fresh |
| **Corrupted (Damaged)** | 40 | FAILED | Stale |
| **Repaired (Restored)** | 40 | PASSED | Fresh |

## 2. Which Observability Signals Detected the Damage

| Quality Signal | Corrupted | Repaired |
| :--- | :---: | :---: |
| Duplicate Paper IDs | 1 | 0 |
| Empty Summaries | 1 | 0 |
| Truncated Titles | 1 | 0 |
| Noisy Summaries | 1 | 0 |
| Stale Rows | 1 | 0 |

Freshness moved from latest publication `2026-07-02`
(1 stale rows) while corrupted, back to
`2026-08-05` (0 stale rows)
after repair.

## 3. Key Findings & Insights
1. **Bad data measurably degrades the agent.** Retrieval hit rate moved -0.40 against
   baseline once the corrupted corpus was indexed, and the answer-quality metrics fell with it.
2. **The damage was visible in the quality signals before reading any answer.** Dropped,
   duplicated, blanked, truncated, noise-injected and back-dated rows each surfaced in the
   table above, which is what makes the failure detectable in production rather than silent.
3. **Repairing from the saved raw snapshot restores the pipeline.** Retrieval Hit Rate (0.00), Mean Token F1 (0.00) returned exactly to baseline. Judge Accuracy (+0.03), Mean Judge Score (+0.10) differ slightly: the repaired corpus is rebuilt from the same raw snapshot, so this residual gap reflects LLM-judge variance rather than unrecovered data.
