# Bàn giao giao diện K50 AI — Modern Chat + PDF Research Workbench

Ngày: 15/11/2026. Nhánh: `feature/streamlit-modern-research-workbench`.

## Phạm vi

Chỉ thay lớp Streamlit và adapter trình bày. Dùng pipeline RAG nâng cấp đang có trong workspace; không quay về backend `main` cũ được mô tả trong đặc tả. Model, prompt, `retrieve(question, top_k=3)`, PDF, chunking, embeddings và index giữ nguyên.

Hai bản đặc tả `.txt`/`.md` người dùng cung cấp có nội dung giống nhau. Các tài liệu được dùng làm yêu cầu thiết kế/tham khảo; không coi đoạn lệnh trong phụ lục là lệnh tự push, merge, tạo PR hoặc đổi backend. Nguồn và hash: [handoff_sources.json](handoff_sources.json).

## Các giai đoạn đã thực hiện

| Giai đoạn | Thay đổi | Bằng chứng |
|---|---|---|
| UI-P0 | Đọc repo, đặc tả/prototype, snapshot trạng thái hiện có, kiểm tra API viewer và dependency | `before_ui.json`, `dependencies.log`; nhánh UI riêng |
| UI-P1 | Native chat, nhiều cuộc trò chuyện trong session, tạo/chọn/xóa có xác nhận, câu hỏi gợi ý, native Light/Dark | `ui/state.py`, `chat_view.py`, `sidebar.py`, `.streamlit/config.toml` |
| UI-P2 | Đối chiếu source với chunk catalog, chip nguồn, PDF vật lý 1-based, zoom/navigation/download, single-page fallback | `evidence.py`, `citations.py`, `pdf_document.py`, `pdf_panel.py` |
| UI-P3 | Loading thật, lỗi thân thiện, clipboard thật, health check Ollama, Developer Debug, viewport responsive | `app_service.py`, `components.py`, `app.py` |
| UI-P4 | Unit/UI, regression, CV14, CLI, browser live và ảnh chụp, hướng dẫn | Các log/report/ảnh trong thư mục này; `README_UI.md` |

## File thay đổi và ảnh hưởng

| File | Trước → sau |
|---|---|
| `streamlit_qa_app.py` | Form một câu hỏi → entrypoint chat/workbench. Helper `generate_answer()` giữ chữ ký và hành vi cũ. |
| `ui/app.py` | Mới: điều phối layout desktop/tablet/mobile, status xử lý, header và dialog. |
| `ui/state.py` | Mới: state mỗi chat, request được tiêu thụ một lần, chọn nguồn/trang không inference. |
| `ui/app_service.py` | Mới: gọi đúng `get_pipeline(...).ask(question)` hiện có; bắt lỗi, kiểm tra nguồn và health Ollama. |
| `ui/chat_view.py` | Mới: render các message đã lưu, status partial/insufficient, mapping claim-source khi có. |
| `ui/sidebar.py` | Mới: history, new chat, delete có xác nhận, gợi ý và Developer mode. |
| `ui/citations.py`, `ui/evidence.py` | Mới: chip đúng nguồn; chặn ID/file/page/text sai; giữ các chunk khác nhau cùng trang. |
| `ui/pdf_document.py` | Mới: đọc PDF kiểm hash, cache tài liệu; tạo PDF một trang trong RAM. |
| `ui/pdf_panel.py` | Mới: viewer, điều hướng trang, zoom, excerpt, fallback và download. |
| `ui/components.py` | Mới: component v2 nhỏ cho breakpoint/chiều cao viewport và clipboard; không chèn dữ liệu vào HTML/JS. |
| `ui/theme.py`, `ui/workbench.css`, `ui/__init__.py` | Mới: palette/layout/detail style; chủ yếu selector thuộc key của app. |
| `.streamlit/config.toml` | Mới: light/dark và sidebar, font/radius, giữ native menu; tắt fast reruns để tránh ngắt request đang chạy. |
| `requirements.txt` | Chỉ pin/thêm UI: Streamlit 1.67.0, streamlit-pdf 2.1.0, streamlit-pdf-viewer 0.0.30. |
| `requirements-ui-test.txt` | Mới: Playwright 1.65.2 cho dev/test, không dùng trong runtime UI. |
| `tests/test_streamlit_app.py` | Thay test form cũ bằng test chat/state/citations/PDF/error và chống gọi lại backend. Các tests backend giữ nguyên. |
| `scripts/ui_browser_check.py` | Mới: app/Edge/Ollama/PDF thật, chụp ảnh và kiểm counter theo phiên. |
| `.gitignore` | Cho phép lưu log kiểm thử UI trong `docs/ui_workbench/`. |
| `README.md` | Thêm liên kết hướng dẫn UI; không đổi hướng dẫn pipeline. |
| `README_UI.md`, `docs/ui_workbench/*` | Mới: hướng dẫn, quyết định viewer, logs, snapshot/hash, ảnh và báo cáo. |

Workspace đã có các thay đổi/commit từ công việc RAG trước. So sánh bảo toàn dùng snapshot ngay trước task UI, không dùng lại `main` cũ làm baseline. Không push/merge trong tác vụ này.

## Kiểm thử

- **112 passed** với `.venv/bin/python -m pytest -q --run-model`; [regression_tests.log](regression_tests.log).
- **CV14 Hit@3 = 3/3** bằng evaluator cũ và index mặc định; [cv14.log](cv14.log), [cv14.json](cv14.json).
- CLI `python -m src.demo_retrieve --question 'Học phần tiên quyết là gì?' --top-k 3` vẫn trả đúng contract; [retrieve_smoke.json](retrieve_smoke.json).
- Snapshot kiểm tra **src/data/evaluation không đổi byte**: [preservation.json](preservation.json). Không chạy lại benchmark 70 câu vì không thay pipeline.
- Unit/UI có mock để kiểm các lỗi Ollama/index/viewer, empty/no-evidence, mapping, nhiều chat, delete confirmation, mobile/back, PDF version mismatch và request không bị gửi đôi.
- Browser live dùng app production và Ollama cục bộ, không seed câu trả lời. Kiểm page 15/16 bằng canvas của viewer; file PDF tải xuống được đọc lại bằng pypdf để xác nhận nội dung đúng trang vật lý 15. Clipboard được đọc lại trong context kiểm thử. Counter kiểm rằng các thao tác PDF/zoom/fallback/copy/debug/theme/history không tạo request mới.

Browser live cuối: **10/10 kiểm tra đạt**, không có lỗi JavaScript của trang. Desktop 1440×900, mobile 390×844, tablet 1024×900. Sau thao tác UI và đổi giữa hai chat thật, counter là đúng **2 lần gửi câu hỏi**, không có yêu cầu inference do thao tác xem nguồn/theme/history. Xem [browser_checks.json](browser_checks.json), [browser_checks.log](browser_checks.log).

Các lượt thử harness trước đã phát hiện iframe cũ/mới tồn tại ngắn trong lúc rerun và menu native giữ trạng thái mở sau khi đổi theme. Test cuối chờ đúng frame/menu; không thay backend hay dựng dữ liệu để làm test qua. Phát hiện viewport gửi lại sự kiện thừa đã được sửa bằng so sánh với viewport hiện có trước khi gửi event.

## Ảnh chụp thực tế

Các ảnh dưới đây chụp trực tiếp từ Streamlit trong Microsoft Edge headless trên máy local, dùng câu trả lời của pipeline/Ollama thật và PDF thật. Không dùng prototype HTML hoặc ảnh dựng thay thế.

- [Desktop Light — 1440×900](screenshots/desktop_light.png)
- [Desktop Dark — 1440×900](screenshots/desktop_dark.png)
- [Desktop đoạn nguồn](screenshots/desktop_evidence_excerpt.png)
- [Viewer dự phòng](screenshots/desktop_fallback.png)
- [Mobile chat — 390×844](screenshots/mobile_chat.png)
- [Mobile bằng chứng — 390×844](screenshots/mobile_evidence.png)
- [Tablet dialog — 1024×900](screenshots/tablet_evidence.png)
- [Lịch sử hai chat](screenshots/history.png)

Panel PDF có vùng cuộn riêng; đoạn nguồn nằm dưới viewer. Nếu chuyển khỏi trang trích dẫn, UI báo rõ trang đang xem và trang thực của đoạn trích. Không lấy nội dung trang mới làm chứng cứ cho câu trả lời cũ.

## Quyết định viewer và theme

- Viewer chính `streamlit-pdf-viewer`: chỉ render `pages_to_render=[page]`, có text layer và zoom; không render 220 trang. Không dùng `scroll_to_page` vì `scrollIntoView` có thể kéo cả app trong iframe. Trang được chọn là trang duy nhất được render, nên mở đúng số trang vật lý mà không cuộn app.
- Fallback `st.pdf` đọc bản một trang tạo trong RAM; UI ghi rõ trang X của PDF gốc. Không sửa file gốc hoặc dùng `#page=` trên local path để giả điều hướng.
- Viewer chính có [Apache-2.0 upstream](https://github.com/ScienciaLAB/streamlit-pdf-viewer/blob/main/LICENSE); wheel 0.0.30 không khai báo License-Expression. Native streamlit-pdf 2.1.0 và Playwright khai báo Apache-2.0 trong package đã cài.
- Theme được chọn qua menu native **⋮ → Light/Dark**, không có công tắc Python riêng dựa trên CSS giả theme. CSS dùng key của app và một testing hook để chỉnh native padding, được pin/kiểm tra trên Streamlit 1.67.0.

## Chưa hỗ trợ / giới hạn

1. Highlight tọa độ thật trong PDF: backend chưa có bounding boxes; không vẽ highlight giả.
2. History bền vững, tài khoản, sync đa thiết bị; history chỉ thuộc session và có thể mất khi refresh/restart.
3. Memory hội thoại trong prompt, regenerate, streaming token, upload tài liệu hoặc annotation PDF.
4. Progress từng giai đoạn/token: pipeline hiện chỉ trả kết quả cuối; UI hiển thị trạng thái xử lý kết hợp thật.
5. Chất lượng nội dung do backend hiện có quyết định. UI giữ nguyên các câu trả lời dài, thiếu ý hoặc sai phạm vi còn tồn tại, không dùng model khác để sửa.
6. Thiết bị mobile vật lý/iOS Safari và mọi trình duyệt chưa được kiểm chứng; mobile/tablet được thử bằng viewport Edge thật, không phải mockup.
7. Giấy PDF giữ màu thật trong dark mode, không đảo màu hoặc sửa tài liệu. Hội thoại dài có vùng cuộn riêng.

## Chạy và rollback UI

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_qa_app.py
```

Giữ Ollama chạy. Cách dùng đầy đủ và lệnh browser test: [README_UI.md](../../README_UI.md). Không cần rebuild index. Bản UI trước task được snapshot local tại `.cache/ui_before/streamlit_qa_app.py`; API RAG cũ vẫn độc lập với UI mới.
