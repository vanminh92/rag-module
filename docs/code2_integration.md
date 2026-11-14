# Bàn giao Retrieval Module cho Code 2

Code 1 đọc PDF, tạo embedding passage và lưu index một lần. Code 2 chỉ gọi API bên dưới; giao diện, prompt và LLM thuộc phạm vi của Code 2.

## Cài đặt và sử dụng

Cần Python 3.11+, cài `python -m pip install -r requirements.txt`. Chạy từ thư mục gốc dự án hoặc thêm thư mục gốc Code 1 vào `PYTHONPATH` để import được package `src`. Không cài package PyPI có tên `src`.

```python
from src.retriever import retrieve

results = retrieve("Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào?", top_k=3)
for item in results:
    print(item["text"])
    print(item["source"], item["page"], item["score"])
```

Chữ ký công khai: `retrieve(question: str, top_k: int = 3) -> list[dict]`. Kết quả là đối tượng Python, không phải chuỗi JSON. Mỗi phần tử có đúng năm trường:

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `chunk_id` | `str` | ID ổn định với cùng nguồn, cấu hình và chiến lược chia đoạn |
| `text` | `str` | Văn bản thật đã chuẩn hóa khoảng trắng/NFC |
| `source` | `str` | `so_tay_sinh_vien_k50.pdf` |
| `page` | `int` | Trang vật lý PDF, bắt đầu từ **1** |
| `score` | `float` | Cosine similarity; không phải xác suất đúng hay phần trăm tin cậy |

Sắp xếp giảm dần theo score, điểm bằng nhau giữ `order` tăng dần. `top_k` phải là số nguyên dương, không nhận `bool`. Trả `min(top_k, num_chunks)` phần tử. Câu hỏi ngoài tài liệu vẫn có thể trả Top-3; API không xác nhận tài liệu có đáp án và không sinh câu trả lời.

## Index, cache và chuyển máy

Mặc định đọc `data/processed/` dưới thư mục dự án, không phụ thuộc working directory của Code 2. Tải model E5 trên CPU một lần trong tiến trình; cache model tại `.cache/models/`. Truy vấn chỉ encode câu hỏi, không mở lại PDF bằng `PdfReader`, không encode lại passages. Mỗi lần gọi kiểm tra hash PDF; chỉ nạp lại index nếu artifact/cấu hình thay đổi.

Để dùng thư mục index khác, đặt `RAG_INDEX_DIR` **trước khi import**:

```python
import os
os.environ["RAG_INDEX_DIR"] = "data/processed_pilot"
from src.retriever import retrieve
```

Có thể dùng lớp hỗ trợ khi cần kiểm tra phạm vi trang rõ ràng; API bắt buộc phía trên vẫn giữ nguyên:

```python
from src.retriever import Retriever
pilot = Retriever("data/processed_pilot", expected_page_range=(8, 31))
results = pilot.retrieve("Học phần tiên quyết là gì?")
```

`index_meta.json` ghi rõ `page_range`; dữ liệu của index đang chọn quyết định phạm vi truy xuất. Không có lọc trang hay thay câu hỏi ngầm. Muốn đổi phạm vi, build index khác rồi chọn thư mục đó. Truyền `expected_page_range` khác phạm vi index sẽ báo lỗi yêu cầu rebuild.

Khi chuyển sang máy khác, copy `src/`, `requirements.txt` và cả `data/so_tay_sinh_vien_k50.pdf` cùng ba file index vào cấu trúc tương ứng. Giữ đường dẫn tương đối `source_path` trong metadata; PDF cần có để xác minh checksum. Không cần copy `.venv/` hoặc cache: tạo môi trường mới, tải model một lần trên máy nhận. Nếu không copy index, chạy lệnh build trong README. Model được cố định revision trong `src/config.py` để passage/query dùng cùng weights.

## Xử lý lỗi

```python
from src.retriever import IndexValidationError, retrieve

try:
    results = retrieve("Học phần tiên quyết là gì?")
except FileNotFoundError as error:
    print("Chưa có đủ ba file index:", error)
except IndexValidationError as error:
    print("Index/PDF/cấu hình không khớp, cần build lại:", error)
except ValueError as error:
    print("Câu hỏi/top_k/token đầu vào không hợp lệ:", error)
```

Không thay model, tiền tố, normalization hoặc chiến lược chia đoạn giữa build và query. Đổi các giá trị này phải rebuild index và kiểm tra lại gold IDs nếu chunks thay đổi. Câu hỏi quá giới hạn token bị từ chối, không cắt âm thầm. Lần đầu tải model cần Internet; nếu tải thất bại, kiểm tra kết nối rồi chạy lại. Không cần API key cho model công khai.

## Phạm vi kiểm chứng

Đọc báo cáo pilot và full trong `evaluation/`, cùng lịch sử thử nghiệm trong `docs/ingestion_notes.md`. Ba câu benchmark là kiểm tra hồi quy nhỏ, không chứng minh mọi câu hỏi hoặc bảng biểu đều truy xuất chính xác. Sổ tay có nhiều phần quy chế; Code 2 cần giữ nguồn/trang khi hiển thị và tránh diễn giải các quy chế khác nhau như cùng một quy định.
