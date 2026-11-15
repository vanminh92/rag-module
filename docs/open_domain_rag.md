# Hỏi đáp tự do trong phạm vi PDF

## Các thành phần

`src.retriever.retrieve(question, top_k=3)` và `Retriever.retrieve()` không đổi: dense E5, cosine giảm dần, đúng năm trường đã bàn giao. Không thay PDF, chunking, embeddings, checksum hoặc câu hỏi CV14. Streamlit gọi API mới `RAGPipeline` để nhận cả câu trả lời và chẩn đoán.

Luồng mặc định:

1. NFC và khoảng trắng; nhận diện ý định, cấp đào tạo, loại hình, số liệu, đối tượng và thời điểm được nêu. Giữ câu hỏi gốc trong mọi lượt. Từ đồng nghĩa chỉ phục vụ tìm kiếm, không chứa đáp án/trang/ID benchmark. Có thể bật Qwen để viết lại và tách truy vấn; mặc định dùng quy tắc để giảm độ trễ.
2. Tối đa 4 truy vấn/lượt. Mỗi truy vấn tìm 20 ứng viên bằng E5 và 20 bằng BM25 Okapi. BM25 giữ dấu, dùng âm tiết và n-gram 2/3 âm tiết để biểu diễn từ ghép tiếng Việt, không phụ thuộc tokenizer/model ngoài. Truy vấn E5 vẫn dùng `query:` và revision cũ, batch các biến thể.
3. Lọc phạm vi đã nêu; RRF với k=60, chuẩn hóa theo số danh sách để so được giữa hai lượt. Loại đoạn trùng trong cùng phạm vi; không gộp đoạn giống nhau của hai quy chế khác nhau. Reranking mặc định dùng RRF, độ phủ từ và cụm từ; không coi các score là xác suất có đáp án.
4. Chọn 4 đoạn cho câu đơn, tối đa 8 cho câu phức hợp; ngân sách mặc định 2.200 token ước lượng bằng tokenizer E5, gồm phần dự phòng metadata. Đây không phải số token Qwen chính xác. Ollama dùng `num_ctx=8192`; số token thật được lưu khi gọi model.
5. Ưu tiên truy vấn con và phạm vi cần so sánh. Mở rộng tối đa các chỗ còn trống bằng lân cận cùng quy chế, điều, khoản, phạm vi, cách không quá một trang; từng chunk giữ ID và trang riêng. Nếu model thiếu chứng cứ, dùng phần thiếu để tìm thêm, tổng tối đa 2 lượt.
6. Qwen tạo các luận điểm, mỗi luận điểm tự chọn nguồn. Schema giới hạn ID và buộc quote bằng toàn văn chunk ngắn đã chọn (index gốc tối đa 500 ký tự), không theo câu hỏi benchmark. Cách này tránh việc model 3B chọn câu gần đó nhưng bỏ mất điều kiện quyết định. Không tự thêm nguồn khi model thiếu ID; trích đúng vẫn chưa tự chứng minh tính liên quan.
7. Kiểm tra ID, trích đoạn nguyên văn, vị trí ký tự, đối tượng và số liệu; số thứ tự khoản không được dùng làm số liệu trả lời. Tên chỉ số được kiểm tra riêng để không đổi điểm học kỳ thành tích lũy hoặc điểm rèn luyện. Một lần gọi Qwen riêng đánh giá hỗ trợ ngữ nghĩa, tính liên quan và độ đầy đủ. NLI đa ngôn ngữ cục bộ kiểm tra thêm các câu diễn giải; không dùng score NLI để suy ra đã tìm đủ tài liệu. Các câu trả lời chỉ vài từ được mở rộng bằng chính trích đoạn nguyên văn mô hình đã chọn, rồi kiểm tra lại đối tượng/chỉ số. Không tự thêm nguồn. Kiểm tra các phạm vi được yêu cầu và các mục cùng khoản còn thiếu để không coi một trường hợp là toàn bộ quy định.
8. Phản hồi sai hoặc thiếu được sửa tối đa một lần, ưu tiên câu nguồn khi mô hình dễ mất điều kiện; có thể kết hợp lượt tìm bổ sung. Chỉ dựng câu trả lời từ luận điểm đã qua kiểm tra; giữ phần có căn cứ nếu phần còn lại thất bại.

Tối đa một lần viết lại tùy chọn, hai lượt retrieval, hai lần sinh và hai lần kiểm tra ngữ nghĩa mỗi câu hỏi. Không có vòng lặp không giới hạn.

## Metadata và bảng

`src/document_structure.py` đọc ranh giới dòng PDF để nhận diện phần/chương/điều/khoản/điểm. ID quy chế bao gồm trang bắt đầu, tránh nối Điều 12 của đại học với Điều 12 của cao đẳng. Tiêu đề xuống dòng được nối thận trọng; phạm vi kế thừa qua trang và dừng tại quy chế/phần mới. Tên “Trường Đại học” không được dùng để suy ra mọi quy chế chỉ áp dụng cho trình độ đại học.

Sidecar `structure.json` gắn với hash PDF, chunks, phiên bản parser và checksum metadata. File thiếu, hỏng hoặc cũ được tạo lại; thư mục chỉ đọc dùng metadata trong RAM. Không tái trích xuất PDF hoặc encode passages ở mỗi truy vấn. Retriever cũ vẫn tự kiểm tra tính toàn vẹn index/PDF.

Bảng/sơ đồ được pypdf trích xuất tuyến tính, chưa tái dựng ô. Trang có dấu hiệu bảng được gắn `table_risk` và cảnh báo trong prompt, kiểm chứng và giao diện. Không cam kết trả lời được quan hệ hàng/cột hoặc chữ nằm trong ảnh. Trang hiển thị luôn là vị trí vật lý PDF 1-based từ metadata, không phải số trang LLM viết ra.

## Cấu hình

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `RAG_MODEL` | `qwen2.5:3b` | Model Ollama, không đổi mặc định |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama cục bộ |
| `RAG_INDEX_DIR` | `data/processed` | Artifact E5 cũ |
| `RAG_QUERY_REWRITE` | `rules` | `rules` hoặc `llm` |
| `RAG_RERANKER` | `lexical` | `none`, `lexical`, `cross-encoder` |
| `RAG_SUPPORT_CHECK` | `nli` | `nli` hoặc `llm`; bỏ NLI để đối chiếu bộ nhớ/độ trễ |
| `RAG_RERANK_MODEL` | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | Model neural tùy chọn hoặc đường dẫn local |
| `RAG_CONTEXT_TOKENS` | `2200` | Ngân sách ngữ cảnh ước lượng |

Neural reranker chỉ dùng cache local, CPU, batch 8, max_length 512. Chưa tải model thì báo lỗi thay vì âm thầm gọi mạng. Muốn thử, tải một lần trước khi chạy:

```bash
.venv/bin/python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1', cache_folder='.cache/models', device='cpu')"
RAG_RERANKER=cross-encoder .venv/bin/python -m evaluation.run_benchmark --split dev --system hybrid --reranker cross-encoder --out evaluation/neural_dev.json
```

Không khuyến nghị bật neural reranker cho bản bàn giao trước khi đo trên tập phát triển. Benchmark hiện tại đánh giá mặc định lexical và ablation `none`; không tuyên bố neural tốt hơn hoặc đã kiểm tra bộ nhớ của nó.

NLI sử dụng `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, revision `8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c`, CPU float32. Chuẩn bị bằng `python -m src.entailment --download`; lúc hỏi chỉ đọc cache. NLI có giới hạn 512 token, không âm thầm cắt chứng cứ. Ngưỡng entailment 0,7 là cổng kiểm tra thử nghiệm, không phải xác suất trả lời đúng. Model này bổ sung kiểm tra, không thay Qwen2.5 3B hoặc E5.

Các probe dev tại `evaluation/nli_development_probes.json` và `evaluation/nli_structured_probes.json` cho thấy cần tiêu đề điều/khoản để kiểm chứng đúng, đồng thời NLI vẫn có thể nhầm học kỳ với tích lũy. Vì vậy còn cần kiểm tra tên chỉ số và kiểm tra cơ học; không tuyên bố NLI tự bảo đảm tính đúng. Thông tin và giới hạn của model có trong [model card NLI](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli).

SDK/schema tham chiếu: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [Sentence Transformers CrossEncoder](https://sbert.net/docs/package_reference/cross_encoder/model.html), [model card của reranker tùy chọn](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1).

## Giới hạn và rollback

Qwen 3B và NLI có thể bỏ sót thông tin, hiểu sai điều kiện hoặc kiểm tra ngữ nghĩa sai. Trích dẫn nguyên văn đúng không bảo đảm đã chọn đúng thông tin để trả lời câu hỏi; cần xem cả tỷ lệ hỗ trợ và câu trả lời đúng/đầy đủ trong báo cáo. Không cam kết trả lời mọi câu hỏi, không coi cosine cao là bằng chứng đủ. Chính sách hiện hành ngoài PDF, dữ liệu cá nhân và thông tin thời gian thực không có trong index.

Rollback giao diện bằng bản baseline được giữ nguyên từ commit `6be6f89`:

```bash
.venv/bin/python -m streamlit run evaluation/baseline_streamlit.py
```

Ba artifact cũ và public API không phụ thuộc pipeline mới. Dừng app mới rồi chạy baseline không cần rebuild PDF/index hoặc đổi model. Nếu xóa riêng sidecar để thử lại parser, lần dùng pipeline mới kế tiếp sẽ tạo lại nó.
