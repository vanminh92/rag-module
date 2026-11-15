"""An adapter around the current pipeline; no prompt, model or retrieval changes."""

from dataclasses import asdict
import logging
import json
import time
import traceback

import streamlit as st
from httpx import RequestError
from ollama import Client, ResponseError

from src import config
from src.retriever import IndexValidationError
from src.settings import RAGSettings
from .evidence import read_catalog, validated_sources


@st.cache_data(show_spinner=False, ttl=15, max_entries=4)
def health(host, model):
    try:
        names = {m.model for m in Client(host=host, timeout=1.5).list().models}
        return {"status": "ready" if model in names else "missing_model",
                "model": model, "checked_at": time.time()}
    except Exception as exc:
        return {"status": "offline", "model": model, "checked_at": time.time(),
                "detail": f"{type(exc).__name__}: {exc}"}


@st.cache_data(show_spinner=False, max_entries=2)
def catalog(path, modified_ns, size):
    return read_catalog(path)


def ask(question):
    # Import here: opening the interface, browsing PDF or switching chats does
    # not initialize E5/NLI or acquire a pipeline.
    from src.pipeline import get_pipeline

    settings = RAGSettings.from_env()
    result = asdict(get_pipeline(str(config.INDEX_DIR.resolve()), settings).ask(question))
    result["ui_model"] = settings.model
    result["ui_sources"], result["ui_warnings"] = [], []
    if result.get("sources"):
        try:
            path = config.INDEX_DIR / "chunks.json"
            stat = path.stat()
            index = catalog(str(path), stat.st_mtime_ns, stat.st_size)
            meta = json.loads((config.INDEX_DIR / "index_meta.json").read_text(encoding="utf-8"))
            result["ui_sources"], result["ui_warnings"] = validated_sources(
                result["sources"], index, config.INPUT_PATH.name, meta["page_range"][1])
            for source in result["ui_sources"]:
                source["ui_document_sha256"] = meta["source_sha256"]
        except (OSError, ValueError, KeyError) as exc:
            # Never discard a saved answer just because the PDF viewer failed.
            result["ui_warnings"] = [f"Không xác minh được liên kết PDF: {exc}"]
    return result


def error_message(exc):
    model = RAGSettings.from_env().model
    if isinstance(exc, ResponseError):
        if exc.status_code == 404:
            text = f"Ollama chưa có model {model}. Hãy chạy: ollama pull {model}"
        else:
            text = f"Ollama báo lỗi ({exc.status_code}). Hãy kiểm tra Ollama rồi gửi lại câu hỏi."
    elif isinstance(exc, (ConnectionError, RequestError)):
        text = "Không kết nối được Ollama. Hãy mở Ollama trên máy rồi gửi lại câu hỏi."
    elif isinstance(exc, (IndexValidationError, FileNotFoundError)):
        text = "Không đọc được index hoặc tài liệu. Hãy kiểm tra data/processed và PDF gốc; ứng dụng không tự build lại index."
    else:
        text = "Chưa xử lý được câu hỏi. Hội thoại đã được giữ lại; hãy kiểm tra chi tiết trong Developer mode."
    return {"message": text, "detail": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}


def process_pending(state):
    from .state import complete_request

    request = state.get("request")
    if not request or request["status"] != "queued":
        return False
    request["status"] = "running"  # consume before any work; never retry on UI reruns
    state["backend_invocations"] += 1
    try:
        result = ask(request["question"])
        complete_request(state, request, result=result)
    except Exception as exc:
        logging.getLogger(__name__).exception("Question failed: request %s", request["id"])
        complete_request(state, request, error=error_message(exc))
    finally:
        if request["status"] == "running":
            complete_request(state, request, error={"message": "Lượt xử lý đã bị ngắt. Hãy gửi lại câu hỏi.", "detail": "Interrupted request"})
    return True
