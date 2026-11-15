import streamlit as st
from . import state


def chips(message_id, sources, prefix):
    with st.container(horizontal=True, key=f"source_chips_{prefix}"):
        for source in sources:
            st.button(f'[{source["ui_number"]}] Sổ tay K50 · Trang {source["page"]}',
                      icon=":material/description:", key=f'cite_{prefix}_{source["chunk_id"]}',
                      disabled=st.session_state["is_generating"], on_click=state.select_evidence,
                      args=(st.session_state, message_id, source["chunk_id"]))
