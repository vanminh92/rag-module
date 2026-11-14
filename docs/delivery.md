# Bàn giao CV12 → CV13 → CV14

Đã hoàn thành pipeline tuần tự trên PDF được cung cấp. Pilot 8–31 được nghiệm thu trước khi mở rộng 1–220. Index mặc định hiện là full, Hit@3 = 3/3. Chưa triển khai CV15/CV16.

## Cây thư mục thực tế

Loại khỏi cây dưới: môi trường `.venv/`, công cụ bootstrap `.tools/`, model/download cache `.cache/`, Python/pytest cache và `.DS_Store`. Bản upload tên in hoa còn nguyên cục bộ, được gitignore và không tham gia index.

```text
rag-demo/
├── data/
│   ├── processed/
│   │   ├── chunks.json
│   │   ├── embeddings.npy
│   │   └── index_meta.json
│   ├── processed_pilot/
│   │   ├── chunks.json
│   │   ├── embeddings.npy
│   │   └── index_meta.json
│   ├── processed_pilot_baseline/
│   │   ├── chunks.json
│   │   ├── embeddings.npy
│   │   └── index_meta.json
│   ├── SO TAY SINH VIEN K50.pdf
│   └── so_tay_sinh_vien_k50.pdf
├── docs/
│   ├── chunking_trial_400_80.log
│   ├── chunking_trial_articles.log
│   ├── chunking_trial_clauses.log
│   ├── code2_integration.md
│   ├── code2_smoke.log
│   ├── cv12_ingestion.log
│   ├── cv12_tests.log
│   ├── cv13_demo.log
│   ├── cv13_pilot_build.log
│   ├── cv13_q01_top3.json
│   ├── cv13_tests.log
│   ├── cv14_pilot_evaluation.log
│   ├── cv14_pilot_final_evaluation.log
│   ├── cv14_pilot_final_tests.log
│   ├── cv14_pilot_rebuild.log
│   ├── cv14_pilot_tests.log
│   ├── delivery.md
│   ├── environment.txt
│   ├── final_demo_top3.json
│   ├── full_build.log
│   ├── full_content_check.log
│   ├── full_evaluation.log
│   ├── full_tests.log
│   ├── ingestion_notes.md
│   ├── technical_spec.md
│   └── unit_tests.log
├── evaluation/
│   ├── __init__.py
│   ├── chunking_trial_400_80.json
│   ├── chunking_trial_articles.json
│   ├── chunking_trial_clauses.json
│   ├── questions.json
│   ├── questions_baseline.json
│   ├── retrieval_report.json
│   ├── retrieval_report_baseline.json
│   ├── retrieval_report_pilot.json
│   └── run_evaluation.py
├── src/
│   ├── __init__.py
│   ├── build_index.py
│   ├── chunking.py
│   ├── config.py
│   ├── demo_retrieve.py
│   ├── document_loader.py
│   ├── embeddings.py
│   └── retriever.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_chunking.py
│   ├── test_document_loader.py
│   ├── test_embeddings.py
│   ├── test_integration.py
│   └── test_retriever.py
├── .gitignore
├── README.md
└── requirements.txt
```

## File đã tạo/sửa và chức năng

| Nhóm | File và vai trò |
|---|---|
| CV12 | `src/config.py` cấu hình; `src/document_loader.py` xác thực/extract theo trang; `src/chunking.py` chuẩn hóa/chia điều-khoản-điểm và overlap; `src/build_index.py --chunks-only` lưu chunks |
| CV13 | `src/embeddings.py` E5/prefix/token/vector; `src/build_index.py` build ba artifact và checksum; `src/retriever.py` cache/validate/cosine Top-k |
| CV14 | `src/demo_retrieve.py` CLI; `evaluation/questions.json` nhãn đã xác minh; `evaluation/run_evaluation.py` chấm theo ID/nguồn/trang/nội dung và xuất báo cáo |
| Tests | `tests/conftest.py`, năm file `test_*.py`, `__init__.py`; PDF/model thật và negative tests trên bản sao tạm |
| Tài liệu | `README.md` thay bằng hướng dẫn chạy/kết quả thật; bản đặc tả README cũ giữ nguyên tại `docs/technical_spec.md`; `docs/code2_integration.md`, `docs/ingestion_notes.md`, file này và `docs/environment.txt` |
| Thiết lập | `requirements.txt`, `.gitignore`, package `__init__.py` |
| Dữ liệu | Bản sao PDF tên chuẩn; index baseline/pilot/full, báo cáo và logs đều sinh từ thực thi thật |

## Lệnh đã chạy và kết quả

Các lệnh sử dụng `.venv/bin/python` trên máy thực thi; sau khi kích hoạt môi trường có thể dùng `python`:

```bash
python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out data/processed --pages 8-31 --chunks-only
python -m pytest -q tests/test_document_loader.py tests/test_chunking.py
python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out data/processed --pages 8-31
python -m src.demo_retrieve --question "Một tín chỉ học lý thuyết được quy định bao nhiêu giờ, và cần bao nhiêu giờ tự học có hướng dẫn?" --top-k 3
python -m evaluation.run_evaluation
python -m pytest -q --run-model
# Chỉ sau pilot đạt: full build và đánh giá lại
python -m src.build_index --input data/so_tay_sinh_vien_k50.pdf --out data/processed
python -m evaluation.run_evaluation
python -m pytest -q
python -m pytest -q --run-model
```

| Mốc | Output thật |
|---|---|
| CV12 ban đầu | 24/24 trang, 43.281 ký tự thô, 122 chunks; 23 passed |
| CV13 baseline | (122, 384), float32/L2; 30 passed |
| CV14 baseline | Hit@3 2/3; 2 failed, 56 passed; đã lưu để phân tích |
| Pilot cuối sau sửa chunking | 254 chunks; max 143 tokens; Hit@3 3/3; 59 passed in 5.10s |
| Full | 220/220 trang có text, 376.208 ký tự thô, 1.907 chunks, (1907, 384), max 200 tokens; Hit@3 3/3 |
| Tests nhanh cuối | 52 passed, 7 skipped in 0.96s |
| Tests E5/integration đầy đủ cuối | 59 passed in 6.29s |
| Kiểm tra bổ sung | Không mất ký tự ngoài khoảng trắng sau normalize trên toàn 220 trang; chunk IDs/text/nguồn/trang của pilot giữ nguyên ở full |
| Tích hợp Code 2 | Import và retrieve thành công từ working directory khác; schema đúng năm khóa; xem `code2_smoke.log` |

## Ba câu hỏi và Top-3 full

Nguồn chung: `so_tay_sinh_vien_k50.pdf`. ID viết tắt bỏ tiền tố `so_tay_sinh_vien_k50-`; report JSON chứa ID đầy đủ và toàn bộ văn bản từng kết quả.

| Câu | Câu hỏi | Top-3 theo thứ tự, trang và cosine | Hit |
|---|---|---|---|
| Q01 | Một tín chỉ học lý thuyết được quy định bao nhiêu giờ, và cần bao nhiêu giờ tự học có hướng dẫn? | 1. `p008-c006` / trang 8 / 0.931322; 2. `p032-c006` / trang 32 / 0.931322; 3. `p072-c003` / trang 72 / 0.895142 | 1 |
| Q02 | Sinh viên cần hoàn thành học phần tiên quyết vào thời điểm nào? | 1. `p009-c007` / trang 9 / 0.902875; 2. `p033-c007` / trang 33 / 0.902875; 3. `p019-c006` / trang 19 / 0.880307 | 1 |
| Q03 | Sinh viên chính quy bắt đầu tự đăng ký học phần từ học kỳ nào? | 1. `p011-c008` / trang 11 / 0.892101; 2. `p035-c006` / trang 35 / 0.892101; 3. `p015-c011` / trang 15 / 0.891929 | 1 |

**Hit@3 = 3/3 = 1,0**. [Báo cáo full](../evaluation/retrieval_report.json), [pilot](../evaluation/retrieval_report_pilot.json), [lịch sử thất bại/thử nghiệm](ingestion_notes.md).

## Điểm còn giới hạn/chưa kiểm chứng

Không còn mục triển khai CV12–CV14 bị chặn trong môi trường đã chạy. Chưa kiểm chứng trực tiếp Windows/Linux; chưa đối chiếu thủ công toàn bộ 220 trang, mọi bảng hoặc mọi câu hỏi. Cấu trúc hàng/cột PDF chưa được bảo toàn, không OCR. Ba câu chỉ là benchmark nhỏ. Quy chế trùng nội dung gây cạnh tranh Top-3; Q03 đúng ở hạng 3, không bảo đảm top-1 đúng. Xem chi tiết trong `ingestion_notes.md`.
