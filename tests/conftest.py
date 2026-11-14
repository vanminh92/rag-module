"""Fixtures always read the supplied PDF; no fabricated document/evidence."""

import pytest

from src.config import INPUT_PATH
from src.document_loader import load_document


@pytest.fixture(scope="session")
def pdf_path():
    return INPUT_PATH


@pytest.fixture(scope="session")
def pilot_pages(pdf_path):
    return load_document(pdf_path, 8, 31)


def pytest_addoption(parser):
    parser.addoption("--run-model", action="store_true", help="Chạy tests E5/index thật (cần model/cache)")


def pytest_configure(config):
    config.addinivalue_line("markers", "real_model: dùng E5 thật; bật bằng --run-model")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-model"):
        skip = pytest.mark.skip(reason="Cần --run-model để dùng E5 thật")
        for item in items:
            if "real_model" in item.keywords:
                item.add_marker(skip)


@pytest.fixture(scope="session")
def encoder():
    from src.embeddings import get_embedder
    return get_embedder()


@pytest.fixture(scope="session")
def real_vectors(encoder, pilot_pages):
    from src.chunking import build_chunks
    passages = build_chunks(pilot_pages[:1], "so_tay_sinh_vien_k50.pdf")
    return encoder.encode_passages([chunk["text"] for chunk in passages])
