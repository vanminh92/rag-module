"""Physical-page navigation, with text and an actual single-page PDF fallback."""

import logging
import streamlit as st
from src import config
from . import state
from .pdf_document import document, one_page


def render(compact=False):
    s = st.session_state
    source = state.selected_source(s)
    chat = state.active_chat(s)
    busy = s["is_generating"]
    with st.container(border=True, key="pdf_panel"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**Bằng chứng PDF**")
            label = "Quay lại hội thoại" if compact else "Đóng PDF"
            if st.button(label, icon=":material/close:", key="close_pdf", disabled=busy):
                state.close_panel(s)
                st.rerun()
        try:
            info = document()
            page_count = info["page_count"]
            page = chat["pdf_page"]
            if not 1 <= page <= page_count:
                raise ValueError("Trang được chọn nằm ngoài tài liệu gốc.")
            st.caption(f"{config.INPUT_PATH.name} · Trang PDF {page}/{page_count}")
            with st.container(horizontal=True, vertical_alignment="bottom"):
                st.button("Trước", icon=":material/chevron_left:", key="pdf_previous",
                          disabled=busy or page <= 1, on_click=state.set_page, args=(s, page - 1, page_count))
                page_key = f'pdf_page_{chat["id"]}'
                s.setdefault(page_key, page)

                def choose_page():
                    state.set_page(s, s[page_key], page_count)

                st.number_input("Trang PDF", min_value=1, max_value=page_count, step=1,
                                key=page_key, on_change=choose_page, disabled=busy, width=110)
                st.button("Sau", icon=":material/chevron_right:", key="pdf_next",
                          disabled=busy or page >= page_count, on_click=state.set_page, args=(s, page + 1, page_count))
            with st.container(horizontal=True, vertical_alignment="bottom"):
                zoom = st.selectbox("Thu phóng", ["Vừa chiều rộng", "100%", "125%", "150%"],
                                    key="pdf_zoom", disabled=busy, width=170)
                engine = st.selectbox("Trình xem", ["PDF.js", "Bản dự phòng", "Chỉ văn bản"],
                                      key="pdf_engine", disabled=busy, width=170)
            st.caption("Nếu PDF không hiển thị, chọn Bản dự phòng hoặc tải trang được chọn.")
            if engine == "PDF.js":
                try:
                    from streamlit_pdf_viewer import pdf_viewer

                    pdf_viewer(info["bytes"], height=460, pages_to_render=[page], scroll_to_page=page,
                               scroll_behavior="instant", zoom_level="auto" if zoom.startswith("Vừa") else float(zoom[:-1]) / 100,
                               resolution_boost=1, render_text=True,
                               key=f'pdf_view_{chat["id"]}_{page}_{zoom}')
                except Exception as exc:
                    logging.getLogger(__name__).exception("PDF.js rendering failed")
                    st.warning("Trình xem PDF chính không khả dụng. Đang dùng bản dự phòng.")
                    fallback(info, page, chat["id"])
                    if s["debug_enabled"]:
                        st.code(f"{type(exc).__name__}: {exc}")
            elif engine == "Bản dự phòng":
                fallback(info, page, chat["id"])
            else:
                st.info("Chế độ văn bản: xem đoạn nguồn bên dưới hoặc tải trang PDF.")
            with st.container(horizontal=True):
                st.download_button("Tải trang này", one_page(info["bytes"], page),
                                   file_name=f"K50-trang-{page}.pdf", mime="application/pdf",
                                   key="download_page", on_click="ignore")
                st.download_button("PDF gốc", info["bytes"], file_name=config.INPUT_PATH.name,
                                   mime="application/pdf", key="download_original", on_click="ignore")
        except (OSError, ValueError, KeyError) as exc:
            st.error("Không hiển thị được PDF gốc. Bạn vẫn có thể đọc đoạn nguồn đã truy xuất bên dưới.")
            if s["debug_enabled"]:
                st.code(f"{type(exc).__name__}: {exc}")
        st.divider()
        if source:
            st.markdown(f'**Đoạn được truy xuất · Trang PDF {source["page"]}**')
            if chat["pdf_page"] != source["page"]:
                st.info(f'Bạn đang xem trang {chat["pdf_page"]}; đoạn trích này thuộc trang {source["page"]}.')
                st.button(f'Về trang trích dẫn {source["page"]}', key="back_to_source", disabled=busy,
                          on_click=state.set_page, args=(s, source["page"]))
            st.text(source["text"])
            with st.expander("Thông tin nguồn"):
                st.caption(source["source"])
                st.text(source["chunk_id"])
                meta = source.get("metadata", {})
                for field in ("regulation", "article_title", "clause_title"):
                    if meta.get(field):
                        st.text(meta[field])
        else:
            st.caption("Chọn một trích dẫn trong câu trả lời để xem đoạn nguồn tương ứng.")


def fallback(info, page, chat_id):
    st.caption(f'Bản xem chỉ gồm trang {page} của PDF gốc ({info["page_count"]} trang).')
    try:
        st.pdf(one_page(info["bytes"], page), height=460, key=f"pdf_fallback_{chat_id}_{page}",
               alt=f"Sổ tay sinh viên K50, trang vật lý {page}")
    except Exception:
        st.warning("Bản dự phòng cũng chưa hiển thị được. Dùng nút Tải trang này và đọc đoạn nguồn bên dưới.")
