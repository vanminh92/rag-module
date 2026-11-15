"""Read-only PDF resources. Page previews never write to data/ or the index."""

import hashlib
from io import BytesIO
import json

from pypdf import PdfReader, PdfWriter
import streamlit as st
from src import config


@st.cache_data(show_spinner=False, max_entries=2)
def _document(path, modified_ns, size, expected_hash):
    data = config.INPUT_PATH.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_hash:
        raise ValueError("PDF gốc không khớp hash của index; không mở nhầm tài liệu.")
    return {"bytes": data, "sha256": digest, "page_count": len(PdfReader(BytesIO(data)).pages)}


def document():
    stat = config.INPUT_PATH.stat()
    meta = json.loads((config.INDEX_DIR / "index_meta.json").read_text(encoding="utf-8"))
    return _document(str(config.INPUT_PATH), stat.st_mtime_ns, stat.st_size, meta["source_sha256"])


@st.cache_data(show_spinner=False, max_entries=8)
def one_page(data, page):
    reader = PdfReader(BytesIO(data))
    if type(page) is not int or not 1 <= page <= len(reader.pages):
        raise ValueError("Số trang nằm ngoài PDF gốc.")
    writer = PdfWriter()
    writer.add_page(reader.pages[page - 1])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
