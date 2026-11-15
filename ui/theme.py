"""Native switchable Streamlit themes, with CSS scoped to our public widget keys."""

from pathlib import Path
import streamlit as st


def apply():
    st.html(f'<style>{Path(__file__).with_name("workbench.css").read_text()}</style>')


def brand():
    st.html('<div class="k50-brand"><span class="k50-mark">K50</span>'
            '<div><strong>K50 AI</strong><small>Student Knowledge Assistant</small></div></div>')
