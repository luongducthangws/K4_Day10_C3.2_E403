from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


from core.utils import compact_join, normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    rows = []
    run_dt = run_date.date() if isinstance(run_date, datetime) else run_date

    for record in records:
        title = normalize_whitespace(record.title or "")
        summary = normalize_whitespace(record.summary or "")
        if not title or len(summary) < 10:
            continue

        authors_clean = [normalize_whitespace(a) for a in record.authors if a.strip()]
        categories_clean = [normalize_whitespace(c) for c in record.categories if c.strip()]
        authors_joined = compact_join(authors_clean) or "Unknown Author"
        categories_joined = compact_join(categories_clean) or "General"

        try:
            pub_date = datetime.strptime(record.published, "%Y-%m-%d").date()
        except Exception:
            pub_date = run_dt

        age_days = (run_dt - pub_date).days

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {record.published}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category or "General",
                "published": record.published,
                "updated": record.updated,
                "age_days": age_days,
                "summary_chars": len(summary),
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"]).drop_duplicates(subset=["title"])
        df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
