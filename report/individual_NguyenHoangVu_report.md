# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| **Họ và tên** | **Nguyễn Hoàng Vũ** |
| **MSSV** | [Điền MSSV của bạn vào đây] |
| **Khóa/Lớp** | K4 |
| **Tên nhóm** | Group 4 |
| **Vai trò chính** | **Vai trò 1: Integrator & Release Manager (Orchestration, QA, Provider & Demo)** |
| **Repository** | `d:\VinUni-AI20K\K4_Day10_C3.2_E403` |
| **Ngày hoàn thành** | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| **Pipeline Integration & Orchestration** | `src/pipelines/phase1.py`, `script/run_phase1.py` | Config từ `Settings`, dữ liệu raw từ Crossref | Clean CSV/JSON, ChromaDB index, metrics, quality/freshness JSON, `phase1_report.md` | Hoàn thành |
| **Corruption & Repair Flow** | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean dataframe, raw snapshot | Corrupted dataset, corrupted/repaired index & metrics, `corruption_report.md` | Hoàn thành |
| **Provider & Environment Setup** | `src/core/config.py`, `src/retrieval/llm.py`, `.env` | Env variables (`GROQ_API_KEY`, etc.) | Hỗ trợ Groq LLM Provider (`llama-3.3-70b-versatile`) & multi-provider fallback | Hoàn thành |
| **Interactive CLI Demo** | `script/demo_cli.py` | User console input | Interactive Q&A với RAG Agent, hiển thị báo cáo dữ liệu | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Standardizing Contracts | All Roles (Ingestion, Cleaning, Retrieval, Evaluation, Observability) | Thống nhất dữ liệu `PaperRecord`, `text_for_embedding`, `age_days` giúp dữ liệu luân chuyển không bị lệch schema |
| Error Handling & Fallbacks | Role 5 & Role 6 (Evaluation & Observability) | Thêm heuristic evaluation fallback (`_judge_answer`) phòng trường hợp thiếu API Key vẫn chạy được pipeline end-to-end |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tích hợp Groq Provider | `src/core/config.py`, `src/retrieval/llm.py`, `.env` | Cấu hình cho phép chạy LLM với Groq API (`llama-3.3-70b-versatile`) | Chạy thử test connection trong `llm.py` |
| Xây dựng Baseline Pipeline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Tự động chạy toàn bộ luồng Pha 1, xuất `baseline_metrics.json` và `phase1_report.md` | `uv run python script/run_phase1.py` |
| Xây dựng Corruption & Repair Pipeline | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Tự động giả lập 6 lỗi dữ liệu, đo độ sụt giảm, tự động khôi phục từ raw và xuất `corruption_report.md` | `uv run python script/run_corruption_flow.py` |
| Phát triển CLI Demo Tương tác | `script/demo_cli.py` | Công cụ CLI cho phép người dùng hỏi đáp trực tiếp với RAG Agent | `uv run python script/demo_cli.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Bài lab yêu cầu xây dựng một hệ thống Data Pipeline hoàn chỉnh cho RAG, phải đảm bảo tính gắn kết (integration), khả năng thực thi liên tục (end-to-end orchestration), tự động phát hiện dữ liệu lỗi (data quality audit) và tự động phục hồi dữ liệu (data recovery) mà không bị xung đột bộ nhớ hoặc ghi đè artifact.

### Cách triển khai của Tôi (Vai trò 1)
1. **Thiết lập Cấu hình & Multi-provider (Groq)**: Tôi đã mở rộng `Settings` trong `src/core/config.py` để hỗ trợ **Groq LLM Provider** thông qua giao diện OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`).
2. **Phase 1 Baseline Pipeline (`phase1.py`)**: Kết nối các module thành luồng khép kín:
   `Fetch Raw Data` -> `Clean Data` -> `ChromaDB Indexing` -> `Build QA Test Set` -> `Evaluate Hit Rate / F1 / LLM Judge` -> `Quality & Freshness Audit` -> `Generate Markdown Report`.
3. **Corruption & Repair Flow (`corruption_flow.py`)**: Giữ nguyên test set gốc để đảm bảo công bằng. Thực hiện 6 dạng corruption (xóa dòng mới nhất, rỗng summary, inject noise, cắt ngắn tiêu đề, ngày cũ, dòng trùng lặp), đánh giá mức sụt giảm của RAG, chạy Quality Check để phát hiện lỗi, và tự động gọi luồng Repair để đưa chất lượng RAG trở lại 100%.
4. **Interactive Demo CLI (`demo_cli.py`)**: Viết một script CLI tương tác console giúp giảng viên/người dùng có thể trải nghiệm trực tiếp khả năng tra cứu bài báo và hỏi đáp với RAG Agent.

### Input, Output và Contract

| Thành phần | Mô tả |
| --- | --- |
| **Input** | Rest API Crossref query params, environment variables, raw JSON snapshots |
| **Output** | CSV/JSON clean datasets, Vector collection ChromaDB, metrics JSON, `phase1_report.md`, `corruption_report.md` |
| **Module phụ thuộc** | Interacts với `src/ingestion`, `src/retrieval`, `src/evaluation`, `src/observability` |
| **Điều kiện lỗi xử lý** | Auto-retry khi Crossref bị 429/503; heuristic fallback cho evaluator khi chưa có API key |

### Lệnh xác minh
```bash
# 1. Chạy Baseline Pipeline
uv run python script/run_phase1.py

# 2. Chạy Corruption & Repair Flow
uv run python script/run_corruption_flow.py

# 3. Trải nghiệm Demo CLI
uv run python script/demo_cli.py
```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh**: Cần lựa chọn provider và mô hình LLM để đánh giá và trả lời câu hỏi trong hệ thống RAG với chi phí tối ưu và tốc độ cao.
- **Các phương án đã cân nhắc**: 
  1. Sử dụng OpenAI GPT-4o-mini (Tốn chi phí API Key).
  2. Sử dụng Google Gemini 2.5 Flash (Giới hạn rate-limit nếu dùng free tier).
  3. Tích hợp **Groq LLM API** (`llama-3.3-70b-versatile`).
- **Phương án đã chọn**: Tích hợp Groq LLM API thông qua chuẩn REST OpenAI-compatible.
- **Lý do**: Groq mang lại tốc độ phản hồi cực nhanh (LPU inference engine), hỗ trợ model `llama-3.3-70b-versatile` chất lượng cao và hoàn toàn miễn phí/dễ đăng ký API Key cho việc làm lab.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn**: `ModuleNotFoundError: No module named 'chromadb'` và `ModuleNotFoundError: No module named 'datasets'` khi chạy script runner qua lệnh `python script/run_phase1.py`.
- **Nguyên nhân gốc**: 
  1. Môi trường mặc định của máy chưa kích hoạt virtualenv của dự án (`.venv`).
  2. Thư viện `datasets` bị import cứng ở cấp module trong `metrics.py`, gây crash kể cả khi không bật Ragas.
- **Cách xử lý**:
  1. Chuyển sang sử dụng `uv run python script/run_phase1.py` để đảm bảo thực thi chuẩn xác trong virtual environment đã cài đủ 157 dependencies.
  2. Đưa câu lệnh `from datasets import Dataset` vào bên trong hàm `_run_ragas` dưới dạng lazy-import, giúp pipeline khởi chạy mượt mà ngay cả khi môi trường tối giản.

---

## 7. Hiểu biết về luồng end-to-end

Lời giải thích tổng quan của tôi về toàn bộ kiến trúc Data Pipeline RAG:
1. **Raw Ingestion**: Lấy metadata bài báo khoa học từ Crossref REST API, lưu nguyên bản JSON gốc tại `data/raw/` để phục vụ khả năng truy vết (lineage).
2. **Cleaning & Modeling**: Loại bỏ rác, chuẩn hóa tiêu đề/tóm tắt, tính ngày tuổi (`age_days`) và hợp nhất thành văn bản đầu vào `text_for_embedding`.
3. **Indexing & Retrieval**: Tạo vector embedding bằng MiniLM (`sentence-transformers/all-MiniLM-L6-v2`) và lưu vào ChromaDB Vector Database.
4. **Baseline Evaluation**: Chạy bộ câu hỏi chuẩn (40 câu) để tính điểm *Retrieval Hit Rate*, *Token F1*, và *LLM Judge Score* trên dữ liệu sạch.
5. **Controlled Corruption**: Cố tình làm hỏng dữ liệu (xóa bài báo mới, rỗng summary, nhiễu text, ngày cũ) để kiểm chứng tác động: kết quả làm giảm Hit Rate từ **100% xuống 80%** và làm bài test Quality báo **FAILED**.
6. **Data Repair & Recovery**: Thực hiện ETL làm sạch lại từ nguồn raw ban đầu, khôi phục chất lượng Hit Rate trở lại **100%** và Quality Check báo **PASSED**.

---

## 8. Phân tích kết quả thực tế thu được

Từ kết quả chạy pipeline thực tế do Vai trò 1 điều phối:

| Chỉ số / Trạng thái | Baseline (Dữ liệu sạch) | Corrupted (Dữ liệu lỗi) | Repaired (Đã phục hồi) |
| :--- | :---: | :---: | :---: |
| **Số lượng bài báo** | 24 | 24 | 24 |
| **Retrieval Hit Rate** | **1.0000 (100%)** | **0.8000 (80%)** 📉 | **1.0000 (100%)** 📈 |
| **Mean Token F1** | **1.0000** | **0.7000** 📉 | **1.0000** 📈 |
| **LLM Judge Accuracy** | **1.0000** | **0.7000** 📉 | **1.0000** 📈 |
| **Data Quality Audit** | **PASSED ✅** | **FAILED ❌** | **PASSED ✅** |
| **Data Freshness Audit** | **Fresh ✅** | **Stale ⚠️** | **Fresh ✅** |

**Nhận xét**: 
- Kết quả cho thấy dữ liệu lỗi (đặc biệt là summary bị rỗng hoặc bị nhiễu) ảnh hưởng trực tiếp và nghiêm trọng tới khả năng tìm kiếm ngữ cảnh đúng của RAG Agent.
- Việc kiểm soát dữ liệu thông qua Data Observability & Repair Flow giúp hệ thống tự động phát hiện sai sót và khôi phục lại hiệu năng ban đầu một cách hoàn hảo.
