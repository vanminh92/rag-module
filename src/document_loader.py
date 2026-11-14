"""Read physical PDF pages without OCR, preserving 1-based page numbers."""

import logging
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

logger = logging.getLogger(__name__)


def load_document(
    path: str | Path,
    start_page: int | None = None,
    end_page: int | None = None,
) -> list[dict]:
    """Extract a PDF range (both bounds inclusive); omit and log empty pages."""
    pdf = Path(path)
    if not pdf.is_file():
        raise FileNotFoundError(f"Không tìm thấy PDF: {pdf}")
    if pdf.suffix.lower() != ".pdf":
        raise ValueError("Chỉ hỗ trợ tài liệu PDF có lớp văn bản")
    if pdf.stat().st_size == 0:
        raise ValueError(f"PDF rỗng: {pdf}")
    for value in (start_page, end_page):
        if value is not None and (type(value) is not int or value < 1):
            raise ValueError("Số trang phải là số nguyên từ 1")
    try:
        with pdf.open("rb") as stream:
            reader = PdfReader(stream)
            if reader.is_encrypted and not reader.decrypt(""):
                raise ValueError("PDF bị khóa; cần bản PDF không yêu cầu mật khẩu")
            count = len(reader.pages)
            first = start_page if start_page is not None else 1
            last = end_page if end_page is not None else count
            if not 1 <= first <= last <= count:
                raise ValueError(f"Phạm vi trang không hợp lệ: {first}-{last}; PDF có {count} trang")
            pages = []
            empty = []
            for number in range(first, last + 1):
                text = reader.pages[number - 1].extract_text() or ""
                if not text.strip():
                    empty.append(number)
                    logger.warning("Trang PDF %d không có văn bản; bỏ qua (không OCR)", number)
                    continue
                pages.append({"text": text, "page": number})
            logger.info(
                "PDF %s | total_pages=%d range=%d-%d selected=%d text_pages=%d empty_pages=%s chars=%d",
                pdf.name, count, first, last, last - first + 1, len(pages), empty,
                sum(len(page["text"]) for page in pages),
            )
    except (PyPdfError, OSError, UnicodeError) as exc:
        raise ValueError(f"Không đọc được PDF {pdf.name}: {exc}") from exc
    if not pages:
        raise ValueError("PDF không có văn bản trích xuất được; OCR ngoài phạm vi")
    return pages
