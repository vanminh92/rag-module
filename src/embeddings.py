"""Cached E5 encoder, with explicit prefixes and preflight token validation."""

from functools import lru_cache

import numpy as np

from .config import EMBEDDING_DIM, MAX_MODEL_TOKENS, MODEL_NAME, MODEL_REVISION, PROJECT_ROOT


def validate_vectors(vectors: np.ndarray, rows: int) -> np.ndarray:
    if not isinstance(vectors, np.ndarray) or vectors.shape != (rows, EMBEDDING_DIM) or vectors.dtype != np.float32:
        raise ValueError(f"Embedding phải có shape ({rows}, {EMBEDDING_DIM}), dtype float32")
    if not np.isfinite(vectors).all():
        raise ValueError("Embedding chứa NaN/Inf")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4):
        raise ValueError("Embedding chưa được chuẩn hóa L2 hoặc có vector bằng 0")
    return vectors


def prepare_texts(texts: list[str], kind: str) -> list[str]:
    if kind not in ("passage", "query"):
        raise ValueError("Tiền tố E5 phải là passage hoặc query")
    if not texts or any(not isinstance(t, str) or not t.strip() for t in texts):
        raise ValueError("Nội dung embedding phải là chuỗi không rỗng")
    return [f"{kind}: {text.strip()}" for text in texts]


class E5Embedder:
    def __init__(self) -> None:
        # Lazy import: importing the public API doesn't load PyTorch or the model.
        from sentence_transformers import SentenceTransformer

        options = {"cache_folder": str(PROJECT_ROOT / ".cache" / "models"),
                   "device": "cpu", "revision": MODEL_REVISION}
        try:
            self.model = SentenceTransformer(MODEL_NAME, local_files_only=True, **options)
        except OSError:
            self.model = SentenceTransformer(MODEL_NAME, **options)
        dimension = getattr(self.model, "get_embedding_dimension", self.model.get_sentence_embedding_dimension)()
        if dimension != EMBEDDING_DIM:
            raise ValueError(f"Model E5 phải tạo vector {EMBEDDING_DIM} chiều")
        self.max_tokens = min(MAX_MODEL_TOKENS, self.model.max_seq_length,
                              self.model.tokenizer.model_max_length)
        self.revision = MODEL_REVISION

    def token_lengths(self, texts: list[str], kind: str) -> list[int]:
        prefixed = prepare_texts(texts, kind)
        tokens = self.model.tokenizer(
            prefixed, add_special_tokens=True, truncation=False,
            padding=False, return_attention_mask=False,
        )["input_ids"]
        return [len(ids) for ids in tokens]

    def encode(self, texts: list[str], kind: str, *, show_progress: bool = False) -> np.ndarray:
        prefixed = prepare_texts(texts, kind)
        lengths = self.token_lengths(texts, kind)
        for index, length in enumerate(lengths):
            if length > self.max_tokens:
                raise ValueError(
                    f"{kind} #{index} có {length} token > {self.max_tokens}; "
                    "hãy giảm chunk_size hoặc rút ngắn câu hỏi, rồi build lại nếu cần. Không cắt âm thầm"
                )
        vectors = self.model.encode(
            prefixed, batch_size=32, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=show_progress, prompt="",
        )
        return validate_vectors(np.asarray(vectors, dtype=np.float32), len(texts))

    def encode_passages(self, texts: list[str], *, show_progress: bool = False) -> np.ndarray:
        return self.encode(texts, "passage", show_progress=show_progress)

    def encode_query(self, question: str) -> np.ndarray:
        return self.encode([question], "query")[0]


@lru_cache(maxsize=1)
def get_embedder() -> E5Embedder:
    """One E5 model per process; never re-embed passages during retrieval."""
    return E5Embedder()
