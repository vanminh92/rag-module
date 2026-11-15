# Kết quả đánh giá RAG

Đo trên MacBook Air M5 16GB ngày 14/11/2026, dùng Qwen2.5 3B và E5 hiện tại. Môi trường: [upgrade_environment.json](upgrade_environment.json). Các báo cáo cuối và nhãn vẫn được giữ nguyên; log/trial trước đó có thể tìm lại trong Git.

## Kết quả cuối

Cấu hình đóng băng trong `evaluation/benchmark/frozen_config.json`: rules rewrite, 20 ứng viên mỗi method/truy vấn, RRF 60, lexical reranker, 4–8 contexts/2.200 token ước lượng, tối đa hai lượt retrieval, Qwen2.5 3B và NLI local. Mã nguồn được khóa bằng SHA-256; chỉ điều chỉnh theo dev. Bộ 70 câu chia 35 dev/35 test theo nhóm bằng chứng, mỗi split có 20 câu trực tiếp, 5 diễn đạt lại, 5 tổng hợp và 5 thiếu thông tin.

Chạy tuần tự bốn lượt trong tiến trình riêng, với khóa chống chạy chồng và thư mục đầu ra mới:

```bash
.venv/bin/python -m evaluation.run_final_suite --out-dir evaluation/final_v3 --logs-dir docs/final_v3
```

Raw reports và manifest ở `evaluation/final_v3/`; logs ở `docs/final_v3/`. Muốn tái chạy, chọn tên thư mục khác vì runner từ chối ghi đè kết quả. Dừng runner cũng dừng worker và các stage kế tiếp; đã có kiểm thử hồi quy cho việc ngắt process.

**Kết quả không đồng đều giữa các tập.** Trên test 35 câu, đúng/đủ tăng từ 21/30 lên 22/30 và trích dẫn sai giảm, nhưng Recall@10 giảm từ 98,48% xuống 92,42%; MRR cũng giảm. Chưa chứng minh cải thiện retrieval ổn định trên câu hỏi mới. Thời gian trung bình test tăng từ 1,86 lên 25,11 giây. Không điều chỉnh hệ thống sau khi xem kết quả test.

| Chỉ số | Test baseline | Test mới | Gộp 70 baseline | Gộp 70 mới |
|---|---:|---:|---:|---:|
| Recall@5, lượt đầu | 95.45% | 90.91% | 74.60% | 89.68% |
| Recall@10, lượt đầu | 98.48% | 92.42% | 82.54% | 94.71% |
| MRR@10, lượt đầu | 0.8957 | 0.7889 | 0.6882 | 0.8282 |
| Độ phủ ngữ cảnh ban đầu | 86.36% | 92.42% | 69.84% | 93.92% |
| Trả lời đúng và đầy đủ, nhãn full | 70.0% (21/30) | 73.3% (22/30) | 58.3% (35/60) | 71.7% (43/60) |
| Luận điểm được hỗ trợ | 77.4% (24/31) | 89.5% (34/38) | 80.9% (38/47) | 94.4% (68/72) |
| Trích dẫn sai | 25.0% (9/36) | 9.8% (4/41) | 28.8% (17/59) | 5.1% (4/78) |
| Từ chối đúng, nhãn none | 100.0% (2/2) | 100.0% (2/2) | 100.0% (7/7) | 85.7% (6/7) |
| Thời gian trung bình (giây) | 1.86 | 25.11 | 1.47 | 21.16 |
| Thời gian p95 (giây) | 3.49 | 64.51 | 2.93 | 50.63 |
| Peak RSS Python (MiB) | 1044.8 | 3057.0 | 1044.8 | 3059.8 |
| Max RSS Ollama lấy mẫu (MiB) | 2682.4 | 4656.3 | 2682.4 | 4656.3 |

Tập test có 30 câu full, 2 câu none và 3 câu partial. Gộp 70 câu có 60 full, 7 none và 3 partial; chỉ số retrieval lấy trung bình trên 63 câu có chứng cứ. Cột gộp chứa cả dev đã dùng để phát triển, không đại diện cho khả năng khái quát độc lập. Không có lỗi thực thi trong 140 cặp câu hỏi–hệ thống.

- Độ phủ context cuối dev/baseline: 51.67%.
- Độ phủ context cuối dev/hybrid: 98.89%.
- Độ phủ context cuối test/baseline: 86.36%.
- Độ phủ context cuối test/hybrid: 95.45%.

Ba câu chỉ trả lời được một phần: baseline đáp ứng cả phần có chứng cứ và thông báo phần thiếu **0/3**; bản mới **2/3** (U09, U10). `U08` vẫn bỏ thông báo không biết trạng thái chuyển tiền cá nhân.

Peak RSS Python tăng khoảng 1,02 lên 2,99 GiB; RSS Ollama là mẫu server/runner sau phản hồi, không phải peak unified memory. Không cộng các cột để suy ra RAM thực dùng: có vùng chia sẻ và thời điểm lấy mẫu khác nhau. Toàn bộ lượt chạy trên M5 16 GiB không gặp lỗi hết bộ nhớ.

Báo cáo máy: [quality_report.json](../evaluation/final_v3/quality_report.json). Nhãn và lý do: [reviews_final.json](../evaluation/benchmark/reviews_final.json). Đối chiếu từng câu: [question_review.md](../evaluation/final_v3/question_review.md). Các ca chưa đạt: [failure_cases.json](../evaluation/final_v3/failure_cases.json).

Ablation chỉ trên dev, retrieval-only, cùng mã nguồn:

| Dev | Recall@5 | Recall@10 | MRR@10 | Độ phủ context |
|---|---:|---:|---:|---:|
| Dense baseline | 51.67% | 65.00% | 0.4599 | 51.67% |
| Hybrid, reranker none | 90.00% | 94.44% | 0.7664 | 92.78% |
| Hybrid, lexical đã chốt | 88.33% | 97.22% | 0.8714 | 95.56% |

Lexical được chọn vì MRR/độ phủ dev cao hơn `none`. Sự giảm trên test cho thấy lựa chọn này chưa khái quát ổn định. Ablation không sinh câu trả lời nên không so thời gian của nó với end-to-end. Cross-encoder neural tùy chọn chưa được benchmark.

Lệnh ablation: `.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --reranker none --out evaluation/final_v3/dev_no_rerank.json`; log `docs/final_v3/dev_no_rerank.log`.

Không lấy tỷ lệ supported do Qwen/NLI tự đánh giá làm độ chính xác. Nhãn trong `evaluation/benchmark/reviews_final.json` do Codex đối chiếu câu hỏi, mọi điều kiện cần thiết và nguồn PDF; đây là đánh giá của agent, không phải kiểm định độc lập bởi con người. Mỗi nhãn gắn với hash câu trả lời thực tế. Baseline không tách luận điểm nên toàn bộ câu trả lời được chấm như một luận điểm tổng hợp; tỷ lệ hỗ trợ hai hệ thống có giới hạn so sánh này.

Thử thêm ngoài bộ 70 câu, sau khi đóng băng: “Mình ở trọ và vừa chuyển chỗ ở, cần báo việc thay đổi cho ai?”. Pipeline tìm được quy định cập nhật địa chỉ trên Cổng thông tin điện tử sinh viên trong tối đa 20 ngày, trang PDF 118. Phản hồi còn đưa thêm một câu về quản lý dữ liệu chưa nói rõ chủ thể; không tính smoke này vào điểm benchmark hoặc coi đó là bằng chứng trả lời được mọi câu mới. Raw trace: `evaluation/final_v3/free_form_smoke.json`, log `docs/final_v3/free_form_smoke.log`.

```bash
.venv/bin/python -m evaluation.review_results \
  --reports evaluation/final_v3/dev_baseline.json evaluation/final_v3/dev_hybrid.json evaluation/final_v3/test_baseline.json evaluation/final_v3/test_hybrid.json \
  --annotations evaluation/benchmark/reviews_final.json --out evaluation/final_v3/quality_report.json
```

## Các giới hạn đo được

Các giới hạn quan sát trực tiếp trong lượt cuối:

| Ca | Kết quả / nguyên nhân quan sát từ raw trace |
|---|---|
| Dev `C01`, test `D21`, `D23` | Context chứa đủ chứng cứ (coverage 1,0), nhưng NLI phủ quyết diễn giải ở cả hai lần; từ chối sai. Kiểm chứng chặt làm tăng false negatives. |
| Dev `D09`, `P03`, `C03` | Tìm bổ sung được các mục cần thiết, nhưng câu trả lời còn thiếu trường hợp 03 lần cảnh báo liên tiếp; đã báo partial. |
| Dev `D14`, `D20`, `C04` | Còn bỏ điều kiện bắt buộc dù model báo complete. Nhãn review chấm chưa đầy đủ, không dùng trạng thái này làm ground truth. |
| Dev `P05` | Context có đủ điều kiện; kiểm tra tên chỉ số loại một diễn giải và chỉ giữ điều kiện tín chỉ. Bộ kiểm tra cơ học cũng có false positives. |
| Dev `U05` | Hỏi mật khẩu cá nhân nhưng trả thông tin liên hệ Trung tâm Tin học. Thông tin liên hệ có nguồn, song không liên quan; không được tính là từ chối đúng. |
| Test `D27` | Gộp “tham gia nhiều đề tài” và “chủ nhiệm một đề tài” thành một số lượng. Qwen/NLI đều chưa chặn được lỗi gắn thuộc tính. Review chấm bảo thủ là sai. |
| Test `D38` | Ý chính về chương trình 2+2 đúng, nhưng thêm thông tin từ ngành/chương trình khác. Lọc đại học/cao đẳng đã có; phạm vi tên ngành chưa được xử lý đủ chặt. |
| Test `P07`, `C09`, `U08` | Có câu trả về phạm vi áp dụng thay vì chuẩn ngoại ngữ; có câu chỉ trả số tiền nhưng thiếu thời lượng hoặc thiếu thông báo không biết trạng thái chuyển tiền cá nhân. Trạng thái complete chưa đáng tin tuyệt đối. |
| Test `D36` và một số câu ngắn | Mở rộng câu ngắn bằng nguyên văn giữ điều kiện nhưng có thể lặp cả đoạn hoặc mang theo mẩu câu từ mục trước. Câu trả lời còn dài và chưa luôn tự nhiên. |

Không diễn giải tỷ lệ hỗ trợ cao thành độ chính xác tuyệt đối: nguồn có thể chứng minh một thông tin liên hệ nhưng thông tin đó không trả lời câu hỏi (`U05`). Bộ test nhỏ, do người triển khai soạn; cần kiểm định độc lập và bổ sung câu hỏi thực tế trước khi dùng làm thước đo rộng hơn. Trích xuất bảng/ảnh và ranh giới chunk qua tiêu đề vẫn có giới hạn. Mặc định ưu tiên các kiểm tra nguồn; có thể đo chế độ `RAG_SUPPORT_CHECK=llm` riêng để đánh giá đánh đổi của NLI, không coi đó là cấu hình đã được chứng minh tốt hơn.


## Tái chạy

Cách đo, review và định nghĩa chỉ số: [evaluation/README.md](../evaluation/README.md). Thiết kế/cấu hình: [open_domain_rag.md](open_domain_rag.md). Hướng dẫn cài/chạy: [README](../README.md).

Bản baseline phục vụ đối chiếu vẫn ở `evaluation/baseline_streamlit.py`; không xóa file này vì evaluator còn dùng.
