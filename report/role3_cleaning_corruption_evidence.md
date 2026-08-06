# Role 3 — Cleaning & corruption owner — Evidence log

Phạm vi: `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, clean/corrupted/repaired artifacts và validation tests.

## CP0 — Clean contract và validation plan

- Clean schema được khóa trong `CLEAN_COLUMNS`: stable `paper_id`, normalized text/list fields, ISO dates, `age_days`, `summary_chars`, URLs và `text_for_embedding`.
- `build_text_for_embedding` là helper dùng chung cho baseline, corrupted và repaired data; tránh lệch format khi rebuild.
- Validation gồm unit tests với dữ liệu giả và integration run trên raw snapshot 24 records.

## CP1 — Cleaning, data model và quality gates

- Chuẩn hóa whitespace, HTML/JATS, authors và categories; deduplicate list values không phân biệt hoa thường.
- Fallback rõ ràng: `Unknown Author`, `General`; không để ground truth author/category rỗng.
- Loại record thiếu `paper_id`, title, summary; summary dưới 10 ký tự; ngày published không hợp lệ.
- Deduplicate theo stable `paper_id`; ưu tiên record có summary dài hơn và updated mới hơn.
- `df.attrs["cleaning_stats"]` giữ input/output count, lý do reject và duplicate count.
- Baseline thật: raw 24, clean 24, reject 0, duplicate 0; `paper_id` unique, `text_for_embedding` không rỗng.

## CP2 — Handoff clean sang index/test set

- `data/clean/papers_clean.csv` và `.json` có đủ field index cần: `paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`, URLs và `text_for_embedding`.
- `data/embeddings/papers_embeddings.json` chứa 24 documents trong collection `papers-baseline`.
- Test set có 40 câu từ 10 papers; tất cả `ground_truth_doc_ids` dùng stable `paper_id` trong clean data.
- Unit tests xác minh schema ổn định, HTML được loại, fallback fields, deduplication và derived text.

## CP3 — Baseline end-to-end

- Lệnh chạy offline deterministic:

```bash
env GOOGLE_API_KEY= RUN_RAGAS=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv/bin/python script/run_phase1.py
```

- Kết quả baseline: 24 rows, quality pass, freshness pass.
- Metrics trên 40 samples: retrieval hit `1.0000`, token F1 `1.0000`, judge accuracy `1.0000`, mean judge score `5.00`.
- Judge dùng heuristic fallback có sẵn vì run này chủ động không gọi LLM; Ragas được ghi `skipped` trong metrics. Không trình bày hai giá trị này như kết quả LLM/Ragas online.

## CP4 — Nghỉ

- Raw snapshot và baseline artifacts được giữ nguyên làm mốc trước corruption.

## CP5 — Corruption có kiểm soát và impact

- `corrupt_clean_dataframe` deterministic, không mutate baseline dataframe.
- Sáu event được ghi trong `data/results/corruption_log.json`:
  - drop 4 latest records;
  - blank 1 summary;
  - inject noise 1 summary;
  - truncate 1 title;
  - làm stale 1 publication date thêm 3650 ngày;
  - duplicate 1 row.
- Row count: baseline 24, sau drop còn 20, sau duplicate thành 21.
- Quality phát hiện đúng: 1 empty summary, 1 duplicate `paper_id`, 1 stale row; `all_passed=false`.
- Metrics corrupted: retrieval hit `0.6000`, token F1 `0.6630`, judge accuracy `0.6500`, mean judge score `3.60`.
- Evidence nhân quả: drop/title/summary corruption làm retrieval hit giảm 0.40 và token F1 giảm khoảng 0.337; quality signals đồng thời chuyển fail.

## CP6 — Repair, comparison và hygiene

- Repair chạy lại `build_clean_dataframe` từ raw snapshot, không copy baseline và không sửa tay answers/metrics.
- Repaired data: 24 rows, 0 duplicate, 0 empty summary, 0 stale row; quality pass.
- Repaired metrics phục hồi: retrieval hit `1.0000`, token F1 `1.0000`, judge accuracy `1.0000`, mean judge score `5.00`.
- Sample lineage `10-2118-234689-pa`: có trong raw/baseline, bị drop theo corruption log, xuất hiện lại trong repaired data.
- `data/reports/corruption_report.md` phản ánh baseline/corrupted/repaired metrics sau lần chạy này.

## Tests và lệnh xác minh

```bash
.venv/bin/python -m pytest -q
# 6 passed

.venv/bin/python -m compileall -q src script
git diff --check
```

`tests/test_cleaning_corruption.py` kiểm tra cleaning rules, stable empty schema, corruption deterministic, audit log, derived fields và invalid input.
