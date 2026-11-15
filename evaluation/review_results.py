"""Attach explicit, answer-hash-bound reviews; never infer correctness from IDs."""

import argparse
import hashlib
import json
from pathlib import Path

from .run_benchmark import summarize


def answer_hash(qa):
    data = {key: value for key, value in qa.items() if key != "debug"}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def review_template(reports):
    reviews = {}
    for report in reports:
        for row in report["results"]:
            if "qa" not in row:
                continue
            qa = row["qa"]
            claims = qa.get("claims", [])
            total_citations = sum(len(c.get("citations", [])) for c in claims) if row["system"] == "hybrid" else len(qa["sources"])
            reviews.setdefault(row["id"], {})[row["system"]] = {
                "answer_sha256": answer_hash(qa), "correct": None, "complete": None,
                "total_claims": len(claims), "supported_claims": None,
                "total_citations": total_citations, "wrong_citations": None, "reason": ""}
    return {"reviewer": "", "method": "Review answer, conditions and every claim/citation against PDF-derived text; whole baseline answer is one composite claim.",
            "reviews": reviews}


def apply_reviews(reports, annotations):
    if not all(report.get("complete") for report in reports):
        raise ValueError("Không tổng kết chất lượng từ báo cáo dừng giữa chừng")
    rows = [row for report in reports for row in report["results"]]
    if len({(r["id"], r["system"]) for r in rows}) != len(rows):
        raise ValueError("Các báo cáo có câu hỏi/system trùng nhau")
    template = review_template(reports)["reviews"]
    reviews = annotations["reviews"]
    expected_pairs = {(identifier, system) for identifier, systems in template.items() for system in systems}
    actual_pairs = {(identifier, system) for identifier, systems in reviews.items() for system in systems}
    if actual_pairs != expected_pairs:
        raise ValueError("Review phải bao phủ đúng mọi câu hỏi/system trong các báo cáo")
    for identifier, systems in reviews.items():
        for system, review in systems.items():
            expected = template[identifier][system]
            for key in ("answer_sha256", "total_claims", "total_citations"):
                if review[key] != expected[key]:
                    raise ValueError(f"{identifier}/{system}: nhãn review không khớp phản hồi ({key})")
            if not isinstance(review["correct"], bool) or not isinstance(review["complete"], bool):
                raise ValueError(f"{identifier}/{system}: chưa chấm đúng/đầy đủ")
            for key, total in (("supported_claims", "total_claims"), ("wrong_citations", "total_citations")):
                if type(review[key]) is not int or not 0 <= review[key] <= review[total]:
                    raise ValueError(f"{identifier}/{system}: sai số đếm review")
    combined = {"systems": sorted({row["system"] for row in rows}), "answers": True, "results": rows}
    result = {"reviewer": annotations["reviewer"], "method": annotations["method"],
              "summary": summarize(combined, reviews), "by_split": {},
              "source_reports": [{key: r.get(key) for key in ("split", "dataset_sha256", "implementation_sha256", "settings", "complete")}
                                 for r in reports]}
    for split in {r["split"] for r in reports}:
        split_rows = [row for report in reports if report["split"] == split for row in report["results"]]
        result["by_split"][split] = summarize({**combined, "results": split_rows}, reviews)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, nargs="+", required=True)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.reports]
    result = apply_reviews(reports, json.loads(args.annotations.read_text(encoding="utf-8"))) if args.annotations else review_template(reports)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
