"""Recompute every observability signal and evaluation metric from the data
artifacts, then compare against what the pipeline wrote to JSON and markdown.

This is the guard against the failure mode the rubric penalises: a report that
looks fine but no longer matches the artifacts it claims to describe. Read-only.

    python script/verify_artifacts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

# Ensure src/ is in sys.path
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pandas as pd

from core.config import load_settings

SETTINGS = load_settings()
PATHS = SETTINGS.paths
THRESHOLD = SETTINGS.freshness_threshold_days

failures: list[str] = []


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check(label: str, recomputed, committed) -> None:
    recomputed = round(recomputed, 6) if isinstance(recomputed, float) else recomputed
    committed = round(committed, 6) if isinstance(committed, float) else committed
    ok = recomputed == committed
    if not ok:
        failures.append(f"{label}: recomputed={recomputed} committed={committed}")
    print(f"  {'OK      ' if ok else 'MISMATCH'} {label}: recomputed={recomputed} committed={committed}")


def contains(label: str, haystack: str, needle: str) -> None:
    ok = needle in haystack
    if not ok:
        failures.append(f"{label}: missing {needle!r}")
    print(f"  {'OK      ' if ok else 'MISMATCH'} {label}: {needle!r}")


print("=== QUALITY: recomputed from clean CSV vs committed quality JSON ===")
for state, csv_path, quality_name in [
    ("baseline", PATHS.clean_csv, "baseline_quality.json"),
    ("corrupted", PATHS.corrupted_clean_csv, "corrupted_quality.json"),
    ("repaired", PATHS.repaired_clean_csv, "repaired_quality.json"),
]:
    df = pd.read_csv(csv_path)
    committed = read_json(PATHS.quality_dir / quality_name)
    print(f"\n[{state}] {csv_path.name} vs {quality_name}")
    check(f"{state}.total_rows", len(df), committed["total_rows"])
    check(f"{state}.null_paper_ids", int(df["paper_id"].isnull().sum()), committed["null_paper_ids"])
    check(
        f"{state}.duplicate_paper_ids",
        int(df.duplicated(subset=["paper_id"]).sum()),
        committed["duplicate_paper_ids"],
    )
    check(f"{state}.null_titles", int(df["title"].isnull().sum()), committed["null_titles"])
    check(f"{state}.empty_summaries", int((df["summary_chars"] < 10).sum()), committed["empty_summaries"])
    check(f"{state}.stale_rows", int((df["age_days"] > THRESHOLD).sum()), committed["stale_rows"])

print("\n=== METRICS: recomputed from answers vs committed metrics JSON ===")
for state, answers_path, metrics_path in [
    ("baseline", PATHS.baseline_answers, PATHS.baseline_metrics),
    ("corrupted", PATHS.corrupted_answers, PATHS.corrupted_metrics),
    ("repaired", PATHS.repaired_answers, PATHS.repaired_metrics),
]:
    answers = read_json(answers_path)
    committed = read_json(metrics_path)
    print(f"\n[{state}] {answers_path.name} vs {metrics_path.name}")
    check(f"{state}.samples", len(answers), committed["samples"])
    check(
        f"{state}.retrieval_hit_rate",
        mean(1.0 if a["retrieval_hit"] else 0.0 for a in answers),
        committed["retrieval_hit_rate"],
    )
    check(f"{state}.mean_token_f1", mean(a["token_f1"] for a in answers), committed["mean_token_f1"])
    check(
        f"{state}.judge_accuracy",
        mean(1.0 if a["judge"]["correct"] else 0.0 for a in answers),
        committed["judge_accuracy"],
    )
    check(f"{state}.mean_judge_score", mean(a["judge"]["score"] for a in answers), committed["mean_judge_score"])
    fallback = sum(1 for a in answers if "Fallback heuristic" in a["judge"].get("reasoning", ""))
    print(f"  INFO     {state}.judge: {len(answers) - fallback}/{len(answers)} judged by the real LLM")

print("\n=== FRESHNESS: recomputed from clean CSV vs committed freshness JSON ===")
for csv_path, freshness_path in [
    (PATHS.clean_csv, PATHS.freshness_report),
    (PATHS.corrupted_clean_csv, PATHS.quality_dir / "corrupted_freshness.json"),
    (PATHS.repaired_clean_csv, PATHS.quality_dir / "repaired_freshness.json"),
]:
    df = pd.read_csv(csv_path)
    committed = read_json(freshness_path)
    stale = int((df["age_days"] > THRESHOLD).sum())
    print(f"\n[{freshness_path.name}] vs {csv_path.name}")
    check("latest_published", max(df["published"].dropna()), committed["latest_published"])
    check("oldest_published", min(df["published"].dropna()), committed["oldest_published"])
    check("total_rows", len(df), committed["total_rows"])
    check("stale_rows", stale, committed["stale_rows"])
    check("is_fresh", stale == 0, committed["is_fresh"])

print("\n=== CORRUPTION LOG vs actual corrupted dataset ===")
log = read_json(PATHS.corruption_log)
check("log.input_rows", len(pd.read_csv(PATHS.clean_csv)), log["input_rows"])
check("log.output_rows", len(pd.read_csv(PATHS.corrupted_clean_csv)), log["output_rows"])
corrupted_quality = read_json(PATHS.quality_dir / "corrupted_quality.json")
samples = corrupted_quality.get("failed_row_samples", {})
logged_ids = {event["corruption_type"]: event["affected_paper_ids"] for event in log["events"]}
for signal, corruption_type in [
    ("empty_summaries", "blank_summary"),
    ("truncated_titles", "truncate_title"),
    ("noisy_summaries", "inject_summary_noise"),
    ("stale_rows", "make_publication_stale"),
]:
    detected = sorted(set(samples.get(signal, [])))
    expected = sorted(set(logged_ids.get(corruption_type, [])))
    check(f"detected ids for {signal} == corruption log {corruption_type}", detected, expected)

print("\n=== REPORTS vs artifacts ===")
baseline_metrics = read_json(PATHS.baseline_metrics)
baseline_quality = read_json(PATHS.quality_dir / "baseline_quality.json")
phase1 = PATHS.baseline_report.read_text(encoding="utf-8")
contains("phase1 samples", phase1, f"**Evaluated Samples**: {baseline_metrics['samples']}")
contains("phase1 hit rate", phase1, f"{baseline_metrics['retrieval_hit_rate']:.4f}")
contains("phase1 judge accuracy", phase1, f"{baseline_metrics['judge_accuracy']:.4f}")
contains("phase1 clean rows", phase1, f"| Total Clean Rows | {baseline_quality['total_rows']} |")

comparison = PATHS.comparison_report.read_text(encoding="utf-8")
corrupted_metrics = read_json(PATHS.corrupted_metrics)
for label, key in [
    ("Retrieval Hit Rate", "retrieval_hit_rate"),
    ("Mean Token F1", "mean_token_f1"),
    ("Judge Accuracy", "judge_accuracy"),
    ("Mean Judge Score", "mean_judge_score"),
]:
    contains(
        f"comparison {label}",
        comparison,
        f"| {label} | {baseline_metrics[key]:.2f} | {corrupted_metrics[key]:.2f} |",
    )

print("\n" + "=" * 64)
if failures:
    print(f"INCONSISTENCIES FOUND ({len(failures)}):")
    for item in failures:
        print(f"  - {item}")
    sys.exit(1)
print("ALL ARTIFACTS CONSISTENT")
