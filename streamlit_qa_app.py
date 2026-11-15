"""Free-form, source-grounded Vietnamese handbook QA with an optional debug view."""

from dataclasses import asdict, replace

import streamlit as st
from httpx import RequestError
from ollama import ResponseError

from src import config
from src.answering import AnswerGenerator, NO_ANSWER
from src.llm import OllamaJSON
from src.entailment import get_entailment
from src.pipeline import get_pipeline
from src.retriever import IndexValidationError
from src.settings import RAGSettings

MODEL = RAGSettings.from_env().model
TITLE = "Hỏi đáp Sổ tay sinh viên Khóa 50"


def generate_answer(question: str, chunks: list[dict]) -> tuple[str, list[dict]]:
    """Keep the original helper's calling convention for existing integrations."""
    settings = RAGSettings.from_env()
    checker = (lambda premise, hypothesis: get_entailment().check(premise, hypothesis)) if settings.support_check == "nli" else None
    result = AnswerGenerator(OllamaJSON(settings), entailment=checker).generate(question, chunks)
    return result.answer, result.sources


def display_result(result: dict, debug: bool):
    st.subheader("Câu trả lời")
    if result["status"] == "partial":
        st.warning("Chỉ tìm được bằng chứng để trả lời một phần câu hỏi.")
    elif result["status"] == "insufficient":
        st.info("Chưa có đủ bằng chứng trong tài liệu để trả lời.")
    st.write(result["answer"])
    if result["missing_information"]:
        st.caption("Phần chưa xác minh: " + " · ".join(result["missing_information"]))
    if result["sources"]:
        st.subheader("Nguồn")
        for index, source in enumerate(result["sources"], 1):
            label = f'[{index}] {source["source"]} · trang PDF {source["page"]}'
            with st.expander(label):
                metadata = source.get("metadata", {})
                heading = " · ".join(dict.fromkeys(metadata.get(key, "") for key in ("regulation", "article_title")))
                if heading.strip(" ·"):
                    st.caption(heading)
                for quote in dict.fromkeys(source.get("quotes", [])):
                    st.text(quote)
                st.caption("Toàn bộ đoạn nguồn")
                st.text(source["text"])
    for warning in result["warnings"]:
        st.caption(warning)
    if debug:
        with st.expander("Debug dành cho nhà phát triển", expanded=True):
            data = result["debug"]
            st.caption(f'Tổng thời gian: {data["total_seconds"]:.2f}s · Số lượt truy xuất: {len(data["rounds"])}')
            st.write("Phân tích câu hỏi và truy vấn tìm kiếm")
            st.json(data["plan"])
            st.write("Ứng viên E5/BM25 theo từng lượt")
            st.json(data["rounds"], expanded=False)
            st.write("Hợp nhất RRF và reranking")
            st.json(data["candidates"], expanded=False)
            st.write("Ngữ cảnh cuối")
            st.json(data["contexts"], expanded=False)
            st.write("Phản hồi LLM, kiểm tra chứng cứ và lần sửa")
            st.json(data["generation_attempts"], expanded=False)
            st.json(data["llm_calls"], expanded=False)


def main() -> None:
    st.set_page_config(page_title=TITLE)
    st.title(TITLE)
    st.caption("Đặt câu hỏi bằng lời của bạn. Câu trả lời dựa trên Sổ tay sinh viên Khóa 50, kèm trang PDF để đối chiếu.")
    settings = RAGSettings.from_env()
    debug = st.sidebar.checkbox("Debug dành cho nhà phát triển")
    if debug:
        choices = ["lexical", "none", "cross-encoder"]
        mode = st.sidebar.selectbox("Reranker", choices, index=choices.index(settings.reranker))
        rewrite = st.sidebar.checkbox("Viết lại truy vấn bằng Qwen cục bộ", value=settings.rewrite == "llm")
        settings = replace(settings, reranker=mode, rewrite="llm" if rewrite else "rules")
    with st.form("student_handbook_question"):
        question = st.text_area("Câu hỏi", placeholder="Nhập câu hỏi bất kỳ liên quan đến nội dung sổ tay…", height=100)
        submitted = st.form_submit_button("Hỏi")
    if submitted:
        if not question.strip():
            st.info("Bạn hãy nhập câu hỏi.")
            return
        st.session_state.pop("qa_result", None)
        try:
            with st.spinner("Đang tìm tài liệu, tổng hợp và kiểm tra bằng chứng…"):
                pipeline = get_pipeline(str(config.INDEX_DIR.resolve()), settings)
                st.session_state["qa_result"] = asdict(pipeline.ask(question.strip()))
                st.session_state["answered_question"] = question.strip()
        except ResponseError as exc:
            st.error(f"Ollama báo lỗi ({exc.status_code}): {exc.error}")
            return
        except (ConnectionError, RequestError):
            st.error("Không kết nối được với Ollama. Hãy mở Ollama rồi thử lại.")
            return
        except (FileNotFoundError, IndexValidationError, ValueError, OSError, RuntimeError) as exc:
            st.error(f"Chưa xử lý được câu hỏi. {exc}")
            return
    if "qa_result" in st.session_state:
        st.caption("Câu hỏi: " + st.session_state.get("answered_question", ""))
        display_result(st.session_state["qa_result"], debug)


if __name__ == "__main__":
    main()
