"""Run Q01-Q03 through the public API and save auditable Top-3 evidence."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src import config
from src.build_index import file_sha256
from src.retriever import get_retriever, retrieve


QUESTIONS_PATH = config.PROJECT_ROOT / "evaluation" / "questions.json"
REPORT_PATH = config.PROJECT_ROOT / "evaluation" / "retrieval_report.json"


def validate_gold(questions: list[dict], chunks: list[dict]) -> None:
    if not isinstance(questions, list) or len(questions) != 3:
        raise ValueError("CV14 yêu cầu đúng ba câu Q01-Q03")
    if {q.get("id") for q in questions} != {"Q01", "Q02", "Q03"}:
        raise ValueError("Cần đủ Q01, Q02, Q03; không trùng ID")
    by_id = {c["chunk_id"]: c for c in chunks}
    for question in questions:
        evidence = question.get("expected_evidence")
        gold = question.get("gold_chunk_ids")
        if not isinstance(question.get("question"), str) or not question["question"].strip():
            raise ValueError("Câu hỏi phải có nội dung")
        if not isinstance(evidence, str) or not evidence.strip() or not isinstance(gold, list) or not gold:
            raise ValueError(f"{question['id']}: cần bằng chứng và gold_chunk_ids đã gán nhãn")
        for chunk_id in gold:
            chunk = by_id.get(chunk_id)
            if (chunk is None or chunk["source"] != question.get("expected_source")
                    or chunk["page"] != question.get("expected_page") or evidence not in chunk["text"]):
                raise ValueError(f"{question['id']}: gold {chunk_id} không chứa đúng chứng cứ; kiểm tra lại nhãn sau rebuild")


def score_results(question: dict, results: list[dict]) -> bool:
    """A page match alone never passes; require label + source + page + evidence."""
    return any(
        item["chunk_id"] in question["gold_chunk_ids"]
        and item["source"] == question["expected_source"]
        and item["page"] == question["expected_page"]
        and question["expected_evidence"] in item["text"]
        for item in results
    )


def run_evaluation(questions_path: str | Path = QUESTIONS_PATH, report_path: str | Path = REPORT_PATH) -> dict:
    questions_path, report_path = Path(questions_path), Path(report_path)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    index = get_retriever(str(Path(config.INDEX_DIR).resolve()))
    index._ensure_index()
    validate_gold(questions, index.chunks)
    results = []
    for question in questions:
        top3 = retrieve(question["question"], top_k=3)
        hit = score_results(question, top3)
        results.append({**question, "top_3": top3, "hit_at_3": int(hit),
                        "notes": "Có gold chunk chứa nguyên chứng cứ trong Top-3" if hit else
                        "Top-3 không có gold chunk đủ chứng cứ; cần kiểm tra chunking/ranking. Giữ nguyên câu hỏi và nhãn"})
    hits = sum(result["hit_at_3"] for result in results)
    meta = index.meta
    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "source": meta["source"], "source_sha256": meta["source_sha256"],
        "page_range": meta["page_range"], "model_name": meta["model_name"],
        "model_revision": meta["model_revision"], "num_chunks": meta["num_chunks"],
        "chunk_size_chars": meta["chunk_size_chars"], "chunk_overlap_chars": meta["chunk_overlap_chars"],
        "chunk_strategy": meta["chunk_strategy"],
        "max_passage_tokens": meta["max_passage_tokens"],
        "index_build_timestamp": meta["build_timestamp"],
        "chunks_sha256": meta["chunks_sha256"], "embeddings_sha256": meta["embeddings_sha256"],
        "questions_sha256": file_sha256(questions_path),
        "scoring_rule": "Hit iff one Top-3 chunk matches a gold ID, source, page AND contains the entire expected_evidence; each gold ID independently contains the full evidence",
        "questions": results, "hits": hits, "total": 3, "hit_at_3": hits / 3,
        "target_met": hits == 3,
        "notes": ["Ba câu kiểm tra chỉ bao phủ trang 8, 9, 15; không chứng minh độ chính xác toàn bộ sổ tay.",
                  "Các phần khác có quy chế tương tự; score là cosine similarity, không phải xác suất đúng."],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH)
    parser.add_argument("--out", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    try:
        report = run_evaluation(args.questions, args.out)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Lỗi đánh giá: {exc}\n")
    for result in report["questions"]:
        print(f"{result['id']} | Hit@3={result['hit_at_3']} | {result['question']}")
        for rank, item in enumerate(result["top_3"], 1):
            print(f"  {rank}. {item['chunk_id']} | trang={item['page']} | cosine={item['score']:.6f}")
    print(f"Hit@3 = {report['hits']}/{report['total']} = {report['hit_at_3']:.6f}; report={args.out}")
    if not report["target_met"]:
        parser.exit(2, "Chưa đạt mục tiêu 3/3; kết quả thật đã được lưu\n")


if __name__ == "__main__":
    main()
