import json
import shutil

import numpy as np
import pytest

from src import config
from src.build_index import file_sha256
from src.retriever import IndexValidationError, Retriever, get_retriever, retrieve


@pytest.mark.parametrize("question", [None, 42, "", " \n "])
def test_invalid_query_before_loading_index(question):
    with pytest.raises(ValueError, match="question"):
        retrieve(question)


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5, "3"])
def test_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        retrieve("Học phần tiên quyết là gì?", top_k)


def test_missing_index(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_index"):
        Retriever(tmp_path)


@pytest.fixture
def copied_index(tmp_path, pdf_path):
    """Copy real build artifacts; corrupt copies only for negative tests."""
    source = config.INDEX_DIR
    if not (source / "index_meta.json").exists():
        pytest.skip("Cần build index thật trước (không tạo index giả trong tests)")
    for name in ("chunks.json", "embeddings.npy", "index_meta.json"):
        shutil.copyfile(source / name, tmp_path / name)
    shutil.copyfile(pdf_path, tmp_path / pdf_path.name)
    meta = json.loads((tmp_path / "index_meta.json").read_text(encoding="utf-8"))
    meta["source_path"] = pdf_path.name
    (tmp_path / "index_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return tmp_path


def test_artifact_schema(copied_index):
    index = Retriever(copied_index)
    assert index.vectors.shape == (len(index.chunks), 384)
    assert index.vectors.dtype == np.float32


@pytest.mark.parametrize("field,value", [("model_name", "wrong-model"), ("model_revision", "changed"),
    ("chunk_size_chars", 501), ("num_chunks", -1), ("page_range", [0, 31]), ("embedding_dim", 383)])
def test_metadata_mismatch(copied_index, field, value):
    path = copied_index / "index_meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta[field] = value
    path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(IndexValidationError, match="build lại"):
        Retriever(copied_index)


def test_page_range_mismatch(copied_index):
    with pytest.raises(IndexValidationError, match="Phạm vi trang"):
        Retriever(copied_index, expected_page_range=(8, 9))


def test_corrupt_artifacts_and_source_change(copied_index):
    index = Retriever(copied_index)
    source = index.source_path
    original = source.read_bytes()
    source.write_bytes(original[:-1])
    with pytest.raises(IndexValidationError, match="PDF nguồn"):
        index._ensure_index()
    source.write_bytes(original)
    chunks = copied_index / "chunks.json"
    chunks.write_bytes(chunks.read_bytes()[:-10])
    with pytest.raises(IndexValidationError, match="Checksum"):
        index._ensure_index()


def test_bad_matrix_dimensions(copied_index):
    path = copied_index / "embeddings.npy"
    np.save(path, np.load(path, allow_pickle=False)[:, :-1])
    meta_path = copied_index / "index_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["embeddings_sha256"] = file_sha256(path)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(IndexValidationError, match="shape"):
        Retriever(copied_index)


@pytest.mark.real_model
def test_real_retrieval_sort_schema_and_reuse(encoder):
    question = "Một tín chỉ học lý thuyết được quy định bao nhiêu giờ?"
    results = retrieve(question)
    index = get_retriever(str(config.INDEX_DIR.resolve()))
    assert len(results) == 3
    assert [r["score"] for r in results] == sorted([r["score"] for r in results], reverse=True)
    for item in results:
        assert set(item) == {"chunk_id", "text", "source", "page", "score"}
        assert item["source"] == config.INPUT_PATH.name
        assert type(item["score"]) is float
    vectors, chunks = index.vectors, index.chunks
    another = retrieve("Sinh viên chính quy bắt đầu tự đăng ký học phần từ học kỳ nào?")
    assert vectors is index.vectors and chunks is index.chunks
    assert results[0]["chunk_id"] != another[0]["chunk_id"]
    scores = index.vectors @ encoder.encode_query(question)
    ranking = np.argsort(-scores, kind="stable")[:3]
    assert [item["chunk_id"] for item in results] == [index.chunks[i]["chunk_id"] for i in ranking]
    assert len(retrieve(question, top_k=len(index.chunks) + 1)) == len(index.chunks)


@pytest.mark.real_model
def test_ties_follow_order_with_duplicate_real_vectors(copied_index, encoder):
    # Duplicate a real embedding to exercise ties; no fabricated model output.
    path = copied_index / "embeddings.npy"
    matrix = np.load(path, allow_pickle=False)
    matrix[:] = matrix[0]
    np.save(path, matrix)
    meta_path = copied_index / "index_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["embeddings_sha256"] = file_sha256(path)
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    index = Retriever(copied_index)
    results = index.retrieve("Học phần tiên quyết là gì?")
    assert [r["chunk_id"] for r in results] == [c["chunk_id"] for c in index.chunks[:3]]
