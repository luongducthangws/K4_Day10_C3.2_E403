# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | [Lương Trí Tuệ] |
| MSSV | [2A201601919] |
| Khóa/Lớp | K4 |
| Tên nhóm | Group 4 |
| Vai trò chính | Role 4: Corruption, repair, evaluation integration |
| Repository | F:\K4_Day10_C3.2_E403 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Corruption simulation | src/ingestion/corruption.py | Cleaned dataframe và config | Corrupted dataframe + corruption log | Hoàn thành |
| Repair workflow | src/pipelines/corruption_flow.py | Corrupted data và raw baseline | Repaired dataframe + compared metrics | Hoàn thành |
| Evaluation integration | src/pipelines/phase1.py, src/pipelines/corruption_flow.py | Baseline/corrupted/repaired data | Metrics JSON và report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Debug tích hợp pipeline | src/observability/reporting.py | Tạo report so sánh baseline/corrupted/repaired |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tạo corruption scenarios | src/ingestion/corruption.py | Corrupted data + log | Chạy script/run_corruption_flow.py |
| Tạo repair/compare flow | src/pipelines/corruption_flow.py | Repaired metrics + comparison report | Chạy script/run_corruption_flow.py |
| Tạo report và metrics | src/observability/reporting.py, data/results/*.json | Baseline/corrupted/repaired reports | Kiểm tra file dưới data/reports và data/results |

Một output cụ thể mà phần việc của tôi tạo ra là báo cáo so sánh hiệu quả của corruption và repair, cùng các metrics JSON để minh chứng cho từng trạng thái.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Role 4 cần chứng minh rằng dữ liệu bị làm sai sẽ ảnh hưởng đến chất lượng retrieval và answer generation, đồng thời kiểm tra xem repair có giúp khôi phục hệ thống hay không. Đây là phần khác với việc chỉ tạo clean dataset hoặc report riêng lẻ.

### Cách triển khai

Tôi triển khai một pipeline có ba trạng thái: baseline, corrupted và repaired. Baseline dùng dữ liệu sạch để tạo embedding và đánh giá. Corrupted tạo các tình huống làm sai dữ liệu như drop rows, blank summaries, noise, truncate title và duplicate rows. Repair sau đó khôi phục lại dữ liệu từ nguồn dữ liệu gốc/clean baseline để tạo lại index và đánh giá lại. Quy trình này được nối vào report và metrics để dễ đối chiếu.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Cleaned dataframe, raw records, config path, test set |
| Output | Corrupted dataframe, repaired dataframe, metrics JSON, markdown report |
| Module phụ thuộc | src/ingestion/cleaning.py, src/evaluation/testset.py, src/observability/quality.py |
| Module sử dụng output | src/pipelines/phase1.py, src/pipelines/corruption_flow.py, src/observability/reporting.py |
| Điều kiện lỗi cần xử lý | Missing artifact, failed embedding build, mismatch path giữa các trạng thái |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- Kết quả mong đợi: tạo được corrupted/repaired metrics và comparison report.
- Kết quả thực tế: script chạy thành công và tạo artifact trong data/results và data/reports.
- Artifact/log: data/results/corrupted_metrics.json, data/results/repaired_metrics.json, data/reports/corruption_report.md.

## 5. Một quyết định kỹ thuật quan trọng

- Bối cảnh: Cần có một cách đánh giá corruption và repair mà không phụ thuộc vào từng module riêng lẻ.
- Các phương án đã cân nhắc: chỉ ghi log terminal, hoặc tạo artifact chuẩn cho baseline/corrupted/repaired.
- Phương án đã chọn: dùng một pipeline chung và lưu metrics/report riêng cho từng trạng thái.
- Lý do: cách này tăng tính reproducibility, dễ so sánh và phù hợp với mục tiêu observability của lab.
- Bằng chứng quyết định phù hợp: baseline/corrupted/repaired đều có file metrics và report riêng.

## 6. Một lỗi hoặc blocker đã xử lý

- Triệu chứng/lỗi nguyên văn: pipeline bị lỗi hoặc report không đồng bộ vì các artifact được tạo ở các path khác nhau.
- Lệnh hoặc bước tái hiện: chạy baseline rồi corruption flow liên tiếp.
- Nguyên nhân gốc: path config chưa thống nhất và một số output chưa được lưu đúng tên/state.
- Cách xử lý: thống nhất config path và lưu output theo từng trạng thái rõ ràng.
- Cách xác minh sau khi sửa: chạy lại pipeline và kiểm tra các file JSON/markdown được tạo đúng.
- Điều học được: observability chỉ hiệu quả khi output định hình tốt từ đầu.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của tôi:

1. Dữ liệu đi từ Crossref đến vector index qua ba bước: fetch raw records, clean thành structured dataframe, rồi tạo text_for_embedding và index cho retrieval.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality bằng cách so sánh retrieved docs và câu trả lời với câu hỏi/ground truth.
3. Quality checks đo tính đầy đủ và hợp lệ của dữ liệu, còn freshness monitoring đo mức mới cũ của bản ghi; cả hai phục vụ cho việc phát hiện dữ liệu có đang bị suy giảm hay không.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để đảm bảo so sánh là fair và không bị lệch bởi câu hỏi khác nhau.
5. Repair được xem là thành công nếu metric và report sau repair quay trở về mức gần baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| retrieval_hit_rate | 1.000 | 0.167 | 1.000 | Corruption làm giảm đáng kể, repair khôi phục đầy đủ |
| mean_token_f1 | 0.559 | 0.204 | 0.559 | Câu trả lời bị sai rõ sau corruption và phục hồi sau repair |
| judge_accuracy | 0.500 | 0.167 | 0.500 | Đánh giá của judge cũng giảm mạnh rồi hồi về |
| mean_judge_score | 3.000 | 1.667 | 3.000 | Chất lượng câu trả lời được khôi phục |
| Quality checks | PASS | FAIL | PASS | Dữ liệu bị hỏng thì quality check fail |
| Freshness status | FRESH | FRESH/unknown | FRESH | Repair không làm freshness xấu hơn |

### Kết luận từ số liệu

1. Corruption làm dữ liệu mất tính đầy đủ và bị nhiễu, dẫn tới quality checks fail và retrieval/answer quality giảm mạnh.
2. Repair từ raw source khôi phục lại dữ liệu và làm các metric quay về gần baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao? Corruption làm mất/đánh sai mô tả và title của tài liệu đang được dùng làm ground truth, nên retrieval và answer quality giảm rõ nhất.

Kết quả nào khác với kỳ vọng ban đầu? Không có kết quả quá khác biệt; phần đáng chú ý là repair thực sự phục hồi được hệ thống khá đầy đủ, cho thấy pipeline có đủ sức chống chịu với một mức độ corruption vừa phải.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Dữ liệu tốt là nền tảng cho RAG; một chút corruption có thể làm chất lượng hệ thống giảm mạnh.
2. Observability không chỉ là ghi log, mà là tạo artifact và report đủ để người đọc hiểu nguyên nhân và hậu quả.
3. Metrics và report cần được thiết kế từ đầu, nếu không kết luận về hệ thống sẽ rất dễ bị sai lệch.

### Nếu có thêm thời gian

Có thể thêm unit tests cho corruption và repair flow, cùng metadata về thời gian chạy và environment, để báo cáo trở nên dễ audit và bảo trì hơn.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Lương Trí Tuệ]
**Ngày xác nhận:** 2026-08-06
