"""Switchable CPU reranking; the neural model is opt-in and local-cache only."""

from functools import lru_cache

from . import config
from .text_utils import content_terms, vietnamese_tokens


@lru_cache(maxsize=1)
def _cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name, device="cpu", max_length=512, local_files_only=True,
                        cache_folder=str(config.PROJECT_ROOT / ".cache" / "models"))


def passage_text(chunk: dict) -> str:
    metadata = chunk.get("metadata", {})
    headings = dict.fromkeys(metadata.get(key, "") for key in ("regulation", "article_title", "clause_title"))
    return " ".join([text for text in headings if text and text not in chunk["text"]] + [chunk["text"]])


def rerank(question: str, candidates: list[dict], mode: str, model_name: str) -> list[dict]:
    if not candidates:
        return []
    max_rrf = max(c["rrf_score"] for c in candidates)
    query_terms = content_terms(question)
    query_compounds = {term for term in vietnamese_tokens(question) if "_" in term}
    if mode == "cross-encoder":
        scores = _cross_encoder(model_name).predict([(question, passage_text(c)) for c in candidates],
                                                     batch_size=8, show_progress_bar=False)
    else:
        scores = []
        for chunk in candidates:
            if mode == "none":
                score = chunk["rrf_score"]
            else:
                text = passage_text(chunk)
                coverage = len(query_terms & content_terms(text)) / max(len(query_terms), 1)
                compounds = set(vietnamese_tokens(text))
                phrase_match = len(query_compounds & compounds) / max(len(query_compounds), 1)
                # Ranking features, never an answerability threshold or a probability.
                score = 0.5 * chunk["rrf_score"] / max_rrf + 0.3 * coverage + 0.2 * phrase_match
            scores.append(score)
    ranked = [{**chunk, "rerank_score": float(score)} for chunk, score in zip(candidates, scores)]
    return sorted(ranked, key=lambda c: (-c["rerank_score"], c["order"]))
