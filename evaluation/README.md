# Đánh giá bản nâng cấp

Kết quả sửa chất lượng ngày 15/11/2026 được lưu riêng và giải thích trong [báo cáo](../docs/answer_quality.md). Bộ 70 câu đã được xem trong quá trình phát triển: ở đợt này nó là **bộ hồi quy đã biết**, không còn là tập test độc lập chưa được xem. Không đổi các nhãn, PDF hoặc báo cáo `final_v3/` để làm đẹp kết quả.

`questions.json` và `run_evaluation.py` vẫn là ba câu CV14, không sửa nhãn hoặc tiêu chí cũ. `baseline_streamlit.py` là bản chụp nguyên gốc của app tại commit `6be6f89`; evaluator gọi đúng hàm sinh cũ, Top-3, prompt cũ và 256 token, không sửa để làm baseline yếu hơn.

## Bộ 70 câu

`benchmark/dev.json` và `benchmark/test.json`: mỗi tập 35 câu; tổng 40 trực tiếp, 10 diễn đạt thường, 10 tổng hợp, 10 thiếu thông tin. Trong 10 câu cuối có 7 câu hoàn toàn không có thông tin và 3 câu trả lời được một phần. Cần đánh giá riêng việc từ chối và trả lời phần có căn cứ.

Các nhãn được viết từ chunks trích xuất thực: nguồn, trang vật lý, câu trích và tất cả chunk ID chứa trọn câu trích trên trang đó. Manifest đóng băng hash PDF/chunks/hai tập. Câu diễn đạt lại và câu tổng hợp dùng cùng nhóm bằng chứng được đặt cùng split; evaluator chặn rò rỉ nhóm. 40 câu trực tiếp trải từ trang 4 đến 210, bao gồm tổng quan, đào tạo, học bổng, kỷ luật, rèn luyện, ngoại ngữ, ngoại trú, nghiên cứu khoa học, ứng xử, hỗ trợ, KTX, liên hệ, nghề nghiệp và bảo tàng.

Đây là bộ do người triển khai soạn, không phải bộ kiểm định độc lập. Nhãn “không có thông tin” cần được người am hiểu tài liệu kiểm tra lại. Không điều chỉnh hệ thống theo kết quả tập test. Chỉ dùng dev để thử cấu hình và prompt; chạy test sau khi chốt.

## Chạy lại

```bash
# Kiểm thử cũ và mới, gồm model E5 thật đã cache.
.venv/bin/python -m src.entailment --download
.venv/bin/python -m pytest -q --run-model

# CV14 cũ.
.venv/bin/python -m evaluation.run_evaluation --out evaluation/cv14_recheck.json

# Retrieval: không gọi Ollama khi rewrite=rules.
.venv/bin/python -m evaluation.run_benchmark --split dev --out evaluation/dev_retrieval.json

# Ablation: bỏ reranking.
.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --reranker none --out evaluation/dev_none.json

# End-to-end: giữ Ollama chạy; chạy tuần tự từng lệnh để không tranh tài nguyên.
.venv/bin/python -m evaluation.run_benchmark --split dev --system baseline --answers --out evaluation/dev_baseline.json
.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --answers --out evaluation/dev_hybrid.json
.venv/bin/python -m evaluation.run_benchmark --split test --system baseline --answers --out evaluation/test_baseline.json
.venv/bin/python -m evaluation.run_benchmark --split test --system hybrid --answers --out evaluation/test_hybrid.json

# Lượt bàn giao: khóa chống chạy chồng, kiểm tra code đóng băng và chạy tuần tự.
# Chọn thư mục mới khi tái chạy; không ghi đè final_v3 đã đo.
.venv/bin/python -m evaluation.run_final_suite --out-dir evaluation/recheck --logs-dir docs/recheck
```

`--rewrite llm` thử Qwen viết lại; `--ids D01,D02` chạy smoke subset và ghi rõ danh sách ID trong báo cáo. `--resume` chỉ tiếp tục khi hash code/dữ liệu/cấu hình không đổi. Báo cáo ghi dần sau mỗi câu; `complete=false` và log KeyboardInterrupt là lượt thử dừng giữa chừng, không phải kết quả đầy đủ. Lỗi thực thi được ghi rõ, exit code 2, không tính là từ chối đúng.

Mặc định `--support-check nli` bổ sung bộ kiểm chứng local; dùng `--support-check llm` để đo chế độ nhẹ hơn. Không được lấy việc Qwen/NLI chấm supported làm ground truth. Tập test chỉ chạy sau khi chốt cấu hình từ dev; các report thử trước đó có hash code khác là lịch sử phát triển.

Bộ bàn giao cuối ở `final_v3/`, logs `../docs/final_v3/`; cấu hình khóa trong `benchmark/frozen_config.json`. Các report lịch sử/trial đã được dọn khỏi phiên bản hiện tại; có thể tìm lại trong Git theo [bản ghi dọn repo](../docs/cleanup.md). Chúng không tham gia số liệu cuối. Runner suite dùng `fcntl` trên macOS/Linux; Windows có thể chạy lần lượt bốn lệnh end-to-end bên trên.

Muốn tạo phiên bản nhãn mới sau rebuild, chạy `python -m evaluation.prepare_benchmark --out evaluation/benchmark_v2`; không ghi đè bộ đã đóng băng. Không dùng script này trong serving.

## Chỉ số

- Recall@5/10: trung bình tỷ lệ **nhóm chứng cứ bắt buộc** tìm được trong Top-k. Một câu trích có thể xuất hiện trong nhiều chunk overlap, nhưng chỉ tính một nhóm. Phải đúng ID, nguồn, trang và toàn bộ trích đoạn; cùng trang chưa đủ. Đây là evidence-group recall, không phải tỷ lệ tất cả bản sao overlap được tìm thấy. Nhãn chưa bao quát mọi đoạn tương đương có thể có trên những trang khác; chất lượng câu trả lời được chấm riêng theo nguồn thực tế.
- MRR@10: nghịch đảo thứ hạng chunk đầu tiên chứa ít nhất một chứng cứ được gán nhãn; câu ngoài tài liệu không tham gia các chỉ số retrieval.
- Độ phủ ngữ cảnh: tỷ lệ nhóm chứng cứ có trong các đoạn thực sự được gửi model, trước và sau tìm bổ sung.
- Đúng và đầy đủ: reviewer so câu trả lời với mọi ý được hỏi. Câu từ chối khi nhãn `full` là không đúng/không đầy đủ. Các câu trả lời thiếu điều kiện bắt buộc không được chấm đầy đủ.
- Hỗ trợ luận điểm: số luận điểm được nguồn thực sự chứng minh / số luận điểm đã hiển thị. Baseline không tách claim nên mỗi câu trả lời cũ được chấm là một luận điểm tổng hợp; đây là hạn chế của so sánh và được ghi trong file nhãn.
- Trích dẫn sai: số liên kết claim–nguồn không chứng minh claim / tổng liên kết. Bản mới đếm theo citations từng claim; baseline đếm theo nguồn kèm câu trả lời. Trích nguồn quy chế sai đối tượng hoặc chính sách khác dù có cùng số không được chấm đúng.
- Từ chối đúng: trên 7 câu nhãn `none`; không thưởng từ chối ba câu có thể trả lời một phần. Lỗi thực thi không được tính là từ chối đúng.
- Thời gian: đo wall time, lưu mean và p95; model/index được reuse trong tiến trình. Câu đầu bao gồm tải E5. Thời gian end-to-end gồm sinh, kiểm chứng và thử lại; không so số này với retrieval-only.
- Bộ nhớ: peak RSS Python trong suốt tiến trình; RSS Ollama/server/runner lấy mẫu sau phản hồi. RSS nhiều process có thể tính trùng vùng chia sẻ, không phải peak unified memory hoặc phép đo VRAM riêng. Chạy từng system trong process riêng để giảm nhiễu.

## Review có kiểm chứng

Không dùng việc verifier Qwen đánh dấu supported làm “độ chính xác”. Những chỉ số chất lượng chưa review là `null`. Tạo nhãn review gắn với hash câu trả lời:

```bash
.venv/bin/python -m evaluation.review_results --reports evaluation/dev_baseline.json evaluation/dev_hybrid.json evaluation/test_baseline.json evaluation/test_hybrid.json --out evaluation/reviews_template.json

# Điền correct/complete, số claims được hỗ trợ và số nguồn sai sau khi đọc chứng cứ.
.venv/bin/python -m evaluation.review_results --reports evaluation/dev_baseline.json evaluation/dev_hybrid.json evaluation/test_baseline.json evaluation/test_hybrid.json --annotations evaluation/reviews.json --out evaluation/quality_report.json
```

Review do Codex thực hiện phải ghi đúng là đánh giá của agent, không gọi là người dùng hoặc kiểm định viên độc lập. Trường hợp mơ hồ ghi trong reason để người đọc kiểm tra lại.
