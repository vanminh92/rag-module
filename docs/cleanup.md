# Dọn cấu trúc repository

Thực hiện ngày 15/11/2026. Bản trước khi dọn: `0076441`; bản này đã được push lên GitHub và có thể dùng để khôi phục các tài liệu cũ.

## Những gì đã đổi

- Xóa **128 file** lịch sử/thử nghiệm/trùng lặp: `evaluation/history/`, log các giai đoạn cũ, báo cáo pilot/trial, review nháp, ảnh lỗi và snapshot UI tạm.
- Gộp `README_UI.md` và `docs/ui_workbench/report.md` thành [hướng dẫn UI](ui_workbench/README.md).
- Thay tài liệu bàn giao CV12–CV14 cũ bằng [hướng dẫn phát triển](development.md), giữ [contract Code 2](code2_integration.md) riêng.
- Viết lại [README](../README.md) theo thứ tự: chuẩn bị → cài lần đầu → chạy mỗi ngày → cách dùng → lỗi thường gặp → tài liệu kỹ thuật.
- Rút [báo cáo RAG](upgrade_report.md) về kết quả cuối, cách tái chạy và các lỗi còn tồn tại. Giữ đủ raw reports và nhãn để kiểm tra lại số liệu.

Các file thuộc phiên bản hiện tại giảm từ **240 xuống 118**; tổng dung lượng file được Git quản lý giảm từ **40.65 xuống khoảng 32.00 MiB**. Không tính `.venv`, cache model và dữ liệu được Git ignore. Không viết lại lịch sử Git.

## Những gì giữ nguyên

- Toàn bộ `src/`, `ui/`, `tests/`, PDF và các index trong `data/`: **54 file được đối chiếu SHA-256**, không thay nội dung.
- API `retrieve(question, top_k=3)`, model/prompt, thuật toán retrieval và cách chia đoạn.
- Bộ câu hỏi CV14 đang dùng, 70 câu benchmark cùng nhãn cuối, baseline dùng bởi evaluator và kết quả trong `evaluation/final_v3/`.
- Ảnh desktop/mobile/tablet cuối cùng, browser check 10/10 và log kiểm thử gần nhất.

Chỉ manifest artifact cuối được bỏ các entry trỏ tới file lịch sử đã xóa; không sửa raw câu trả lời, điểm đánh giá hoặc hash mã nguồn trong report. Các module chạy được giữ riêng theo trách nhiệm; không gộp code UI vào pipeline để giảm số file.

## Kiểm tra sau khi dọn

- `.venv/bin/python -m pytest -q --run-model`: **112 passed**, xem [log](ui_workbench/regression_tests.log).
- Kiểm tra các liên kết Markdown nội bộ và `git diff --check`.
- So sánh hash mã chạy/UI/tests/data và raw benchmark với trạng thái trước khi dọn.
- Không chạy lại LLM benchmark hoặc thay giao diện trong tác vụ dọn tài liệu này.

## Khôi phục file lịch sử nếu cần

Ví dụ đọc lại một file đã xóa mà không thay working tree:

```bash
git show 0076441:docs/ingestion_notes.md
```

Hoặc khôi phục đúng một file:

```bash
git restore --source=0076441 -- docs/ingestion_notes.md
```

Danh sách thay đổi đầy đủ nằm trong commit dọn repo; không cần giữ thêm một bản archive trùng trong thư mục dự án.
