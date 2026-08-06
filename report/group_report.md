# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | Group 4 |
| Repository | https://github.com/luongducthangws/K4_Day10_C3.2_E403 |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

> Cột "Họ và tên" và "MSSV" cần điền trước khi nộp. Cột "Tác giả commit" lấy từ `git log` để đối chiếu ai thực sự đóng góp phần nào.

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu | Tác giả commit |
| --: | --- | --- | --- | --- | --- |
| 1 | [Điền] | [MSSV] | Role 1 - Integrator & release | `src/pipelines/`, `script/` | `lichtchess666-ai20k` |
| 2 | [Điền] | [MSSV] | Role 2 - Ingestion | `src/ingestion/crossref.py`, `data/raw/` | `p-dat1301` |
| 3 | [Điền] | [MSSV] | Role 3 - Cleaning & corruption | `src/ingestion/cleaning.py`, `corruption.py` | `duong` |
| 4 | [Điền] | [MSSV] | Role 4 - RAG & agent | `src/retrieval/`, `data/embeddings/` | `Tri Tue` |
| 5 | Lương Đức Thắng | [MSSV] | Role 5 - Evaluation / Bonus | `src/evaluation/` | `luongducthangDS` |
| 6 | [Điền - người nộp báo cáo này] | [MSSV] | Role 6 - Observability | `src/observability/`, `script/verify_artifacts.py`, `data/quality/` | [điền sau khi commit] |

## 2. Tóm tắt kết quả

Nhóm đã triển khai toàn bộ luồng dữ liệu từ ingestion, cleaning, embedding, evaluation, observability đến corruption và repair. Baseline pipeline tạo ra đầy đủ artifact raw/clean/embedding/evaluation/results/report. Corruption làm giảm rõ rệt các chỉ số retrieval và judging: retrieval hit rate giảm từ 1.000 xuống 0.600, mean_token_f1 từ 1.000 xuống 0.663, judge_accuracy từ 0.900 xuống 0.600. Repair từ raw snapshot khôi phục **chính xác** hai metric deterministic về baseline (Δ = 0.000); hai metric do LLM judge chấm lệch nhẹ trong biên độ variance của judge. Blocker chính là đảm bảo các artifact và báo cáo luôn khớp với nhau khi chạy lại pipeline; nhóm đã xử lý bằng một script đối chiếu (recompute mọi signal/metric từ dữ liệu thật rồi so với JSON/report đã ghi).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref query/filter | Fetch, retry/backoff, parse, lưu raw trước khi parse | `data/raw/` | Role 2 |
| Cleaning | Raw records | Normalize, deduplicate, build `text_for_embedding`, tính `age_days` | `data/clean/` | Role 3 |
| Embedding/index | Cleaned dataframe | MiniLM embeddings + 3 Chroma collection tách biệt | `data/embeddings/`, `data/chroma/` | Role 4 |
| Evaluation | Cleaned data + test set | Sinh test set, chấm retrieval/answer, LLM judge | `data/eval/`, `data/results/` | Role 5 |
| Observability | Dataframe của cả 3 trạng thái + metrics | Quality checks, freshness, 2 report markdown, script đối chiếu | `data/quality/`, `data/reports/` | Role 6 |
| Corruption/repair | Baseline clean dataframe + raw snapshot | Corrupt có chủ đích + repair từ raw | `data/results/corruption_log.json` | Role 3 |
| Orchestration | Pipeline config | Chạy baseline flow và corruption flow | Toàn bộ artifact + metrics | Role 1 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| LLM_PROVIDER | openrouter |
| LLM_MODEL | google/gemini-2.5-flash |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 |
| Retrieval top_k | 4 |
| Freshness threshold | 180 ngày |

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

Kiểm tra tính nhất quán (chạy sau hai lệnh trên):

```bash
python script/verify_artifacts.py
```

Script recompute lại toàn bộ quality signal, freshness và evaluation metric từ dữ liệu thật rồi so với JSON/markdown đã ghi; exit code `1` nếu có bất kỳ sai lệch nào.

Chạy test:

```bash
python -m pytest tests/ -q
```

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 | data/results/baseline_metrics.json, data/reports/phase1_report.md |
| Corruption flow | Thành công | 2026-08-06 | data/results/corrupted_metrics.json, data/results/repaired_metrics.json, data/reports/corruption_report.md |
| verify_artifacts.py | Thành công (exit 0, ALL ARTIFACTS CONSISTENT) | 2026-08-06 | Console output; đối chiếu mọi signal/metric với artifact |
| pytest | Thành công (6 passed) | 2026-08-06 | tests/test_crossref.py, tests/test_cleaning_corruption.py |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Query/filter | agentic retrieval augmented generation large language model + from-pub-date threshold |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Tối đa 4 lần thử, backoff lũy tiến `1.5 * attempt` giây, áp dụng cho 429/503 và lỗi timeout/connection; hết số lần thử thì raise `RuntimeError` (không có fallback dữ liệu mẫu) |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại record thiếu title/summary | Completeness | 0 | Clean dataframe có các row hợp lệ |
| Normalize authors/categories | Validity | 24 | data/clean/papers_clean.json |
| Tạo text_for_embedding | Relevance | 24 | data/embeddings/papers_embeddings.json |
| Tính age_days | Freshness | 24 | data/quality/freshness_report.json |

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 40 |
| Các question_type | summary, authors, date, categories |
| Ground-truth document ID | Từ paper_id của cleaned dataset |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection | Chroma persistent collection papers-baseline/papers-corrupted/papers-repaired |
| Retrieval top_k | 4 |
| Test set dùng chung cho ba trạng thái | data/eval/test_set.json |

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | data/raw/ | Có | Có raw response và raw records JSON |
| Cleaned dataset | data/clean/ | Có | Có CSV/JSON clean |
| Embedding manifest/index | data/embeddings/ | Có | Có manifest cho baseline/corrupted/repaired |
| Evaluation set | data/eval/ | Có | Có test_set.json |
| Baseline metrics | data/results/baseline_metrics.json | Có | Metrics baseline đã lưu |
| Quality/freshness | data/quality/ | Có | Baseline và các trạng thái khác |
| Baseline report | data/reports/phase1_report.md | Có | Report baseline đã tạo |

### Baseline metrics

Nguồn: `data/results/baseline_metrics.json` (40 sample).

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| retrieval_hit_rate | 1.000 | Baseline retrieval trúng ground-truth doc trên toàn bộ 40 sample |
| mean_token_f1 | 1.000 | `qa.py` trích đáp án trực tiếp từ metadata nên khớp tuyệt đối với ground truth |
| judge_accuracy | 0.900 | LLM judge (thật) chấm 36/40 sample là đúng về mặt nội dung |
| mean_judge_score | 4.600 | Điểm trung bình của LLM judge trên thang 1-5 |

Lưu ý trung thực: `mean_token_f1 = 1.000` không phải dấu hiệu "hệ thống hoàn hảo". `src/retrieval/qa.py` là extractive - nó lấy thẳng `authors_joined`, `published`, `categories_joined` hoặc câu đầu của `summary` từ metadata, và test set dùng đúng các trường đó làm ground truth. Vì vậy token F1 chỉ đo được retrieval có lấy đúng document hay không. `judge_accuracy = 0.900` (thấp hơn 1.0) mới là tín hiệu chất lượng độc lập, vì LLM judge đánh giá nội dung câu trả lời chứ không so token.

## 8. Data quality và freshness

Bộ check chia hai tầng. Tầng *blocking* quyết định `all_passed`; tầng *content-integrity* bắt các hư hại vẫn để field non-null và đủ dài nên tầng blocking không thấy được.

| Tầng | Check | Baseline | Corrupted | Bằng chứng |
| --- | --- | ---: | ---: | --- |
| Blocking | Row count | 24 | 21 | `data/quality/*_quality.json` |
| Blocking | Null paper IDs | 0 | 0 | `data/quality/*_quality.json` |
| Blocking | Duplicate paper IDs | 0 | 1 | `data/quality/*_quality.json` |
| Blocking | Null titles | 0 | 0 | `data/quality/*_quality.json` |
| Blocking | Empty summaries | 0 | 1 | `data/quality/*_quality.json` |
| Content-integrity | Truncated titles | 0 | 1 | `data/quality/*_quality.json` |
| Content-integrity | Noisy summaries | 0 | 1 | `data/quality/*_quality.json` |
| Content-integrity | Stale rows | 0 | 1 | `data/quality/*_quality.json` |
| Freshness | Trạng thái | FRESH | STALE | `freshness_report.json`, `baseline_freshness.json`, `corrupted_freshness.json` |

Hai check `truncated_titles` và `noisy_summaries` được bổ sung sau khi phát hiện một **blind spot**: hai corruption `truncate_title` và `inject_summary_noise` không làm thay đổi bất kỳ tín hiệu nào của bộ check ban đầu (title vẫn non-null, summary vẫn dài), nhưng vẫn làm giảm chất lượng retrieval. Nếu một sự cố thật chỉ gồm hai dạng này, `all_passed` sẽ vẫn là `true` trong khi agent đã trả lời sai - đúng kiểu lỗi âm thầm mà data observability phải chặn.

Ngưỡng được hiệu chỉnh trên chính corpus thật, không chọn tùy ý:

| Signal | Ngưỡng | Baseline thực đo | Corrupted thực đo |
| --- | --- | --- | --- |
| Title truncation | `< 30` ký tự hoặc kết thúc bằng `...` | ngắn nhất 92 ký tự | 14 ký tự |
| Summary noise | 1 cụm 3 từ lặp `> 4` lần | tối đa 3 lần | 22 lần |

`failed_row_samples` trong mỗi quality report ghi lại `paper_id` cụ thể bị bắt lỗi, và các ID này **khớp chính xác** với `data/results/corruption_log.json`:

| Signal | paper_id bị bắt | Sự kiện tương ứng trong corruption log |
| --- | --- | --- |
| duplicate_paper_ids | `10-20944-preprints202602-0996-v1` | `duplicate_row` |
| empty_summaries | `10-3390-buildings16132637` | `blank_summary` |
| truncated_titles | `10-1111-exsy-70341` | `truncate_title` |
| noisy_summaries | `10-21079-11681-50309` | `inject_summary_noise` |
| stale_rows | `10-63646-kpqm1958` | `make_publication_stale` |

## 9. Corruption scenarios và repair

Corruption là **deterministic** (không dùng random seed ngẫu nhiên) nên chạy lại cho ra đúng cùng một tập lỗi - điều kiện bắt buộc để so sánh ba trạng thái là công bằng.

| Corruption | Cách tạo | Số row | Quality signal bắt được | Cách repair |
| --- | --- | ---: | --- | --- |
| `drop_latest_records` | Xóa 4 record có `published` mới nhất | 4 | `total_rows` 24->21, freshness `latest_published` lùi lại | Rebuild từ raw snapshot |
| `blank_summary` | Đặt `summary = ""` | 1 | `empty_summaries` = 1 | Rebuild từ raw snapshot |
| `inject_summary_noise` | Chèn cụm `CORRUPTED_NOISE ...` lặp 12 lần hai đầu | 1 | `noisy_summaries` = 1 *(check mới)* | Rebuild từ raw snapshot |
| `truncate_title` | Cắt title còn 12 ký tự + `...` | 1 | `truncated_titles` = 1 *(check mới)* | Rebuild từ raw snapshot |
| `make_publication_stale` | Lùi `published` 3650 ngày | 1 | `stale_rows` = 1, `is_fresh` = false | Rebuild từ raw snapshot |
| `duplicate_row` | Nhân bản 1 row | 1 | `duplicate_paper_ids` = 1 | Rebuild từ raw snapshot |

Corruption log:
- Đường dẫn: `data/results/corruption_log.json`
- Nội dung: `input_rows`, `output_rows` và 6 event, mỗi event có `corruption_type`, `affected_paper_ids`, `affected_rows` cùng tham số before/after.
- Đã đối chiếu: `input_rows = 24` khớp số row baseline thật, `output_rows = 21` khớp số row corrupted thật.

Repair không sửa tay dữ liệu corrupted. `corruption_flow.py` nạp lại `data/raw/crossref_records.json` rồi chạy lại `build_clean_dataframe`, tức là đi lại đúng đường ETL của baseline từ snapshot thô đã lưu.

## 10. So sánh baseline, corrupted và repaired

Cả ba trạng thái được chấm trên **cùng một** test set đóng băng (`data/eval/test_set.json`, 40 câu), cùng `top_k = 4`, cùng embedding model và cùng LLM judge.

| Metric/signal | Baseline | Corrupted | Δ corrupted | Repaired | Δ repaired | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.000 | 0.600 | -0.400 | 1.000 | 0.000 | Mất 4 record mới nhất + duplicate làm top-4 không còn chứa ground-truth doc |
| mean_token_f1 | 1.000 | 0.663 | -0.337 | 1.000 | 0.000 | Summary rỗng/nhiễu làm đáp án trích ra sai |
| judge_accuracy | 0.900 | 0.600 | -0.300 | 0.925 | +0.025 | LLM judge xác nhận nội dung câu trả lời kém đi |
| mean_judge_score | 4.600 | 3.425 | -1.175 | 4.700 | +0.100 | Điểm trung bình giảm hơn 1 bậc rồi hồi phục |
| Quality checks | PASS | FAIL | - | PASS | - | 6/8 signal đổi trạng thái |
| Freshness status | FRESH | STALE | - | FRESH | - | 1 stale row, latest_published lùi 2026-08-05 -> 2026-07-02 |

Chuỗi nhân quả được chứng minh bằng artifact:

1. **Corruption -> quality signal.** 6 sự kiện trong `corruption_log.json` làm 5 quality signal đổi trạng thái, với `paper_id` khớp 1-1 (bảng ở mục 8). Freshness bắt được `latest_published` lùi lại vì 4 record mới nhất bị xóa.
2. **Quality signal -> answer impact.** Cùng lúc đó retrieval_hit_rate giảm 0.400 và judge_accuracy giảm 0.300 trên cùng test set. Tách nguyên nhân từ `corrupted_answers.json` cho thấy quan hệ **1-1**, không phải suy đoán:

   | Nguồn suy giảm | Bằng chứng định lượng |
   | --- | --- |
   | `drop_latest_records` (4 paper) | Đúng **16/16** câu retrieval miss là các câu có ground-truth doc nằm trong 4 paper bị xóa (4 paper × 4 question_type = 16 câu). **0** câu miss do nguyên nhân khác. Đây chính là mức giảm 0.400 của hit rate |
   | `blank_summary` | Paper `10-3390-buildings16132637`: retrieval vẫn **trúng** nhưng token F1 = **0.000** vì summary rỗng nên không trích được đáp án |
   | `make_publication_stale` | Paper `10-63646-kpqm1958`: retrieval trúng, token F1 = **0.000** vì ngày trả về là ngày đã bị lùi |
   | `inject_summary_noise` | Paper `10-21079-11681-50309`: retrieval trúng, token F1 giảm nhẹ còn **0.972** do nhiễu chen vào câu đầu |
   | `truncate_title`, `duplicate_row` | **Không** làm sai câu trả lời nào trong test set này, nhưng vẫn bị quality check bắt được |

   Nhóm 24 câu retrieval trúng có token F1 trung bình 0.916, nhóm 16 câu miss chỉ 0.284 - cho thấy phần lớn mức giảm F1 đến từ retrieval miss, phần còn lại đến từ 3 paper bị hỏng nội dung ở trên.

   Điểm đáng giá về mặt observability: hai corruption cuối (`truncate_title`, `duplicate_row`) **chưa** gây hại đo được trên test set này nhưng đã bị tín hiệu quality bắt. Tức là quality check cảnh báo *sớm hơn* thời điểm người dùng thấy câu trả lời sai - đúng mục đích của data observability.
3. **Repair -> recovery.** Repair chạy lại `build_clean_dataframe` từ `data/raw/crossref_records.json` (không sửa tay corrupted data). Hai metric deterministic (`retrieval_hit_rate`, `mean_token_f1`) quay về **đúng** baseline (Δ = 0.000) và mọi quality signal về 0. Hai metric do LLM judge chấm lệch nhẹ **theo hướng tốt hơn** (+0.025 và +0.100): dữ liệu repaired được dựng lại từ cùng một raw snapshot nên nội dung giống hệt baseline, phần lệch này là **variance của LLM judge**, không phải dữ liệu chưa phục hồi. Nhóm giữ nguyên con số thay vì làm tròn thành "hồi phục 100%" để không overclaim.

Giới hạn của kết luận (nêu rõ để không overclaim):

- `mean_token_f1` không phải thước đo sinh ngữ; `qa.py` là extractive nên baseline luôn đạt 1.000 (xem mục 7).
- Repair phục hồi đúng baseline một phần vì nguồn raw snapshot không đổi giữa hai lần chạy; đây là điều kiện lý tưởng, sự cố thật có thể mất cả raw.
- Không phải 100% sample được LLM judge chấm: lần chạy cuối có 2/40 sample ở baseline và 1/40 ở corrupted/repaired rơi vào fallback heuristic do lỗi LLM tạm thời. `script/verify_artifacts.py` in rõ tỉ lệ này mỗi lần chạy (`judged by the real LLM`) để không nhầm là judge thật toàn bộ.

## 11. Vấn đề tích hợp quan trọng

Một vấn đề quan trọng là khi ghép các module, các artifact phải dùng đúng contract và path. Nếu report hoặc metrics không đồng bộ, kết luận sẽ bị sai. Nhóm đã xử lý bằng cách dùng chung config path, dùng cùng test set cho ba trạng thái và lưu artifact riêng cho baseline/corrupted/repaired.

Ở bước tích hợp cuối, nhóm chạy một script đối chiếu (`script/verify_artifacts.py`) recompute lại toàn bộ signal/metric từ dữ liệu thật rồi so với JSON/markdown đã ghi. Script này phát hiện và nhóm đã sửa 4 vấn đề thật:

| # | Vấn đề phát hiện | Bằng chứng | Cách xử lý |
| --: | --- | --- | --- |
| 1 | LLM judge **chưa từng chạy**: cả 120 lượt chấm ở 3 trạng thái đều là fallback heuristic | `judge.reasoning` = "Fallback heuristic judge used..." ở 120/120 sample | `.env` để `LLM_PROVIDER=gemini` nhưng `GOOGLE_API_KEY` rỗng (key thực tế là OpenRouter). Đổi sang `openrouter` + `google/gemini-2.5-flash`, xác minh judge thật phân biệt đúng/sai rồi chạy lại |
| 2 | 3 file `*_freshness.json` không sinh từ pipeline và **không khớp dữ liệu** | `baseline_freshness.json` ghi `latest_published: 2026-12-01` trong khi ngày lớn nhất trong dataset là `2026-08-05`; `corrupted_freshness.json` ghi `22 rows / 0 stale / is_fresh: true` trong khi dữ liệu thật là `21 rows / 1 stale / not fresh` `config.py` đã khai báo sẵn 3 field `baseline/corrupted/repaired_freshness_report` nhưng **không module nào dùng**, còn `corruption_flow.py` thì truyền `report_path=None` nên không ghi file. Nối 3 field này vào `phase1.py`/`corruption_flow.py` để cả 3 file đều do pipeline sinh ra từ dữ liệu thật |
| 3 | Blind spot: 2/6 corruption không tạo bất kỳ tín hiệu quality nào | `truncate_title` và `inject_summary_noise` không đổi signal nào của bộ check cũ | Thêm 2 check `truncated_titles`, `noisy_summaries` với ngưỡng hiệu chỉnh trên corpus thật |
| 4 | `group_report.md` ghi số liệu không khớp artifact | Report ghi `retrieval_hit_rate 0.167`, `mean_token_f1 0.559`, `6 câu hỏi` trong khi artifact thật là `0.600`, `1.000`, `40 câu` | Cập nhật toàn bộ số liệu theo artifact thật sau lần chạy cuối |

Vấn đề 1 và 2 đáng chú ý nhất vì cả hai đều thuộc dạng "pipeline chạy xong không báo lỗi nhưng kết luận sai": fallback judge vẫn trả điểm đẹp (1.000/5.00) và file freshness giả vẫn nói `is_fresh: true` cho tập dữ liệu thực tế đã stale.

## 12. Kết luận cuối cùng

Nhóm đã hoàn thành được luồng end-to-end từ ingestion tới observability và corruption/repair. Các số liệu đã được lưu bằng artifact thật và đủ để làm bằng chứng cho việc so sánh baseline, corrupted và repaired trong bài lab này.
