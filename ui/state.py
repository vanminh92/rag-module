"""Session-local events. None of these operations perform retrieval or inference."""

from datetime import datetime
from uuid import uuid4


def initialize(state):
    for key, value in {"chats": {}, "active_chat_id": None, "pdf_panel_open": True,
                       "pdf_focus": False, "debug_enabled": False, "is_generating": False,
                       "request": None, "delete_chat_id": None, "backend_invocations": 0}.items():
        if key not in state:
            state[key] = value
    if not state["chats"]:
        new_chat(state)


def new_chat(state):
    if state.get("is_generating"):
        return
    identifier = uuid4().hex
    state["chats"][identifier] = {"id": identifier, "title": "Cuộc trò chuyện mới",
                                "created_at": datetime.now().isoformat(), "messages": [],
                                "selection": None, "pdf_page": 1}
    state["active_chat_id"] = identifier
    state["pdf_focus"] = False
    return identifier


def active_chat(state):
    return state["chats"][state["active_chat_id"]]


def switch_chat(state, identifier):
    if not state["is_generating"] and identifier in state["chats"]:
        state["active_chat_id"] = identifier
        state["pdf_focus"] = False
        state["delete_chat_id"] = None


def delete_chat(state, identifier):
    if state["is_generating"]:
        return
    state["chats"].pop(identifier, None)
    state["delete_chat_id"] = None
    if state["active_chat_id"] == identifier:
        state["active_chat_id"] = next(reversed(state["chats"]), None)
    if not state["chats"]:
        new_chat(state)
    state["pdf_focus"] = False


def enqueue(state, question):
    if state["is_generating"] or not isinstance(question, str) or not question.strip():
        return False
    question = question.strip()
    chat = active_chat(state)
    if not chat["messages"]:
        chat["title"] = question[:56] + ("…" if len(question) > 56 else "")
    request_id = uuid4().hex
    chat["messages"].append({"id": uuid4().hex, "role": "user", "content": question})
    state["request"] = {"id": request_id, "chat_id": chat["id"], "question": question, "status": "queued"}
    state["is_generating"] = True
    return True


def complete_request(state, request, result=None, error=None):
    chat = state["chats"].get(request["chat_id"])
    if chat is not None and not any(m.get("request_id") == request["id"] for m in chat["messages"]):
        chat["messages"].append({"id": uuid4().hex, "role": "assistant", "request_id": request["id"],
                                 "result": result, "error": error})
    request["status"] = "done"
    state["is_generating"] = False


def select_evidence(state, message_id, chunk_id):
    if state["is_generating"]:
        return
    chat = active_chat(state)
    for message in chat["messages"]:
        if message["id"] != message_id:
            continue
        for source in (message.get("result") or {}).get("ui_sources", []):
            if source["chunk_id"] == chunk_id:
                chat["selection"] = {"message_id": message_id, "chunk_id": chunk_id}
                set_page(state, source["page"])
                state["pdf_panel_open"] = state["pdf_focus"] = True
                return
    raise ValueError("Nguồn không thuộc câu trả lời đang chọn.")


def selected_source(state):
    chat = active_chat(state)
    selection = chat["selection"]
    if selection:
        for message in chat["messages"]:
            if message["id"] == selection["message_id"]:
                return next((s for s in (message.get("result") or {}).get("ui_sources", [])
                             if s["chunk_id"] == selection["chunk_id"]), None)
    return None


def set_page(state, page, page_count=None):
    if type(page) is not int or page < 1 or (page_count is not None and page > page_count):
        raise ValueError("Số trang PDF không hợp lệ.")
    chat = active_chat(state)
    chat["pdf_page"] = page
    state[f'pdf_page_{chat["id"]}'] = page


def open_panel(state):
    state["pdf_panel_open"] = state["pdf_focus"] = True


def close_panel(state):
    state["pdf_panel_open"] = state["pdf_focus"] = False
