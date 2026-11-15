"""E5 + Vietnamese BM25, RRF, scoped expansion and bounded adaptive retrieval."""

from dataclasses import dataclass, field
import re

import numpy as np

from .bm25 import BM25
from .answer_requirements import question_requirements
from .document_structure import load_structure
from .embeddings import get_embedder
from .query_processing import QueryPlan, constraint_suffix
from .reranking import passage_text, rerank
from .settings import RAGSettings
from .text_utils import audience_qualifiers, canonical, content_terms, folded


def scope_matches(metadata: dict, constraints: dict) -> bool:
    for key in ("levels", "modes"):
        requested, applies = set(constraints.get(key, [])), set(metadata.get(key, []))
        if requested and applies and not requested & applies:
            return False
    tracks = set(constraints.get("program_tracks", []))
    if tracks and not tracks & set(metadata.get("program_tracks", [])):
        return False
    return True


def annotate_program_tracks(chunks: list[dict]) -> list[dict]:
    """Keep numbered joint programs separate using verbatim heading boundaries.

    Enrich only RAM metadata; never alter stored chunks, vectors or sidecars.
    A chunk can straddle two programs, so retain exact ranges for each track.
    """
    heading = re.compile(r"CHƯƠNG TRÌNH[A-ZĐÀ-Ỹ\s]{0,150}?(\d+\s*\+\s*\d+)|\bNGÀNH\s+([^\W\d_]+)")
    active, previous_source, result = None, None, []
    for chunk in chunks:
        if chunk["source"] != previous_source:
            active = None
        previous_source = chunk["source"]
        ranges, start = {}, 0
        for match in heading.finditer(chunk["text"]):
            if match[2] and not match[2].isupper():
                continue
            if active and match.start() > start:
                ranges.setdefault(active, []).append([start, match.start()])
            active = re.sub(r"\s+", "", match[1]) if match[1] else None
            start = match.start()
        if active and start < len(chunk["text"]):
            ranges.setdefault(active, []).append([start, len(chunk["text"])])
        result.append({**chunk, "metadata": {**chunk.get("metadata", {}),
                       "program_tracks": sorted(ranges), "program_ranges": ranges}})
    return result


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    scores = {}
    for ranking in rankings:
        for rank, index in enumerate(dict.fromkeys(ranking), 1):
            scores[index] = scores.get(index, 0.0) + 1.0 / (k + rank)
    return scores


def deduplicate(candidates: list[dict]) -> list[dict]:
    result, seen = [], set()
    for candidate in candidates:
        metadata = candidate["metadata"]
        scope = (metadata.get("document_id"), metadata.get("article"), metadata.get("clause"), metadata.get("item_title"),
                 tuple(metadata.get("levels", [])), tuple(metadata.get("modes", [])), tuple(metadata.get("program_tracks", [])))
        key = (canonical(candidate["text"]).casefold(), scope)
        if key in seen:
            continue
        terms = content_terms(candidate["text"])
        near_duplicate = False
        if len(terms) >= 20:
            for prior in result:
                if prior["metadata"] != metadata:
                    continue
                other = content_terms(prior["text"])
                if len(terms & other) / max(len(terms | other), 1) > 0.92:
                    near_duplicate = True
                    break
        if not near_duplicate:
            result.append(candidate)
            seen.add(key)
    return result


@dataclass
class RetrievalResult:
    plan: QueryPlan
    candidates: list[dict]
    contexts: list[dict]
    rounds: list[dict]
    warnings: list[str] = field(default_factory=list)

    def debug_dict(self):
        return {"plan": self.plan.to_dict(), "rounds": self.rounds, "warnings": self.warnings,
                "candidates": self.candidates, "contexts": self.contexts}


class HybridRetriever:
    def __init__(self, index, settings: RAGSettings | None = None, *, encoder=None):
        self.index = index
        self.settings = settings or RAGSettings.from_env()
        self.encoder = encoder
        self._signature = None
        self._refresh()

    def _refresh(self):
        self.index._ensure_index()
        signature = (self.index.meta["chunks_sha256"], self.index.meta["source_sha256"])
        if signature != self._signature:
            self.metadata = load_structure(self.index)
            self.chunks = annotate_program_tracks([{**c, "metadata": self.metadata[c["chunk_id"]]} for c in self.index.chunks])
            self.by_id = {c["chunk_id"]: c for c in self.chunks}
            self.bm25 = BM25([passage_text(c) for c in self.chunks])
            self._signature = signature

    def _retrieve_round(self, plan: QueryPlan, queries: list[str]) -> tuple[list[dict], dict]:
        self._refresh()
        encoder = self.encoder or get_embedder()
        if encoder.revision != self.index.meta["model_revision"]:
            raise ValueError("Phiên bản E5 không khớp index; hãy build lại")
        vectors = encoder.encode(queries, "query")
        dense = self.index.vectors @ vectors.T
        allowed = np.array([scope_matches(c["metadata"], plan.constraints) for c in self.chunks])
        rankings, traces = [], []
        for q_index, query in enumerate(queries):
            sparse_scores = self.bm25.scores(query)
            dense_order = [int(i) for i in np.argsort(-dense[:, q_index], kind="stable") if allowed[i]][:self.settings.candidates_per_method]
            sparse_order = [int(i) for i in np.argsort(-sparse_scores, kind="stable") if allowed[i] and sparse_scores[i] > 0][:self.settings.candidates_per_method]
            rankings.extend([dense_order, sparse_order])
            traces.append({"query": query,
                           "dense": [{"chunk_id": self.chunks[i]["chunk_id"], "score": float(dense[i, q_index])} for i in dense_order],
                           "bm25": [{"chunk_id": self.chunks[i]["chunk_id"], "score": float(sparse_scores[i])} for i in sparse_order]})
        fused = {i: score / max(len(rankings), 1)
                 for i, score in reciprocal_rank_fusion(rankings, self.settings.rrf_k).items()}
        candidates = [{**self.chunks[i], "score": float(dense[i, 0]), "rrf_score": score}
                      for i, score in sorted(fused.items(), key=lambda item: (-item[1], item[0]))]
        candidates = deduplicate(candidates)
        ranked = rerank(" ".join(plan.queries), candidates, self.settings.reranker, self.settings.reranker_model)
        return ranked, {"queries": traces, "candidate_count": len(candidates)}

    def _select_contexts(self, plan: QueryPlan, candidates: list[dict]) -> tuple[list[dict], list[str]]:
        limit = self.settings.complex_contexts if plan.complex else self.settings.simple_contexts
        encoder = self.encoder or get_embedder()
        selected, selected_ids, used_tokens = [], set(), 0

        def add(chunk, reason):
            nonlocal used_tokens
            if chunk["chunk_id"] in selected_ids or len(selected) >= limit:
                return False
            # Includes metadata overhead; no silent source truncation.
            tokens = encoder.token_lengths([passage_text(chunk)], "passage")[0] + 50
            if used_tokens + tokens > self.settings.context_tokens:
                return False
            selected.append({**chunk, "selection_reason": reason, "estimated_tokens": tokens})
            selected_ids.add(chunk["chunk_id"])
            used_tokens += tokens
            return True

        # Cover explicit subquestions before filling by global rank.
        def generality(chunk):
            meta = chunk.get("metadata", {})
            qualifiers = audience_qualifiers(chunk["text"] + " " + meta.get("item_title", "") + " " + meta.get("regulation", ""))
            return sum(folded(q) not in folded(plan.original) for q in qualifiers)

        for requirement in question_requirements(plan.original):
            if requirement.key not in {"months", "credits", "money", "times", "discipline", "conduct", "academic", "language_exit", "earliest", "registration_first", "registration_later", "email", "website"}:
                continue
            matching = [c for c in candidates if requirement.matches(c["text"])]
            attribute_scores = self.bm25.scores(requirement.query)
            best = min(matching, key=lambda c: (generality(c), -float(attribute_scores[c["order"]]), -c["rerank_score"]), default=None)
            if best:
                add(best, "requested_attribute:" + requirement.key)
        for subquestion in plan.subquestions[:3]:
            terms = content_terms(subquestion)
            best = max(candidates, key=lambda c: (len(terms & content_terms(passage_text(c))) / max(len(terms), 1), c["rerank_score"]), default=None)
            if best:
                add(best, "subquestion")
        anchor_limit = max(1, limit - (2 if plan.complex else 1))
        for level in plan.constraints.get("levels", []):
            scoped = next((c for c in candidates if c["metadata"].get("levels") == [level]), None)
            if scoped:
                add(scoped, "requested_level")
        for candidate in candidates:
            if len(selected) >= anchor_limit:
                break
            add(candidate, "ranked")
        for candidate in list(selected):
            meta = candidate["metadata"]
            # Expand tiny/continuation items within exactly the same regulation,
            # article and clause. Each neighboring source keeps its own ID/page.
            if len(candidate["text"]) < 240 and meta.get("article_key"):
                neighbors = self.chunks[max(0, candidate["order"] - 2):candidate["order"] + 3]
                for neighbor in neighbors:
                    other = neighbor["metadata"]
                    if (other.get("article_key") == meta["article_key"]
                            and other.get("clause") == meta.get("clause")
                            and abs(neighbor["page"] - candidate["page"]) <= 1
                            and scope_matches(other, plan.constraints)):
                        add(neighbor, "same_clause_neighbor")
                        if len(selected) >= limit:
                            break
        for candidate in candidates:
            if len(selected) >= limit:
                break
            add(candidate, "ranked")
        warnings = list(dict.fromkeys(warning for c in selected for warning in c["metadata"].get("extraction_warnings", [])))
        return selected, warnings

    def search(self, plan: QueryPlan) -> RetrievalResult:
        ranked, trace = self._retrieve_round(plan, plan.queries[:self.settings.max_queries])
        contexts, warnings = self._select_contexts(plan, ranked)
        return RetrievalResult(plan, ranked, contexts, [trace], warnings)

    def search_more(self, previous: RetrievalResult, missing: list[str]) -> RetrievalResult:
        if len(previous.rounds) >= self.settings.max_rounds:
            return previous
        suffix = constraint_suffix(previous.plan.constraints)
        queries = [canonical(q + " " + suffix) for q in missing if isinstance(q, str) and q.strip()]
        if not queries:
            queries = [canonical(previous.plan.original + " " + previous.plan.intent + " " + suffix)]
        # Original constraints and question participate in every round.
        queries = list(dict.fromkeys([previous.plan.original] + queries))[:self.settings.max_queries]
        ranked, trace = self._retrieve_round(previous.plan, queries)
        merged = {c["chunk_id"]: c for c in previous.candidates}
        for chunk in ranked:
            if chunk["chunk_id"] not in merged or chunk["rerank_score"] > merged[chunk["chunk_id"]]["rerank_score"]:
                merged[chunk["chunk_id"]] = chunk
        # Rank against the original question, not invented missing-aspect terms.
        candidates = rerank(" ".join(previous.plan.queries), deduplicate(list(merged.values())), self.settings.reranker, self.settings.reranker_model)
        contexts, warnings = self._select_contexts(previous.plan, candidates)
        return RetrievalResult(previous.plan, candidates, contexts, previous.rounds + [trace], warnings)
