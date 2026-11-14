# YÊU CẦU KỸ THUẬT TRIỂN KHAI RAG CODE 1 — CV12, CV13, CV14

**Phiên bản:** 2.0 — chốt dữ liệu PDF thật  
**Ngày:** 14/11/2026  
**Đối tượng nhận:** Trợ lý lập trình / AI coding assistant  
**Trạng thái:** Yêu cầu cần thực hiện, KHÔNG phải báo cáo đã chạy  
**Mục tiêu bàn giao:** Module Python truy xuất Top-3 đoạn liên quan từ một tài liệu PDF tiếng Việt và metadata nguồn, sẵn sàng dùng cho Code 2 (CV15–CV16).

> **Nguyên tắc:** Chỉ triển khai CV12 (trích xuất + chunking), CV13 (embedding + retrieval Top-3), CV14 (kiểm thử 3 câu + bàn giao). Chưa xây giao diện Streamlit, chưa gọi LLM, chưa làm OCR hay thêm cơ sở dữ liệu vector nếu không có yêu cầu bổ sung. Không tự bịa đầu ra, số liệu hay kết quả kiểm thử.

## 1. Bối cảnh và dữ liệu đã chốt

- **Tài liệu đầu vào chính thức:** File PDF người dùng cung cấp: **`SO TAY SINH VIEN K50.pdf`** (*Sổ tay sinh viên Khóa 50*, Trường Đại học Sư phạm Thành phố Hồ Chí Minh).
- **Dung lượng/nội dung đã xác nhận:** 220 trang PDF; có lớp văn bản trích xuất được bằng `pypdf` tại các trang đã kiểm tra; nội dung chủ yếu tiếng Việt, gồm nhiều quy định và các bảng.
- **Cách đặt trong repository:** Đổi tên *bản sao* thành `data/so_tay_sinh_vien_k50.pdf` (không sửa nội dung PDF). Tên file gốc cần ghi trong README hoặc metadata nguồn nếu muốn phục vụ truy vết.
- **Phạm vi thử nghiệm lần đầu:** Trang PDF **8–31** (đánh số trang vật lý của PDF, tính từ 1, bao gồm hai đầu); thuộc phần Quy chế đào tạo trình độ đại học. Chỉ mở rộng sang **toàn bộ 220 trang** sau khi bản thử nghiệm đáp ứng điều kiện nghiệm thu.
- **Lý do thử nghiệm một phần:** PDF dài, có nhiều văn bản quy định khác nhau; cần kiểm tra chất lượng chunk, số trang và retrieval trước khi mở rộng. Không dùng số trang 8–31 như một lời khẳng định về hiệu lực quy định hiện hành.
- **Lưu ý nguồn:** Có các phần quy chế thuộc những nhóm đào tạo khác nhau; giữ ranh giới trang và nguồn để tránh trộn quy định. Các bảng biểu có thể bị đọc sai thứ tự khi extract; ghi nhận giới hạn và KHÔNG tự suy diễn hay sửa số liệu.

### 1.1. Phân biệt hai loại input

1. **Input cho xây index:** đường dẫn đến PDF (`data/so_tay_sinh_vien_k50.pdf`) và cấu hình xử lý.
2. **Input cho truy vấn:** một câu hỏi tiếng Việt (`question: str`).

PDF không được gửi trực tiếp vào embedding. Pipeline phải trích văn bản → chia chunks → embedding → lưu index; khi hỏi thì embedding câu hỏi → so sánh index → trả Top-3 chunks.

## 2. Phạm vi công việc và sản phẩm cần bàn giao

| Task | Phải làm | Đầu ra chính |
|---|---|---|
| **CV12** | Xác thực PDF, trích xuất text từng trang, làm sạch ở mức tối thiểu, chia chunks có overlap, lưu nguồn/trang | `data/processed/chunks.json`, log thống kê |
| **CV13** | Embedding chunks bằng cùng model E5, lưu index, triển khai `retrieve(question, top_k=3)` | `embeddings.npy`, `index_meta.json`, API retrieval |
| **CV14** | Viết 3 câu hỏi dựa trên PDF thật, xác định gold evidence, chạy Top-3, tính Hit@3, viết hướng dẫn bàn giao | `questions.json`, `retrieval_report.json`, `docs/code2_integration.md`, README, test output |

## 3. Công nghệ bắt buộc cho MVP

| Thành phần | Quyết định |
|---|---|
| Python | 3.11+ |
| Đọc PDF | `pypdf` / `PdfReader` |
| Embedding tiếng Việt | `sentence-transformers`, `intfloat/multilingual-e5-small` |
| Tìm Top-3 | NumPy, dot product trên vector L2-normalized (cosine similarity) |
| Lưu artifact | JSON UTF-8, NumPy `.npy` |
| Kiểm thử | `pytest` |
| Cấu hình | `src/config.py` và tham số CLI; không hard-code đường dẫn tuyệt đối |

**Cấu hình mặc định đề xuất:** `CHUNK_SIZE_CHARS=500`, `CHUNK_OVERLAP_CHARS=100`, `TOP_K_DEFAULT=3`, `MODEL_NAME="intfloat/multilingual-e5-small"`. Các giá trị là baseline thử nghiệm, không phải kết quả tối ưu đã chứng minh.

**Quy tắc E5:** embedding passage phải dùng tiền tố `"passage: "`, embedding câu hỏi phải dùng `"query: "`. Cả hai cùng model. Chuẩn hóa vector L2. Model có embedding 384 chiều; cần kiểm tra giới hạn token thực tế bằng tokenizer (đầu vào tối đa 512 token) và **không cắt âm thầm**.

## 4. Cây thư mục HOÀN CHỈNH (phải tạo đúng)

```text
rag-demo/
│
├── data/
│   ├── so_tay_sinh_vien_k50.pdf          # PDF gốc, bản sao đã đổi tên
│   └── processed/                       # Tạo tự động khi build index
│       ├── chunks.json                  # CV12: text chunks + metadata
│       ├── embeddings.npy              # CV13: ma trận vector (N, 384)
│       └── index_meta.json              # CV13: cấu hình/hash/nguồn/index
│
├── src/
│   ├── __init__.py
│   ├── config.py                        # Cấu hình model, chunk, paths
│   ├── document_loader.py              # CV12: đọc PDF theo trang
│   ├── chunking.py                     # CV12: normalize + split + metadata
│   ├── embeddings.py                   # CV13: E5 encode passage/query
│   ├── build_index.py                  # CV12+13: CLI build index
│   ├── retriever.py                    # CV13: API retrieve(question, top_k=3)
│   └── demo_retrieve.py                # CV14: demo CLI in Top-3
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Fixtures tài liệu giả lập nhỏ
│   ├── test_document_loader.py
│   ├── test_chunking.py
│   ├── test_embeddings.py
│   ├── test_retriever.py
│   └── test_integration.py
│
├── evaluation/
│   ├── __init__.py
│   ├── questions.json                  # 3 câu + đáp án nguồn được xác minh
│   ├── run_evaluation.py              # Kiểm tra 3 câu, tính Hit@3
│   └── retrieval_report.json           # Sinh tự động, KHÔNG tạo giả
│
├── docs/
│   ├── code2_integration.md            # Hợp đồng API để Code 2 import
│   └── ingestion_notes.md              # Ghi hạn chế PDF/bảng/trang rỗng
│
├── requirements.txt
├── README.md
└── .gitignore
```

**Quy ước artifact:** `data/processed/*` và `evaluation/retrieval_report.json` chỉ xuất hiện **sau khi chạy thật**. Trợ lý phải tự tạo thư mục đích; không ghi kết quả giả vào các file sinh tự động. `tests/` dùng fixtures để unit test nhanh, không bắt buộc tải model ở mỗi lần chạy.

## 5. Hợp đồng kỹ thuật chung giữa các module

### 5.1. Lập index

```text
PDF → validate → PdfReader.extract_text() từng trang (1-based)
    → chuẩn hóa nhẹ → chia chunks (không vượt ranh giới trang)
    → prefix passage → E5 embeddings → normalize → lưu index
```

### 5.2. Truy vấn

```text
question → validate → prefix query → E5 query embedding
         → cosine similarity với embeddings đã lưu
         → sắp xếp score giảm dần → Top-3 chunks + metadata
```

**Các chữ ký tối thiểu phải có:**

```python
# src/document_loader.py
load_document(path: str | Path, start_page: int | None = None,
              end_page: int | None = None) -> list[dict]
# Mỗi phần tử có ít nhất: {"text": str, "page": int}.

# src/chunking.py
build_chunks(pages: list[dict], source: str,
             chunk_size: int = 500, overlap: int = 100) -> list[dict]

# src/build_index.py
build_index(input_path: str | Path, index_dir: str | Path,
            start_page: int | None = None,
            end_page: int | None = None) -> dict

# src/retriever.py -- API công khai KHÔNG được thay đổi
retrieve(question: str, top_k: int = 3) -> list[dict]
```

Có thể tạo thêm class nội bộ hoặc dataclass nhưng **không thay đổi** chữ ký `retrieve()` hoặc năm trường đầu ra bắt buộc. Hàm `retrieve()` dùng đường dẫn index mặc định từ config, không nhận bắt buộc tham số PDF.

## 6. CV12 — PDF extraction + chunking

### 6.1. Đầu vào và xác thực

- Đọc đúng `data/so_tay_sinh_vien_k50.pdf`; cần hỗ trợ `--pages 8-31` ở CLI, với số trang **1-based inclusive**. Bỏ `--pages` nghĩa là xử lý toàn bộ file.
- Kiểm tra file tồn tại, đuôi PDF, không rỗng, không bị hỏng/khóa không đọc được; thông báo lỗi rõ ràng nếu thất bại.
- Mỗi trang sử dụng `page.extract_text() or ""`; ghi nhận trang rỗng, không làm hỏng index nếu chỉ một vài trang rỗng. Nếu toàn bộ vùng chọn không có text, dừng với thông báo *"PDF không có văn bản trích xuất được; OCR ngoài phạm vi"*.
- Không dùng OCR, vision-LM, upload cloud hay chuyển PDF sang TXT thủ công ở MVP.

### 6.2. Làm sạch và chia đoạn

- Chuẩn hóa Unicode NFC; xử lý `\r`, khoảng trắng thừa, ngắt dòng bất hợp lý ở mức thận trọng. **Bảo toàn dấu tiếng Việt, con số, dấu câu và nội dung quy định.**
- Loại bỏ header/footer lặp lại chỉ khi có quy tắc rõ ràng và test chứng minh không xóa nhầm; không tự paraphrase quy định.
- Chia theo thứ tự trang, tối đa 500 ký tự (baseline), overlap 100 ký tự (baseline), ưu tiên cắt ở ranh giới câu/từ.
- **Không nối nội dung của hai trang thành một chunk**, để `page` không bị mơ hồ. Giữ cả chunk cuối; không tạo chunk rỗng hoặc vòng lặp vô hạn.
- `chunk_id` là chuỗi ổn định theo file + trang + số thứ tự, ví dụ `k50-p008-c001`; `order` tăng dần toàn cục; một trang có thể có nhiều chunks.
- Đếm token của `"passage: " + text` trước khi embedding; nếu quá giới hạn tokenizer, chia thêm hoặc báo lỗi để xử lý, **không silent truncation**.
- Bảng biểu/công thức: trích xuất text ở mức có thể, ghi vào `docs/ingestion_notes.md` những trường hợp bị sai thứ tự; không đưa ra cam kết truy xuất chính xác từ bảng nếu parser chưa giữ được cấu trúc.

### 6.3. Định dạng dữ liệu CV12

**`data/processed/chunks.json`** là mảng JSON, UTF-8, `ensure_ascii=False`:

```json
[
  {
    "chunk_id": "k50-p008-c001",
    "text": "[Nội dung thật trích từ trang 8]",
    "source": "so_tay_sinh_vien_k50.pdf",
    "page": 8,
    "order": 0
  }
]
```

Đây là **schema minh họa**, không phải kết quả thực tế của chương trình.

### 6.4. Nghiệm thu CV12

1. Có báo cáo số trang đã đọc, số trang có/không có text, số ký tự và tổng số chunks.
2. Kiểm tra bằng tay ít nhất trang 8, 9, 15: chữ tiếng Việt và thông tin trích xuất đúng nội dung PDF.
3. Mọi chunk có `text` không rỗng, `chunk_id` duy nhất, `source`, `page`, `order` hợp lệ.
4. Không có chunk lẫn nội dung hai trang. Không làm mất đoạn cuối trang/tài liệu.
5. Unit tests pass; lưu output test thực tế.

## 7. CV13 — Embedding + truy xuất Top-3

### 7.1. Embedding và lưu chỉ mục

- Dùng model `intfloat/multilingual-e5-small` tải qua `sentence-transformers` (lần đầu có thể cần Internet, sau đó dùng cache).
- Encode `"passage: " + chunk["text"]`, dùng `normalize_embeddings=True`; chuyển `float32`, kiểm tra NaN/Inf và vector dimension **384**.
- Sinh `data/processed/embeddings.npy` shape `(N, 384)` với `N == len(chunks)` và cùng thứ tự `order`.
- Sinh `data/processed/index_meta.json` gồm tối thiểu:
  - `source`, `source_sha256`;
  - `page_range` (`[8, 31]` với pilot, hoặc `[1, 220]` khi full-run);
  - `model_name`, `embedding_dim`, `num_chunks`;
  - `chunk_size_chars`, `chunk_overlap_chars`, `index_version`, `build_timestamp`.
- Nếu hash PDF, model, giới hạn trang hoặc cấu hình chia chunks khác với index hiện có thì yêu cầu build lại. Không tính lại embedding cả tài liệu khi gọi truy vấn.

### 7.2. API retriever

```python
from src.retriever import retrieve

results = retrieve("Một tín chỉ học lý thuyết có bao nhiêu giờ?", top_k=3)
```

**BẮT BUỘC:** `retrieve(question: str, top_k: int = 3) -> list[dict]`. Mỗi dict chỉ cần bảo đảm **năm trường chính**:

```json
[
  {
    "chunk_id": "k50-p008-c001",
    "text": "[Đoạn văn bản liên quan được truy xuất thực tế]",
    "source": "so_tay_sinh_vien_k50.pdf",
    "page": 8,
    "score": 0.0
  }
]
```

`0.0` là số minh họa kiểu dữ liệu, **không phải score thật**. `score` là **cosine similarity**, không phải xác suất câu trả lời đúng.

**Yêu cầu xử lý:**
- Kiểm tra `question` là chuỗi không trống, `top_k` là số nguyên dương.
- Embed `"query: " + question` bằng chính model E5 ở bước lập index.
- Tính scores = embedding-matrix @ query-vector sau normalize; xếp giảm dần, tie-break theo `order` tăng dần để ổn định.
- Trả đúng `min(top_k, N)` kết quả; không hard-code Top-3 và không bịa ngưỡng score.
- Báo lỗi rõ ràng khi thiếu index, index mismatch, sai kích thước hoặc file hỏng.
- Tải model/index một lần và tái sử dụng nếu chạy nhiều câu liên tục.

### 7.3. Nghiệm thu CV13

1. CLI cho phép hỏi trực tiếp và in Top-3 cùng source/page/score.
2. Truy xuất bằng kết quả tính toán thực; index đã build được tái sử dụng ở câu hỏi tiếp theo.
3. `src/retriever.py` import được từ Code 2 mà không phải copy logic extraction/chunking.
4. Có tests cho query rỗng, `top_k` không hợp lệ, schema, sắp xếp, index lỗi và vectors.

## 8. CV14 — Kiểm thử 3 câu + bàn giao Code 2

### 8.1. Bộ câu hỏi thực tế đã chọn từ PDF

Chỉ đánh giá trên **vùng trang 8–31** ở lượt pilot, tránh lẫn nội dung từ các phần quy chế khác.

| ID | Câu hỏi | Trang tham chiếu | Căn cứ cần tìm trong PDF |
|---|---|---|---|
| Q01 | Một tín chỉ học lý thuyết được quy định bao nhiêu giờ, và cần bao nhiêu giờ tự học có hướng dẫn? | 8 | Điều 2: 15 giờ lý thuyết và 30 giờ tự học, chuẩn bị cá nhân có hướng dẫn |
| Q02 | Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào? | 9 | Mục các loại học phần: phải tích lũy học phần tiên quyết trước các học phần liên quan |
| Q03 | Sinh viên chính quy bắt đầu tự đăng ký học phần từ học kỳ nào? | 15 | Điều 9: từ học kỳ thứ hai của khóa học |

**Chú ý:** Đây là câu hỏi + thông tin nguồn đã xác định, **không phải kết quả retrieved**. Trợ lý phải trích nguyên đoạn nguồn ngắn từ PDF, xác nhận trang, sau khi build chunks mới gán `gold_chunk_ids` chứa thông tin cần thiết. Không gán chunk ID bằng suy đoán; không chấm đúng chỉ vì cùng số trang nếu chunk không chứa bằng chứng.

### 8.2. Format `evaluation/questions.json`

```json
[
  {
    "id": "Q01",
    "question": "Một tín chỉ học lý thuyết được quy định bao nhiêu giờ, và cần bao nhiêu giờ tự học có hướng dẫn?",
    "expected_source": "so_tay_sinh_vien_k50.pdf",
    "expected_page": 8,
    "expected_evidence": "[Trích nguyên văn ngắn từ PDF sau khi kiểm tra]",
    "gold_chunk_ids": []
  }
]
```

Tạo **đủ Q01–Q03** trong file thật. `gold_chunk_ids` phải được điền sau khi kiểm tra chunks đã tạo; không để rỗng rồi chấm đạt. Khi một câu trả lời cần nhiều chunks, ghi rõ quy tắc chấm trong báo cáo.

### 8.3. Chấm điểm và báo cáo

- Chạy `retrieve(question, top_k=3)` cho từng câu; lưu cả ba kết quả cùng `chunk_id`, text, source, page, score.
- Một câu có **Hit@3 = 1** nếu ít nhất một chunk trong Top-3 thực sự chứa bằng chứng được gán nhãn đúng; ngược lại `0`. Không tính pass chỉ dựa vào page match.
- `Hit@3 tổng = số câu có hit / 3`, báo cáo cả số lượng và tỷ lệ.
- Mục tiêu thử nghiệm ban đầu: **3/3**, nhưng nếu chưa đạt, phải ghi rõ kết quả thật, nguyên nhân dự kiến, đề xuất sửa; không chỉnh dữ liệu chứng cứ chỉ để làm đẹp chỉ số.
- `retrieval_report.json` ghi nguồn, cấu hình, ngày chạy, model, 3 câu hỏi, Top-3, gold IDs, nhận xét về các trường hợp thất bại và điểm tổng.

### 8.4. Unit / integration tests tối thiểu

1. Đọc PDF nhiều trang; số trang trả về 1-based và đúng phạm vi `--pages 8-31`.
2. Text tiếng Việt không lỗi mã hóa, không mất chữ hoặc ký tự khi chuẩn hóa; xử lý trang không có text.
3. Chunking không tạo chunk rỗng, không lặp vô hạn, giữ chunk cuối, ID ổn định, overlap đúng mục tiêu.
4. Embedding E5 luôn có prefix `passage:`/`query:` và normalize; không vượt giới hạn token mà im lặng.
5. `embeddings.npy` có shape/dtype hợp lệ, metadata trùng index.
6. Retriever trả Top-k đúng số lượng, sắp theo score giảm dần; đủ năm trường và đúng nguồn/trang.
7. Query trắng, top_k <= 0, file/index thiếu hoặc hỏng: thông báo lỗi dễ hiểu.
8. Chạy 3 câu thực trên PDF, ghi lại output và Hit@3 thật.

## 9. CLI và lệnh chạy bắt buộc

```bash
# Từ thư mục gốc rag-demo/
python -m venv .venv
# Kích hoạt .venv theo Windows/macOS/Linux (hướng dẫn cụ thể trong README)
python -m pip install -r requirements.txt

# 1) Pilot: chỉ trang 8–31
python -m src.build_index --input "data/so_tay_sinh_vien_k50.pdf" --out data/processed --pages 8-31

# 2) Top-3 retrieval thực tế
python -m src.demo_retrieve --question "Sinh viên chính quy bắt đầu tự đăng ký học phần từ học kỳ nào?" --top-k 3

# 3) Chạy bộ 3 câu CV14
python -m evaluation.run_evaluation

# 4) Unit tests
pytest -q

# 5) Mở rộng sau khi pilot đạt: xử lý toàn bộ 220 trang (xây lại index)
python -m src.build_index --input "data/so_tay_sinh_vien_k50.pdf" --out data/processed
```

Nếu demo real model cần Internet lần đầu, README phải nêu rõ. Các unit test phải chạy bằng fixtures/mocks khi thích hợp để không download model liên tục; một bài smoke/integration dùng model thật có thể được gắn nhãn riêng và báo rõ điều kiện chạy.

## 10. Hợp đồng bàn giao cho Code 2

Code 2 sẽ chịu trách nhiệm giao diện, prompt, LLM. Code 1 chỉ cần cung cấp import:

```python
from src.retriever import retrieve

chunks = retrieve("Học phần tiên quyết là gì?", top_k=3)
for item in chunks:
    print(item["text"], item["source"], item["page"], item["score"])
```

**Không yêu cầu Code 2:** mở PDF, cắt chunk, gọi embedding passage hoặc tái tạo index trên mỗi câu hỏi. File `docs/code2_integration.md` phải giải thích cách sử dụng API, schema, quy ước page 1-based, setup index và xử lý lỗi. Nếu Code 2 chạy khác máy, hướng dẫn copy artifact hoặc build lại index và tải model một lần.

## 11. Definition of Done / điều kiện nghiệm thu cuối cùng

- [ ] Đúng **một** nguồn PDF được chốt và đặt ở `data/so_tay_sinh_vien_k50.pdf`.
- [ ] Pilot **trang 8–31** trích xuất được tiếng Việt, logs rõ ràng; chunks giữ đúng source/page.
- [ ] `chunks.json`, `embeddings.npy`, `index_meta.json` là output sinh **bằng chạy thật**.
- [ ] Model E5 dùng đúng prefix, có bảo vệ giới hạn token, embeddings được lưu và reuse.
- [ ] API `retrieve(question, top_k=3)` có đúng năm khóa, Top-3 score giảm dần, không hard-code.
- [ ] Có ba câu Q01–Q03, gold evidence/IDs được kiểm tra sau khi build, kết quả thực và Hit@3.
- [ ] Có tests, README, `docs/code2_integration.md`, `docs/ingestion_notes.md`, log và câu lệnh tái tạo.
- [ ] Có giải thích những giới hạn PDF như bảng biểu, scan, sự khác nhau giữa các quy chế trong sổ tay.
- [ ] Code 2 có thể import module `src.retriever` và dùng index có sẵn.
- [ ] Mọi lỗi, test chưa chạy và kết quả chưa đạt được liệt kê trung thực.

## 12. Chỉ thị triển khai cho trợ lý (đọc trước khi code)

1. **Trước khi code:** xác nhận đã nhận file PDF, kiểm tra `PdfReader` đọc được; báo cáo số trang và preview text trang 8, 9, 15. Không cần hỏi lại nguồn dữ liệu vì đã chốt.
2. **CV12:** viết loader/chunker và unit tests trước; chạy thử trang 8–31, báo thống kê thật, lưu `chunks.json`.
3. **CV13:** build embedding + index và API `retrieve()`, chạy thử câu Q01, xuất Top-3 thật.
4. **CV14:** tạo Q01–Q03 từ nguồn thật, gán gold IDs sau khi đọc chunks, chạy evaluation và tests, viết tài liệu bàn giao.
5. **Không làm ngoài phạm vi** CV15/CV16; không tự thêm LangChain, FAISS, Chroma, OCR, Streamlit, LLM/API key hay nhiều tài liệu chỉ vì tiện.
6. Không đổi schema/hợp đồng API nếu chưa có sự đồng ý. Có lỗi thì giải thích nguyên nhân và thay đổi tối thiểu.
7. Khi bàn giao, báo: cây thư mục thực tế; danh sách file đã viết; lệnh chạy; output thật của `pytest`; thống kê chunks; Top-3 của cả ba câu; Hit@3; những điểm còn lỗi/chưa kiểm chứng.

**Phụ lục kỹ thuật tham khảo:**
- `pypdf`: https://pypdf.readthedocs.io/en/stable/user/extract-text.html
- `sentence-transformers`: https://www.sbert.net/docs/package_reference/sentence_transformer/model.html
- Model E5: https://huggingface.co/intfloat/multilingual-e5-small

**Kết luận:** Hoàn tất CV12 → CV13 → CV14 trên `SO TAY SINH VIEN K50.pdf` (thử trang 8–31 trước). Chỉ bàn giao Code 2 khi API `retrieve` và index hoạt động thật và có kết quả đánh giá minh bạch.
