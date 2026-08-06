# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Lương Đức Thắng |
| MSSV | [MSSV] |
| Khóa/Lớp | K4 |
| Tên nhóm | Group 4 |
| Vai trò chính | Role 5: Bonus (CLI, Advanced Visualization & Validation) |
| Repository | F:\K4_Day10_C3.2_E403 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Command Line Interface (CLI) | script/cli.py | Tham số dòng lệnh (phase1, corruption, all) | Chạy tự động các pipeline tương ứng | Hoàn thành |
| Advanced Visualization | script/generate_bonus_report.py | Các file JSON metrics (baseline, corrupted, repaired) | Báo cáo Markdown chứa biểu đồ Mermaid (final_bonus_report.md) | Hoàn thành |
| Extra Validation Tests | tests/test_bonus.py | Metrics của 3 trạng thái | Assertions pass/fail tự động trên pytest | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Refactor & Orchestration | Hỗ trợ Role 4 nối các luồng | Script CLI giúp chạy end-to-end toàn bộ flow chỉ bằng 1 lệnh |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng CLI tool | script/cli.py | Công cụ chạy script tự động | Chạy `uv run python script/cli.py --help` |
| Báo cáo trực quan nâng cao | script/generate_bonus_report.py, data/reports/final_bonus_report.md | Biểu đồ cột (Mermaid bar chart) so sánh metrics | Mở file `final_bonus_report.md` trên GitHub hoặc trình duyệt Markdown |
| Viết test kiểm tra metric | tests/test_bonus.py | Các test case pass thành công | Chạy `uv run pytest tests/test_bonus.py` |

Một output cụ thể mà phần việc của tôi tạo ra là bảng báo cáo so sánh trực quan (với biểu đồ) giúp người đọc dễ dàng thấy được sự sụt giảm của hệ thống khi dữ liệu lỗi và khả năng phục hồi của hệ thống.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Để đạt điểm Bonus (90-100), bài lab yêu cầu hệ thống phải dễ dàng reproduce (reproducibility) thông qua CLI, cũng như báo cáo phải thật sự trực quan, phân tích sâu sự thay đổi metrics. Ngoài ra, việc kiểm thử tự động (automation test) cho sự sụt giảm/phục hồi của metrics giúp đảm bảo pipeline chạy đúng yêu cầu nghiệp vụ.

### Cách triển khai

- **CLI (`cli.py`)**: Tôi sử dụng thư viện `argparse` có sẵn của Python để tạo ra các sub-commands, giúp người dùng không cần nhớ nhiều file script mà chỉ cần chạy 1 entrypoint duy nhất.
- **Visualization (`generate_bonus_report.py`)**: Thay vì dùng matplotlib sinh ảnh tĩnh khó nhúng vào markdown, tôi parse các file JSON và sinh ra mã **Mermaid** trực tiếp vào `final_bonus_report.md`. Điều này đảm bảo biểu đồ render native trên GitHub và rất đẹp.
- **Extra Validation (`test_bonus.py`)**: Tôi dùng pytest viết các test case đơn giản nhưng chặt chẽ: `corrupted_metrics < baseline_metrics` và `repaired_metrics >= corrupted_metrics`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | JSON metrics files (baseline, corrupted, repaired) |
| Output | final_bonus_report.md (chứa biểu đồ), console output của pytest |
| Module phụ thuộc | Các pipeline (phase1, corruption) phải chạy thành công trước khi sinh report |
| Điều kiện lỗi cần xử lý | Xử lý file not found nếu chạy sinh report trước khi chạy pipeline |

### Cách xác minh

```bash
uv run python script/cli.py all
uv run pytest tests/test_bonus.py
```

- Kết quả mong đợi: Toàn bộ pipeline chạy mượt mà không lỗi, test pass 100%, file report có biểu đồ xuất hiện.

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: Vẽ biểu đồ báo cáo cho hệ thống.
- Các phương án đã cân nhắc: Dùng `matplotlib` lưu thành `.png` hoặc sinh `Mermaid` text.
- Phương án đã chọn: Sinh mã `Mermaid` nhúng vào Markdown.
- Lý do: Code nhẹ hơn (không cần cài thêm dependency nặng như matplotlib), render động trên GitHub, dễ dàng thay đổi format, không cần quản lý file ảnh dư thừa.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng/lỗi nguyên văn: Báo lỗi "File not found" khi `generate_bonus_report.py` chạy.
- Lệnh hoặc bước tái hiện: Chạy sinh báo cáo trước khi chạy phase 1 và corruption.
- Nguyên nhân gốc: Metrics JSON chưa được sinh ra do thiếu dữ liệu.
- Cách xử lý: Thêm bước check `os.path.exists` và cảnh báo người dùng chạy pipeline trước, hoặc tích hợp luôn vào lệnh `all` của CLI để đảm bảo thứ tự.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của tôi:

1. Hệ thống lấy dữ liệu thô (raw) từ Crossref, làm sạch (clean) và chuyển đổi thành embedding lưu vào vector database (ChromaDB).
2. Chúng ta dùng bộ test set chuẩn để lấy metric ban đầu (Baseline) về độ phủ (recall/hit rate) và độ chính xác (F1, Judge).
3. Sau đó, ta cố tình tiêm lỗi (Corruption) vào dữ liệu, đẩy lại vào DB và chạy lại test set. Lúc này, pipeline của Role 5 sẽ bắt được sự sụt giảm metric qua test case tự động.
4. Cuối cùng, dữ liệu được sửa (Repair) từ nguồn gốc, và chạy lại. Biểu đồ của Role 5 minh họa trực quan sự phục hồi này.

## 8. Phân tích kết quả

Phần này trùng khớp với số liệu chung của nhóm, nhưng thông qua Role 5, các số liệu này được visualize trực quan hơn:
- `retrieval_hit_rate` sụt giảm thẳng đứng (từ 1.0 -> 0.167) cho thấy lỗi metadata (title/summary) phá hủy hoàn toàn khả năng tìm kiếm.
- `mean_token_f1` giảm 1 nửa, cho thấy LLM bị "ảo giác" do thiếu ngữ cảnh.
- Test tự động `test_bonus.py` đã assert thành công mô hình "Bình thường -> Xấu đi -> Phục hồi", chứng minh pipeline hoạt động hoàn hảo.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Reproducibility (khả năng tái hiện) là cực kỳ quan trọng; CLI giúp mọi người trong team chạy lại code của nhau mà không bị rối.
2. Markdown + Mermaid là công cụ vô cùng mạnh mẽ để tạo Data Report trực tiếp mà không cần Notebook.
3. Việc assert các metrics trong Pytest giúp ngăn chặn các lỗi logic bị ẩn giấu trong quá trình phát triển (ví dụ: vô tình sửa sai hàm cleaning làm metric sụt giảm).

### Nếu có thêm thời gian

Tôi sẽ làm cho CLI phong phú hơn (cho phép truyền parameter như số lượng bài báo, threshold từ command line thay vì hardcode) và thêm CI/CD GitHub Action tự động sinh report mỗi khi push code.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lương Đức Thắng
**Ngày xác nhận:** 2026-08-06
