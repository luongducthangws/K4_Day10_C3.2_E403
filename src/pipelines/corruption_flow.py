from __future__ import annotations


import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== [CORRUPTION FLOW] Starting Data Corruption, Evaluation & Repair Pipeline ===")

    # 1. Load Settings & Baseline Data
    settings = load_settings()
    if not settings.paths.clean_csv.exists() or not settings.paths.baseline_metrics.exists():
        print("Baseline data or metrics missing. Running Phase 1 baseline first...")
        from pipelines.phase1 import main as run_phase1
        run_phase1()

    print("Step 1: Loading Baseline Clean Data & Baseline Metrics...")
    df_baseline = pd.read_csv(settings.paths.clean_csv)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"Loaded {len(df_baseline)} baseline rows.")

    # 2. Corrupt Dataset
    print("Step 2: Simulating Data Corruption (Row drops, blank summaries, noise, stale dates, duplicates)...")
    df_corrupted = corrupt_clean_dataframe(df_baseline, settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    corrupted_records = df_corrupted.to_dict(orient="records")
    write_json(settings.paths.corrupted_clean_json, corrupted_records)
    print(f"Generated corrupted dataset with {len(df_corrupted)} rows.")

    # 3. Rebuild Corrupted Index & Evaluate
    print("Step 3: Building Vector Store Index for Corrupted Data...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    print("Step 4: Evaluating Corrupted Pipeline against Baseline Test Set...")
    corrupted_eval_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_eval_bundle.summary
    print("Corrupted Evaluation Metrics:")
    print(f"  - Retrieval Hit Rate : {corrupted_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  - Mean Token F1     : {corrupted_metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  - LLM Judge Accuracy : {corrupted_metrics.get('judge_accuracy', 0.0):.4f}")

    # 4. Quality & Freshness Checks on Corrupted Data
    print("Step 5: Running Quality & Freshness Audits on Corrupted Data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted_quality.json")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.corrupted_freshness_report
    )

    # 5. Data Repair Flow
    print("Step 6: Executing Data Repair Flow (Re-ingesting & Re-cleaning from Raw Records)...")
    if settings.paths.raw_records_json.exists():
        raw_records = load_raw_records(settings.paths.raw_records_json)
    else:
        raw_records = fetch_source_records(settings)
    df_repaired = build_clean_dataframe(raw_records, now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    repaired_records = df_repaired.to_dict(orient="records")
    write_json(settings.paths.repaired_clean_json, repaired_records)
    print(f"Repaired dataset built with {len(df_repaired)} clean rows.")

    # 6. Rebuild Repaired Index & Evaluate
    print("Step 7: Building Vector Store Index for Repaired Data...")
    repaired_index = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    print("Step 8: Re-evaluating Repaired Pipeline against Test Set...")
    repaired_eval_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_eval_bundle.summary
    print("Repaired Evaluation Metrics:")
    print(f"  - Retrieval Hit Rate : {repaired_metrics.get('retrieval_hit_rate', 0.0):.4f}")
    print(f"  - Mean Token F1     : {repaired_metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"  - LLM Judge Accuracy : {repaired_metrics.get('judge_accuracy', 0.0):.4f}")

    # 7. Quality & Freshness Checks on Repaired Data
    print("Step 9: Running Quality & Freshness Audits on Repaired Data...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired_quality.json")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.repaired_freshness_report
    )

    # 8. Comparison Report
    print("Step 10: Generating Markdown Comparison Report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Comparison report written to: {settings.paths.comparison_report}")
    print("=== [CORRUPTION FLOW] Completed Successfully! ===")


if __name__ == "__main__":
    main()
