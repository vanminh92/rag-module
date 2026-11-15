"""UI interactions use saved responses; only a submission calls the pipeline."""

from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock
import json

import pytest
from streamlit.testing.v1 import AppTest
from src import config
from src.answering import QAResult
from src.retriever import IndexValidationError
from ui import app_service, state
from ui.evidence import read_catalog, validated_sources, verified_claim_sources

APP = str(Path(__file__).resolve().parents[1] / "streamlit_qa_app.py")


@pytest.fixture
def backend(monkeypatch):
    index = read_catalog(config.INDEX_DIR / "chunks.json")
    source = next(s for s in index.values() if s["page"] == 15 and "Từ học kỳ thứ hai" in s["text"])
    source2 = next(s for s in index.values() if s["page"] == 8 and "15 giờ học lý thuyết" in s["text"])
    result = QAResult("partial", "Phần trả lời có bằng chứng [1] [2].",
        sources=[source, source2], missing_information=["Chưa xác minh phần còn lại."],
        debug={"total_seconds": 1, "plan": {}, "rounds": [], "contexts": [], "candidates": [], "llm_calls": []})
    pipeline = Mock()
    pipeline.ask.return_value = result
    monkeypatch.setattr("src.pipeline.get_pipeline", lambda *a, **k: pipeline)
    monkeypatch.setattr(app_service, "health", Mock(return_value={"status": "ready"}))
    return pipeline, source, source2


def button(app, key):
    return next(b for b in app.button if b.key == key)


def test_chat_submission_citations_navigation_and_debug_do_not_repeat_backend(backend):
    pipeline, source, other = backend
    app = AppTest.from_file(APP).run()
    assert not app.exception and pipeline.ask.call_count == 0
    app.chat_input[0].set_value("Câu hỏi tự do có nhiều ý?").run()
    assert not app.exception and pipeline.ask.call_count == 1
    assert len(app.chat_message) == 2
    assert any("một phần" in w.value for w in app.warning)
    citation = next(b for b in app.button if b.key.startswith("cite_") and source["chunk_id"] in b.key)
    citation.click().run()
    assert app.session_state["chats"][app.session_state["active_chat_id"]]["pdf_page"] == 15
    assert any(source["text"] == t.value for t in app.text)
    button(app, "pdf_next").click().run()
    assert app.number_input[0].value == 16
    assert any("thuộc trang 15" in i.value for i in app.info)
    button(app, "back_to_source").click().run()
    assert app.number_input[0].value == 15
    next(b for b in app.button if b.key.startswith("cite_") and other["chunk_id"] in b.key).click().run()
    assert app.number_input[0].value == 8
    app.sidebar.toggle[0].set_value(True).run()
    assert any(e.label == "Developer Debug" for e in app.expander)
    app.selectbox[0].select("125%").run()
    app.selectbox[1].select("Bản dự phòng").run()
    assert not app.exception and pipeline.ask.call_count == 1
    button(app, "close_pdf").click().run()
    assert pipeline.ask.call_count == 1


def test_two_chats_history_delete_confirmation_and_empty_submission(backend):
    pipeline, _, _ = backend
    app = AppTest.from_file(APP).run()
    app.chat_input[0].set_value("   ").run()
    assert pipeline.ask.call_count == 0
    first_id = app.session_state["active_chat_id"]
    app.chat_input[0].set_value("Câu hỏi đầu tiên").run()
    button(app, "new_chat").click().run()
    second_id = app.session_state["active_chat_id"]
    assert second_id != first_id and len(app.chat_message) == 0
    app.chat_input[0].set_value("Câu hỏi thứ hai").run()
    button(app, f"chat_{first_id}").click().run()
    assert app.chat_message[0].markdown[0].value == "Câu hỏi đầu tiên"
    assert pipeline.ask.call_count == 2
    button(app, "delete_chat").click().run()
    button(app, "cancel_delete").click().run()
    assert first_id in app.session_state["chats"]
    button(app, "delete_chat").click().run()
    button(app, "confirm_delete").click().run()
    assert first_id not in app.session_state["chats"]
    assert app.session_state["active_chat_id"] == second_id
    assert pipeline.ask.call_count == 2 and not app.exception


@pytest.mark.parametrize("error,expected", [(ConnectionError("offline"), "Ollama"),
    (IndexValidationError("bad index"), "index"), (FileNotFoundError("missing"), "index")])
def test_errors_keep_history_and_dont_auto_retry(backend, error, expected):
    pipeline, _, _ = backend
    pipeline.ask.side_effect = error
    app = AppTest.from_file(APP).run()
    app.chat_input[0].set_value("Câu hỏi bị lỗi").run()
    assert not app.exception
    assert any(expected in e.value for e in app.error)
    assert len(app.chat_message) == 2
    app.run()
    assert pipeline.ask.call_count == 1
    assert not app.session_state["is_generating"]


def test_no_evidence_has_no_citation_buttons(backend):
    pipeline, _, _ = backend
    pipeline.ask.return_value = QAResult("insufficient", "Chưa đủ bằng chứng.")
    app = AppTest.from_file(APP).run()
    app.chat_input[0].set_value("Ngoài tài liệu?").run()
    assert not any(b.key.startswith("cite_") for b in app.button)
    assert any("đủ bằng chứng" in i.value for i in app.info)


def test_pdf_failure_keeps_source_excerpt(backend, monkeypatch):
    _, source, _ = backend
    monkeypatch.setattr("ui.pdf_panel.document", Mock(side_effect=ValueError("PDF mismatch")))
    app = AppTest.from_file(APP).run()
    app.chat_input[0].set_value("Tôi muốn xem nguồn").run()
    next(b for b in app.button if b.key.startswith("cite_") and source["chunk_id"] in b.key).click().run()
    assert not app.exception
    assert any("Không hiển thị được PDF" in e.value for e in app.error)
    assert any(t.value == source["text"] for t in app.text)


def test_pdf_component_python_error_uses_real_fallback(backend, monkeypatch):
    monkeypatch.setattr("streamlit_pdf_viewer.pdf_viewer", Mock(side_effect=RuntimeError("viewer failed")))
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert any("dự phòng" in w.value for w in app.warning)
    assert any("trang 1 của PDF gốc" in c.value for c in app.caption)


def test_source_validation_rejects_fake_and_out_of_range_and_deduplicates(backend):
    _, a, b = backend
    catalog = read_catalog(config.INDEX_DIR / "chunks.json")
    valid, errors = validated_sources([a,a,b,{**a,"page":221},{**a,"source":"../../bad.pdf"},
                                      {**a,"chunk_id":"invented"},{**a,"text":"fake"}],catalog,config.INPUT_PATH.name,220)
    assert [s["chunk_id"] for s in valid] == [a["chunk_id"],b["chunk_id"]]
    assert len(errors)==4
    assert not verified_claim_sources({"citations":[{"source_id":a["chunk_id"],"quote":"invented quote"}]},valid)
    assert verified_claim_sources({"citations":[{"source_id":a["chunk_id"],"quote":a["text"]}]},valid)


def test_session_events_lock_pending_work_and_keep_selection_per_chat(backend):
    s={};state.initialize(s);first=s["active_chat_id"]
    assert state.enqueue(s,"Một câu hỏi")
    assert not state.enqueue(s,"Không được gửi đôi")
    assert state.new_chat(s) is None
    request=s["request"];request["status"]="running"
    assert not app_service.process_pending(s)
    state.complete_request(s,request,result={"ui_sources":[backend[1]]})
    message=state.active_chat(s)["messages"][-1]
    state.select_evidence(s,message["id"],backend[1]["chunk_id"])
    second=state.new_chat(s)
    assert state.selected_source(s) is None
    state.switch_chat(s,first)
    assert state.selected_source(s)["chunk_id"]==backend[1]["chunk_id"]
    with pytest.raises(ValueError):state.select_evidence(s,"wrong",backend[1]["chunk_id"])
    for bad in (0,-1,221,True,1.5):
        with pytest.raises(ValueError):state.set_page(s,bad,220)


def test_single_page_fallback_is_physical_page_15():
    from io import BytesIO
    from pypdf import PdfReader
    from ui.pdf_document import document,one_page
    info=document();assert info["page_count"]==220
    page=PdfReader(BytesIO(one_page(info["bytes"],15)))
    assert len(page.pages)==1
    text=" ".join(page.pages[0].extract_text().split())
    assert "Từ học kỳ thứ hai" in text
    for bad in (0,221):
        with pytest.raises(ValueError):one_page(info["bytes"],bad)


def test_mobile_evidence_is_a_separate_screen_and_back_keeps_chat(backend, monkeypatch):
    pipeline, source, _ = backend
    monkeypatch.setattr("ui.app.viewport",lambda:{"mode":"mobile","height":850})
    app=AppTest.from_file(APP).run()
    app.chat_input[0].set_value("Câu hỏi trên điện thoại").run()
    next(b for b in app.button if b.key.startswith("cite_") and source["chunk_id"] in b.key).click().run()
    assert not app.chat_input
    assert button(app,"close_pdf").label=="Quay lại hội thoại"
    button(app,"close_pdf").click().run()
    assert len(app.chat_input)==1 and len(app.chat_message)==2
    assert pipeline.ask.call_count==1 and not app.exception


def test_claim_mapping_uses_verified_source_ids(backend):
    pipeline, source, _ = backend
    pipeline.ask.return_value.claims=[{"text":"Câu có mapping từ backend.","citations":[
        {"source_id":source["chunk_id"],"quote":source["text"]}]}]
    app=AppTest.from_file(APP).run()
    app.chat_input[0].set_value("Hỏi về nguồn").run()
    assert any("_claim_0_" in b.key for b in app.button if b.key.startswith("cite_"))
    assert not app.exception


def test_wrong_pdf_version_is_not_opened_for_saved_evidence(backend,monkeypatch):
    _,source,_=backend
    from ui.pdf_document import document
    real=document()
    monkeypatch.setattr("ui.pdf_panel.document",lambda:{**real,"sha256":"different"})
    app=AppTest.from_file(APP).run()
    app.chat_input[0].set_value("Xem PDF có đúng phiên bản không?").run()
    next(b for b in app.button if b.key.startswith("cite_") and source["chunk_id"] in b.key).click().run()
    assert any("Không hiển thị được PDF" in e.value for e in app.error)
    assert any(t.value==source["text"] for t in app.text)
    assert not app.exception
