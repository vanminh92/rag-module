import re
import unicodedata

import pytest

from src.chunking import build_chunks, normalize_text, split_text


def test_nfc_and_content(pilot_pages):
    raw = pilot_pages[0]["text"]
    normalized = normalize_text(unicodedata.normalize("NFD", raw))
    assert unicodedata.is_normalized("NFC", normalized)
    assert re.sub(r"\s", "", normalized) == re.sub(r"\s", "", unicodedata.normalize("NFC", raw))


def test_chunks_stable_metadata_size(pilot_pages, pdf_path):
    chunks = build_chunks(pilot_pages, pdf_path.name)
    assert chunks == build_chunks(pilot_pages, pdf_path.name)
    assert len(chunks) >= 3
    assert len(set(c["chunk_id"] for c in chunks)) == len(chunks)
    assert [c["order"] for c in chunks] == list(range(len(chunks)))
    for chunk in chunks:
        assert 0 < len(chunk["text"]) <= 500
        assert chunk["source"] == pdf_path.name
        assert f'-p{chunk["page"]:03d}-' in chunk["chunk_id"]
        original = next(p["text"] for p in pilot_pages if p["page"] == chunk["page"])
        assert chunk["text"] in normalize_text(original)


@pytest.mark.parametrize("size,overlap", [(500, 100), (31, 0), (30, 29), (1, 0)])
def test_no_lost_characters_or_tail(pilot_pages, size, overlap):
    for page in pilot_pages:
        text = normalize_text(page["text"])
        chunks = split_text(text, size, overlap)
        covered = set()
        cursor = 0
        previous_start = -1
        for chunk in chunks:
            start = text.find(chunk, max(0, previous_start, cursor - overlap))
            assert start >= 0
            covered.update(range(start, start + len(chunk)))
            cursor = start + len(chunk)
            previous_start = start
        assert all(i in covered for i, char in enumerate(text) if not char.isspace())
        assert chunks[-1].endswith(text[-1])


def test_overlap(pilot_pages):
    chunks = split_text(normalize_text(pilot_pages[0]["text"]), 500, 100)
    for left, right in zip(chunks, chunks[1:]):
        assert any(left.endswith(right[:n]) for n in range(98, 101))


def test_structural_chunks_preserve_every_page_character(pilot_pages, pdf_path):
    chunks = build_chunks(pilot_pages, pdf_path.name)
    for page in pilot_pages:
        text = normalize_text(page["text"])
        covered = set()
        cursor = 0
        for chunk in [c for c in chunks if c["page"] == page["page"]]:
            start = text.find(chunk["text"], max(0, cursor - 100))
            assert start >= 0
            covered.update(range(start, start + len(chunk["text"])))
            cursor = start + len(chunk["text"])
        assert all(i in covered for i, char in enumerate(text) if not char.isspace())
    registration = [c for c in chunks if c["page"] == 15 and "Từ học kỳ thứ hai" in c["text"]]
    assert len(registration) == 1
    assert registration[0]["text"].startswith("b) Từ học kỳ thứ hai")
    assert "Phòng Khảo thí" not in registration[0]["text"]


@pytest.mark.parametrize("size,overlap", [(0, 0), (20, 20), (20, -1), (True, 0), (20, 1.5)])
def test_invalid_chunk_config(size, overlap):
    with pytest.raises(ValueError):
        split_text("", size, overlap)


def test_invalid_page_metadata(pilot_pages, pdf_path):
    with pytest.raises(ValueError, match="lặp"):
        build_chunks([pilot_pages[0], pilot_pages[0]], pdf_path.name)
    with pytest.raises(ValueError, match="thứ tự"):
        build_chunks(list(reversed(pilot_pages[:2])), pdf_path.name)
    with pytest.raises(ValueError, match="Không tạo"):
        build_chunks([], pdf_path.name)
