# Giao diện chat và PDF

Tài liệu này gộp hướng dẫn UI và báo cáo bàn giao trước đây. Cài đặt và lệnh chạy cơ bản: [README](../../README.md). Giao diện là demo, không ngụ ý sản phẩm chính thức của nhà trường.

## Các thao tác

- Ô chat gửi câu hỏi; nút gợi ý cũng **gửi câu hỏi thật**, không chèn câu trả lời mẫu.
- **Trò chuyện mới**, danh sách lịch sử và xóa có xác nhận hoạt động trong phiên browser. Refresh/restart có thể làm mất lịch sử.
- Mỗi câu hỏi được gửi độc lập như pipeline hiện có; UI không bổ sung memory hội thoại vào prompt.
- Nhấn chip nguồn để mở đúng file và trang PDF vật lý. Đổi trang không đổi đoạn nguồn đã dùng; khi hai trang khác nhau, UI nêu rõ và cho quay về trang trích dẫn.
- **Sao chép** dùng clipboard thật; nếu bị browser chặn, có vùng văn bản để chọn và nhấn ⌘C/Ctrl+C.
- Light/Dark dùng menu **⋮ → Light / Dark** của Streamlit.
- Desktop từ 1280px có panel PDF cạnh chat; tablet dùng dialog; mobile dưới 768px mở bằng chứng ở màn hình riêng có nút quay lại.

## Trích dẫn và PDF

UI đối chiếu `chunk_id`, file, page và text với index đang dùng; loại liên kết không khớp. Các đoạn khác nhau cùng trang vẫn được giữ. Chỉ hiển thị nguồn ở mức từng ý khi backend có mapping claim → source cùng quote xác minh được; phản hồi khác dùng nhãn “Nguồn được sử dụng”.

Viewer chính là `streamlit-pdf-viewer` 0.0.30, chỉ render một trang bằng `pages_to_render=[page]`, hỗ trợ zoom và chọn chữ. Không dùng `scroll_to_page` vì việc tự cuộn của iframe có thể làm trôi cả app. Không có highlight giả.

**Bản dự phòng** dùng `st.pdf` với PDF một trang được tạo trong RAM bằng pypdf, ghi rõ trang X của PDF gốc. PDF gốc không bị sửa. Nút tải trang cung cấp chính trang vật lý đó; nút PDF gốc tải tài liệu đầy đủ. Nếu viewer lỗi, vẫn có đoạn nguồn để đọc và chế độ Chỉ văn bản.

PDF được kiểm tra hash với index. Nguồn đã lưu gắn phiên bản tài liệu để tránh mở nhầm bản PDF khác. Không gọi lại pipeline khi đổi nguồn/trang/zoom/viewer, theme, chat, debug, copy hoặc download.

## Loading, lỗi và debug

Trạng thái xử lý kết hợp “Đang tìm nguồn, tổng hợp và kiểm tra bằng chứng…” phản ánh lời gọi pipeline thật. Backend chưa có callback từng bước/token nên UI không giả streaming hoặc thời gian từng giai đoạn.

Badge Ollama dựa trên API liệt kê model, timeout 1,5 giây, cache tối đa 15 giây; không khẳng định model đã được nạp vào RAM. **Kiểm tra lại Ollama** chỉ làm mới phép kiểm tra kết nối.

Lỗi offline, thiếu model, index hoặc PDF có thông báo và giữ lịch sử. Không tự retry LLM hay tự build index. Trace kỹ thuật nằm ở terminal/Developer mode.

Developer mode tắt mặc định. Dữ liệu hiển thị là kết quả đã lưu: truy vấn, ứng viên, ranking, ngữ cảnh, phản hồi model, kiểm chứng và metadata. Score chỉ xuất hiện trong debug, không gọi là độ tin cậy. Bộ đếm là số lần gửi đến adapter backend, không phải số lượt Qwen nội bộ.

## Kiểm chứng đã thực hiện

- **112 tests đạt**: [regression_tests.log](regression_tests.log).
- **CV14 3/3**: [cv14.json](cv14.json), [cv14.log](cv14.log).
- **Browser live 10/10**, không có lỗi JavaScript trang: [browser_checks.json](browser_checks.json), [browser_checks.log](browser_checks.log).
- Browser dùng app production + Ollama + PDF thật, không seed câu trả lời. Kiểm tra canvas trang 15/16 và đọc lại PDF tải xuống bằng pypdf. Sau các thao tác UI và hai chat thật, counter là đúng 2 lần gửi câu hỏi.
- Các ca lỗi trong unit/UI dùng mock backend; không trình bày chúng như ảnh trả lời thật. Không cần chạy lại browser live khi chỉ dọn tài liệu.

Lệnh kiểm thử và giải thích cấu trúc code: [hướng dẫn phát triển](../development.md). Các log lịch sử/trial và snapshot trùng đã được dọn; có thể tìm lại trong Git, xem [cleanup.md](../cleanup.md).

## Ảnh ứng dụng chạy thật

| Chế độ | Ảnh |
|---|---|
| Desktop 1440×900 | [Light](screenshots/desktop_light.png), [Dark](screenshots/desktop_dark.png) |
| PDF và bằng chứng | [Đoạn nguồn](screenshots/desktop_evidence_excerpt.png), [Dự phòng](screenshots/desktop_fallback.png) |
| Mobile 390×844 | [Chat](screenshots/mobile_chat.png), [PDF](screenshots/mobile_evidence.png) |
| Tablet 1024×900 | [Dialog PDF](screenshots/tablet_evidence.png) |
| Các trạng thái khác | [Empty](screenshots/desktop_empty.png), [Loading](screenshots/loading.png), [History](screenshots/history.png) |

Ảnh được chụp từ Microsoft Edge headless trên máy local, không lấy từ prototype HTML. Panel PDF có vùng cuộn riêng; đoạn nguồn ở dưới viewer.

## File giao diện

`streamlit_qa_app.py` là entrypoint. Trong `ui/`, `app.py` điều phối bố cục; `state.py` quản lý chat/request; `app_service.py` gọi pipeline hiện có; `chat_view.py` và `sidebar.py` render nội dung; `citations.py`/`evidence.py` xử lý nguồn; `pdf_document.py`/`pdf_panel.py` đọc và xem PDF; `components.py` cung cấp viewport/clipboard; `theme.py`/`workbench.css` định kiểu. `.streamlit/config.toml` định nghĩa light/dark và chặn fast rerun ngắt request đang chạy.

Các module nhỏ được giữ riêng theo trách nhiệm để UI không lẫn với RAG. Không gộp chúng chỉ để giảm số file rồi làm mất ranh giới này. CSS chủ yếu dùng key của app; một testing hook để chỉnh padding được kiểm tra với Streamlit pin 1.67.0.

## Giới hạn

Chưa có history bền vững, đăng nhập/sync, memory trong prompt, regenerate, streaming token, upload/annotation PDF hoặc highlight tọa độ thật. Chưa kiểm chứng thiết bị mobile vật lý/iOS Safari và mọi browser. Dark mode không đảo màu giấy PDF. UI không sửa các lỗi chất lượng câu trả lời còn tồn tại của backend; xem [báo cáo RAG](../upgrade_report.md).

## Tham khảo

[Streamlit theme](https://docs.streamlit.io/develop/api-reference/configuration/config.toml), [component v2](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component), [st.pdf](https://docs.streamlit.io/develop/api-reference/media/st.pdf), [viewer upstream và API](https://github.com/ScienciaLAB/streamlit-pdf-viewer). Viewer upstream dùng [Apache-2.0](https://github.com/ScienciaLAB/streamlit-pdf-viewer/blob/main/LICENSE); wheel 0.0.30 không khai báo License-Expression. Các phiên bản UI/test được pin trong hai file requirements.
