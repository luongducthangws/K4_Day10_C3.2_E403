from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


from dataclasses import asdict
import json
import re
import time
import urllib.request
import urllib.parse

from core.utils import ensure_parent, read_json, safe_slug, write_json


def _clean_abstract(raw: str) -> str:
    if not raw:
        return ""
    # Strip HTML / JATS tags like <jats:p>, <jats:sec>, etc.
    cleaned = re.sub(r"<[^>]+>", "", raw)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        doi = item.get("DOI", "")
        titles = item.get("title", [])
        title = titles[0].strip() if titles else ""
        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        # Extract authors
        authors_raw = item.get("author", [])
        authors: list[str] = []
        for a in authors_raw:
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)

        # Extract categories / subjects
        subjects = item.get("subject", [])
        categories = [s.strip() for s in subjects if s.strip()]
        primary_category = categories[0] if categories else "General"

        # Dates
        date_parts = (
            item.get("published-online", {}).get("date-parts", [[]])[0]
            or item.get("published-print", {}).get("date-parts", [[]])[0]
            or item.get("created", {}).get("date-parts", [[]])[0]
        )
        if len(date_parts) >= 3:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-{date_parts[2]:02d}"
        elif len(date_parts) == 2:
            published = f"{date_parts[0]:04d}-{date_parts[1]:02d}-01"
        elif len(date_parts) == 1:
            published = f"{date_parts[0]:04d}-01-01"
        else:
            published = "2024-01-01"

        updated = published
        abs_url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
        pdf_url = ""
        link_list = item.get("link", [])
        for link in link_list:
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        paper_id = safe_slug(doi or title[:30])

        if title and summary:
            records.append(
                PaperRecord(
                    paper_id=paper_id,
                    title=title,
                    summary=summary,
                    authors=authors,
                    categories=categories,
                    primary_category=primary_category,
                    published=published,
                    updated=updated,
                    abs_url=abs_url,
                    pdf_url=pdf_url,
                    comment=f"Crossref record: {doi}",
                )
            )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    if not settings.refresh_source and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    base_url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": str(settings.max_results),
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DataObservabilityLab/1.0 (mailto:student@lab.edu)"},
    )

    payload = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read().decode("utf-8")
                payload = json.loads(data)
                break
        except Exception as exc:
            if attempt == 2:
                if settings.paths.raw_api_response.exists():
                    payload = read_json(settings.paths.raw_api_response)
                else:
                    raise RuntimeError(f"Failed to fetch Crossref data after retries: {exc}") from exc
            time.sleep(1.0 * (attempt + 1))

    if payload is None:
        raise RuntimeError("No payload retrieved from Crossref API.")

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)

    # Save records snapshot
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item.get("primary_category", "General"),
                published=item["published"],
                updated=item.get("updated", item["published"]),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    return records
