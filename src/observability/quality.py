from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from core.config import Settings


from core.utils import write_json


# Thresholds calibrated against the real baseline corpus:
# clean titles are >= 92 characters, clean summaries never repeat a trigram
# more than 3 times. Corrupted rows sit far outside both ranges.
MIN_TITLE_CHARS = 30
MAX_REPEATED_TRIGRAM = 4


def _repeated_phrase_runs(text: str) -> int:
    """Highest number of times any 3-word phrase repeats inside one summary.

    Injected boilerplate/noise repeats the same phrase many times, which stays
    invisible to null and length checks because the field is still long.
    """
    tokens = str(text).lower().split()
    if len(tokens) < 20:
        return 0
    trigrams = [" ".join(tokens[index : index + 3]) for index in range(len(tokens) - 2)]
    if not trigrams:
        return 0
    return Counter(trigrams).most_common(1)[0][1]


def _sample_ids(df: pd.DataFrame, mask: pd.Series, limit: int = 5) -> list[str]:
    if "paper_id" not in df.columns or not mask.any():
        return []
    return df.loc[mask, "paper_id"].astype(str).head(limit).tolist()


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    total_rows = len(df)
    null_paper_ids = int(df["paper_id"].isnull().sum()) if "paper_id" in df.columns else 0
    duplicate_paper_ids = int(df.duplicated(subset=["paper_id"]).sum()) if "paper_id" in df.columns else 0
    null_titles = int(df["title"].isnull().sum()) if "title" in df.columns else 0
    empty_summaries = int((df["summary_chars"] < 10).sum()) if "summary_chars" in df.columns else 0
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0

    # Content-integrity signals: a truncated title or a noise-injected summary
    # keeps the field non-null and long enough, so the checks above cannot see
    # it even though retrieval quality degrades.
    if "title" in df.columns and total_rows:
        titles = df["title"].fillna("").astype(str)
        truncated_title_mask = (titles.str.len() < MIN_TITLE_CHARS) | titles.str.endswith("...")
    else:
        truncated_title_mask = pd.Series([], dtype=bool)
    truncated_titles = int(truncated_title_mask.sum())

    if "summary" in df.columns and total_rows:
        noisy_summary_mask = df["summary"].fillna("").astype(str).map(_repeated_phrase_runs) > MAX_REPEATED_TRIGRAM
    else:
        noisy_summary_mask = pd.Series([], dtype=bool)
    noisy_summaries = int(noisy_summary_mask.sum())

    # `all_passed` keeps its original meaning (blocking data errors only) so the
    # existing pipelines and reports stay compatible.
    all_passed = (
        total_rows > 0
        and null_paper_ids == 0
        and duplicate_paper_ids == 0
        and null_titles == 0
        and empty_summaries == 0
    )
    warnings = truncated_titles + noisy_summaries + stale_rows
    has_warnings = warnings > 0

    report = {
        "report_name": report_name,
        "total_rows": total_rows,
        "null_paper_ids": null_paper_ids,
        "duplicate_paper_ids": duplicate_paper_ids,
        "null_titles": null_titles,
        "empty_summaries": empty_summaries,
        "stale_rows": stale_rows,
        "truncated_titles": truncated_titles,
        "noisy_summaries": noisy_summaries,
        "all_passed": all_passed,
        "has_warnings": has_warnings,
        "warning_count": warnings,
        "status": "pass" if all_passed and not has_warnings else "fail" if not all_passed else "pass_with_warnings",
        "failed_row_samples": {
            "duplicate_paper_ids": _sample_ids(df, df.duplicated(subset=["paper_id"], keep=False))
            if "paper_id" in df.columns and total_rows
            else [],
            "empty_summaries": _sample_ids(df, df["summary_chars"] < 10)
            if "summary_chars" in df.columns and total_rows
            else [],
            "stale_rows": _sample_ids(df, df["age_days"] > settings.freshness_threshold_days)
            if "age_days" in df.columns and total_rows
            else [],
            "truncated_titles": _sample_ids(df, truncated_title_mask) if total_rows else [],
            "noisy_summaries": _sample_ids(df, noisy_summary_mask) if total_rows else [],
        },
    }

    out_path = settings.paths.quality_dir / report_name
    write_json(out_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    if df.empty:
        report = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "stale_ratio": 0.0,
        }
    else:
        dates = df["published"].dropna().tolist()
        latest = max(dates) if dates else "N/A"
        oldest = min(dates) if dates else "N/A"
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
        total_rows = len(df)
        is_fresh = stale_rows == 0

        report = {
            "latest_published": latest,
            "oldest_published": oldest,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "is_fresh": is_fresh,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "stale_ratio": round(stale_rows / total_rows, 4),
        }

    if report_path:
        write_json(report_path, report)

    return report
