"""Compare the frozen dense/Top-3 baseline with advanced QA on disjoint splits.

Retrieval metrics are exact evidence-label checks, not page hits. Answer quality
requires explicit review annotations; unreviewed correctness is null, never 100%.
"""

import argparse
import hashlib
import json
import platform
import resource
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.answering import NO_ANSWER
from src.build_index import file_sha256
from src.pipeline import RAGPipeline
from src.retriever import Retriever
from src.settings import RAGSettings

BENCHMARK_DIR = config.PROJECT_ROOT / "evaluation" / "benchmark"


def validate_dataset(rows: list[dict], index, benchmark_dir: Path):
    manifest = json.loads((benchmark_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_sha256"] != index.meta["source_sha256"] or manifest["chunks_sha256"] != index.meta["chunks_sha256"]:
        raise ValueError("Nhãn benchmark không khớp PDF/chunk index")
    families = {}
    for split in ("dev", "test"):
        path = benchmark_dir / f"{split}.json"
        if file_sha256(path) != manifest["files"][path.name]:
            raise ValueError("Benchmark đã đổi sau khi đóng băng")
        families[split] = {family for row in json.loads(path.read_text(encoding="utf-8")) for family in row["evidence_families"]}
    if families["dev"] & families["test"]:
        raise ValueError("Rò rỉ nhóm chứng cứ giữa dev/test")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("ID câu hỏi bị lặp")
    by_id = {c["chunk_id"]: c for c in index.chunks}
    for row in rows:
        if row["answerability"] != "none" and not row["evidence"]:
            raise ValueError(f"{row['id']}: thiếu nhãn chứng cứ")
        for evidence in row["evidence"]:
            if not evidence["gold_chunk_ids"]:
                raise ValueError(f"{row['id']}: thiếu gold IDs")
            for source_id in evidence["gold_chunk_ids"]:
                chunk = by_id.get(source_id)
                if (not chunk or chunk["source"] != evidence["source"] or chunk["page"] != evidence["page"]
                        or evidence["quote"] not in chunk["text"]):
                    raise ValueError(f"{row['id']}: chứng cứ không khớp nguồn/trang/text")


def retrieval_metrics(row: dict, results: list[dict]) -> dict:
    groups = row["evidence"]
    if not groups:
        return {"recall_at_5": None, "recall_at_10": None, "mrr_at_10": None}

    def relevant(chunk, group):
        return (chunk["chunk_id"] in group["gold_chunk_ids"] and chunk["source"] == group["source"]
                and chunk["page"] == group["page"] and group["quote"] in chunk["text"])

    values = {f"recall_at_{k}": sum(any(relevant(c, group) for c in results[:k]) for group in groups) / len(groups)
              for k in (5, 10)}
    values["mrr_at_10"] = next((1 / rank for rank, chunk in enumerate(results[:10], 1)
                                 if any(relevant(chunk, group) for group in groups)), 0.0)
    return values


def source_coverage(row: dict, contexts: list[dict]) -> float | None:
    if not row["evidence"]:
        return None
    return sum(any(c["chunk_id"] in group["gold_chunk_ids"] and group["quote"] in c["text"]
                   for c in contexts) for group in row["evidence"]) / len(row["evidence"])


def baseline_answer(question, chunks):
    from evaluation import baseline_streamlit as baseline

    responses = []
    original_client = baseline.Client

    class RecordingClient:
        def __init__(self, *args, **kwargs):
            self.client = original_client(*args, **kwargs)

        def chat(self, **kwargs):
            response = self.client.chat(**kwargs)
            responses.append(response.message.content)
            return response

    baseline.Client = RecordingClient
    try:
        answer, sources = baseline.generate_answer(question, chunks)
    finally:
        baseline.Client = original_client
    return {"status": "insufficient" if answer == NO_ANSWER else "complete", "answer": answer,
            "sources": sources, "claims": [] if answer == NO_ANSWER else [{"text": answer}],
            "missing_information": [], "debug": {"raw_responses": responses}}


def implementation_hash():
    digest = hashlib.sha256()
    paths = sorted((config.PROJECT_ROOT / "src").glob("*.py"))
    paths += [Path(__file__), config.PROJECT_ROOT / "evaluation" / "baseline_streamlit.py"]
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def peak_rss_mib():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024 if sys.platform == "darwin" else 1024)


def ollama_memory_snapshot():
    """Server + runner RSS after a request, not a peak or unique unified memory."""
    try:
        processes = subprocess.run(["ps", "-axo", "rss=,comm="], capture_output=True, text=True, check=True)
        return sum(int(line.split(maxsplit=1)[0]) / 1024 for line in processes.stdout.splitlines()
                   if "ollama" in line.casefold())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def summarize(report, reviews=None):
    reviews = reviews or {}
    summary = {}
    def average(values):
        values = [value for value in values if value is not None]
        return statistics.mean(values) if values else None
    for system in report["systems"]:
        rows = [row for row in report["results"] if row["system"] == system]
        quality = [reviews.get(row["id"], {}).get(system, {}) for row in rows if row["answerability"] == "full"]
        reviewed = [q for q in quality if isinstance(q.get("correct"), bool) and isinstance(q.get("complete"), bool)]
        evidence_reviews = [reviews.get(row["id"], {}).get(system, {}) for row in rows]
        claims = sum(q.get("total_claims") or 0 for q in evidence_reviews)
        citations = sum(q.get("total_citations") or 0 for q in evidence_reviews)
        no_answer = [row for row in rows if row["answerability"] == "none"] if report.get("answers") else []
        measured = {key: average(row["retrieval_metrics"][key] for row in rows)
                    for key in ("recall_at_5", "recall_at_10", "mrr_at_10")}
        measured.update(
            questions=len(rows), errors=sum("error" in row for row in rows),
            context_evidence_recall=average(row["context_evidence_recall"] for row in rows),
            response_seconds_mean=statistics.mean(row["elapsed_seconds"] for row in rows) if rows else None,
            response_seconds_p95=float(__import__("numpy").percentile([row["elapsed_seconds"] for row in rows], 95)) if rows else None,
            correct_complete_rate=sum(q["correct"] and q["complete"] for q in reviewed) / len(reviewed) if reviewed else None,
            reviewed_full_answers=len(reviewed),
            supported_claim_rate=sum(q.get("supported_claims") or 0 for q in evidence_reviews) / claims if claims else None,
            wrong_citation_rate=sum(q.get("wrong_citations") or 0 for q in evidence_reviews) / citations if citations else None,
            correct_refusal_rate=sum(row.get("qa", {}).get("status") == "insufficient" for row in no_answer) / len(no_answer) if no_answer else None,
            refusal_denominator=len(no_answer),
            peak_python_rss_mib=max((row["python_peak_rss_mib"] for row in rows), default=0),
            max_sampled_ollama_rss_mib=max((row["ollama_rss_mib_after"] for row in rows
                                           if row.get("ollama_rss_mib_after") is not None), default=None),
        )
        summary[system] = measured
    return summary


def run(args):
    index = Retriever(config.INDEX_DIR)
    dataset_path = args.benchmark / f"{args.split}.json"
    rows = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_dataset(rows, index, args.benchmark)
    if args.ids:
        wanted = set(args.ids.split(","))
        rows = [row for row in rows if row["id"] in wanted]
        if {row["id"] for row in rows} != wanted:
            raise ValueError("ID không thuộc split đã chọn")
    settings = RAGSettings(rewrite=args.rewrite, reranker=args.reranker, support_check=args.support_check)
    systems = ["baseline", "hybrid"] if args.system == "both" else [args.system]
    header = dict(split=args.split, dataset_sha256=file_sha256(dataset_path),
                  implementation_sha256=implementation_hash(), settings=asdict(settings), systems=systems,
                  answers=args.answers, question_ids=[row["id"] for row in rows])
    report = dict(**header, evaluated_at=datetime.now(timezone.utc).isoformat(), complete=False,
                  source_sha256=index.meta["source_sha256"], chunks_sha256=index.meta["chunks_sha256"],
                  platform=platform.platform(), python=sys.version, results=[],
                  definitions={"recall": "Mean evidence-group recall: each gold quotation is a required group, alternative overlapping chunk IDs count once. Require source, physical page, ID and entire quotation.",
                               "mrr": "First chunk containing at least one required quotation within rank 10.",
                               "quality": "Null until explicit review annotations. Automated citation verification is not independent quality measurement.",
                               "memory": "Process-lifetime peak Python RSS. Ollama server/runner RSS sampled after each answer via ps, not a peak or unique unified memory. Both-system runs share caches; do not interpret as isolated memory comparisons.",
                               "timing": "Warm reuse within process; first question includes cold E5 load. End-to-end includes generation, validation and repairs."})
    if args.resume and args.out.exists():
        previous = json.loads(args.out.read_text(encoding="utf-8"))
        if any(previous.get(key) != value for key, value in header.items()):
            raise ValueError("Không resume: dữ liệu/code/cấu hình đã đổi")
        report = previous
        report["complete"] = False
    done = {(row["id"], row["system"]) for row in report["results"]}
    pipeline = RAGPipeline(settings=settings) if "hybrid" in systems else None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for question in rows:
        for system in systems:
            if (question["id"], system) in done:
                continue
            started = time.perf_counter()
            row = {key: question[key] for key in ("id", "question", "category", "answerability")}
            row["system"] = system
            # Errors remain errors, never successful abstentions.
            try:
                if system == "baseline":
                    ranking = index.retrieve(question["question"], top_k=10)
                    contexts = ranking[:3]
                else:
                    retrieval = pipeline.retrieve(question["question"])
                    ranking, contexts = retrieval.candidates[:10], retrieval.contexts
                    row["retrieval_debug"] = retrieval.debug_dict()
                row["ranking"] = ranking
                row["retrieval_metrics"] = retrieval_metrics(question, ranking)
                row["context_evidence_recall"] = source_coverage(question, contexts)
                if args.answers:
                    if system == "baseline":
                        row["qa"] = baseline_answer(question["question"], contexts)
                    else:
                        # Use the same retrieval snapshot as scored; avoid a hidden second initial search.
                        from src.answering import AnswerGenerator

                        def on_missing(missing):
                            nonlocal retrieval
                            retrieval = pipeline.retriever.search_more(retrieval, missing)
                            return retrieval.contexts

                        call_start = len(pipeline.llm.calls)
                        from src.entailment import get_entailment
                        checker = (lambda premise, hypothesis: get_entailment().check(premise, hypothesis)) if settings.support_check == "nli" else None
                        qa = AnswerGenerator(pipeline.llm, entailment=checker).generate(question["question"], contexts, on_missing=on_missing, query_plan=retrieval.plan)
                        qa.warnings = retrieval.warnings
                        qa.debug.update(retrieval.debug_dict())
                        qa.debug["llm_calls"] = pipeline.llm.calls[call_start:]
                        row["qa"] = asdict(qa)
                        row["final_context_evidence_recall"] = source_coverage(question, retrieval.contexts)
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {exc}"
                row.setdefault("retrieval_metrics", {key: None for key in ("recall_at_5", "recall_at_10", "mrr_at_10")})
                row.setdefault("context_evidence_recall", None)
            row["elapsed_seconds"] = time.perf_counter() - started
            row["python_peak_rss_mib"] = peak_rss_mib()
            if args.answers:
                row["ollama_rss_mib_after"] = ollama_memory_snapshot()
            report["results"].append(row)
            report["summary"] = summarize(report)
            args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{row['id']} {system}: {row.get('qa', {}).get('status', 'retrieval')} {row['elapsed_seconds']:.2f}s {row.get('error', '')}", flush=True)
    report["complete"] = True
    report["summary"] = summarize(report)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK_DIR)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--system", choices=["baseline", "hybrid", "both"], default="both")
    parser.add_argument("--reranker", choices=["none", "lexical", "cross-encoder"], default="lexical")
    parser.add_argument("--rewrite", choices=["rules", "llm"], default="rules")
    parser.add_argument("--support-check", choices=["nli", "llm"], default="nli")
    parser.add_argument("--answers", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--ids", help="Optional comma-separated smoke subset; explicitly recorded in report")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run(args)
    if any("error" in row for row in report["results"]):
        parser.exit(2, "Có lỗi thực thi; xem report, không tính lỗi là từ chối đúng.\n")


if __name__ == "__main__":
    main()
