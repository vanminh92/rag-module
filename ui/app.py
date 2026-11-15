"""The Streamlit workbench. Rendering never asks the RAG pipeline."""

import streamlit as st
from src.settings import RAGSettings
from . import app_service, chat_view, pdf_panel, sidebar, state, theme
from .components import viewport


def header():
    s = st.session_state
    settings = RAGSettings.from_env()
    with st.container(key="app_header"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("### Trợ lý Sổ tay sinh viên K50", width="stretch")
            st.button("Nguồn PDF", icon=":material/menu_book:", key="open_pdf",
                      disabled=s["is_generating"], on_click=state.open_panel, args=(s,))
        connection = app_service.health(settings.ollama_host, settings.model)
        labels = {"ready": "● Đã kết nối Ollama", "missing_model": "◌ Chưa tải model", "offline": "◌ Ollama chưa kết nối"}
        st.caption(f'{labels[connection["status"]]} · {settings.model}')
        st.caption("Câu trả lời được tổng hợp từ tài liệu. Hãy đối chiếu nguồn khi sử dụng thông tin học vụ.")


@st.dialog("Bằng chứng PDF", width="large", on_dismiss=lambda: state.close_panel(st.session_state))
def evidence_dialog():
    if st.session_state["pdf_focus"]:
        pdf_panel.render(compact=True)


def main():
    st.set_page_config(page_title="K50 AI · Sổ tay sinh viên", page_icon="📘", layout="wide",
                       initial_sidebar_state="auto", menu_items={"About": "Demo tra cứu Sổ tay sinh viên K50. Không phải sản phẩm chính thức của nhà trường."})
    state.initialize(st.session_state)
    theme.apply()
    screen = viewport()
    mode, height = screen.get("mode", "desktop"), screen.get("height", 900)
    sidebar.render()
    with st.container(key="workbench"):
        header()
        if mode == "mobile" and st.session_state["pdf_focus"]:
            pdf_panel.render(compact=True)
        elif mode == "desktop" and st.session_state["pdf_panel_open"]:
            chat, pdf = st.columns([1.65, 1], gap="large", vertical_alignment="top", wrap=False)
            with chat:
                chat_view.render(max(330, height - 340))
            with pdf:
                pdf_panel.render(height=max(480, height - 200))
        else:
            chat_view.render(max(330, height - 340))
            if mode == "tablet" and st.session_state["pdf_focus"]:
                evidence_dialog()
        if st.session_state["request"] and st.session_state["request"]["status"] == "queued":
            with st.status("Đang tìm nguồn, tổng hợp và kiểm tra bằng chứng…", expanded=True) as status:
                app_service.process_pending(st.session_state)
                status.update(label="Đã xử lý câu hỏi", state="complete", expanded=False)
            st.rerun()
