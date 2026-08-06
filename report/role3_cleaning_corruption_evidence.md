# Báo cáo cá nhân Role 3 — Cleaning & Corruption owner

## Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Thái Dương |
| MSSV | 2A202601518 |
| Khóa/Lớp | K4 |
| Nhóm | Nhóm 6 thành viên |
| Vai trò chính | Role 3 — Cleaning & Corruption owner |
| Repository | `luongducthangws/K4_Day10_C3.2_E403` |
| Ngày hoàn thành | 2026-08-06 |

## Vai trò và phạm vi

Phạm vi: `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, clean/corrupted/repaired artifacts và validation tests.

Tôi phụ trách contract dữ liệu sạch, triển khai cleaning, tạo corruption có kiểm soát và xác minh khả năng repair từ raw snapshot. Tôi không nhận ownership cho orchestration, evaluation, retrieval hoặc observability; các phần đó chỉ được dùng để kiểm tra handoff và tác động end-to-end của dữ liệu.

| Deliverable | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- |
| Cleaning và data model | Danh sách `PaperRecord`, thời điểm chạy | DataFrame theo clean schema, `cleaning_stats` | Hoàn thành |
| Corruption simulation | Clean DataFrame | Corrupted DataFrame, event log JSON | Hoàn thành |
| Validation | Dữ liệu test xác định trước | Test cleaning contract, corruption và audit log | Hoàn thành |
| Evidence CP0–CP6 | Code, tests và artifacts | Báo cáo cá nhân này | Hoàn thành |

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

## Giải thích kỹ thuật

### Cleaning và data model

Payload nguồn có thể chứa HTML/JATS, khoảng trắng thừa, list tác giả/chủ đề trùng, ngày sai, trường thiếu và paper trùng ID. Nếu đưa trực tiếp vào index, document identity và nội dung embedding không ổn định, khiến test set và retrieval khó đối chiếu.

Giải pháp đã triển khai:

- Chuẩn hóa whitespace, loại HTML/JATS khỏi title, summary và comment.
- Chuẩn hóa, loại trùng authors/categories không phân biệt hoa thường.
- Dùng fallback `Unknown Author` và `General` khi list hợp lệ bị thiếu.
- Chuẩn hóa ngày sang ISO; loại record thiếu ID/title/summary, summary dưới 10 ký tự hoặc ngày published sai.
- Chuẩn hóa `paper_id` về chữ thường và deduplicate theo ID ổn định.
- Khi trùng ID, ưu tiên summary dài hơn; nếu cần, ưu tiên bản updated mới hơn.
- Tính `age_days`, `summary_chars` và tạo `text_for_embedding` bằng helper dùng chung.
- Ghi `cleaning_stats` gồm số input/output, duplicate và lý do reject; không loại record âm thầm.

| Thành phần | Contract |
| --- | --- |
| Input | `list[PaperRecord]`, `run_date: datetime` |
| Identity | `paper_id` đã normalize, unique sau cleaning |
| Output | DataFrame có thứ tự cột cố định trong `CLEAN_COLUMNS` |
| Trường index cần | `paper_id`, `title`, metadata, `text_for_embedding` |
| Audit | `df.attrs["cleaning_stats"]` |
| Empty input hợp lệ | DataFrame rỗng nhưng vẫn giữ đúng schema |

### Corruption và repair

`corrupt_clean_dataframe` copy sâu đầu vào để không sửa baseline. Hàm kiểm tra required columns, chọn record theo quy tắc xác định trước và tạo sáu event: drop record mới nhất, blank summary, inject noise, truncate title, làm ngày published stale và duplicate row.

Sau mutation, `summary_chars` và `text_for_embedding` được build lại để dữ liệu dẫn xuất khớp nội dung đã hỏng. Log lưu loại lỗi, `paper_id`, tham số, giá trị hoặc row count trước/sau. Repair không sửa tay corrupted data mà chạy lại cleaning từ raw snapshot đã dùng ở baseline.

## Quyết định kỹ thuật quan trọng

- **Bối cảnh:** baseline, corrupted và repaired đều cần text cho index; nếu mỗi flow tự ghép chuỗi, format dễ lệch và comparison mất công bằng.
- **Phương án cân nhắc:** ghép text riêng trong từng pipeline, hoặc dùng một helper duy nhất.
- **Lựa chọn:** dùng `build_text_for_embedding` cho cả cleaning và corruption.
- **Lý do:** output deterministic, giảm contract drift và bảo đảm derived field được cập nhật sau corruption.
- **Bằng chứng:** unit test duyệt mọi corrupted row và so `text_for_embedding` với kết quả helper.

Corruption cũng không dùng random. Quy tắc chọn row cố định giúp cùng input tạo cùng output và event log, nên tác động có thể audit và debug.

## Blocker đã xử lý

- **Triệu chứng:** test suite sau lần pull mới báo `Paths.__init__() missing 3 required positional arguments`.
- **Nguyên nhân:** shared `Paths` contract được thêm ba freshness artifact nhưng fixture trong `tests/test_crossref.py` chưa cập nhật.
- **Cách xử lý:** bổ sung `baseline_freshness_report`, `corrupted_freshness_report`, `repaired_freshness_report` vào fixture.
- **Kết quả:** test suite trở lại `6 passed`.
- **Điều học được:** khi shared config thay đổi, mọi constructor/fixture phải được cập nhật cùng lúc; integration test giúp phát hiện contract drift sớm.

## Hiểu biết luồng end-to-end

1. Crossref được fetch và lưu raw response/raw records trước khi cleaning.
2. Cleaning tạo schema ổn định và `text_for_embedding`; `paper_id` nối raw, clean, index và ground truth.
3. MiniLM tạo embeddings; Chroma lưu collection tách biệt cho baseline, corrupted và repaired.
4. Evaluation dùng một test set cố định để đo retrieval và answer quality.
5. Quality/freshness artifacts phát hiện dữ liệu thiếu, trùng hoặc stale.
6. Corruption làm hỏng clean data có chủ đích, build lại index rồi đánh giá trên cùng test set.
7. Repair chạy lại cleaning từ raw snapshot, build collection riêng và đánh giá lại. Chỉ kết luận phục hồi khi artifacts và metrics quay về baseline.

## Bảng kết quả

Số liệu lấy trực tiếp từ artifacts trong `data/results/` và `data/quality/`:

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| Rows | 24 | 21 | 24 | Drop và duplicate tạo đúng chênh lệch đã log |
| retrieval_hit_rate | 1.000 | 0.600 | 1.000 | Giảm 0.400 rồi phục hồi |
| mean_token_f1 | 1.000 | 0.663 | 1.000 | Nội dung hỏng làm answer quality giảm |
| judge_accuracy | 1.000 | 0.650 | 1.000 | Giảm 0.350 rồi phục hồi |
| mean_judge_score | 5.000 | 3.600 | 5.000 | Corrupted thấp hơn baseline |
| duplicate IDs | 0 | 1 | 0 | Quality check phát hiện duplicate |
| empty summaries | 0 | 1 | 0 | Quality check phát hiện summary rỗng |
| stale rows theo quality | 0 | 1 | 0 | Quality check phát hiện age bị làm stale |
| Quality status | PASS | FAIL | PASS | Repair khôi phục quality |

Corruption tác động rõ vì 4 record mới nhất bị drop, đồng thời title/summary của các record còn lại bị làm thiếu hoặc nhiễu. Retrieval hit giảm kéo theo token F1 và judge metrics giảm. Repair từ raw đưa row count, quality signals và metrics trở lại baseline.

### Giới hạn kết luận

- Lần chạy evidence dùng heuristic judge fallback, không phải online LLM judge.
- Ragas được chủ động tắt và ghi `skipped`; không trình bày metrics trên như kết quả Ragas.
- `corrupted_freshness.json` hiện có row count khác corrupted dataset sau thay đổi từ nhánh khác, nên tôi không dùng artifact đó để kết luận quan hệ nhân quả. Cần rerun corruption flow nếu nhóm muốn chốt freshness comparison mới.

## Tests và lệnh xác minh

```bash
.venv/bin/python -m pytest -q
# 6 passed

.venv/bin/python -m compileall -q src script
git diff --check
```

`tests/test_cleaning_corruption.py` kiểm tra cleaning rules, stable empty schema, corruption deterministic, audit log, derived fields và invalid input.

## Điều học được và hướng cải thiện

1. Stable identity và schema là contract nối toàn bộ pipeline, không chỉ là chi tiết cleaning.
2. Corruption phải deterministic, có event log và đo trên cùng test set mới chứng minh được tác động.
3. Derived fields phải được rebuild sau mutation; nếu không, index có thể dùng nội dung cũ và làm kết quả sai lệch.

Nếu có thêm thời gian, tôi sẽ thay regex HTML đơn giản bằng parser chuyên dụng cho JATS phức tạp hơn, thêm property-based tests và chạy online LLM judge/Ragas để bổ sung góc đánh giá.

## Cam kết thành viên

- [x] Báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận chính có code, test hoặc artifact để đối chiếu.
- [x] Tôi phân biệt rõ heuristic judge với online LLM judge/Ragas.
- [x] Tôi không nhận ownership cho module do vai trò khác phụ trách.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn report nhóm hoặc report thành viên khác.

**Họ và tên:** Hoàng Thái Dương

**MSSV:** 2A202601518

**Ngày xác nhận:** 2026-08-06
