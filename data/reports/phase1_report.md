# Phase 1 Baseline Data Pipeline Report

## Executive Summary
This report summarizes the baseline ingestion, cleaning, vector indexing, evaluation, and data observability metrics.

## 1. Source Ingestion Summary
- **Source API**: Crossref REST API
- **Search Query**: `agentic retrieval augmented generation large language model`
- **Raw Records Ingested**: 24
- **Cleaned Records**: 24

## 2. Baseline Evaluation Metrics
- **Evaluated Samples**: 40
- **Retrieval Hit Rate**: 1.0000 (100.0%)
- **Mean Token F1**: 1.0000
- **LLM Judge Accuracy**: 0.9000 (90.0%)
- **Mean LLM Judge Score**: 4.60 / 5.0

## 3. Data Observability & Quality Audit

### 3.1 Blocking checks (drive the pass/fail status)
| Check | Value |
| :--- | :---: |
| Total Clean Rows | 24 |
| Null Paper IDs | 0 |
| Duplicate Paper IDs | 0 |
| Null Titles | 0 |
| Empty Summaries | 0 |

### 3.2 Content-integrity warnings
These catch damage that leaves a field non-null and long enough to pass the
blocking checks, but still degrades retrieval.

| Signal | Value |
| :--- | :---: |
| Truncated Titles | 0 |
| Noisy Summaries (repeated-phrase injection) | 0 |
| Stale Rows | 0 |

- **Overall Data Quality Audit Status**: PASSED

## 4. Freshness Audit
- **Latest Publication Date**: 2026-08-05
- **Oldest Publication Date**: 2026-02-13
- **Freshness Threshold**: 180 days
- **Stale Rows Count**: 0 / 24
- **Is Dataset Fresh?**: YES
