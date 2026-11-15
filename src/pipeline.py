"""Public advanced QA entry point, alongside the unchanged dense Code 2 API."""

import argparse
import json
import time
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from . import config
from .answering import AnswerGenerator
from .hybrid_retriever import HybridRetriever
from .llm import OllamaJSON
from .entailment import get_entailment
from .query_processing import plan_query
from .retriever import get_retriever
from .settings import RAGSettings


class RAGPipeline:
    def __init__(self, index_dir=None, *, settings=None, llm=None, encoder=None):
        self.settings = settings or RAGSettings.from_env()
        self.llm = llm if llm is not None else OllamaJSON(self.settings)
        index = get_retriever(str(Path(index_dir or config.INDEX_DIR).resolve()))
        self.retriever = HybridRetriever(index, self.settings, encoder=encoder)

    def retrieve(self, question: str):
        plan = plan_query(question, llm=self.llm if self.settings.rewrite == "llm" else None,
                          max_queries=self.settings.max_queries)
        return self.retriever.search(plan)

    def ask(self, question: str):
        started = time.perf_counter()
        call_start = len(getattr(self.llm, "calls", []))
        retrieval = self.retrieve(question)
        retrieved_at = time.perf_counter()

        def on_missing(missing):
            nonlocal retrieval
            retrieval = self.retriever.search_more(retrieval, missing)
            return retrieval.contexts

        checker = (lambda premise, hypothesis: get_entailment().check(premise, hypothesis)) if self.settings.support_check == "nli" else None
        result = AnswerGenerator(self.llm, entailment=checker).generate(question, retrieval.contexts, on_missing=on_missing, query_plan=retrieval.plan)
        result.warnings = list(dict.fromkeys(retrieval.plan.warnings + retrieval.warnings))
        result.debug.update(retrieval.debug_dict())
        result.debug.update(retrieval_seconds=retrieved_at - started, total_seconds=time.perf_counter() - started,
                            llm_calls=getattr(self.llm, "calls", [])[call_start:], settings=asdict(self.settings))
        return result


@lru_cache(maxsize=2)
def get_pipeline(index_dir: str, settings: RAGSettings):
    return RAGPipeline(index_dir, settings=settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--retrieve-only", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    pipeline = RAGPipeline()
    result = pipeline.retrieve(args.question).debug_dict() if args.retrieve_only else asdict(pipeline.ask(args.question))
    if not args.debug and not args.retrieve_only:
        result.pop("debug", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
