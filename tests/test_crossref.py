from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from core.config import Paths, Settings
from core.utils import read_json, write_json
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records, parse_crossref_payload


def make_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        llm_provider="gemini",
        model_name="gemini-2.5-flash",
        google_api_key="test",
        openai_api_key=None,
        anthropic_api_key=None,
        openrouter_api_key=None,
        openrouter_base_url="https://openrouter.ai/api/v1",
        ollama_base_url="http://localhost:11434",
        custom_llm_api_key=None,
        custom_llm_base_url=None,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        baseline_collection_name="papers-baseline",
        corrupted_collection_name="papers-corrupted",
        repaired_collection_name="papers-repaired",
        source_api="https://api.crossref.org/works",
        source_query="agentic retrieval augmented generation large language model",
        source_filter="from-pub-date:2025-01-01,has-abstract:true",
        max_results=2,
        top_k=4,
        freshness_threshold_days=180,
        refresh_source=False,
        refresh_test_set=False,
        paths=Paths(
            project_dir=tmp_path,
            workspace_dir=tmp_path.parent,
            raw_api_response=data_dir / "raw" / "crossref_response.json",
            raw_records_json=data_dir / "raw" / "crossref_records.json",
            clean_csv=data_dir / "clean" / "papers_clean.csv",
            clean_json=data_dir / "clean" / "papers_clean.json",
            chroma_dir=data_dir / "chroma",
            embeddings_json=data_dir / "embeddings" / "papers_embeddings.json",
            corrupted_clean_csv=data_dir / "clean" / "papers_clean_corrupted.csv",
            corrupted_clean_json=data_dir / "clean" / "papers_clean_corrupted.json",
            corrupted_embeddings_json=data_dir / "embeddings" / "papers_embeddings_corrupted.json",
            repaired_clean_csv=data_dir / "clean" / "papers_clean_repaired.csv",
            repaired_clean_json=data_dir / "clean" / "papers_clean_repaired.json",
            repaired_embeddings_json=data_dir / "embeddings" / "papers_embeddings_repaired.json",
            eval_testset=data_dir / "eval" / "test_set.json",
            baseline_metrics=data_dir / "results" / "baseline_metrics.json",
            baseline_answers=data_dir / "results" / "baseline_answers.json",
            demo_answers=data_dir / "results" / "agent_demo_answers.json",
            quality_dir=data_dir / "quality",
            gx_dir=data_dir / "quality" / "gx",
            freshness_report=data_dir / "quality" / "freshness_report.json",
            baseline_report=data_dir / "reports" / "phase1_report.md",
            corruption_log=data_dir / "results" / "corruption_log.json",
            corrupted_metrics=data_dir / "results" / "corrupted_metrics.json",
            corrupted_answers=data_dir / "results" / "corrupted_answers.json",
            repaired_metrics=data_dir / "results" / "repaired_metrics.json",
            repaired_answers=data_dir / "results" / "repaired_answers.json",
            comparison_report=data_dir / "reports" / "corruption_report.md",
        ),
    )


def test_parse_crossref_payload_and_roundtrip(tmp_path: Path) -> None:
    payload = {
        "message": {
            "items": [
                {
                    "DOI": "https://doi.org/10.1000/xyz123",
                    "title": ["  Example Paper  "],
                    "abstract": "<jats:p>  Hello <b>world</b>. </jats:p>",
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "subject": ["AI", "RAG"],
                    "published-online": {"date-parts": [[2024, 5, 2]]},
                    "updated": {"date-parts": [[2024, 5, 3]]},
                    "URL": "https://example.org/paper",
                    "link": [{"content-type": "application/pdf", "URL": "https://example.org/paper.pdf"}],
                    "comment": "  note  ",
                }
            ]
        }
    }

    records = parse_crossref_payload(payload)
    assert records == [
        PaperRecord(
            paper_id="doi:10.1000/xyz123",
            title="Example Paper",
            summary="Hello world.",
            authors=["Ada Lovelace"],
            categories=["AI", "RAG"],
            primary_category="AI",
            published="2024-05-02",
            updated="2024-05-03",
            abs_url="https://example.org/paper",
            pdf_url="https://example.org/paper.pdf",
            comment="note",
        )
    ]

    snapshot = tmp_path / "raw_records.json"
    write_json(snapshot, [asdict(record) for record in records])
    assert load_raw_records(snapshot) == records


def test_fetch_source_records_persists_raw_artifacts_and_retries(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.1000/abc456",
                    "title": ["Retry Paper"],
                    "abstract": "<jats:p>Retry works.</jats:p>",
                    "author": [{"given": "Grace", "family": "Hopper"}],
                    "subject": ["Systems"],
                    "issued": {"date-parts": [[2024, 1, 1]]},
                    "updated": {"date-parts": [[2024, 1, 2]]},
                    "URL": "https://example.org/retry",
                }
            ]
        }
    }

    calls: list[int] = []

    class FakeResponse:
        def __init__(self, status_code: int, body: dict) -> None:
            self.status_code = status_code
            self._body = body

        def json(self) -> dict:
            return self._body

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    def fake_get(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return FakeResponse(429, payload)
        return FakeResponse(200, payload)

    monkeypatch.setattr("ingestion.crossref.requests.get", fake_get)
    monkeypatch.setattr("ingestion.crossref.time.sleep", lambda *_args, **_kwargs: None)

    records = fetch_source_records(settings)

    assert len(calls) == 2
    assert records[0].paper_id == "doi:10.1000/abc456"
    assert settings.paths.raw_api_response.exists()
    assert settings.paths.raw_records_json.exists()
    assert read_json(settings.paths.raw_api_response) == payload
    assert read_json(settings.paths.raw_records_json)[0]["title"] == "Retry Paper"
