# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | Group 4 |
| Repository | F:\K4_Day10_C3.2_E403 |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | [Tên thành viên 1] | [MSSV] | Source owner | src/ingestion/crossref.py |
| 2 | [Tên thành viên 2] | [MSSV] | Data model & evaluation-set owner | src/ingestion/cleaning.py, src/evaluation/testset.py |
| 3 | [Tên thành viên 3] | [MSSV] | Observability owner | src/observability/quality.py, src/observability/reporting.py |
| 4 | [Tên thành viên 4] | [MSSV] | Corruption & integration owner | src/ingestion/corruption.py, src/pipelines/phase1.py, src/pipelines/corruption_flow.py |

## 2. Tóm tắt kết quả

Nhóm đã triển khai toàn bộ luồng dữ liệu từ ingestion, cleaning, embedding, evaluation, observability đến corruption và repair. Baseline pipeline tạo ra đầy đủ artifact raw/clean/embedding/evaluation/results/report. Corruption làm giảm rõ rệt các chỉ số retrieval và judging, đặc biệt retrieval hit rate giảm từ 1.000 xuống 0.167. Repair từ dữ liệu nguồn giúp khôi phục lại baseline ở hầu hết các metric. Blocker chính là đảm bảo các artifact và báo cáo luôn khớp với nhau khi chạy lại pipeline.

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
| Ingestion | Crossref query/filter | Fetch, retry, parse, lưu raw | data/raw/ | Member 1 |
| Cleaning | Raw records | Normalize, deduplicate, build text_for_embedding | data/clean/ | Member 2 |
| Embedding/index | Cleaned dataframe | Build MiniLM embeddings + Chroma | data/embeddings/ | Member 2/4 |
| Evaluation | Cleaned data + test set | Run retrieval/answer evaluation | data/results/ | Member 2/4 |
| Observability | Cleaned/corrupted/repaired data | Quality/freshness checks + report | data/quality/, data/reports/ | Member 3 |
| Corruption/repair | Baseline clean dataframe | Corrupt and repair from raw source | data/results/corruption_log.json | Member 4 |
| Orchestration | Pipeline config | Run baseline and corruption flow | Reports + metrics | Member 4 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| LLM_PROVIDER | gemini |
| LLM_MODEL | gemini-2.5-flash |
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

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công | 2026-08-06 | data/results/baseline_metrics.json, data/reports/phase1_report.md |
| Corruption flow | Thành công | 2026-08-06 | data/results/corrupted_metrics.json, data/results/repaired_metrics.json, data/reports/corruption_report.md |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API |
| Query/filter | agentic retrieval augmented generation large language model + from-pub-date threshold |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Có retry cho 429/503 và fallback dữ liệu mẫu khi offline |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại record thiếu title/summary | Completeness | 0 | Clean dataframe có các row hợp lệ |
| Normalize authors/categories | Validity | 24 | data/clean/papers_clean.json |
| Tạo text_for_embedding | Relevance | 24 | data/embeddings/papers_embeddings.json |
| Tính age_days | Freshness | 24 | data/quality/baseline_freshness.json |

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 6 |
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

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| retrieval_hit_rate | 1.000 | Baseline retrieval đúng trên toàn bộ sample test |
| mean_token_f1 | 0.559 | Đáp án gần đúng và phù hợp với ground truth |
| judge_accuracy | 0.500 | Judge cho thấy nửa số sample đạt độ chính xác tương đối |
| mean_judge_score | 3.000 | Độ tin cậy câu trả lời ở mức trung bình |

## 8. Data quality và freshness

| Check | Kết quả baseline | Bằng chứng |
| --- | --- | --- |
| Row count | 24 | data/quality/baseline_quality.json |
| Duplicate paper IDs | 0 | data/quality/baseline_quality.json |
| Missing summaries | 0 | data/quality/baseline_quality.json |
| Freshness status | FRESH | data/quality/baseline_freshness.json |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | --- | --- | --- |
| Drop latest rows | Loại một số dòng đầu tiên | Giảm coverage | Retrieval hit rate giảm | Rebuild từ raw/clean baseline |
| Blank summary/noise | Đặt summary rỗng và thêm noise | Giảm relevance | Quality fail | Reclean từ source |
| Truncate title/date staleness | Cắt title và làm ngày cũ | Giảm freshness/quality | Quality fail | Rebuild từ source |
| Duplicate rows | Thêm bản sao | Giảm uniqueness | Quality fail | Rebuild từ source |

Corruption log:
- Đường dẫn: data/results/corruption_log.json
- Trạng thái: Có
- Nhận xét: Log ghi đủ các thao tác corruption và số lượng record bị tác động.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.000 | 0.167 | 1.000 | Corruption làm giảm mạnh, repair phục hồi đầy đủ |
| mean_token_f1 | 0.559 | 0.204 | 0.559 | Corruption làm câu trả lời kém khớp, repair phục hồi |
| judge_accuracy | 0.500 | 0.167 | 0.500 | Tương tự như trên |
| mean_judge_score | 3.000 | 1.667 | 3.000 | Repair khôi phục mức đánh giá |
| Quality checks pass/fail | PASS | FAIL | PASS | Corruption làm data quality fail |
| Freshness status | FRESH | FRESH/unknown | FRESH | Repair không làm freshness xấu hơn |

Hai kết luận có quan hệ nhân quả:
1. Corruption làm summary bị trống/tiếng ồn và mất một số rows, dẫn đến quality fail và giảm retrieval hit rate.
2. Repair từ raw source khôi phục lại clean data và làm metrics quay về baseline.

## 11. Vấn đề tích hợp quan trọng

Một vấn đề quan trọng là khi ghép các module, các artifact phải dùng đúng contract và path. Nếu report hoặc metrics không đồng bộ, kết luận sẽ bị sai. Nhóm đã xử lý bằng cách dùng chung config path, dùng cùng test set cho ba trạng thái và lưu artifact riêng cho baseline/corrupted/repaired.

## 12. Kết luận cuối cùng

Nhóm đã hoàn thành được luồng end-to-end từ ingestion tới observability và corruption/repair. Các số liệu đã được lưu bằng artifact thật và đủ để làm bằng chứng cho việc so sánh baseline, corrupted và repaired trong bài lab này.
