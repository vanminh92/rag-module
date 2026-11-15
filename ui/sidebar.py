"""Conversation navigation and a queue of suggested questions, never sample answers."""

import streamlit as st
from . import state
from .theme import brand

SUGGESTIONS = [
    ("Học phần", "Sinh viên đại học chính quy tự đăng ký học phần từ học kỳ nào?"),
    ("Cảnh báo học tập", "Điểm học kỳ thấp cỡ nào thì sinh viên đại học chính quy bị cảnh báo?"),
    ("Tốt nghiệp", "Chuẩn đầu ra ngoại ngữ tối thiểu để sinh viên đại học tốt nghiệp là gì?"),
    ("Quyền lợi sinh viên", "Sinh viên có quyền lợi gì về đăng ký ngoại trú?"),
]


def render():
    s = st.session_state
    busy = s["is_generating"]
    with st.sidebar, st.container(key="sidebar_body"):
        brand()
        st.button("Trò chuyện mới", icon=":material/add:", key="new_chat", width="stretch",
                  type="primary", disabled=busy, on_click=state.new_chat, args=(s,))
        st.caption("TRONG PHIÊN NÀY")
        for chat in reversed(list(s["chats"].values())):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.button(chat["title"], icon=":material/chat_bubble_outline:", key=f'chat_{chat["id"]}',
                          type="secondary" if chat["id"] == s["active_chat_id"] else "tertiary",
                          width="stretch", disabled=busy, on_click=state.switch_chat, args=(s, chat["id"]))
        st.button("Xóa cuộc trò chuyện này", icon=":material/delete_outline:", key="delete_chat", disabled=busy,
                  type="tertiary", on_click=lambda: s.update(delete_chat_id=s["active_chat_id"]))
        if s["delete_chat_id"]:
            st.warning("Xóa toàn bộ nội dung cuộc trò chuyện này?")
            left, right = st.columns(2)
            left.button("Xác nhận xóa", key="confirm_delete", type="primary", on_click=state.delete_chat,
                        args=(s, s["delete_chat_id"]))
            right.button("Hủy", key="cancel_delete", on_click=lambda: s.update(delete_chat_id=None))
        st.divider()
        st.caption("KHÁM PHÁ CHỦ ĐỀ")
        for i, (title, question) in enumerate(SUGGESTIONS):
            st.button(title, icon=":material/arrow_outward:", key=f"topic_{i}", width="stretch", type="tertiary",
                      disabled=busy, on_click=state.enqueue, args=(s, question))
        st.divider()
        st.toggle("Developer mode", key="debug_enabled", disabled=busy)
        st.caption("Sáng / tối: chọn Theme trong menu ⋮ phía trên.")
        st.caption("Lịch sử chỉ lưu trong phiên trình duyệt. Tải lại trang hoặc khởi động lại app có thể làm mất hội thoại.")
        st.caption("Demo tra cứu Sổ tay sinh viên K50 · Không phải sản phẩm chính thức của nhà trường.")
