# Nguồn dữ liệu, kiểm tra trích xuất và lịch sử thử nghiệm

## Nguồn đã xác minh

- File được cung cấp: `data/SO TAY SINH VIEN K50.pdf`, 2.725.959 bytes, 220 trang vật lý, không mã hóa.
- Bản sao chính thức: `data/so_tay_sinh_vien_k50.pdf`; kiểm tra byte và SHA-256 bằng nhau, không sửa PDF gốc.
- SHA-256: `bbae270b9821c71eeede660e3168c868bde07f458f07b648645c14584bdeb8b0`.
- Bản upload ban đầu được giữ cục bộ và bỏ qua trong `.gitignore`; chỉ bản tên chuẩn được lập chỉ mục.
- Thực thi ngày 14/11/2026 (giờ Việt Nam); timestamps máy đọc được trong JSON dùng UTC.

Đã đối chiếu ảnh render trực tiếp từ PDF với text `pypdf` tại trang 8, 9, 15. Công cụ render chỉ phục vụ kiểm tra trực quan cục bộ, không thuộc pipeline hay requirements. Không dùng OCR, dịch, tóm tắt hoặc sửa nội dung quy định.

| Trang PDF | Nội dung kiểm tra |
|---|---|
| 8 | Điều 2 có 15 giờ học lý thuyết và 30 giờ tự học, chuẩn bị cá nhân có hướng dẫn |
| 9 | Điểm d) nêu phải tích lũy học phần tiên quyết trước học phần khác có liên quan |
| 15 | Điều 9, mục chính quy, điểm b) bắt đầu tự đăng ký từ học kỳ thứ hai |

## Thống kê chạy thật

| Lượt | Phạm vi | Trang có text / chọn | Ký tự thô | Chunks | Token passage lớn nhất | Hit@3 |
|---|---|---|---|---|---|---|
| CV12 / baseline | 8–31 | 24/24 | 43.281 | 122 | 166 (đo ở CV13) | 2/3 khi chạy CV14 |
| Pilot cuối | 8–31 | 24/24 | 43.281 | 254 | 143 | 3/3 |
| Toàn bộ | 1–220 | 220/220 | 376.208 | 1.907 | 200 | 3/3 |

Không có trang rỗng theo tiêu chí `extract_text().strip()` trong hai phạm vi này. Pilot có 40.688 ký tự sau chuẩn hóa; toàn bộ có 346.180. Số này chưa cộng phần overlap. Kiểm tra độc lập toàn bộ 220 trang xác nhận mọi ký tự không phải khoảng trắng sau NFC/normalize đều được bao phủ bởi chunks: `docs/full_content_check.log`. Các chunk trang 8–31 trong index full giữ nguyên ID, text, nguồn, trang so với pilot; `order` thay đổi theo vị trí toàn cục.

## Lịch sử sửa chất lượng truy xuất

1. Cửa sổ theo trang 500/100: 122 chunks, Q01/Q02 có hit; Q03 không có hit. Bộ nghiệm thu báo **2 failed, 56 passed**. Giữ nguyên tại `evaluation/retrieval_report_baseline.json`, `evaluation/questions_baseline.json`, `data/processed_pilot_baseline/`, `docs/cv14_pilot_tests.log`.
2. Thử 400/80: vẫn 2/3. Kết quả thật lưu ở `evaluation/chunking_trial_400_80.json`.
3. Thử tách đầu Điều rồi cửa sổ 500/100: vẫn 2/3. Kết quả lưu ở `evaluation/chunking_trial_articles.json`.
4. Tách đầu điều/khoản/điểm từ **dòng gốc trong PDF**, sau đó cửa sổ 500/100 trong từng đơn vị dài: đạt 3/3. Kết quả thử lưu ở `evaluation/chunking_trial_clauses.json`; thuật toán này được đưa vào `src/chunking.py`, tên `pdf-clause-windows-v1`, index version 2.
5. Build pilot thật bằng thuật toán cuối, gán lại **chỉ gold IDs** từ chunks mới sau khi kiểm tra. Không đổi câu hỏi, trang tham chiếu hoặc bất kỳ ký tự nào trong `expected_evidence`. Chạy API công khai qua evaluator: 3/3, **59 passed**.
6. Chỉ sau pilot đạt mới build 220 trang, đánh giá lại: 3/3, **59 passed**.

Lý do thay đổi: cửa sổ cũ trộn đoạn về phản hồi chất lượng với Điều 9, hoặc nhiều quy định khác nhau. Tách theo cấu trúc pháp quy giúp chunk tập trung hơn. Đây là cải tiến chunking dùng quy tắc chung, không thêm từ khóa câu hỏi, không thay score, không lọc trang ngầm và không rerank. Chỉ có ba câu cố định nên đây chưa phải bằng chứng thuật toán tối ưu cho toàn tài liệu.

Overlap mục tiêu 100 ký tự áp dụng **bên trong** điều/khoản/điểm dài; không ép overlap qua ranh giới đơn vị quy định. Trimming có thể bỏ khoảng trắng ở mép cửa sổ; không bỏ chữ. Các chunk ngắn theo cấu trúc có thể dưới 500 ký tự. ID tuần tự theo nguồn/trang, không mã hóa đáp án. Artifact baseline thuộc version cũ chỉ để kiểm toán; mã hiện tại từ chối dùng nó làm index tương thích.

## Giới hạn đã ghi nhận

- Footer/header được parser đưa vào text, đôi khi xuất hiện trước thân trang (ví dụ trang 8/9). Giữ lại để tránh xóa nhầm nội dung; không tự coi footer là số trang metadata. Metadata luôn dùng vị trí trang của `PdfReader`.
- Bảng thời gian đào tạo tại trang 10 và các bảng tương tự được trải thành chuỗi text. Thứ tự đọc và quan hệ hàng/cột không được bảo đảm; không suy diễn lại số liệu hoặc cam kết trả lời đúng câu hỏi bảng.
- Một số trang có thể có ảnh/biểu mẫu; “có text” chỉ xác nhận có phần văn bản trích xuất được, không chứng minh tất cả chữ bên trong ảnh đã được lấy. OCR ngoài phạm vi.
- Toàn sổ tay có nhiều quy chế và đoạn giống nhau. Q01 trả cùng đoạn tại trang 8/32; Q02 tại trang 9/33; Top-3 Q03 gồm hai đoạn chưa trả lời câu hỏi ở trang 11/35 trước bằng chứng đúng ở trang 15. Không deduplicate hay coi top-1 luôn đúng.
- Score cosine không phải xác suất đúng. Truy vấn ngoài phạm vi vẫn có thể có Top-3. Ba câu benchmark kiểm tra đúng nguồn, trang, ID và **toàn bộ chứng cứ** trong một chunk; không pass chỉ vì cùng trang.
- Chưa kiểm tra thủ công toàn bộ nội dung 220 trang, mọi bảng, mọi loại PDF hỏng hoặc mọi câu hỏi tiếng Việt. Chạy thật trên macOS ARM64/Python 3.11; hướng dẫn Windows/Linux dùng thư viện đa nền tảng nhưng chưa chạy trên hai hệ đó.

## Bằng chứng thực thi

Các `.log` trong `docs/` là output thực của các lệnh. `cv12_*` ghi giai đoạn CV12; `cv13_*` ghi baseline embedding/demo; `cv14_pilot_*` ghi cả thất bại ban đầu và pilot cuối; `full_*` ghi lượt 220 trang. Model revision, cấu hình, checksum và timestamps nằm trong metadata/report. `docs/environment.txt` ghi phiên bản thư viện thực tế đã dùng.
