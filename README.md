# K50 AI — Hỏi đáp Sổ tay sinh viên

**K50 AI** là ứng dụng tra cứu bằng tiếng Việt dựa trên **Sổ tay sinh viên Khóa 50 của Trường Đại học Sư phạm TP. Hồ Chí Minh**. Bạn đặt câu hỏi, hệ thống tìm bằng chứng trong PDF 220 trang rồi tạo câu trả lời kèm trang nguồn để đối chiếu.

Dự án sử dụng **RAG**: model trả lời dựa trên tài liệu được tìm thấy, thay vì chỉ dựa vào kiến thức có sẵn. Đây là **bản demo**, không phải sản phẩm chính thức của nhà trường; câu trả lời vẫn có thể sai hoặc thiếu điều kiện.

![Giao diện chat và xem PDF](docs/ui_workbench/screenshots/desktop_light.png)

## Dự án có những chức năng gì?

- Nhập câu hỏi tự nhiên bằng tiếng Việt, có câu hỏi gợi ý.
- Chat và quản lý nhiều cuộc trò chuyện trong một phiên trình duyệt.
- Tìm kiếm kết hợp theo ý nghĩa và từ khóa, tổng hợp từ nhiều đoạn tài liệu.
- Hiển thị nguồn, đoạn trích và mở đúng trang PDF vật lý.
- Điều hướng/zoom PDF, tải trang, sao chép câu trả lời.
- Giao diện sáng/tối, bố cục desktop và mobile, chế độ debug cho người phát triển.
- Thông báo khi chỉ trả lời được một phần hoặc chưa đủ bằng chứng.

## Hệ thống hoạt động như thế nào?

```text
Câu hỏi tiếng Việt
    ↓
Phân tích câu hỏi → Tìm nguồn trong PDF → Chọn đoạn liên quan
    ↓
Qwen chọn đủ đoạn trả lời → Kiểm tra từng ý → Chat + trang PDF nguồn
```

| Thành phần | Vai trò |
|---|---|
| Streamlit | Giao diện chat và panel PDF. |
| Multilingual E5-small + BM25 | Tìm đoạn văn theo ý nghĩa và từ khóa. |
| RRF và reranking | Kết hợp và sắp xếp kết quả tìm kiếm. |
| Qwen2.5 3B qua Ollama | Chọn các đoạn trả lời và kiểm tra độ đầy đủ trên máy local. |
| Checklist, kiểm tra trích dẫn và NLI | Kiểm tra ý được hỏi, chứng cứ và các câu diễn giải. |
| PDF và index có sẵn | Nguồn kiến thức của ứng dụng. |

Không cần API key để chạy cấu hình local này. Internet cần cho lần đầu cài thư viện/tải model; sau khi đã đủ cache, ứng dụng xử lý câu hỏi cục bộ. Các model kiểm chứng cũng có thể đánh giá sai, nên nguồn trích dẫn vẫn cần được người dùng kiểm tra.

Để tránh model nhỏ làm mất điều kiện khi viết lại, câu trả lời mặc định sử dụng **các đoạn trích đã được chọn và kiểm chứng**. Hệ thống kiểm tra riêng những ý như mức tiền, số tháng, tín chỉ và thông tin cá nhân; khi còn thiếu sẽ hiển thị phần chưa xác minh. Chi tiết đợt sửa chất lượng: [báo cáo](docs/answer_quality.md).

## Hướng dẫn cài đặt trên Windows

Các lệnh bên dưới dành cho **PowerShell** hoặc **Windows Terminal → PowerShell**. Chạy từng bước, chỉ chuyển sang bước tiếp theo khi bước trước thành công.

### Bước 1 — Cài phần mềm cần thiết

Cài từ nguồn chính thức:

- [Python cho Windows](https://www.python.org/downloads/windows/): dùng **Python 3.11** cho các lệnh trong hướng dẫn; cần có lệnh `py`.
- [Git cho Windows](https://git-scm.com/install/windows): tải mã nguồn từ GitHub.
- [Ollama cho Windows](https://ollama.com/download/windows): chạy Qwen trên máy.

Sau khi cài, đóng và mở lại PowerShell, rồi kiểm tra:

```powershell
py -3.11 --version
git --version
ollama --version
```

Ollama hỗ trợ Windows 10 22H2 trở lên theo [tài liệu chính thức](https://docs.ollama.com/windows). Mở ứng dụng Ollama từ Start Menu và để ứng dụng chạy nền.

### Bước 2 — Tải mã nguồn

Bản giao diện hiện tại nằm trên nhánh `feature/streamlit-modern-research-workbench`:

```powershell
git clone --branch feature/streamlit-modern-research-workbench https://github.com/vanminh92/rag-module.git
cd rag-module
```

Nếu đã có mã nguồn trên máy, bỏ qua clone và dùng `cd` đến thư mục dự án. Ví dụ `cd "D:\DuAn\rag-module"` — thay bằng đường dẫn thật của bạn. Thư mục đúng phải có `README.md`, `requirements.txt` và `streamlit_qa_app.py`.

### Bước 3 — Tạo môi trường và cài thư viện

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Hướng dẫn gọi thẳng Python trong `.venv`, **không cần chạy `Activate.ps1`** hoặc đổi Execution Policy. Không copy `.venv` từ máy khác, đặc biệt từ macOS sang Windows.

### Bước 4 — Tải model một lần

Giữ Ollama chạy, rồi thực hiện:

```powershell
ollama pull qwen2.5:3b
.\.venv\Scripts\python.exe -m src.entailment --download
```

Lệnh đầu tải model tạo câu trả lời; lệnh sau chuẩn bị model kiểm tra bằng chứng. Quá trình có thể mất vài phút và cần dung lượng lưu trữ cho model. E5 cũng cần được tải vào cache ở lần truy xuất đầu tiên.

PDF và index đã có trong repository. **Không cần build lại index để chạy ứng dụng.**

### Bước 5 — Mở ứng dụng

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_qa_app.py
```

Mở địa chỉ Streamlit in trong Terminal, thường là **http://localhost:8501**. Giữ cửa sổ Terminal và Ollama chạy khi sử dụng. Nhấn **Ctrl+C** trong Terminal để dừng ứng dụng.

## Những lần chạy tiếp theo trên Windows

Không cần cài lại thư viện hoặc tải lại model mỗi lần:

1. Mở **Ollama** từ Start Menu.
2. Mở PowerShell, đi đến thư mục dự án.
3. Chạy:

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_qa_app.py
```

## Cách sử dụng

1. **Đặt câu hỏi:** nhập vào ô chat và nhấn Enter hoặc nút gửi. Ví dụ: “Sinh viên đại học chính quy tự đăng ký học phần từ học kỳ nào?”. Nhấn câu gợi ý cũng gửi một câu hỏi thật.
2. **Đọc phản hồi:** chú ý cảnh báo trả lời một phần và mục chưa xác minh. Không coi nhãn complete là bảo đảm câu trả lời tuyệt đối chính xác.
3. **Đối chiếu nguồn:** nhấn chip `[1] Sổ tay K50 · Trang …`. Panel mở đúng tài liệu và trang vật lý trong PDF, hiển thị đoạn văn bản làm bằng chứng.
4. **Đọc PDF:** dùng Trước/Sau, nhập số trang hoặc chọn zoom. Nếu xem trang khác trang trích dẫn, UI nêu rõ sự khác nhau và có nút quay về trang nguồn.
5. **Khi PDF lỗi:** chọn Bản dự phòng, Chỉ văn bản hoặc Tải trang này. Bản dự phòng là một trang được trích từ PDF gốc, không sửa tài liệu gốc.
6. **Quản lý chat:** dùng Trò chuyện mới, chọn lịch sử bên trái hoặc xóa với xác nhận. Lịch sử chỉ lưu trong phiên browser và có thể mất khi refresh/restart.
7. **Đổi giao diện:** menu **⋮ → Light / Dark**. Trên mobile, bằng chứng mở ở màn hình riêng có nút Quay lại hội thoại.

Các thao tác xem nguồn, chuyển trang PDF, đổi theme hoặc đổi chat không gọi lại LLM. Mỗi câu hỏi được tra cứu **độc lập**; khi hỏi tiếp, hãy nhắc lại chủ đề vì UI chưa thêm lịch sử vào prompt. Phản hồi có thể mất hàng chục giây; lần đầu nạp model thường lâu hơn.

## Lỗi thường gặp trên Windows

| Hiện tượng | Cách xử lý |
|---|---|
| Không nhận lệnh `py`, `git` hoặc `ollama` | Kiểm tra phần mềm đã cài, rồi đóng/mở lại PowerShell. Với Python, kiểm tra đã cài bản 3.11 và launcher. |
| `py -3.11` báo không có Python phù hợp | Cài Python 3.11 trước khi tạo `.venv`. |
| Không thấy `.venv\Scripts\python.exe` | Kiểm tra đang ở thư mục gốc dự án và đã chạy bước tạo `.venv`. |
| Báo thiếu thư viện | Chạy lại `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. |
| Không kết nối được Ollama | Mở ứng dụng Ollama và nhấn Kiểm tra lại Ollama trong sidebar. Nếu chạy dịch vụ bằng terminal thay vì ứng dụng, dùng `ollama serve` trong một cửa sổ riêng. |
| Không có model Qwen | Chạy `ollama pull qwen2.5:3b`; có thể kiểm tra model đã tải bằng `ollama list`. |
| Thiếu model NLI | Chạy `.\.venv\Scripts\python.exe -m src.entailment --download`. |
| Cổng 8501 đang dùng | Thêm `--server.port 8502` vào cuối lệnh Streamlit và mở địa chỉ mới được in ra. |
| PDF không hiển thị | Chọn Bản dự phòng hoặc tải trang; vẫn có thể đọc đoạn nguồn. |
| Thiếu/hỏng PDF hoặc index | Kiểm tra `data/so_tay_sinh_vien_k50.pdf` và `data/processed/`; xem hướng dẫn phát triển bên dưới. Không xóa index để sửa lỗi UI. |

## Cấu trúc dự án

```text
streamlit_qa_app.py       Điểm khởi chạy ứng dụng
ui/                      Chat, history, theme, nguồn và viewer PDF
src/                     Pipeline tìm kiếm, tạo và kiểm tra câu trả lời
data/                    PDF gốc và index đã chuẩn bị
tests/                   Kiểm thử tự động
evaluation/              Bộ câu hỏi, công cụ đánh giá và kết quả cuối
docs/                    Tài liệu kỹ thuật, kết quả và ảnh giao diện
requirements.txt         Thư viện chạy ứng dụng
requirements-ui-test.txt  Thư viện bổ sung để kiểm thử browser
```

## Kiểm chứng và giới hạn

Đợt sửa chất lượng đã đạt **140 tests** gồm E5/NLI thật và CV14 **3/3**. Bản giao diện trước đó đã đạt browser live **10/10** trên môi trường macOS/Edge. **Chưa chạy kiểm thử trực tiếp trên Windows trong phiên phát triển này**; hướng dẫn Windows dùng các entrypoint Python hiện có. Script chạy trọn bộ benchmark `run_final_suite` dùng `fcntl`, chỉ dành cho macOS/Linux; Windows có thể chạy từng lệnh benchmark theo tài liệu đánh giá.

Bộ đánh giá có 70 câu, chia dev/test. Kết quả **22/30** câu test đúng và đủ trong `evaluation/final_v3/` thuộc bản trước khi sửa chất lượng; kết quả chạy lại được ghi riêng trong [báo cáo mới](docs/answer_quality.md). Bộ cũ hiện được dùng để kiểm tra hồi quy, không phải kiểm định độc lập. Ứng dụng không có dữ liệu cá nhân/thời gian thực ngoài PDF, chưa có history bền vững, memory trong prompt hoặc highlight tọa độ thật trên PDF.

## Đọc thêm

- [Hướng dẫn phát triển, CLI và build index](docs/development.md)
- [Chi tiết UI và ảnh desktop/mobile](docs/ui_workbench/README.md)
- [Thiết kế pipeline RAG](docs/open_domain_rag.md)
- [API retrieval cho Code 2](docs/code2_integration.md)
- [Kết quả chất lượng và các ca lỗi](docs/upgrade_report.md)
- [Chạy benchmark và định nghĩa chỉ số](evaluation/README.md)

<details>
<summary>Chạy trên macOS nếu đã có môi trường và model</summary>

Tại thư mục gốc dự án:

```bash
open -a Ollama
.venv/bin/python -m streamlit run streamlit_qa_app.py
```

Nếu chưa cài môi trường: tạo bằng `python3.11 -m venv .venv`, cài `requirements.txt`, tải Qwen và chuẩn bị NLI theo các bước tương ứng phía trên.

</details>
