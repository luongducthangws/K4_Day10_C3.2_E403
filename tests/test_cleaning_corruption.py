from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from core.utils import read_json
from ingestion.cleaning import CLEAN_COLUMNS, build_clean_dataframe, build_text_for_embedding
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord


RUN_DATE = datetime(2026, 8, 6, tzinfo=UTC)


def make_record(
    number: int,
    *,
    paper_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    published: str | None = None,
    updated: str = "",
    authors: list[str] | None = None,
    categories: list[str] | None = None,
    primary_category: str = "",
) -> PaperRecord:
    return PaperRecord(
        paper_id=paper_id if paper_id is not None else f"doi:10.1000/{number}",
        title=title if title is not None else f"Paper {number} about retrieval augmented generation",
        summary=(
            summary
            if summary is not None
            else f"Paper {number} contains enough factual abstract text for deterministic testing."
        ),
        authors=authors if authors is not None else [f"Author {number}"],
        categories=categories if categories is not None else ["AI", "RAG"],
        primary_category=primary_category,
        published=published if published is not None else f"2026-07-{number + 1:02d}",
        updated=updated,
        abs_url=f"https://doi.org/10.1000/{number}",
        pdf_url="",
        comment="",
    )


def test_cleaning_normalizes_filters_deduplicates_and_tracks_counts() -> None:
    records = [
        make_record(
            1,
            paper_id="DOI:10.1000/ONE",
            title=" <b> First   paper </b> ",
            summary="<jats:p>Original abstract with valid content.</jats:p>",
            published="2026-07-01",
            authors=[" Ada  Lovelace ", "Ada Lovelace"],
            categories=["AI", "AI"],
        ),
        make_record(
            2,
            paper_id="doi:10.1000/one",
            title="First paper",
            summary="Longer duplicate abstract selected because it contains more useful factual content.",
            published="2026-07-01",
            updated="2026-07-03",
        ),
        make_record(
            3,
            paper_id="doi:10.1000/fallback",
            published="2026-07-02",
            authors=[],
            categories=[],
        ),
        make_record(4, paper_id=""),
        make_record(5, title=""),
        make_record(6, summary=""),
        make_record(7, summary="short"),
        make_record(8, published="not-a-date"),
    ]

    clean = build_clean_dataframe(records, RUN_DATE)

    assert list(clean.columns) == CLEAN_COLUMNS
    assert clean["paper_id"].tolist() == ["doi:10.1000/fallback", "doi:10.1000/one"]
    assert clean["paper_id"].is_unique
    selected = clean.loc[clean["paper_id"] == "doi:10.1000/one"].iloc[0]
    assert selected["summary"].startswith("Longer duplicate abstract")
    assert "<" not in selected["title"] + selected["summary"]
    fallback = clean.loc[clean["paper_id"] == "doi:10.1000/fallback"].iloc[0]
    assert fallback["authors_joined"] == "Unknown Author"
    assert fallback["categories_joined"] == "General"
    assert fallback["primary_category"] == "General"
    assert fallback["age_days"] == 35
    assert selected["text_for_embedding"] == build_text_for_embedding(selected)

    stats = clean.attrs["cleaning_stats"]
    assert stats == {
        "input_rows": 8,
        "rejected": {
            "missing_paper_id": 1,
            "missing_title": 1,
            "missing_summary": 1,
            "summary_too_short": 1,
            "invalid_published": 1,
        },
        "duplicates_removed": 1,
        "output_rows": 2,
    }


def test_cleaning_returns_stable_empty_schema() -> None:
    clean = build_clean_dataframe([make_record(1, summary="")], RUN_DATE)

    assert clean.empty
    assert list(clean.columns) == CLEAN_COLUMNS
    assert clean.attrs["cleaning_stats"]["output_rows"] == 0
    assert clean.attrs["cleaning_stats"]["rejected"]["missing_summary"] == 1


def test_corruption_is_deterministic_auditable_and_rebuilds_text(tmp_path: Path) -> None:
    records = [
        make_record(
            number,
            published=(RUN_DATE.date() - timedelta(days=number + 1)).isoformat(),
        )
        for number in range(12)
    ]
    clean = build_clean_dataframe(records, RUN_DATE)
    original = clean.copy(deep=True)
    first_log = tmp_path / "first_corruption.json"
    second_log = tmp_path / "second_corruption.json"

    first = corrupt_clean_dataframe(clean, first_log)
    second = corrupt_clean_dataframe(clean, second_log)

    pd.testing.assert_frame_equal(clean, original)
    pd.testing.assert_frame_equal(first, second)
    assert read_json(first_log) == read_json(second_log)

    log = read_json(first_log)
    event_types = [event["corruption_type"] for event in log["events"]]
    assert event_types == [
        "drop_latest_records",
        "blank_summary",
        "inject_summary_noise",
        "truncate_title",
        "make_publication_stale",
        "duplicate_row",
    ]
    assert log["input_rows"] == 12
    assert log["output_rows"] == 11
    assert log["events"][0]["affected_paper_ids"] == clean.head(2)["paper_id"].tolist()
    assert first["paper_id"].duplicated().sum() == 1
    assert (first["summary"] == "").sum() == 1
    assert first["summary"].str.contains("CORRUPTED_NOISE").sum() == 1
    assert (first["summary_chars"] == first["summary"].str.len()).all()
    for row in first.to_dict(orient="records"):
        assert row["text_for_embedding"] == build_text_for_embedding(row)


def test_corruption_rejects_invalid_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty clean dataframe"):
        corrupt_clean_dataframe(pd.DataFrame(columns=CLEAN_COLUMNS), tmp_path / "empty.json")

    with pytest.raises(ValueError, match="missing required columns"):
        corrupt_clean_dataframe(pd.DataFrame([{"paper_id": "one"}]), tmp_path / "missing.json")
