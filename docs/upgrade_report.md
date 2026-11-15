# Báo cáo nâng cấp hỏi đáp tự do

Ngày thực hiện: 14/11/2026, giờ Việt Nam. Nhánh làm việc: `codex/open-domain-rag`, xuất phát từ `6be6f89`. Không push hoặc commit lên main.

## Phạm vi và dữ liệu được bảo toàn

- PDF chính thức: `data/so_tay_sinh_vien_k50.pdf`, 220 trang, SHA-256 `bbae270b9821c71eeede660e3168c868bde07f458f07b648645c14584bdeb8b0`.
- Giữ nguyên ba artifact gốc của index 1.907 chunks, revision multilingual-E5-small, thuật toán chunking và API `retrieve(question, top_k=3)` với đúng năm trường/cosine.
- Giữ nguyên câu hỏi, nhãn, evaluator CV14 và toàn bộ các tests cũ. Thêm sidecar cấu trúc riêng, pipeline mới và các tests hồi quy.
- Môi trường được xác minh thực: Apple M5, RAM 16 GiB, Python 3.11.18. Qwen2.5 3B Q4_K_M qua Ollama; không gọi dịch vụ LLM bên ngoài. Phiên bản và model digests tại `upgrade_environment.json`.

Kiểm tra bảo toàn cuối: [upgrade_preservation.log](upgrade_preservation.log). Hash các báo cáo, nhãn và log cuối: [artifact_manifest.json](../evaluation/final_v3/artifact_manifest.json). Core SHA-256 `a11c54800bb99e6ad148cd3cf8051cfc1255631d697f7e724d93b8e8cc8734b6` khớp cấu hình đã khóa.

## Các giai đoạn, lệnh và bằng chứng

| Giai đoạn | File chính | Lệnh / kết quả thực |
|---|---|---|
| 0. Kiểm tra và baseline | `evaluation/baseline_streamlit.py`, `baseline_failure_analysis.json` | Tests gốc **59 passed**; CV14 **3/3**. Logs `upgrade_stage0_*`. Bản chụp app cũ giữ nguyên prompt/Top-3/256 token. |
| 1. Phân tích truy vấn và cấu trúc | `src/query_processing.py`, `text_utils.py`, `document_structure.py`, `settings.py`; `data/processed/structure.json` | Chuẩn hóa, ràng buộc, từ đồng nghĩa/tách truy vấn; metadata điều/khoản/điểm và phạm vi; artifact gốc không đổi. |
| 2. Retrieval/context | `src/bm25.py`, `hybrid_retriever.py`, `reranking.py` | 20 ứng viên/method/truy vấn, RRF, lọc trùng, chọn 4–8 đoạn và hai lượt có giới hạn. Báo cáo dev và ablation có trong `evaluation/upgrade_dev_*.json`. |
| 3. Câu trả lời và trích dẫn | `src/llm.py`, `answering.py`, `pipeline.py` | Luận điểm + trích đoạn thực; ID/nguyên văn/số/đối tượng; một lần sửa. Tests và logs `upgrade_stage3_*`, `upgrade_stage4_*`, `upgrade_stage5_tests.log`. |
| 4. Kiểm chứng bổ sung | `src/entailment.py`, các kiểm tra chỉ số/phạm vi/độ phủ trong `answering.py` | NLI local được thử trên chứng cứ thật. Probe cho thấy model cũng có lỗi; bổ sung kiểm tra tên chỉ số và dùng cấu trúc để nhận ra mục điều kiện còn thiếu. Không coi NLI là oracle. `upgrade_nli_tests.log`: **90 passed**. |
| 5. Giao diện và đánh giá | `streamlit_qa_app.py`; `evaluation/prepare_benchmark.py`, `run_benchmark.py`, `review_results.py`, `run_final_suite.py`; `tests/test_open_domain.py`, `test_streamlit_app.py`, `test_suite_runner.py` | Giao diện nhập tự do, partial, nguồn/trang, debug bền qua rerun; 70 câu gán nhãn từ PDF, chia dev/test, khóa hash; review gắn hash phản hồi. Kiểm thử cuối **100 passed**, CV14 vẫn **3/3**. |

Các lỗi baseline quan sát được, không chỉ suy đoán:

- Câu đăng ký học phần từng trượt trong baseline cửa sổ trang; CV14 hiện tại đạt 3/3 nhưng diễn đạt lại vẫn có thể trượt.
- `P01` cũ trả định nghĩa học phần tự chọn thay cho thời điểm tự chọn môn.
- `D15` cũ trả đúng con số tình cờ nhưng dẫn chính sách người khuyết tật thay cho học bổng khuyến khích.
- `C03` cũ trộn xử lý học vụ với chương trình thứ hai và điểm rèn luyện.
- Model có thể lấy số thứ tự khoản làm số lần cảnh báo; kiểm tra mới loại số thứ tự trước khi so số liệu.
- Model có thể đổi điểm tích lũy thành học kỳ dù số khớp. Cả Qwen và NLI từng chấp nhận sai; kiểm tra tên chỉ số độc lập chặn việc đổi thuộc tính này.

Chi tiết các ca và raw responses: `evaluation/baseline_failure_analysis.json`, các report trial, và `evaluation/nli_*probes.json`. Các report phát triển được nén nguyên byte trong `evaluation/history/`; `archive_manifest.json` ghi đường dẫn cũ và SHA-256. Report có `complete=false` là lượt thử dừng, không phải kết quả cuối. Một số trial hoàn tất nhưng có hash code cũ; chúng là lịch sử phát triển, không dùng thay báo cáo final. Hai lượt đo từng bị chạy chồng đã bị loại riêng với tiền tố `discarded_concurrent_`.

Các lệnh theo giai đoạn (chạy từ gốc repository):

```bash
# Giai đoạn 0: trước khi đổi app; log ghi 59 passed và CV14 3/3.
.venv/bin/python -m pytest -q --run-model
.venv/bin/python -m evaluation.run_evaluation --out evaluation/upgrade_baseline_cv14.json
.venv/bin/python -m evaluation.run_benchmark --split dev --system baseline --answers --out evaluation/upgrade_dev_baseline_answers.json

# Giai đoạn 1–2: retrieval và ablation, chưa chấm câu trả lời.
.venv/bin/python -m pytest -q
.venv/bin/python -m evaluation.run_benchmark --split dev --out evaluation/upgrade_dev_retrieval.json
.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --reranker none --out evaluation/upgrade_dev_no_rerank.json

# Giai đoạn 3–5: sinh, sửa một lần, kiểm chứng, NLI và giao diện.
.venv/bin/python -m src.entailment --download
.venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --answers --out evaluation/upgrade_dev_hybrid_final.json
.venv/bin/python -m pytest -q --run-model
.venv/bin/python -m evaluation.run_evaluation --out evaluation/upgrade_final_cv14.json
```

Log tương ứng: `docs/upgrade_stage0_*`, `upgrade_stage1_tests.log`, `upgrade_stage2_*`, `upgrade_stage3_*`, `upgrade_stage4_*`, `upgrade_stage5_tests.log`, `upgrade_final_tests.log`, `upgrade_final_cv14.log`. Các log trial/dev cũ cũng được nén trong `evaluation/history/`, có ánh xạ đường dẫn ở manifest. Tên `final` trong các report phát triển cũ không làm chúng trở thành số liệu bàn giao; chỉ bộ `evaluation/final_v3/` bên dưới là kết quả cuối.

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

Các file bàn giao thêm ngoài các module trong bảng giai đoạn: `requirements.txt` khai báo Pydantic/Transformers/Hugging Face Hub; `.gitignore` giữ logs lượt cuối; `README.md`, `docs/open_domain_rag.md`, báo cáo này, môi trường xác minh, dữ liệu benchmark, nhãn review và raw reports. Cache trọng số nằm ngoài Git. Các module `src/` cũ, toàn bộ tests cũ, PDF, ba artifact index và evaluator CV14 không đổi.

## Tái chạy và rollback

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m src.entailment --download
.venv/bin/python -m pytest -q --run-model
.venv/bin/python -m evaluation.run_evaluation --out evaluation/cv14_recheck.json
.venv/bin/python -m streamlit run streamlit_qa_app.py

# Giao diện baseline, không rebuild index/PDF:
.venv/bin/python -m streamlit run evaluation/baseline_streamlit.py
```

Hướng dẫn cấu hình và giới hạn: `docs/open_domain_rag.md`; định nghĩa chỉ số và cách review: `evaluation/README.md`. Không suy rộng một benchmark 70 câu thành khả năng trả lời mọi câu hỏi. Thông tin nằm trong ảnh, quan hệ ô bảng, quy định hiện hành ngoài PDF và dữ liệu cá nhân/thời gian thực vẫn có giới hạn.
