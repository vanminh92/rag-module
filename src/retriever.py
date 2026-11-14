"""Public Code 2 API: cached, validated cosine retrieval from a persisted index."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import config
from .build_index import file_sha256
from .embeddings import get_embedder, validate_vectors


class IndexValidationError(ValueError):
    """Missing compatibility or integrity: rebuild the index before querying."""


def validate_query(question: str, top_k: int) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question phải là chuỗi không rỗng")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k phải là số nguyên dương")
    return question.strip()


class Retriever:
    """Alternative index directory/expected range for tools and Code 2 deployments."""

    def __init__(self, index_dir: str | Path, *, expected_page_range: tuple[int, int] | None = None) -> None:
        self.index_dir = Path(index_dir).resolve()
        self.expected_page_range = expected_page_range
        self._signature: tuple | None = None
        self.chunks: list[dict] = []
        self.meta: dict = {}
        self.vectors = np.empty((0, config.EMBEDDING_DIM), dtype=np.float32)
        self._ensure_index()

    def _ensure_index(self) -> None:
        paths = [self.index_dir / name for name in ("chunks.json", "embeddings.npy", "index_meta.json")]
        try:
            signature = tuple((p.stat().st_mtime_ns, p.stat().st_ctime_ns, p.stat().st_size) for p in paths)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Thiếu index. Chạy python -m src.build_index trước khi truy xuất") from exc
        settings = (config.MODEL_NAME, config.MODEL_REVISION, config.CHUNK_SIZE_CHARS, config.CHUNK_OVERLAP_CHARS,
                    config.MAX_MODEL_TOKENS, config.CHUNK_STRATEGY, config.INDEX_VERSION, self.expected_page_range)
        if self._signature != (signature, settings):
            try:
                meta = json.loads(paths[2].read_text(encoding="utf-8"))
                expected = {"model_name": config.MODEL_NAME, "model_revision": config.MODEL_REVISION,
                            "embedding_dim": config.EMBEDDING_DIM,
                            "chunk_size_chars": config.CHUNK_SIZE_CHARS,
                            "chunk_overlap_chars": config.CHUNK_OVERLAP_CHARS,
                            "chunk_strategy": config.CHUNK_STRATEGY,
                            "max_model_tokens": config.MAX_MODEL_TOKENS, "index_version": config.INDEX_VERSION}
                if not isinstance(meta, dict) or any(meta.get(k) != v for k, v in expected.items()):
                    raise ValueError("Model/cấu hình/index_version không khớp")
                first, last = meta["page_range"]
                if type(first) is not int or type(last) is not int or not 1 <= first <= last <= meta["total_pdf_pages"]:
                    raise ValueError("page_range không hợp lệ")
                if self.expected_page_range is not None and list(self.expected_page_range) != meta["page_range"]:
                    raise ValueError("Phạm vi trang không khớp")
                if file_sha256(paths[0]) != meta["chunks_sha256"] or file_sha256(paths[1]) != meta["embeddings_sha256"]:
                    raise ValueError("Checksum chunks/embeddings không khớp; artifact bị sửa hoặc build dở")
                chunks = json.loads(paths[0].read_text(encoding="utf-8"))
                if not isinstance(chunks, list) or not chunks or len(chunks) != meta["num_chunks"]:
                    raise ValueError("Số chunks không khớp metadata")
                ids = set()
                previous_page = 0
                for order, chunk in enumerate(chunks):
                    if (not isinstance(chunk, dict) or not isinstance(chunk.get("chunk_id"), str)
                            or not chunk["chunk_id"] or chunk["chunk_id"] in ids
                            or type(chunk.get("order")) is not int or chunk.get("order") != order
                            or type(chunk.get("page")) is not int
                            or not first <= chunk["page"] <= last or chunk["page"] < previous_page
                            or chunk.get("source") != meta["source"]
                            or not isinstance(chunk.get("text"), str) or not chunk["text"].strip()
                            or len(chunk["text"]) > config.CHUNK_SIZE_CHARS):
                        raise ValueError("Schema/thứ tự/metadata chunk không hợp lệ")
                    ids.add(chunk["chunk_id"])
                    previous_page = chunk["page"]
                vectors = validate_vectors(np.load(paths[1], allow_pickle=False), len(chunks))
                self.source_path = (self.index_dir / meta["source_path"]).resolve()
                if self.source_path.name != meta["source"]:
                    raise ValueError("Đường dẫn nguồn không khớp tên nguồn")
            except (ValueError, KeyError, TypeError, OSError, EOFError) as exc:
                raise IndexValidationError(f"Index lỗi: {exc}. Hãy build lại index") from exc
            self.meta, self.chunks, self.vectors = meta, chunks, vectors
            self._signature = (signature, settings)
        # Reading the 2.7 MB source hash is cheap; no PDF parsing or passage encoding.
        if not self.source_path.is_file() or file_sha256(self.source_path) != self.meta["source_sha256"]:
            raise IndexValidationError("PDF nguồn thiếu hoặc đã thay đổi; hãy build lại index")

    def retrieve(self, question: str, top_k: int = 3) -> list[dict]:
        question = validate_query(question, top_k)
        self._ensure_index()
        encoder = get_embedder()
        if encoder.revision != self.meta.get("model_revision"):
            raise IndexValidationError("Phiên bản model đã đổi; hãy build lại index")
        query = encoder.encode_query(question)
        scores = self.vectors @ query
        # Chunks are in increasing order; stable sort preserves order for ties.
        ranking = np.argsort(-scores, kind="stable")[:min(top_k, len(self.chunks))]
        return [{"chunk_id": self.chunks[i]["chunk_id"], "text": self.chunks[i]["text"],
                 "source": self.chunks[i]["source"], "page": self.chunks[i]["page"],
                 "score": float(scores[i])} for i in ranking]


@lru_cache(maxsize=4)
def get_retriever(index_dir: str) -> Retriever:
    return Retriever(index_dir)


def retrieve(question: str, top_k: int = 3) -> list[dict]:
    """Return min(top_k, N) chunks with source, physical PDF page and cosine score."""
    question = validate_query(question, top_k)
    return get_retriever(str(Path(config.INDEX_DIR).resolve())).retrieve(question, top_k)
