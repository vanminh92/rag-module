"""Render saved answers and real evidence; model calls are handled separately."""

import streamlit as st
from . import state
from .components import copy_answer
from .citations import chips
from .evidence import verified_claim_sources
from .sidebar import SUGGESTIONS


def empty_state():
    st.html('<section class="k50-hero"><div class="k50-eyebrow">TRA CỨU · ĐỐI CHIẾU · TÌM HIỂU</div>'
            '<h1>Bạn muốn tìm hiểu gì<br>trong Sổ tay sinh viên K50?</h1>'
            '<p>Đặt câu hỏi bằng tiếng Việt tự nhiên. Mỗi nguồn dẫn bạn về tài liệu gốc để đối chiếu.</p></section>')
    with st.container(key="suggestions"):
        for start in (0, 2):
            columns = st.columns(2)
            for index in range(start, start + 2):
                title, question = SUGGESTIONS[index]
                with columns[index - start]:
                    st.button(f"{title}  \n{question}", key=f"suggest_{index}", width="stretch", wrap=True,
                              on_click=state.enqueue, args=(st.session_state, question),
                              disabled=st.session_state["is_generating"])


def assistant_message(message):
    result = message.get("result")
    if message.get("error"):
        st.error(message["error"]["message"])
        if st.session_state["debug_enabled"]:
            with st.expander("Chi tiết lỗi"):
                st.code(message["error"].get("traceback") or message["error"]["detail"])
        return
    if result is None:
        return
    status = result.get("status")
    if status == "partial":
        st.warning("Chỉ tìm được bằng chứng để trả lời một phần câu hỏi.")
    elif status == "insufficient":
        st.info("Chưa tìm thấy đủ bằng chứng trong tài liệu.")
    sources = result.get("ui_sources", [])
    claims = result.get("claims", [])
    mappings = [verified_claim_sources(c, sources) for c in claims]
    if claims and all(mappings):
        for i, (claim, links) in enumerate(zip(claims, mappings)):
            st.markdown(claim["text"])
            chips(message["id"], links, f'{message["id"]}_claim_{i}')
    else:
        if any(c.get("citations") for c in claims):
            st.warning("Chưa đối chiếu được nguồn cho từng ý; chỉ hiển thị nguồn ở mức toàn bộ phản hồi.")
        st.markdown(result["answer"])
        if sources:
            st.caption("Nguồn được sử dụng")
            chips(message["id"], sources, f'{message["id"]}_answer')
    if result.get("missing_information"):
        st.caption("Phần chưa xác minh: " + " · ".join(result["missing_information"]))
    for warning in result.get("ui_warnings", []) + result.get("warnings", []):
        st.caption(warning)
    if status != "insufficient" and not sources:
        st.warning("Phản hồi chưa có nguồn PDF được xác minh để mở. Không tự gắn trích dẫn.")
    with st.container(horizontal=True, vertical_alignment="center"):
        copy_answer(result["answer"], key=f'copy_{message["id"]}')
        if sources:
            st.button("Xem nguồn", icon=":material/open_in_new:", key=f'view_{message["id"]}',
                      on_click=state.select_evidence, args=(st.session_state, message["id"], sources[0]["chunk_id"]),
                      disabled=st.session_state["is_generating"])
    if st.session_state["debug_enabled"]:
        with st.expander("Developer Debug", expanded=False):
            debug = result.get("debug", {})
            timing = debug.get("total_seconds")
            if timing is not None:
                st.caption(f"Thời gian backend thực: {timing:.2f} giây")
            st.write("Truy vấn, ứng viên, RRF/reranking, ngữ cảnh và phản hồi LLM")
            st.json(debug, expanded=False)
            st.write("Kết quả đã lưu và metadata nguồn")
            st.json({k: v for k, v in result.items() if k != "debug"}, expanded=False)


def render(height):
    s = st.session_state
    with st.container(key="chat_region"):
        with st.container(height=height, border=False, key="chat_transcript", autoscroll=False):
            messages = state.active_chat(s)["messages"]
            if not messages:
                empty_state()
            for message in messages:
                avatar = ":material/person:" if message["role"] == "user" else ":material/auto_awesome:"
                with st.chat_message(message["role"], avatar=avatar):
                    if message["role"] == "user":
                        st.markdown(message["content"])
                    else:
                        assistant_message(message)
        key = f'question_{s["active_chat_id"]}'

        def submit():
            state.enqueue(s, s.get(key, ""))

        st.chat_input("Hỏi bất kỳ điều gì trong sổ tay…", key=key, disabled=s["is_generating"],
                      on_submit=submit, max_chars=5000)
        st.caption("Mỗi câu hỏi được tra cứu độc lập. Hãy nhắc lại chủ đề khi hỏi tiếp.")
