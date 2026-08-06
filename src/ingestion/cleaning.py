from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import Any, Mapping

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "authors_joined",
    "categories",
    "categories_joined",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "abs_url",
    "pdf_url",
    "comment",
    "summary_chars",
    "text_for_embedding",
]

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _normalize_text(value: Any, *, strip_html: bool = False) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value)
    if strip_html:
        text = unescape(text)
        text = _HTML_TAG_RE.sub(" ", text)
    return normalize_whitespace(text)


def _normalize_list(values: Any, *, strip_html: bool = False) -> list[str]:
    if values is None:
        return []
    candidates = values if isinstance(values, (list, tuple, set)) else [values]
    normalized: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        item = _normalize_text(value, strip_html=strip_html)
        key = item.casefold()
        if item and key not in seen:
            normalized.append(item)
            seen.add(key)
    return normalized


def _parse_date(value: Any) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def build_text_for_embedding(row: Mapping[str, Any]) -> str:
    """Build deterministic text shared by clean and corrupted datasets."""
    return "\n".join(
        [
            f"Title: {_normalize_text(row.get('title'))}",
            f"Authors: {_normalize_text(row.get('authors_joined'))}",
            f"Categories: {_normalize_text(row.get('categories_joined'))}",
            f"Published: {_normalize_text(row.get('published'))}",
            f"Summary: {_normalize_text(row.get('summary'))}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a deterministic dataframe ready for indexing."""
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    run_day = run_timestamp.date()

    rows: list[dict[str, Any]] = []
    rejected = {
        "missing_paper_id": 0,
        "missing_title": 0,
        "missing_summary": 0,
        "summary_too_short": 0,
        "invalid_published": 0,
    }

    for record in records:
        paper_id = _normalize_text(record.paper_id).lower()
        title = _normalize_text(record.title, strip_html=True)
        summary = _normalize_text(record.summary, strip_html=True)
        published = _parse_date(record.published)

        if not paper_id:
            rejected["missing_paper_id"] += 1
            continue
        if not title:
            rejected["missing_title"] += 1
            continue
        if not summary:
            rejected["missing_summary"] += 1
            continue
        if len(summary) < 10:
            rejected["summary_too_short"] += 1
            continue
        if published is None:
            rejected["invalid_published"] += 1
            continue

        authors = _normalize_list(record.authors, strip_html=True) or ["Unknown Author"]
        categories = _normalize_list(record.categories, strip_html=True) or ["General"]
        primary_category = _normalize_text(record.primary_category, strip_html=True)
        if not primary_category:
            primary_category = categories[0]
        known_categories = {item.casefold() for item in categories}
        if primary_category.casefold() not in known_categories:
            categories.insert(0, primary_category)

        updated = _parse_date(record.updated) or published
        published_day = datetime.fromisoformat(published).date()
        row: dict[str, Any] = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "authors_joined": ", ".join(authors),
            "categories": categories,
            "categories_joined": ", ".join(categories),
            "primary_category": primary_category,
            "published": published,
            "updated": updated,
            "age_days": max(0, (run_day - published_day).days),
            "abs_url": _normalize_text(record.abs_url),
            "pdf_url": _normalize_text(record.pdf_url),
            "comment": _normalize_text(record.comment, strip_html=True),
            "summary_chars": len(summary),
        }
        row["text_for_embedding"] = build_text_for_embedding(row)
        rows.append(row)

    if not rows:
        empty = pd.DataFrame(columns=CLEAN_COLUMNS)
        empty.attrs["cleaning_stats"] = {
            "input_rows": len(records),
            "rejected": rejected,
            "duplicates_removed": 0,
            "output_rows": 0,
        }
        return empty

    clean = pd.DataFrame(rows)
    before_deduplication = len(clean)
    clean = clean.sort_values(
        by=["paper_id", "summary_chars", "updated"],
        ascending=[True, False, False],
        kind="stable",
    ).drop_duplicates(subset=["paper_id"], keep="first")
    duplicates_removed = before_deduplication - len(clean)
    clean = clean.sort_values(by=["published", "paper_id"], ascending=[False, True], kind="stable")
    clean = clean.loc[:, CLEAN_COLUMNS].reset_index(drop=True)
    clean.attrs["cleaning_stats"] = {
        "input_rows": len(records),
        "rejected": rejected,
        "duplicates_removed": duplicates_removed,
        "output_rows": len(clean),
    }
    return clean
