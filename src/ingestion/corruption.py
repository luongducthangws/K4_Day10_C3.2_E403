from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import build_text_for_embedding


REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "published",
    "age_days",
    "summary_chars",
    "text_for_embedding",
}


def _rebuild_derived_columns(df: pd.DataFrame) -> None:
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = [build_text_for_embedding(row) for row in df.to_dict(orient="records")]


def _event(corruption_type: str, paper_ids: list[str], **details: Any) -> dict[str, Any]:
    return {
        "corruption_type": corruption_type,
        "affected_paper_ids": paper_ids,
        "affected_rows": len(paper_ids),
        **details,
    }


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create deterministic corruptions and an auditable event log."""
    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {', '.join(missing_columns)}")
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataframe.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    input_rows = len(corrupted)
    events: list[dict[str, Any]] = []

    published_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    latest_order = published_dates.sort_values(ascending=False, na_position="last").index.tolist()
    drop_count = min(max(1, input_rows // 6), input_rows - 1) if input_rows > 1 else 0
    dropped_indices = latest_order[:drop_count]
    dropped_ids = corrupted.loc[dropped_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=dropped_indices).reset_index(drop=True)
    events.append(
        _event(
            "drop_latest_records",
            dropped_ids,
            parameter={"drop_count": drop_count, "selection": "latest published first"},
            before_row_count=input_rows,
            after_row_count=len(corrupted),
        )
    )

    def row_index(offset: int) -> int:
        return offset % len(corrupted)

    blank_index = row_index(0)
    blank_id = str(corrupted.at[blank_index, "paper_id"])
    original_summary = str(corrupted.at[blank_index, "summary"])
    corrupted.at[blank_index, "summary"] = ""
    events.append(
        _event(
            "blank_summary",
            [blank_id],
            before_summary_chars=len(original_summary),
            after_summary_chars=0,
        )
    )

    noise_index = row_index(1)
    noise_id = str(corrupted.at[noise_index, "paper_id"])
    noise = " CORRUPTED_NOISE token-noise-9999 " * 12
    original_noise_summary = str(corrupted.at[noise_index, "summary"])
    corrupted.at[noise_index, "summary"] = f"{noise}{original_noise_summary}{noise}".strip()
    events.append(
        _event(
            "inject_summary_noise",
            [noise_id],
            parameter={"noise_token": "CORRUPTED_NOISE", "repetitions_each_side": 12},
            before_summary_chars=len(original_noise_summary),
            after_summary_chars=len(str(corrupted.at[noise_index, "summary"])),
        )
    )

    title_index = row_index(2)
    title_id = str(corrupted.at[title_index, "paper_id"])
    original_title = str(corrupted.at[title_index, "title"])
    if len(original_title) > 12:
        truncated_title = f"{original_title[:12].rstrip()}..."
    else:
        truncated_title = original_title[: max(1, len(original_title) // 2)]
    corrupted.at[title_index, "title"] = truncated_title
    events.append(
        _event(
            "truncate_title",
            [title_id],
            parameter={"max_original_characters_kept": 12},
            before_title=original_title,
            after_title=truncated_title,
        )
    )

    stale_index = row_index(3)
    stale_id = str(corrupted.at[stale_index, "paper_id"])
    original_published = str(corrupted.at[stale_index, "published"])
    parsed_published = pd.to_datetime(original_published, errors="coerce", utc=True)
    if pd.isna(parsed_published):
        stale_published = "2000-01-01"
    else:
        stale_published = (parsed_published.date() - timedelta(days=3650)).isoformat()
    original_age_days = int(corrupted.at[stale_index, "age_days"])
    corrupted.at[stale_index, "published"] = stale_published
    corrupted.at[stale_index, "age_days"] = original_age_days + 3650
    events.append(
        _event(
            "make_publication_stale",
            [stale_id],
            parameter={"days_subtracted": 3650},
            before_published=original_published,
            after_published=stale_published,
            before_age_days=original_age_days,
            after_age_days=original_age_days + 3650,
        )
    )

    duplicate_index = row_index(len(corrupted) - 1)
    duplicate_id = str(corrupted.at[duplicate_index, "paper_id"])
    duplicate = corrupted.iloc[[duplicate_index]].copy(deep=True)
    before_duplicate = len(corrupted)
    corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
    events.append(
        _event(
            "duplicate_row",
            [duplicate_id],
            before_row_count=before_duplicate,
            after_row_count=len(corrupted),
        )
    )

    _rebuild_derived_columns(corrupted)
    write_json(
        Path(output_log_path),
        {
            "input_rows": input_rows,
            "output_rows": len(corrupted),
            "events": events,
        },
    )
    return corrupted.reset_index(drop=True)
