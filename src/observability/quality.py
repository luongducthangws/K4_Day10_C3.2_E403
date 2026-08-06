from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings


from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    total_rows = len(df)
    null_paper_ids = int(df["paper_id"].isnull().sum()) if "paper_id" in df.columns else 0
    duplicate_paper_ids = int(df.duplicated(subset=["paper_id"]).sum()) if "paper_id" in df.columns else 0
    null_titles = int(df["title"].isnull().sum()) if "title" in df.columns else 0
    empty_summaries = int((df["summary_chars"] < 10).sum()) if "summary_chars" in df.columns else 0
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0

    all_passed = (
        total_rows > 0
        and null_paper_ids == 0
        and duplicate_paper_ids == 0
        and null_titles == 0
        and empty_summaries == 0
    )

    report = {
        "report_name": report_name,
        "total_rows": total_rows,
        "null_paper_ids": null_paper_ids,
        "duplicate_paper_ids": duplicate_paper_ids,
        "null_titles": null_titles,
        "empty_summaries": empty_summaries,
        "stale_rows": stale_rows,
        "all_passed": all_passed,
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
        }

    if report_path:
        write_json(report_path, report)

    return report
