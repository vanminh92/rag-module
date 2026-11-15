"""Exercise free-form submission, partial evidence and persistent debug output."""

from pathlib import Path
import json

from streamlit.testing.v1 import AppTest

from src.answering import QAResult
from src import config


def test_free_form_partial_answer_and_debug_survive_rerun(monkeypatch):
    calls = []
    chunks = json.loads((config.INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
    source = next(chunk for chunk in chunks if chunk["page"] == 8 and "15 giờ học lý thuyết" in chunk["text"])

    class Pipeline:
        def ask(self, question):
            calls.append(question)
            return QAResult("partial", "Chỉ xác minh được phần có bằng chứng.",
                            missing_information=["Chưa có dữ liệu phần còn lại."],
                            sources=[{**source, "quotes": [source["text"]]}],
                            debug={"total_seconds": 1, "rounds": [], "plan": {}, "candidates": [],
                                   "contexts": [], "generation_attempts": [], "llm_calls": []})

    monkeypatch.setattr("src.pipeline.get_pipeline", lambda *a, **k: Pipeline())
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_qa_app.py")).run()
    question = "Câu hỏi tự do có nhiều ý và chưa đủ dữ liệu?"
    app.text_area[0].input(question)
    app.button[0].click().run()
    assert not app.exception
    assert calls == [question]
    assert any("một phần" in warning.value for warning in app.warning)
    assert any("trang PDF 8" in expander.label for expander in app.expander)
    app.sidebar.checkbox[0].check().run()
    assert not app.exception and calls == [question]
    assert any("Debug" in expander.label for expander in app.expander)


def test_empty_question_does_not_call_pipeline(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Empty questions must not call retrieval/generation")

    monkeypatch.setattr("src.pipeline.get_pipeline", fail)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_qa_app.py")).run()
    app.button[0].click().run()
    assert not app.exception
    assert app.info[0].value == "Bạn hãy nhập câu hỏi."
