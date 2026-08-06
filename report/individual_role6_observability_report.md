# Member Role Report — Day 10: Data Pipeline & Data Observability

> Đổi tên file thành `<MSSV>_HoTen.md` theo quy ước ở `report/README.md` mục 1 trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hà Bách |
| MSSV | 2A202601592 |
| Khóa/Lớp | K4 |
| Tên nhóm | Group 4 |
| Vai trò chính | Role 6: Observability owner (quality, freshness, reports) |
| Repository | K4_Day10_C3.2_E403 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data quality checks | `src/observability/quality.py::run_data_quality_checks` | Cleaned dataframe (baseline/corrupted/repaired) + `Settings` | `data/quality/{baseline,corrupted,repaired}_quality.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py::build_freshness_report` | Cùng dataframe, cột `published`/`age_days` | `freshness_report.json`, `{baseline,corrupted,repaired}_freshness.json` | Hoàn thành |
| Baseline report | `src/observability/reporting.py::generate_phase1_report` | source summary + metrics + quality + freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Comparison report | `src/observability/reporting.py::generate_corruption_report` | metrics/quality/freshness của 3 trạng thái | `data/reports/corruption_report.md` | Hoàn thành |
| Artifact verification | `script/verify_artifacts.py` | Toàn bộ artifact trong `data/` | Console report + exit code | Hoàn thành (bổ sung ngoài scope gốc) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Sửa cấu hình provider `.env` | Toàn nhóm | Phát hiện LLM judge chưa bao giờ chạy thật; sửa provider và chạy lại để có metric thật |
| Nối `corrupted/repaired_freshness_report` vào pipeline | Role 4 (config) + Role 1 (orchestration) | 3 field path đã khai báo trong `config.py` nhưng chưa module nào dùng; nay được pipeline ghi thật |
| Sửa test dựng `Paths` bị thiếu field | Role 2 (`tests/test_crossref.py`) | Test suite từ trạng thái không collect được -> 6 passed |
| Thêm `conftest.py` | Toàn nhóm | `pytest` chạy được mà không cần `pip install -e .` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | Artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Bộ quality check 2 tầng | `data/quality/*_quality.json` | 8 signal, tách blocking vs content-integrity | `python script/verify_artifacts.py` |
| Freshness cho cả 3 trạng thái | `data/quality/*_freshness.json` | latest/oldest published, stale_rows, stale_ratio, is_fresh | So với `data/clean/*.csv` |
| Hai report markdown | `data/reports/*.md` | Bảng delta + mục liên kết signal -> impact | Mở file, đối chiếu với JSON |
| Script đối chiếu | `script/verify_artifacts.py` | Exit 0 = mọi report khớp artifact | Chạy lệnh, xem exit code |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Data observability chỉ có giá trị nếu nó **bắt được lỗi trước khi người dùng nhận câu trả lời sai**. Vì vậy phần việc của tôi không dừng ở "sinh ra file JSON", mà phải trả lời được: mỗi dạng corruption có tạo ra tín hiệu nào không, và tín hiệu đó có khớp với mức suy giảm của agent không.

### Phát hiện quan trọng nhất: blind spot của bộ check ban đầu

Khi đối chiếu `corruption_log.json` với quality report, tôi thấy 6 dạng corruption nhưng chỉ 4 dạng tạo ra tín hiệu. Hai dạng **hoàn toàn vô hình**:

- `truncate_title`: title bị cắt còn 12 ký tự nhưng vẫn non-null -> `null_titles` = 0.
- `inject_summary_noise`: summary bị chèn nhiễu nhưng còn dài hơn cũ -> `empty_summaries` = 0.

Hệ quả: nếu một sự cố thật chỉ gồm hai dạng này thì `all_passed` vẫn `true` trong khi retrieval đã kém đi — đúng kiểu lỗi âm thầm mà bài lab muốn chặn.

Tôi bổ sung 2 check, và **hiệu chỉnh ngưỡng bằng số đo trên chính corpus thật** thay vì chọn số tùy ý:

| Signal | Cách đo | Baseline thực đo | Corrupted thực đo | Ngưỡng chọn |
| --- | --- | --- | --- | --- |
| `truncated_titles` | độ dài title, hậu tố `...` | ngắn nhất 92 ký tự | 14 ký tự | `< 30` ký tự |
| `noisy_summaries` | số lần lặp tối đa của một cụm 3 từ | tối đa 3 lần | 22 lần | `> 4` lần |

Tôi đã thử `lexical diversity` trước nhưng **loại bỏ** vì không phân tách được (baseline 0.640 vs corrupted 0.614 — chồng lấn). Repeated-trigram tách rất sạch (3 vs 22).

### Vì sao không hard-code token `CORRUPTED_NOISE`

Check phải bắt được *lớp lỗi* (văn bản bị lặp/chèn boilerplate) chứ không phải đúng một chuỗi mà `corruption.py` sinh ra. Nếu hard-code, check sẽ vô dụng với dữ liệu lỗi thật.

### Bằng chứng check hoạt động đúng

`failed_row_samples` ghi `paper_id` bị bắt lỗi, và khớp **1-1** với `corruption_log.json`:

| Signal | paper_id bị bắt | Event trong corruption log |
| --- | --- | --- |
| `duplicate_paper_ids` | `10-20944-preprints202602-0996-v1` | `duplicate_row` |
| `empty_summaries` | `10-3390-buildings16132637` | `blank_summary` |
| `truncated_titles` | `10-1111-exsy-70341` | `truncate_title` |
| `noisy_summaries` | `10-21079-11681-50309` | `inject_summary_noise` |
| `stale_rows` | `10-63646-kpqm1958` | `make_publication_stale` |

Phép đối chiếu này được tự động hóa trong `script/verify_artifacts.py`.

### Giữ tương thích ngược

`run_data_quality_checks` vẫn trả nguyên các key cũ (`all_passed`, `total_rows`, `null_paper_ids`, `duplicate_paper_ids`, `null_titles`, `empty_summaries`, `stale_rows`) vì `phase1.py` đọc trực tiếp `quality_report['all_passed']`. Hai check mới đưa vào nhóm *warning* (`has_warnings`, `warning_count`) nên không làm đổi ngữ nghĩa `all_passed` của các module khác.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Cleaned dataframe với cột `paper_id`, `title`, `summary`, `summary_chars`, `published`, `age_days` |
| Output | Quality JSON, freshness JSON, 2 report markdown |
| Module phụ thuộc | `cleaning.py` (schema), `corruption.py` (log để đối chiếu), `metrics.py` (metric đưa vào report) |
| Điều kiện lỗi cần xử lý | Dataframe rỗng, thiếu cột, `report_path=None` |

## 5. Vấn đề đã phát hiện và xử lý

| # | Vấn đề | Bằng chứng | Xử lý |
| --: | --- | --- | --- |
| 1 | LLM judge chưa từng chạy: 120/120 lượt chấm là fallback heuristic | `judge.reasoning` = "Fallback heuristic judge used because the LLM evaluator was unavailable." | `.env` để `LLM_PROVIDER=gemini` nhưng `GOOGLE_API_KEY` rỗng; đổi sang `openrouter` + `google/gemini-2.5-flash`, xác minh judge phân biệt đúng/sai rồi chạy lại toàn bộ |
| 2 | 3 file `*_freshness.json` không sinh từ pipeline và không khớp dữ liệu | `baseline_freshness.json` ghi `latest_published: 2026-12-01` (ngày không tồn tại trong dataset, max thật là `2026-08-05`); `corrupted_freshness.json` ghi `22 rows / 0 stale / is_fresh: true` trong khi thật là `21 rows / 1 stale / not fresh` | `corruption_flow.py` truyền `report_path=None` nên không ghi file. Nối vào `settings.paths.*_freshness_report` để pipeline ghi thật |
| 3 | Blind spot 2/6 corruption không tạo tín hiệu | Đối chiếu corruption log vs quality report | Thêm `truncated_titles`, `noisy_summaries` |
| 4 | `group_report.md` ghi số không khớp artifact | Report ghi `0.167` / `0.559` / `6 câu hỏi`; artifact thật `0.600` / `1.000` / `40 câu` | Cập nhật theo artifact sau lần chạy cuối |
| 5 | Test suite không collect được | `ModuleNotFoundError: No module named 'core'`, rồi `Paths.__init__() missing 3 required positional arguments` | Thêm `conftest.py`; bổ sung 3 field còn thiếu trong test |
| 6 | Nguy cơ lộ secret | `.gitignore` chỉ có `.env`, không phủ `.env.*` | Thêm `.env.*` + `!.env.example`; xóa file backup tạm |

Vấn đề 1 và 2 nguy hiểm nhất vì cả hai đều thuộc dạng **pipeline chạy xong không báo lỗi nhưng kết luận sai**: fallback judge vẫn trả điểm đẹp `1.000/5.00`, và file freshness giả vẫn khẳng định `is_fresh: true` cho tập dữ liệu thực tế đã stale.

## 6. Mức độ hiểu luồng end-to-end

Dữ liệu đi: Crossref API -> `crossref.py` lưu raw response **trước khi parse** (để repair được mà không gọi lại API) -> `cleaning.py` chuẩn hóa và sinh `text_for_embedding` + `age_days` -> `index.py` embed bằng MiniLM vào 3 collection Chroma tách biệt -> `qa.py` truy hồi top-4 và trích đáp án -> `metrics.py` chấm bằng token F1 + LLM judge -> phần của tôi đọc dataframe và metrics để sinh tín hiệu quality/freshness và report.

Vì sao `mean_token_f1` baseline = 1.000: `qa.py` là **extractive**, lấy thẳng `authors_joined` / `published` / `categories_joined` / câu đầu của `summary` từ metadata, mà test set cũng dùng đúng các trường đó làm ground truth. Nên token F1 thực chất chỉ đo "retrieval có lấy đúng document không". `judge_accuracy = 0.900` mới là tín hiệu chất lượng độc lập.

Corruption tác động (tách nguyên nhân từ `corrupted_answers.json`, không suy đoán):

- `drop_latest_records`: đúng **16/16** câu retrieval miss có ground-truth doc nằm trong 4 paper bị xóa (4 paper × 4 question_type), **0** câu miss do nguyên nhân khác -> giải thích trọn vẹn mức giảm hit rate 1.000 -> 0.600.
- `blank_summary` (`10-3390-buildings16132637`) và `make_publication_stale` (`10-63646-kpqm1958`): retrieval vẫn **trúng** nhưng token F1 = **0.000**, vì đáp án được trích ra từ trường đã bị hỏng.
- `inject_summary_noise` (`10-21079-11681-50309`): retrieval trúng, F1 chỉ giảm nhẹ còn 0.972.
- `truncate_title` và `duplicate_row`: **không** làm sai câu trả lời nào trong test set này, nhưng vẫn bị quality check bắt.

Chi tiết cuối là điểm tôi thấy có giá trị nhất về mặt observability: hai corruption đó chưa gây hại đo được nhưng đã có tín hiệu, tức là quality check cảnh báo *sớm hơn* thời điểm người dùng thấy câu trả lời sai. Ngược lại, nhóm 24 câu retrieval trúng có F1 trung bình 0.916 so với 0.284 ở nhóm 16 câu miss, nên phần lớn mức giảm F1 đến từ retrieval miss chứ không phải từ nội dung bị hỏng.

Repair: nạp lại `data/raw/crossref_records.json` rồi chạy lại `build_clean_dataframe` — đi lại đúng đường ETL của baseline, không sửa tay dữ liệu corrupted.

## 7. Phần chưa hoàn thiện / giới hạn

- Hai check mới dùng ngưỡng cố định (`30` ký tự, `4` lần lặp) hiệu chỉnh trên corpus 24 record của bài này. Với corpus khác (ví dụ ngành có tiêu đề rất ngắn) cần hiệu chỉnh lại; chưa làm ngưỡng tự thích ứng theo phân phối.
- `noisy_summaries` chỉ bắt nhiễu dạng **lặp cụm từ**. Nhiễu ngẫu nhiên không lặp (ví dụ chèn ký tự rác không trùng nhau) vẫn lọt.
- Great Expectations có trong dependency và `config.py` có `gx_dir`, nhưng nhóm chưa dùng; bộ check hiện viết bằng pandas thuần.
- 1-2/40 sample mỗi lần chạy rơi vào fallback judge do lỗi LLM tạm thời; `verify_artifacts.py` in rõ tỉ lệ `judged by the real LLM` để không nhầm là judge thật 100%.
- `repaired` cao hơn `baseline` ở 2 metric judge (+0.025, +0.100) do LLM judge không deterministic; đã ghi rõ trong report thay vì làm tròn thành "hồi phục hoàn toàn".
