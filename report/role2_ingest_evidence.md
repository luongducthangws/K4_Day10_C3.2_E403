# Role 2 — Ingestion owner — Evidence log (6 checkpoint)

Phạm vi: `src/ingestion/crossref.py` · `data/raw/`.
File này ghi bằng chứng thật cho từng checkpoint, dùng để điền vào `report/individual_report.md` (mục 3, 6, 7).

## Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phùng Đình Đạt |
| MSSV | 2A202601540 |
| Khóa/Lớp | K4 |
| Nhóm | Nhóm 6 thành viên |

## CP0 — Khởi động, contract & ingestion raw

- `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` đã implement đủ trong `src/ingestion/crossref.py`.
- `paper_id` ổn định qua `_stable_paper_id`: ưu tiên `doi:<doi>`, fallback slug từ title+published.
- Raw response được ghi (`write_json(settings.paths.raw_api_response, ...)`) trước khi parse.
- Retry/backoff cho HTTP 429/503: tối đa 4 lần, backoff `1.5 * attempt` giây.
- Xác minh: `python3 -m py_compile src/ingestion/crossref.py` → OK, không còn `TODO(student)`/`NotImplementedError`.

## CP1 — Đối chiếu raw snapshot

- `data/raw/crossref_records.json`: 24 record.
- 0 record thiếu `title` hoặc `published`.
- Kết luận: đủ field để cleaning owner dùng, không phải đoán dữ liệu.

## CP2 — Trace paper_id xuyên raw → clean → index metadata

- Sample `paper_id = 10-2118-234689-pa`.
- Có trong `data/raw/crossref_records.json`.
- Có trong `data/embeddings/papers_embeddings.json` (collection `papers-baseline`, model `sentence-transformers/all-MiniLM-L6-v2`), metadata đầy đủ: `paper_id, title, published, authors_joined, categories_joined, summary, abs_url, pdf_url`.
- Source evidence cho evaluator: toàn bộ 10 `ground_truth_doc_ids` trong `data/results/baseline_answers.json` đều resolve được về `data/raw/crossref_records.json` (0 ID lạc). Baseline hiện tại retrieval hit 40/40 — chưa có case miss để minh hoạ; khi phát sinh miss, tra theo `ground_truth_doc_ids` → raw record là quy trình chuẩn để cung cấp evidence.

## CP3 — Baseline end-to-end

- raw 24 record / clean baseline 24 record — không record nào bị drop khi build baseline (0 chênh lệch).
- Audit `src/pipelines/phase1.py:27`: chỉ gọi `fetch_source_records` khi `settings.refresh_source` bật hoặc `raw_records_json` chưa tồn tại; mặc định dùng `load_raw_records` từ snapshot có sẵn → baseline không refetch nguồn ngoài ý muốn.

## CP4 — Nghỉ

- Raw source giữ nguyên, dùng làm điểm khôi phục cho các bước sau.

## CP5 — Corruption có kiểm soát

- `git status data/raw/` sạch trước và sau khi chạy corruption flow — raw không bị chạm.
- `data/results/corruption_log.json` có entry `drop_records` xoá 2 `paper_id`, trong đó `10-2118-234689-pa` — record có lineage rõ, dùng để chứng minh repair.
- Audit `src/pipelines/corruption_flow.py:69-72`: bước repair ưu tiên `load_raw_records` từ snapshot có sẵn, chỉ `fetch_source_records` khi file raw không tồn tại → không fetch nguồn mới làm lệch so sánh baseline/corrupted.

## CP6 — Repair, comparison, hygiene

- Trace `10-2118-234689-pa`: có ở raw → **mất** ở `data/clean/papers_clean_corrupted.json` (khớp corruption log) → **có lại** ở `data/clean/papers_clean_repaired.json`. Bằng chứng repair từ raw thật, không sửa tay.
- `.env` không nằm trong git tracked files (`git ls-files | grep .env` rỗng), có trong `.gitignore` → không lộ secret/API key.

## Lệnh xác minh dùng để tạo bằng chứng trên

```bash
python3 -m py_compile src/ingestion/crossref.py
rg -n "TODO\(student\)|NotImplementedError" src/ingestion/crossref.py
git status --short data/raw/
rg -n "refresh_source" src/pipelines/phase1.py src/pipelines/corruption_flow.py
```
