# Hướng dẫn phát triển

Hướng dẫn cài và chạy ứng dụng nằm ở [README](../README.md). Tất cả lệnh dưới đây chạy từ thư mục gốc dự án.

## Chạy bằng dòng lệnh

Chỉ tìm nguồn, không gọi Qwen:

```bash
.venv/bin/python -m src.pipeline --retrieve-only --question "Điểm thấp quá có bị đuổi học không?"
```

Hỏi đáp qua pipeline đang dùng trong giao diện:

```bash
.venv/bin/python -m src.pipeline --question "Sinh viên đại học chính quy tự đăng ký học phần từ học kỳ nào?" --debug
```

API retrieval cũ vẫn độc lập với giao diện, trả đúng năm trường `chunk_id`, `text`, `source`, `page`, `score`:

```python
from src.retriever import retrieve
sources = retrieve("Học phần tiên quyết là gì?", top_k=3)
```

API hỏi đáp nâng cao:

```python
from src.pipeline import RAGPipeline
result = RAGPipeline().ask("Sinh viên có quyền lợi gì về đăng ký ngoại trú?")
print(result.status, result.answer, result.sources)
```

Chi tiết contract và lỗi: [code2_integration.md](code2_integration.md). Score cosine không phải xác suất trả lời đúng.

## Dữ liệu và index

Nguồn: `data/so_tay_sinh_vien_k50.pdf`, 220 trang. Index mặc định `data/processed/` gồm `chunks.json`, `embeddings.npy`, `index_meta.json`; `structure.json` là metadata cấu trúc bổ sung có thể được tạo lại. Số trang vật lý bắt đầu từ 1.

Không cần rebuild để chạy app. Khi thật sự thay tài liệu/cấu hình, thử build vào thư mục riêng trước:

```bash
.venv/bin/python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out .cache/rebuilt_index
RAG_INDEX_DIR=.cache/rebuilt_index .venv/bin/python -m src.demo_retrieve --question "Học phần tiên quyết là gì?" --top-k 3
```

Đổi PDF hoặc chunking có thể làm gold IDs của benchmark không còn đúng. Không ghi đè nhãn đánh giá để che việc dữ liệu đã đổi. Các index pilot trong `data/` được giữ cho lịch sử dữ liệu, không phải index mặc định của app.

## Cấu hình tùy chọn

Giữ nguyên model mặc định khi chỉ sửa giao diện. Chỉ dùng các cờ sau khi cần thử nghiệm:

```bash
# Viết lại truy vấn bằng Qwen
RAG_QUERY_REWRITE=llm .venv/bin/python -m streamlit run streamlit_qa_app.py

# Bỏ reranking để đối chiếu
RAG_RERANKER=none .venv/bin/python -m streamlit run streamlit_qa_app.py

# Bỏ lớp NLI, vẫn giữ kiểm tra trích dẫn và Qwen
RAG_SUPPORT_CHECK=llm .venv/bin/python -m streamlit run streamlit_qa_app.py
```

Toàn bộ biến môi trường, thiết kế và giới hạn: [open_domain_rag.md](open_domain_rag.md).

## Kiểm thử

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q --run-model
.venv/bin/python -m evaluation.run_evaluation --out .cache/cv14_recheck.json
```

`--run-model` dùng model đã cache để chạy cả các ca E5/NLI thật. Benchmark 70 câu và cách chấm: [evaluation/README.md](../evaluation/README.md). Không cần chạy benchmark nhiều phút khi chỉ chỉnh README hoặc xóa log cũ.

## Kiểm thử trình duyệt

```bash
.venv/bin/python -m pip install -r requirements-ui-test.txt
.venv/bin/python scripts/ui_browser_check.py
```

Script dùng app, Edge, Ollama và PDF thật, tự mở/dừng server local riêng. Cần Ollama chạy và model đã tải. Dùng `--browser /path/to/chromium` nếu không dùng Edge mặc định trên macOS. Ảnh và kết quả được ghi vào `docs/ui_workbench/`; script có gọi model cho các câu hỏi kiểm thử, không chỉ dựng mockup.
