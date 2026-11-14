"""Conservative Unicode normalization and lossless overlapping page windows."""

import re
import unicodedata
from pathlib import Path

from .config import CHUNK_OVERLAP_CHARS, CHUNK_SIZE_CHARS

# Structural boundaries are recognized only at the start of original PDF lines.
# This does not rewrite content or split ordinary inline references to an Article.
CLAUSE_BOUNDARY = re.compile(r"(?m)(?=^[ \t]*(?:Điều[ \t]+\d+\.|\d+\.[ \t]+|[a-zđ]\)[ \t]+))")


def normalize_text(text: str) -> str:
    """Join wrapped lines; preserve blank paragraphs and all non-whitespace text.

    Headers, footers, numbers and table contents are deliberately retained.
    No dehyphenation or correction of PDF reading order is attempted.
    """
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n[\t \u00a0]*\n+", text)
    return "\n\n".join(
        normalized for paragraph in paragraphs
        if (normalized := re.sub(r"\s+", " ", paragraph).strip())
    )


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Cut windows with exact target overlap before trimming edge whitespace."""
    if type(chunk_size) is not int or type(overlap) is not int or not 0 <= overlap < chunk_size:
        raise ValueError("Cần chunk_size > 0 và 0 <= overlap < chunk_size (số nguyên)")
    result = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Prefer sentence ends in the latter half, then word boundaries.
            # end-start must exceed overlap, so the next window always advances.
            lower = start + max(overlap + 1, chunk_size // 2)
            candidates = list(re.finditer(r"[.!?;](?:\s|$)|\n\n", text[lower:end]))
            if candidates:
                end = lower + candidates[-1].end()
            else:
                boundary = text.rfind(" ", lower, end)
                if boundary != -1:
                    end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            result.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return result


def build_chunks(
    pages: list[dict], source: str,
    chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[dict]:
    """Build stable IDs and globally increasing order; never cross page boundaries."""
    # Validate even when pages is empty.
    split_text("", chunk_size, overlap)
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source phải là tên tệp không rỗng")
    name = Path(source).name
    stem = Path(name).stem
    chunks = []
    seen_pages = set()
    for page in pages:
        number = page["page"]
        if type(number) is not int or number < 1 or number in seen_pages:
            raise ValueError("Trang phải là số nguyên dương và không được lặp lại")
        if seen_pages and number <= max(seen_pages):
            raise ValueError("Các trang phải có thứ tự tăng dần")
        seen_pages.add(number)
        # Keep each regulation item separate; overlap applies within long items.
        # No overlap across explicit clause boundaries, to avoid blending rules.
        texts = [chunk for section in CLAUSE_BOUNDARY.split(page["text"])
                 for chunk in split_text(normalize_text(section), chunk_size, overlap)]
        for index, chunk in enumerate(texts, start=1):
            chunks.append({
                "chunk_id": f"{stem}-p{number:03d}-c{index:03d}",
                "text": chunk, "source": name, "page": number, "order": len(chunks),
            })
    if not chunks:
        raise ValueError("Không tạo được chunk có văn bản từ vùng trang đã chọn")
    return chunks
