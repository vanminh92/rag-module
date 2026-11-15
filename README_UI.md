# K50 AI — Modern Chat + PDF Research Workbench

Giao diện mới cho pipeline RAG đang có, theo đặc tả/prototype UI/UX v1.0. Đây là **demo tra cứu Sổ tay sinh viên K50**, không phải sản phẩm chính thức của nhà trường. Giao diện không đổi prompt, Qwen, E5, retrieval, chunking hoặc index.

## Chạy trên MacBook

Tại gốc repository, dùng môi trường Python 3.11+ hiện có:

```bash
.venv/bin/python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
.venv/bin/python -m streamlit run streamlit_qa_app.py
```

Giữ ứng dụng Ollama chạy. Mở địa chỉ local mà Streamlit in ra, thường là `http://localhost:8501`. Nếu máy chưa có môi trường, chạy `python3.11 -m venv .venv` trước. Với máy mới chưa có cache NLI của pipeline hiện hành, chuẩn bị một lần bằng `.venv/bin/python -m src.entailment --download`, theo README RAG; UI không tự tải model mới hoặc rebuild index.

Các dependency UI được cố định: Streamlit 1.67.0, streamlit-pdf-viewer 0.0.30 và streamlit-pdf 2.1.0. Không cần Node/npm để chạy UI. Playwright chỉ dùng khi kiểm thử trình duyệt.

## Sử dụng

1. Nhập câu hỏi tự nhiên vào ô chat hoặc nhấn câu hỏi gợi ý. Mỗi lần gửi tạo đúng một yêu cầu tới pipeline hiện tại. Nút gợi ý **gửi câu hỏi**, không chèn một câu trả lời mẫu.
2. Nhấn chip `[n] Sổ tay K50 · Trang X` để mở bằng chứng. Số trang lấy từ metadata nguồn đã đối chiếu với index; không lấy từ nội dung model viết.
3. Desktop từ 1280px có chat và panel PDF cạnh nhau. Màn hình vừa mở bằng chứng trong dialog; mobile dưới 768px có màn hình PDF riêng với nút **Quay lại hội thoại**.
4. Trong PDF, dùng Trước/Sau, nhập số trang, chọn zoom hoặc tải trang. Nếu xem trang khác trang trích dẫn, UI nêu rõ sự khác nhau và có nút về trang trích dẫn. Đoạn nguồn không bị đổi thành nội dung trang vừa chuyển.
5. Chọn **Bản dự phòng** nếu viewer chính không hiển thị. Bản này chỉ chứa trang đã chọn, với nhãn `Trang X của PDF gốc`; tải xuống cũng là trang vật lý đó. **Chỉ văn bản** vẫn cho đọc đoạn nguồn và tải PDF.
6. **Sao chép** ghi câu trả lời thật vào clipboard. Nếu trình duyệt chặn clipboard, component hiển thị vùng văn bản có thể chọn và hướng dẫn ⌘C/Ctrl+C.
7. **Trò chuyện mới**, chọn lịch sử, hoặc xóa cuộc trò chuyện với xác nhận. Các cuộc trò chuyện không trộn nội dung.
8. Đổi sáng/tối qua nút **⋮ → Light / Dark** chính thức của Streamlit. Theme có palette riêng cho light/dark và sidebar; không dùng CSS để giả đổi theme.

Lịch sử nằm trong `st.session_state` của phiên trình duyệt. Không hứa lưu sau refresh/restart; không có database lịch sử hoặc chia sẻ giữa người dùng. Các câu hỏi vẫn được gửi **độc lập** như pipeline hiện tại; UI không thêm lịch sử vào prompt để giải quyết đại từ hoặc câu hỏi nối tiếp thiếu chủ đề.

## Nguồn và trạng thái

- UI giữ nguyên câu trả lời, status, warnings và debug do pipeline trả về; không rút gọn hay viết lại nội dung bằng một model khác.
- Chỉ gắn chip ở mức từng luận điểm khi backend thực sự cung cấp claim → source và quote đối chiếu được với đoạn nguồn. Với phản hồi không có mapping, dùng **Nguồn được sử dụng** ở mức toàn câu trả lời.
- Loại liên kết sai `chunk_id`, sai file, sai trang hoặc text không khớp index. Dedupe cùng `chunk_id`, giữ các đoạn khác nhau trên cùng trang. UI không bổ sung nguồn bằng phỏng đoán.
- PDF phải khớp hash nguồn trong `index_meta.json`; nguồn đã lưu cũng gắn phiên bản PDF. Nếu tệp khác/hỏng/không mở được, không hiển thị nhầm tài liệu; vẫn giữ đoạn nguồn đã lưu để đọc.
- `partial` có cảnh báo trả lời một phần và phần chưa xác minh; `insufficient` báo chưa đủ bằng chứng. UI không nâng trạng thái partial thành complete.
- Không gọi lại pipeline khi chọn nguồn, đổi trang/zoom/viewer/theme, mở debug, tải/copy hoặc đổi chat. Cache PDF chỉ chứa tài liệu công khai, không chứa lịch sử chat.

## Ollama, lỗi và Developer mode

Badge kết nối dựa trên `Ollama /api/tags`, timeout 1,5 giây, cache tối đa 15 giây; “đã kết nối” không khẳng định model đã nằm trong RAM. Nút **Kiểm tra lại Ollama** trong sidebar làm mới phép kiểm tra, không sinh câu trả lời.

Lỗi Ollama offline, thiếu model, index thiếu/hỏng hoặc viewer lỗi có thông báo riêng; câu hỏi và lịch sử vẫn còn. Không tự retry LLM hoặc tự build index. Có thể gửi lại bằng một câu hỏi mới sau khi xử lý lỗi.

**Developer mode** tắt mặc định, hiển thị kết quả đã lưu: truy vấn, ứng viên, RRF/reranking, ngữ cảnh, phản hồi model/kiểm chứng, metadata và thời gian thực nếu backend cung cấp. Score chỉ có trong debug, không được gọi là độ tin cậy hoặc xác suất đúng. Bộ đếm trong sidebar là **số lần gửi câu hỏi đến adapter backend**, không phải số lượt nội bộ mà pipeline gọi Qwen. Trace lỗi kỹ thuật chỉ ở terminal/debug.

Backend hiện tại không có callback tiến độ từng giai đoạn; UI dùng một trạng thái thật “Đang tìm nguồn, tổng hợp và kiểm tra bằng chứng…”. Không giả streaming hoặc dựng thời gian cho từng bước.

## Kiểm thử và ảnh chụp

```bash
# Unit/UI và regression, có E5/NLI thật từ cache.
.venv/bin/python -m pytest -q --run-model
.venv/bin/python -m evaluation.run_evaluation --out docs/ui_workbench/cv14_recheck.json

# Browser: Edge thật, app thật, Ollama thật; không seed câu trả lời.
.venv/bin/python -m pip install -r requirements-ui-test.txt
.venv/bin/python scripts/ui_browser_check.py
```

Browser check tự mở server local riêng, thực hiện tương tác và chụp ảnh, rồi dừng server đó. Mặc định dùng Microsoft Edge ở `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge`; dùng `--browser /path/to/chromium` và `--port 8504` nếu cần. Không cần tải thêm Chromium nếu đã có Edge.

Ảnh và kết quả cuối: [docs/ui_workbench/report.md](docs/ui_workbench/report.md), [screenshots](docs/ui_workbench/screenshots/), [browser_checks.json](docs/ui_workbench/browser_checks.json). Các ca lỗi có mock backend trong unit tests không được trình bày như ảnh câu trả lời thật. Script browser không dùng mock và không sửa DOM để thay nội dung hiển thị.

## Giới hạn chưa hỗ trợ

- Chưa highlight tọa độ thật trong PDF vì backend không có bounding boxes; không vẽ highlight giả.
- Chưa có history bền vững, đăng nhập, sync đa thiết bị hoặc xuất toàn bộ cuộc trò chuyện.
- Chưa có memory hội thoại trong prompt, regenerate, streaming token, upload PDF mới hoặc annotation PDF.
- UI không sửa các lỗi trả lời/độ phủ/phạm vi nguồn còn tồn tại của backend; xem [báo cáo RAG](docs/upgrade_report.md).
- Theme dùng menu native, không có công tắc theme riêng do Python không có API công khai đổi theme cho từng phiên.
- Đã kiểm tra desktop/mobile bằng Edge với viewport thật. Chưa kiểm tra máy iOS/Android vật lý hoặc mọi phiên bản Safari/Chrome. Nội dung PDF được hiển thị như tài liệu gốc, không phải chế độ dark đảo màu giấy.

## Quyết định kỹ thuật và nguồn tham khảo

`streamlit-pdf-viewer` render **một trang vật lý** bằng `pages_to_render=[page]`, text layer bật để chọn văn bản, không tạo annotations. Không dùng `scroll_to_page` vì `scrollIntoView` của viewer có thể cuộn cả ancestor ngoài iframe; khi chỉ render một trang thì chính trang đó đã là trang mở. [API upstream](https://github.com/ScienciaLAB/streamlit-pdf-viewer), [giấy phép Apache-2.0 upstream](https://github.com/ScienciaLAB/streamlit-pdf-viewer/blob/main/LICENSE). Wheel 0.0.30 không khai báo License-Expression, nên phần giấy phép được đối chiếu ở nguồn upstream.

Fallback dùng [st.pdf](https://docs.streamlit.io/develop/api-reference/media/st.pdf) với bản một trang tạo trong RAM bằng pypdf; không ghi lại PDF gốc. Native `st.pdf` không có đối số nhảy trang, nên không dựa vào fragment `#page=` trên đường dẫn local.

Theme dùng [cấu hình native](https://docs.streamlit.io/develop/api-reference/configuration/config.toml). Hai component nhỏ dùng [API v2 chính thức](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component) để nhận breakpoint/chiều cao viewport và copy clipboard; không nhúng văn bản PDF/LLM vào HTML/JS. CSS chủ yếu dựa trên key do app sở hữu; có một selector testing hook của Streamlit để chỉnh padding trang, được kiểm tra với phiên bản pin 1.67.0.
