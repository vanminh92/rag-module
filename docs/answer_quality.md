# Sửa chất lượng trả lời RAG — 15/11/2026

Model mặc định vẫn là `qwen2.5:3b` qua Ollama. Không đổi PDF, E5, chunking, embeddings hoặc index gốc. API `retrieve(question, top_k=3)` giữ nguyên. Thay đổi nằm ở phân tích câu hỏi, chọn ngữ cảnh và tạo/kiểm chứng câu trả lời.

## Nguyên nhân tìm được

1. **Tìm được nguồn không có nghĩa đã dùng đủ nguồn.** Trước sửa, câu hỏi về mức hỗ trợ và số tháng tối đa có thể chỉ trả lời mức tiền nhưng vẫn ghi `complete`. Câu tổng hợp học bổng bỏ tín chỉ dù đoạn chứa điều kiện đã được truy xuất.
2. **Lượt tìm bổ sung không ưu tiên đúng ý thiếu.** Việc xếp hạng lại hoàn toàn theo câu hỏi dài khiến đoạn chứa ngưỡng/số tháng vẫn không vào ngữ cảnh. Điều kiện chung đôi khi bị thay bằng điều kiện dành cho năm cuối.
3. **Model 3B vừa phải viết lại vừa sao chép chứng cứ dài.** Mỗi luận điểm phải trả lời, chọn ID và chép lại tới 500 ký tự nguồn. Điều này làm tăng dung lượng đầu ra và có thể làm mất điều kiện, ví dụ gộp “tham gia nhiều đề tài” và “chủ nhiệm một đề tài” thành cùng một số lượng.
4. **Kiểm chứng có cả sai dương và sai âm.** Cùng model có thể bỏ qua ý thiếu lần nữa. NLI có thể không xác nhận một câu diễn giải tiếng Việt đúng, khiến câu có chứng cứ bị từ chối.
5. **Cách xử lý câu ngắn gây lặp.** Mỗi câu dưới 12 từ bị thay bằng cả đoạn trích; email và website cùng nguồn có thể thành hai đoạn trùng nhau.
6. **Danh sách thiếu thông tin không nhất quán.** Verifier có thể xóa phần thiếu mà không bổ sung chứng cứ, hoặc liệt kê chính câu đã được trả lời là phần thiếu.
7. **Phạm vi thời gian và chương trình chưa được bảo vệ đủ.** Nguồn cũ có thể được dùng trả lời học phí/điểm chuẩn năm mới; các đoạn nghề nghiệp của chương trình tiếng Trung khác bị trộn vào chương trình song ngành `2+2`.

## Đã thay đổi

- Tạo checklist trực tiếp từ câu hỏi, tách các thuộc tính như tín chỉ, số lần, tiền, số tháng, ngoại ngữ và thời điểm sớm nhất. Không mã hóa đáp án, số trang hoặc ID của câu kiểm thử vào các quy tắc.
- Truy vấn tập trung cho thuộc tính cần tìm; chọn ứng viên bằng BM25 của từng thuộc tính, giữ giới hạn 4 truy vấn, 2 lượt và tối đa 8 đoạn. Ưu tiên điều kiện chung trước đối tượng đặc biệt chưa được hỏi.
- Qwen chọn ID của các đoạn trực tiếp trả lời. Python lấy nội dung thật của đúng ID để dựng câu trả lời và citation. Cách trả lời mặc định là **trích đoạn có kiểm chứng**, giúp giữ điều kiện và ngoại lệ; chưa phải bản tóm tắt diễn đạt tự nhiên.
- Nếu Qwen bỏ qua đoạn được truy xuất riêng cho một thuộc tính, đoạn đó vẫn được đưa vào lượt kiểm chứng tính liên quan. Nó phải có ID thật, khớp thuộc tính, đúng phạm vi và qua verifier; không tự gắn nguồn vào một khẳng định chưa được chứng minh.
- Kiểm tra từng ý riêng. Có tiền/tháng không được coi là đã có số tháng/năm; công thức học phí một tín chỉ không được coi là điều kiện tín chỉ xét học bổng.
- Không dùng quy định chung để xác nhận mật khẩu, chuyển tiền cá nhân hoặc số giường trống hiện tại. Câu hỏi hỗn hợp vẫn giữ phần trả lời được.
- Năm được hỏi phải được chứng cứ/phạm vi nguồn xác nhận; một công thức học bổng cũ không trả lời được học phí năm 2026–2027. Năm thuộc ý hỏi chuyển tiền cá nhân không làm mất phần trả lời mức hỗ trợ chung.
- Lọc đúng chương trình liên kết có dạng `2+2` bằng ranh giới tiêu đề, kể cả khi một chunk chứa hai chương trình. Chỉ bổ sung metadata trong RAM và chọn span trích dẫn thật; không sửa PDF, chunk hoặc index.
- Bổ sung cách hỏi thường như “mail phòng CNTT”, “cỡ nào mới ra trường”; không coi tên miền trong email là câu trả lời cho địa chỉ website. Ưu tiên quy định chuẩn ngoại ngữ tối thiểu trước một phương án chứng chỉ cụ thể.
- Kiểm chứng riêng tính liên quan, scope và nội dung. Khi NLI chưa xác nhận một diễn giải, có thể dùng chính chứng cứ nguyên văn đã được xác minh; mâu thuẫn rõ vẫn bị loại. Luồng trả nguyên văn không tải NLI vào RAM chỉ để kiểm tra lại cùng một chuỗi.
- Loại nguồn/luận điểm trùng và một số tiêu đề không có thông tin trả lời. Bỏ cơ chế mở rộng tự động mọi câu ngắn.
- Chỉ xóa “phần thiếu” khi có đối chiếu rõ với câu đã trích, checklist đã được đáp ứng, hoặc toàn bộ câu hỏi đã được kiểm chứng với đủ thuộc tính. Không xóa phần thiếu chưa được chứng minh.

Thông tin từng lượt tìm, lựa chọn, lỗi kiểm chứng và checklist nằm trong **Developer Debug**. Tương tác xem nguồn, chuyển trang và đổi chat tiếp tục dùng kết quả đã lưu, không sinh lại câu trả lời.

## Kiểm thử và cách đối chiếu

**140/140 tests** đã qua, gồm model E5/NLI thật, kiểm tra trích dẫn/scope, độ đầy đủ và hồi quy giao diện. CV14 vẫn **3/3**. Đã chạy 70 câu với Ollama thật trong quá trình tìm lỗi, không có lỗi thực thi. Sau những sửa cuối, chạy xác nhận riêng 23 ca trên cùng một hash mã nguồn; kết quả chi tiết được ghi ở phần dưới. Không gộp lượt tìm lỗi vào độ chính xác của mã cuối.

Bộ 70 câu cũ là bộ hồi quy đã biết; kết quả không chứng minh độ chính xác trên mọi câu hỏi mới. Không đổi nhãn hoặc báo cáo `evaluation/final_v3/` của phiên bản trước. Các thay đổi ranh giới tiêu đề cũng được kiểm thử bằng đoạn thật: đoạn có câu trả lời và kết thúc bằng dấu `:` vẫn được giữ, header số trang không được coi là câu trả lời.

| Kiểm tra trên mã cuối | Kết quả |
|---|---|
| Tests tự động, có E5/NLI thật | 140/140 |
| CV14, API retrieval cũ | 3/3 |
| Ollama thật, cùng hash mã nguồn | 23/23 không lỗi thực thi |
| Câu có đủ thông tin: mọi nhóm chứng cứ được gán nhãn xuất hiện trong nội dung trả lời và dẫn đúng nguồn | 17/17 |
| Câu hoàn toàn ngoài dữ liệu được từ chối | 3/3 |
| Câu hỗn hợp giữ phần biết và nêu phần không xác minh được | 3/3 |
| Liên kết trích dẫn đúng ID, file, trang vật lý và span nguyên văn | 62/62 |
| Luận điểm trùng nguyên văn | 0 |

**17/17 là độ hiện diện chứng cứ được gán nhãn trong 17 câu đã chọn, không phải tuyên bố độ chính xác 100% cho hệ thống.** Câu trích đúng vẫn có thể thừa thông tin hoặc chưa trả lời đúng ý ở câu hỏi khác. Verifier Qwen không được dùng làm nhãn đánh giá độc lập.

Kết quả đã lưu:

- [70 câu trong lượt tìm lỗi](../evaluation/answer_quality/diagnostic_70.json): có các lỗi đã dẫn đến sửa bổ sung; các lượt dev/test có hash khác nhau, không dùng làm điểm số của mã cuối.
- [23 câu xác nhận trên mã cuối](../evaluation/answer_quality/confirmation_23.json): câu hỏi, câu trả lời, nguồn, span, checklist, lỗi từng lượt và hash mã nguồn. Hai tập dùng hash `4e61bc0ae8b4d3691d93d1d7c4d95640413aaf6b133a9f6135182abcea2fa715`.

Độ trễ trung bình 12,29 giây, P95 khoảng 24,15 giây trên 23 câu này. Peak RSS Python khoảng 1.167 MiB; RSS Ollama lớn nhất lấy mẫu khoảng 5.949 MiB. Hai số không phải tổng bộ nhớ thống nhất duy nhất hay peak toàn hệ thống. Đã chạy trên máy macOS hiện tại; không suy ra hiệu năng tương tự trên mọi máy 16 GB.

Các ca chính đã xác nhận: đủ hai ngưỡng cảnh báo (D09); thời điểm đăng ký chương trình thứ hai (D11); điều kiện tín chỉ, học tập/rèn luyện/kỷ luật và số tháng học bổng (D14/P05/C04); mức tiền và giới hạn tháng hỗ trợ (C09); nhiều đề tài tham gia nhưng một đề tài chủ nhiệm (D27); nguồn đúng chương trình 2+2 (D38); mail phòng CNTT (P10); không dùng công thức cũ cho học phí năm mới (U02).

**Còn 5 cảnh báo quá thận trọng:** P05, C02, C04, D36 và P07 đã chứa đủ đoạn chứng cứ theo nhãn nhưng verifier vẫn để `partial` hoặc ghi một ý đã trả lời vào phần thiếu. Giữ nguyên kết quả này trong báo cáo; chưa chỉnh nhãn hoặc tự chuyển thành `complete` để đạt điểm đẹp. Chưa chạy lại toàn bộ 70 câu trên hash cuối; lượt xác nhận cuối gồm 23 ca hồi quy trọng yếu.

Chạy từ thư mục dự án:

```bash
.venv/bin/python -m pytest -q --run-model
.venv/bin/python -m evaluation.run_evaluation --out .cache/quality_cv14.json
.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --answers --out .cache/quality_dev.json
.venv/bin/python -m evaluation.run_benchmark --split test --system hybrid --answers --out .cache/quality_test.json
```

Tái lập đúng các nhóm xác nhận (để Ollama chạy):

```bash
.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --answers --ids D09,D11,D14,P05,C01,C02,C04,U01,U02,U05 --out .cache/confirm_dev.json
.venv/bin/python -m evaluation.run_benchmark --split test --system hybrid --answers --ids D21,D23,D27,D33,D36,D38,P07,P10,C06,C09,U08,U09,U10 --out .cache/confirm_test.json
```

Hai lệnh benchmark cần Ollama và chạy tuần tự. Trên Windows, thay `.venv/bin/python` bằng `.\.venv\Scripts\python.exe`. Để xem một câu cùng dấu vết:

```bash
.venv/bin/python -m src.pipeline --question "Sinh viên sư phạm được hỗ trợ sinh hoạt bao nhiêu mỗi tháng và tối đa mấy tháng mỗi năm học?" --debug
```

Khởi động lại ứng dụng để nạp mã mới:

```bash
.venv/bin/python -m streamlit run streamlit_qa_app.py
```

Các câu đã trả lời trong phiên chat giữ nguyên kết quả cũ; gửi lại câu hỏi để kiểm tra phiên bản mới.

## File thay đổi

| File | Vai trò |
|---|---|
| `src/answer_requirements.py` | Checklist thuộc tính, thông tin không có trong sổ tay, năm của từng ý hỏi. |
| `src/query_processing.py` | Từ đồng nghĩa, tách ý, truy vấn tập trung và ràng buộc chương trình. |
| `src/hybrid_retriever.py` | Chọn ngữ cảnh theo từng thuộc tính và phạm vi chương trình trong RAM. |
| `src/answering.py` | Chọn đoạn, kiểm chứng, độ bao phủ, chống lặp và xử lý phần thiếu. |
| `tests/test_answer_quality.py`, `tests/test_open_domain.py` | Các ca thiếu ý, sai thời điểm/scope, từ chối sai, ID/span và kiểm chứng. |
| `README.md`, `docs/open_domain_rag.md`, `evaluation/README.md` | Cập nhật cách hoạt động và cách đọc kết quả. |
| `evaluation/answer_quality/` | Bằng chứng kiểm thử và kết quả từng câu. |

## Giới hạn còn lại

Checklist nhận diện một số thuộc tính phổ biến, không thay thế việc hiểu mọi cách hỏi tiếng Việt. Qwen vẫn có thể chọn thừa/thiếu đoạn hoặc đánh giá sai tính liên quan. Việc trích đúng nguyên văn chỉ chứng minh nội dung tồn tại trong nguồn, chưa tự chứng minh đã chọn đúng phạm vi chương trình hoặc trả lời đủ câu hỏi. Đoạn trích có thể dài và giữ ký hiệu đầu dòng/đoạn nối từ PDF.

Bảng bị trải phẳng, dữ liệu trong ảnh, chính sách cập nhật ngoài sổ tay, trạng thái cá nhân và thông tin thời gian thực vẫn chưa được hỗ trợ. Không thể cam kết mọi câu hỏi tự do đều đầy đủ; các ca chưa đạt cần được công khai thay vì bịa thông tin để lấp phần thiếu.
