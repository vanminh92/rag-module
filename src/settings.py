"""Bounded, local-first settings for the QA pipeline; the Code 2 API is unchanged."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RAGSettings:
    model: str = "qwen2.5:3b"
    ollama_host: str = "http://127.0.0.1:11434"
    rewrite: str = "rules"
    reranker: str = "lexical"
    support_check: str = "nli"
    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    candidates_per_method: int = 20
    max_queries: int = 4
    max_rounds: int = 2
    simple_contexts: int = 4
    complex_contexts: int = 8
    context_tokens: int = 2200
    rrf_k: int = 60
    timeout: float = 180

    def __post_init__(self):
        if self.rewrite not in {"rules", "llm"} or self.reranker not in {"none", "lexical", "cross-encoder"}:
            raise ValueError("rewrite: rules|llm; reranker: none|lexical|cross-encoder")
        if self.support_check not in {"nli", "llm"}:
            raise ValueError("support_check: nli|llm")
        if not 1 <= self.max_queries <= 4 or not 1 <= self.max_rounds <= 2:
            raise ValueError("Tối đa 4 truy vấn mỗi lượt và 2 lượt truy xuất")
        if not 1 <= self.candidates_per_method <= 100 or not 1 <= self.simple_contexts <= self.complex_contexts <= 8:
            raise ValueError("Cần 1–100 ứng viên/method và 1–8 đoạn ngữ cảnh")
        if self.context_tokens < 100 or self.rrf_k < 1 or self.timeout <= 0:
            raise ValueError("Ngân sách token, RRF k và timeout phải dương")

    @classmethod
    def from_env(cls):
        return cls(model=os.getenv("RAG_MODEL", "qwen2.5:3b"),
                   ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
                   rewrite=os.getenv("RAG_QUERY_REWRITE", "rules"),
                   reranker=os.getenv("RAG_RERANKER", "lexical"),
                   support_check=os.getenv("RAG_SUPPORT_CHECK", "nli"),
                   reranker_model=os.getenv("RAG_RERANK_MODEL", cls.reranker_model),
                   context_tokens=int(os.getenv("RAG_CONTEXT_TOKENS", "2200")))
