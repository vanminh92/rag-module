import logging

import pytest
from pypdf import PdfReader, PdfWriter

from src.document_loader import load_document


def test_real_pdf_range_and_vietnamese(pdf_path, pilot_pages):
    assert len(PdfReader(pdf_path).pages) == 220
    assert [p["page"] for p in pilot_pages] == list(range(8, 32))
    assert "15 giờ học lý thuyết và 30 giờ tự học" in pilot_pages[0]["text"]
    assert "\ufffd" not in "".join(p["text"] for p in pilot_pages)


def test_boundaries(pdf_path):
    assert [p["page"] for p in load_document(pdf_path, 9, 9)] == [9]
    assert load_document(pdf_path, 220)[-1]["page"] == 220


@pytest.mark.parametrize("start,end", [(0, 2), (8, 7), (1, 221), (True, 3), (1.5, 4)])
def test_invalid_range(pdf_path, start, end):
    with pytest.raises(ValueError, match="trang"):
        load_document(pdf_path, start, end)


def test_missing_empty_and_corrupt(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_document(tmp_path / "absent.pdf")
    empty = tmp_path / "empty.pdf"
    empty.touch()
    with pytest.raises(ValueError, match="rỗng"):
        load_document(empty)
    # Negative case: truncated bytes of the real input, not invented PDF content.
    from src.config import INPUT_PATH
    empty.write_bytes(INPUT_PATH.read_bytes()[:10])
    with pytest.raises(ValueError, match="Không đọc được PDF"):
        load_document(empty)


def test_unsupported_suffix(pdf_path, tmp_path):
    target = tmp_path / "document.txt"
    target.write_bytes(pdf_path.read_bytes())
    with pytest.raises(ValueError, match="Chỉ hỗ trợ"):
        load_document(target)


def test_blank_and_encrypted_variants_of_real_pdf(pdf_path, tmp_path, caplog):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.add_page(reader.pages[7])
    page = writer.add_page(reader.pages[8])
    # Remove the content stream to test the actual no-text error path.
    del page["/Contents"]
    path = tmp_path / "variant.pdf"
    writer.write(path)
    with caplog.at_level(logging.WARNING):
        assert [p["page"] for p in load_document(path)] == [1]
    assert "Trang PDF 2" in caplog.text
    with pytest.raises(ValueError, match="OCR ngoài phạm vi"):
        load_document(path, 2, 2)
    writer.encrypt("test-only-password")
    writer.write(path)
    with pytest.raises(ValueError, match="bị khóa"):
        load_document(path)
