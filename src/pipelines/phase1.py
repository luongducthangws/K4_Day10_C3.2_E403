from __future__ import annotations


from dataclasses import asdict

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== [PHASE 1] Starting Baseline End-to-End Data Pipeline ===")
    
    # 1. Load Settings
    settings = load_settings()
    print(f"Loaded Settings: provider={settings.llm_provider}, model={settings.model_name}")

    # 2. Fetch or Load Raw Records
    print("Step 1: Ingesting Raw Data from Source...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    print(f"Ingested {len(records)} raw records.")

    # 3. Clean Data
    print("Step 2: Cleaning Data & Computing Features...")
    df_clean = build_clean_dataframe(records, now_utc())
    write_csv(df_clean, settings.paths.clean_csv)
    records_dict = df_clean.to_dict(orient="records")
    write_json(settings.paths.clean_json, records_dict)
    print(f"Cleaned {len(df_clean)} records. Saved to CSV & JSON.")

    # 4. Build Chroma Index
    print("Step 3: Building Vector Store Index with MiniLM Embeddings...")
    index = LocalEmbeddingIndex.build(
        df=df_clean,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"Indexed {len(index.documents)} documents into collection '{index.collection_name}'.")

    # 5. Build or Load Test Set
    print("Step 4: Preparing Evaluation QA Test Set...")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df_clean, settings.paths.eval_testset)
    else:
        test_set = build_test_set(df_clean, settings.paths.eval_testset)
    print(f"Generated {len(test_set)} evaluation test questions.")

    # 6. Evaluate Pipeline
    print("Step 5: Running Baseline Evaluation...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = eval_bundle.summary
    print("Baseline Evaluation Metrics:")
    print(f"  - Retrieval Hit Rate : {metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  - Mean Token F1     : {metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  - LLM Judge Accuracy : {metrics.get('judge_accuracy', 0.0):.4f}")
    print(f"  - Mean Judge Score   : {metrics.get('mean_judge_score', 0.0):.2f} / 5.0")

    # 7. Quality Checks & Freshness Report
    print("Step 6: Running Data Observability & Freshness Audits...")
    quality_report = run_data_quality_checks(df_clean, settings, "baseline_quality.json")
    freshness_report = build_freshness_report(df_clean, settings, settings.paths.freshness_report)
    # Same payload under the state-specific name so baseline/corrupted/repaired
    # freshness artifacts form a symmetric, comparable set.
    build_freshness_report(df_clean, settings, settings.paths.baseline_freshness_report)
    print(f"  - Data Quality Passed: {quality_report['all_passed']}")
    print(f"  - Data Freshness     : {freshness_report['is_fresh']}")

    # 8. Agent Demo Answers (Optional QA Demo)
    print("Step 7: Running Agent QA Demo...")
    demo_questions = [
        "What are the latest advances in agentic RAG for LLMs?",
        f"Who wrote the paper '{df_clean.iloc[0]['title']}'?",
    ]
    demo_results = []
    try:
        agent = build_agent(settings, index)
        for q in demo_questions:
            answer = run_agent_question(agent, q)
            demo_results.append({"question": q, "answer": answer})
    except Exception as exc:
        print(f"Note: Agent demo skipped or ran into fallback: {exc}")
        for q in demo_questions:
            demo_results.append({"question": q, "answer": "Agent answer unavailable under current credentials."})
    write_json(settings.paths.demo_answers, demo_results)

    # 9. Generate Baseline Report
    print("Step 8: Generating Markdown Baseline Report...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "raw_count": len(records),
        "clean_count": len(df_clean),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"Report written to: {settings.paths.baseline_report}")
    print("=== [PHASE 1] Pipeline Completed Successfully! ===")


if __name__ == "__main__":
    main()
