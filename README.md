# RAG Code 1 — Module truy xuất tài liệu sinh viên

Module Python tìm các đoạn liên quan đến câu hỏi tiếng Việt trong **Sổ tay sinh viên Khóa 50 — Trường Đại học Sư phạm Thành phố Hồ Chí Minh**.

**Trạng thái:** đã hoàn thành phần truy xuất tài liệu (CV12–CV14). Phần tạo prompt và gọi LLM để sinh câu trả lời thuộc Code 2, chưa được triển khai trong dự án này. Vì vậy, đây là **thành phần Retrieval của RAG**, chưa phải hệ thống RAG hỏi đáp hoàn chỉnh.

## 1. Dự án làm được gì?

| Công việc | Chức năng đã có |
|---|---|
| CV12 — Nạp tài liệu | Đọc PDF theo trang, chuẩn hóa tiếng Việt, chia đoạn có overlap, lưu nguồn và số trang |
| CV13 — Truy xuất | Tạo embedding bằng E5, lưu index, tìm Top-k theo cosine similarity |
| CV14 — Kiểm tra và bàn giao | Đánh giá ba câu hỏi có bằng chứng, lưu Top-3 và Hit@3, cung cấp tests và API cho Code 2 |

Luồng đã triển khai:

```text
Xây index, chạy khi PDF hoặc cấu hình thay đổi:
PDF → Trích xuất từng trang → Chuẩn hóa → Chia chunks → E5 → Lưu index

Truy vấn:
Câu hỏi → E5 → So sánh với index → Top-3 đoạn + nguồn + trang + score
```

Để hoàn thiện RAG, Code 2 cần bổ sung:

```text
Câu hỏi + các đoạn truy xuất → Prompt cung cấp ngữ cảnh → LLM → Câu trả lời có dẫn nguồn
```

Giao diện thuộc CV15; prompt và LLM thuộc CV16. Giao diện giúp người dùng tương tác nhưng không phải điều kiện bắt buộc của RAG. Khi chạy CLI hiện tại, kết quả là **các đoạn văn bản**, chưa phải câu trả lời do LLM tổng hợp.

## 2. Chạy ngay bản đã bàn giao

Mở Terminal tại thư mục gốc `rag-demo/`, nơi có file README này. Nếu môi trường `.venv/` đã được tạo trên máy hiện tại, kích hoạt:

**macOS / Linux:**

```bash
source .venv/bin/activate
python --version
```

**Windows PowerShell** (với môi trường được tạo trên Windows):

```powershell
.\.venv\Scripts\Activate.ps1
python --version
```

Cần Python **3.11 trở lên**. Nếu chưa có môi trường hoặc đang chuyển máy, xem mục 3 trước.

Index mặc định đã có sẵn cho **toàn bộ 220 trang**, nên có thể thử truy vấn ngay:

```bash
python -m src.demo_retrieve --question "Sinh viên chính quy bắt đầu tự đăng ký học phần từ học kỳ nào?" --top-k 3
```

Kết quả là một mảng JSON gồm ba đoạn, mỗi đoạn có `chunk_id`, `text`, `source`, `page`, `score`. Trong báo cáo hiện tại, bằng chứng đúng cho câu hỏi trên nằm ở **trang 15, vị trí thứ 3**.

Để nhập liên tục nhiều câu hỏi trong cùng một tiến trình:

```bash
python -m src.demo_retrieve
```

Nhập câu hỏi rồi Enter; nhập dòng trống để thoát.

## 3. Cài đặt trên máy mới

Cần Python 3.11+ và Internet lần đầu cài thư viện/tải model. Chạy các lệnh từ thư mục gốc dự án.

**macOS / Linux:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Có thể thay `python3.11` bằng `python3` nếu phiên bản đã từ 3.11 trở lên.

**Windows PowerShell:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn script kích hoạt, dùng trực tiếp `.\.venv\Scripts\python.exe` thay cho `python` trong các lệnh tiếp theo. Windows CMD có thể kích hoạt bằng `.venv\Scripts\activate.bat`. Nếu môi trường thiếu pip, chạy `python -m ensurepip --upgrade` trước khi cài dependencies.

Model `intfloat/multilingual-e5-small` được tải tự động vào `.cache/models/`, không cần API key. Các lần sau ưu tiên cache cục bộ. Revision model được cố định trong `src/config.py`.

Khi chuyển máy, giữ `src/`, `evaluation/`, `requirements.txt`, PDF và index theo cấu trúc dự án. PDF vẫn cần có để kiểm tra hash nguồn. Tạo lại môi trường trên máy nhận; không copy `.venv/` giữa các hệ điều hành. Nếu chưa có index, thực hiện mục 4.

## 4. Xây lại index từ PDF

Nguồn chính thức:

```text
data/so_tay_sinh_vien_k50.pdf
```

Đây là bản sao nguyên byte của file được cung cấp `SO TAY SINH VIEN K50.pdf`, gồm 220 trang. Metadata `page` dùng **trang vật lý PDF, bắt đầu từ 1**.

### 4.1. CV12: chỉ trích xuất và chia đoạn

Lệnh này không tải model:

```bash
python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out data/chunks_preview --pages 8-31 --chunks-only
```

Đầu ra là `data/chunks_preview/chunks.json`, kèm thống kê trong terminal. `--chunks-only` yêu cầu thư mục đích chưa có embedding/index metadata để tránh ghi đè riêng một phần index.

### 4.2. Pilot: xây index trang 8–31

```bash
python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out data/processed_pilot --pages 8-31
```

`--pages 8-31` bao gồm cả hai đầu. Chọn một trang bằng `--pages 8-8`. Chương trình tự tạo thư mục đích.

Để truy vấn và đánh giá đúng index pilot:

**macOS / Linux:**

```bash
RAG_INDEX_DIR=data/processed_pilot python -m src.demo_retrieve --question "Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào?" --top-k 3
RAG_INDEX_DIR=data/processed_pilot python -m evaluation.run_evaluation --out evaluation/retrieval_report_pilot.json
```

**Windows PowerShell:**

```powershell
$env:RAG_INDEX_DIR = "data/processed_pilot"
python -m src.demo_retrieve --question "Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào?" --top-k 3
python -m evaluation.run_evaluation --out evaluation/retrieval_report_pilot.json
Remove-Item Env:RAG_INDEX_DIR
```

Pilot được lưu riêng, không ghi đè index toàn bộ ở `data/processed/`.

### 4.3. Toàn bộ 220 trang

Sau khi pilot hoạt động đúng, bỏ `--pages` để xử lý toàn bộ:

```bash
python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out data/processed
python -m evaluation.run_evaluation
```

Index gồm ba file được sinh bằng chạy thật:

| File | Nội dung |
|---|---|
| `chunks.json` | Văn bản, chunk ID, nguồn, trang và thứ tự |
| `embeddings.npy` | Ma trận vector float32, mỗi chunk có 384 chiều |
| `index_meta.json` | Hash nguồn, phạm vi trang, model/revision, cấu hình, checksum và thời điểm build |

Chỉ build lại khi PDF hoặc cấu hình thay đổi. Mỗi câu hỏi chỉ được embedding một lần; chương trình tái sử dụng model và index trong tiến trình, không trích xuất lại PDF hay embedding lại tất cả chunks. Mỗi lần truy vấn vẫn kiểm tra hash PDF để phát hiện nguồn thay đổi.

## 5. API sử dụng trong Code 2

Chạy từ thư mục gốc dự án hoặc thêm thư mục gốc Code 1 vào `PYTHONPATH` để import được package `src`.

```python
from src.retriever import retrieve

results = retrieve(
    "Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào?",
    top_k=3,
)

for item in results:
    print(item["text"])
    print(item["source"], item["page"], item["score"])
```

Hợp đồng công khai:

```python
retrieve(question: str, top_k: int = 3) -> list[dict]
```

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `chunk_id` | `str` | Định danh đoạn |
| `text` | `str` | Nội dung thật đã chuẩn hóa |
| `source` | `str` | Tên PDF nguồn |
| `page` | `int` | Trang vật lý PDF, 1-based |
| `score` | `float` | Cosine similarity |

API trả đối tượng Python; CLI chuyển kết quả sang JSON. Kết quả sắp theo score giảm dần, điểm bằng nhau giữ `order` tăng dần. Trả `min(top_k, số chunks)` đoạn. `top_k` phải là số nguyên dương.

**Score là mức tương đồng, không phải xác suất trả lời đúng.** API chưa xác nhận câu hỏi có đáp án trong tài liệu và chưa sinh câu trả lời. Code 2 nhận các đoạn này để làm ngữ cảnh cho LLM.

Hướng dẫn chọn index, chuyển máy và bắt lỗi: [docs/code2_integration.md](docs/code2_integration.md).

## 6. Kiểm tra hệ thống

Chạy đánh giá ba câu CV14 với index mặc định:

```bash
python -m evaluation.run_evaluation
```

Chương trình in Top-3 của từng câu và ghi `evaluation/retrieval_report.json`. Một câu có hit khi Top-3 chứa chunk khớp **gold ID, nguồn, trang và toàn bộ bằng chứng**. Trùng trang nhưng không chứa chứng cứ sẽ không được chấm đúng.

Chạy tests nhanh, không tải model:

```bash
python -m pytest -q
```

Chạy đầy đủ với model E5 thật và integration tests:

```bash
python -m pytest -q --run-model
```

Output đã ghi nhận trong lượt bàn giao ngày **14/11/2026**:

```text
# Kiểm thử nhanh
52 passed, 7 skipped in 0.96s

# Kiểm thử đầy đủ với E5 thật
59 passed in 6.29s
```

Bảy tests gắn nhãn `real_model` được bỏ qua ở lệnh nhanh và đã chạy trong lệnh đầy đủ. Fixtures dùng PDF được cung cấp; negative tests làm hỏng bản sao tạm và tests tie-break lặp lại vector thật. Những thay đổi kiểm thử này không tác động artifact bàn giao. Nếu chưa có index, một số tests phụ thuộc artifact sẽ skip và nêu lý do.

Log thực thi: [tests nhanh](docs/unit_tests.log), [tests đầy đủ](docs/full_tests.log), [kiểm tra tích hợp Code 2](docs/code2_smoke.log).

## 7. Kết quả truy xuất đã kiểm chứng

| Lượt | Trang xử lý | Chunks | Token passage lớn nhất | Hit@3 |
|---|---|---|---|---|
| Pilot cuối | 8–31 | 254 | 143 | 3/3 |
| Toàn bộ | 1–220 | 1.907 | 200 | 3/3 |

Index mặc định là `data/processed/` cho toàn bộ 220 trang. Index pilot nằm ở `data/processed_pilot/`.

Ba câu hỏi cố định:

| ID | Câu hỏi | Trang bằng chứng |
|---|---|---|
| Q01 | Một tín chỉ học lý thuyết được quy định bao nhiêu giờ, và cần bao nhiêu giờ tự học có hướng dẫn? | 8 |
| Q02 | Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào? | 9 |
| Q03 | Sinh viên chính quy bắt đầu tự đăng ký học phần từ học kỳ nào? | 15 |

Top-3 trên toàn bộ PDF, từ [báo cáo thực tế](evaluation/retrieval_report.json):

| Câu | Top-1: ID / cosine | Top-2: ID / cosine | Top-3: ID / cosine | Hit |
|---|---|---|---|---|
| Q01 | `p008-c006` / 0.931322 | `p032-c006` / 0.931322 | `p072-c003` / 0.895142 | 1 |
| Q02 | `p009-c007` / 0.902875 | `p033-c007` / 0.902875 | `p019-c006` / 0.880307 | 1 |
| Q03 | `p011-c008` / 0.892101 | `p035-c006` / 0.892101 | `p015-c011` / 0.891929 | 1 |

ID trong bảng bỏ tiền tố chung `so_tay_sinh_vien_k50-`; nguồn là `so_tay_sinh_vien_k50.pdf`. JSON chứa ID đầy đủ, text và score từng kết quả.

**Hit@3 = 3/3 = 1,0** chỉ phản ánh ba câu hỏi này. Riêng Q03 có bằng chứng đúng ở hạng 3; top-1 chưa trả lời được câu hỏi. Chỉ số này đánh giá truy xuất, chưa đánh giá câu trả lời do LLM sinh.

Baseline chia cửa sổ 500/100 theo trang ban đầu đạt **2/3**. Sau khi tách theo cấu trúc điều/khoản/điểm trước khi chia cửa sổ, pilot đạt 3/3 rồi mới mở rộng toàn bộ PDF. Câu hỏi và nội dung chứng cứ được giữ nguyên; gold IDs được cập nhật theo chunks mới đã kiểm tra.

Báo cáo [pilot](evaluation/retrieval_report_pilot.json), [baseline](evaluation/retrieval_report_baseline.json) và [lịch sử thử nghiệm](docs/ingestion_notes.md) được giữ để đối chiếu. `data/processed_pilot_baseline/` thuộc index version cũ, chỉ lưu lịch sử và không dùng với mã hiện tại.

## 8. Cấu trúc dự án

```text
rag-demo/
├── data/
│   ├── so_tay_sinh_vien_k50.pdf
│   ├── processed/
│   │   ├── chunks.json
│   │   ├── embeddings.npy
│   │   └── index_meta.json
│   ├── processed_pilot/
│   └── processed_pilot_baseline/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── document_loader.py
│   ├── chunking.py
│   ├── embeddings.py
│   ├── build_index.py
│   ├── retriever.py
│   └── demo_retrieve.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_document_loader.py
│   ├── test_chunking.py
│   ├── test_embeddings.py
│   ├── test_retriever.py
│   └── test_integration.py
├── evaluation/
│   ├── __init__.py
│   ├── questions.json
│   ├── run_evaluation.py
│   ├── retrieval_report.json
│   ├── retrieval_report_pilot.json
│   └── ...                         # baseline và các lượt thử
├── docs/
│   ├── technical_spec.md
│   ├── code2_integration.md
│   ├── ingestion_notes.md
│   ├── delivery.md
│   ├── environment.txt
│   └── ...                         # log và output chạy thật
├── requirements.txt
├── README.md
└── .gitignore
```

Cây đầy đủ và danh sách file theo giai đoạn: [docs/delivery.md](docs/delivery.md). Bản đặc tả README ban đầu được giữ tại [docs/technical_spec.md](docs/technical_spec.md).

## 9. Cấu hình, lỗi thường gặp và giới hạn

Cấu hình chính nằm trong `src/config.py`:

| Tham số | Giá trị |
|---|---|
| Model | `intfloat/multilingual-e5-small`, cố định revision |
| Kích thước chunk tối đa | 500 ký tự |
| Overlap mục tiêu | 100 ký tự bên trong đơn vị quy định dài |
| Giới hạn model | 512 token, kiểm tra trước khi encode |
| Embedding | 384 chiều, float32, chuẩn hóa L2 |
| Index mặc định | `data/processed/`; có thể chọn bằng `RAG_INDEX_DIR` |

Overlap không được ép qua ranh giới điều/khoản/điểm; chunks không vượt ranh giới trang. Passage có tiền tố `passage: `, câu hỏi có tiền tố `query: `. Nội dung quá giới hạn token bị từ chối, không cắt âm thầm. Đổi model hoặc cấu hình cần build lại index; đổi chunks cần kiểm tra lại gold IDs trước khi đánh giá.

| Tình huống | Cách xử lý |
|---|---|
| Không import được `src` | Chạy tại thư mục gốc hoặc thêm thư mục gốc vào `PYTHONPATH` |
| Thiếu `pypdf`, `numpy` hoặc thư viện khác | Kiểm tra đã kích hoạt đúng môi trường, rồi cài `requirements.txt` |
| Thiếu index | Chạy build để tạo đủ ba artifact |
| PDF/hash/cấu hình không khớp hoặc index hỏng | Kiểm tra PDF nguồn, build lại index |
| Chưa tải được model | Kiểm tra Internet; model sẽ được dùng lại từ cache khi đã tải đủ |
| Query rỗng hoặc `top_k` không hợp lệ | Dùng câu hỏi có nội dung và `top_k` là số nguyên dương |

Các giới hạn còn lại:

- Chỉ hỗ trợ PDF có văn bản trích xuất được; không làm OCR. “Trang có text” không bảo đảm toàn bộ chữ trong ảnh đã được lấy.
- Giữ header/footer để tránh xóa nhầm. Bảng biểu được trải thành text, chưa bảo toàn quan hệ hàng/cột và công thức.
- Sổ tay có các quy chế và đoạn giống nhau, có thể cạnh tranh vị trí Top-3. Không có reranking hoặc lọc trang ngầm.
- Câu hỏi ngoài tài liệu vẫn có thể trả Top-3; hệ thống chưa có bước xác nhận đủ bằng chứng hay sinh câu trả lời.
- Đã chạy trên macOS ARM64/Python 3.11.18; chưa chạy trực tiếp Windows/Linux và chưa đối chiếu thủ công toàn bộ 220 trang.

Phiên bản thư viện thực tế: [docs/environment.txt](docs/environment.txt). Chi tiết trích xuất và hạn chế: [docs/ingestion_notes.md](docs/ingestion_notes.md).

Tài liệu tham khảo triển khai: [model card E5](https://huggingface.co/intfloat/multilingual-e5-small), [pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html), [SentenceTransformer](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html).
