from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import time
from pathlib import Path
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, safe_slug, read_json, write_json


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


def _get_first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = normalize_whitespace(str(item))
            if text:
                return text
        return ""
    if value is None:
        return ""
    return normalize_whitespace(str(value))


def _strip_html(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("<jats:p>", " ").replace("</jats:p>", " ")
    cleaned = cleaned.replace("<p>", " ").replace("</p>", " ")
    while "<" in cleaned and ">" in cleaned:
        start = cleaned.find("<")
        end = cleaned.find(">", start)
        if start == -1 or end == -1:
            break
        cleaned = cleaned[:start] + " " + cleaned[end + 1 :]
    cleaned = normalize_whitespace(cleaned)
    cleaned = cleaned.replace(" .", ".").replace(" ,", ",").replace(" ;", ";").replace(" :", ":")
    return normalize_whitespace(cleaned)


def _normalize_doi(doi: str) -> str:
    cleaned = normalize_whitespace(doi).lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
    return cleaned


def _stable_paper_id(doi: str, title: str, published: str) -> str:
    if doi:
        return f"doi:{_normalize_doi(doi)}"
    basis = normalize_whitespace(f"{title} {published}") or title or published or "record"
    slug = safe_slug(basis)
    if len(slug) <= 80:
        return f"paper:{slug}"
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"paper:{slug[:60]}-{digest}"


def _date_parts_to_iso(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts:
        return ""
    first = date_parts[0]
    if not isinstance(first, list) or not first:
        return ""
    year = first[0]
    month = first[1] if len(first) > 1 else 1
    day = first[2] if len(first) > 2 else 1
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def _parse_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        given = normalize_whitespace(str(item.get("given", "")))
        family = normalize_whitespace(str(item.get("family", "")))
        name = normalize_whitespace(" ".join(part for part in [given, family] if part))
        if not name:
            name = normalize_whitespace(str(item.get("name", "")))
        if name:
            authors.append(name)
    return authors


def _parse_pdf_url(item: dict[str, Any]) -> str:
    links = item.get("link")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            content_type = normalize_whitespace(str(link.get("content-type", ""))).lower()
            url = normalize_whitespace(str(link.get("URL", "")))
            if url and content_type == "application/pdf":
                return url
    return ""


def _coerce_record(item: dict[str, Any]) -> PaperRecord | None:
    title = _get_first_text(item.get("title"))
    doi = _get_first_text(item.get("DOI"))
    summary = _strip_html(_get_first_text(item.get("abstract")))
    authors = _parse_authors(item.get("author"))
    categories = [normalize_whitespace(str(subject)) for subject in item.get("subject", []) if normalize_whitespace(str(subject))]
    primary_category = categories[0] if categories else ""
    published = _date_parts_to_iso(item.get("published-print")) or _date_parts_to_iso(item.get("published-online")) or _date_parts_to_iso(item.get("created")) or _date_parts_to_iso(item.get("issued"))
    updated = _date_parts_to_iso(item.get("updated"))
    abs_url = _get_first_text(item.get("URL"))
    pdf_url = _parse_pdf_url(item)
    comment = _get_first_text(item.get("comment"))

    if not title:
        return None

    paper_id = _stable_paper_id(doi, title, published)
    return PaperRecord(
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
        comment=comment,
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into validated PaperRecord rows."""
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record = _coerce_record(item)
        if record is not None:
            records.append(record)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, persist raw artifacts, and return parsed rows."""

    source_url = settings.source_api if settings.source_api.startswith("http") else "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "K4-Day10-Data-Pipeline/1.0 (mailto:student@example.com)",
        "Accept": "application/json",
    }
    transient_statuses = {429, 503}
    max_attempts = 4
    backoff_seconds = 1.5

    last_error: Exception | None = None
    response_payload: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(source_url, params=params, headers=headers, timeout=30)
            if response.status_code in transient_statuses:
                raise requests.HTTPError(f"Transient Crossref error {response.status_code}", response=response)
            response.raise_for_status()
            response_payload = response.json()
            break
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            is_transient = isinstance(exc, (requests.Timeout, requests.ConnectionError)) or status_code in transient_statuses
            if not is_transient or attempt == max_attempts:
                raise RuntimeError("Failed to fetch Crossref records after retries.") from exc
            time.sleep(backoff_seconds * attempt)

    if response_payload is None:
        raise RuntimeError("Crossref response payload is empty.") from last_error

    write_json(settings.paths.raw_api_response, response_payload)
    records = parse_crossref_payload(response_payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a raw-record snapshot back into PaperRecord objects."""
    payload = read_json(path)
    if isinstance(payload, dict):
        payload = payload.get("records", [])
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected raw records format in {path}")

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(PaperRecord(**item))
    return records
