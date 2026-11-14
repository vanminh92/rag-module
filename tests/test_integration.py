import json

import numpy as np
import pytest

from evaluation.run_evaluation import QUESTIONS_PATH, run_evaluation, score_results, validate_gold
from src.build_index import build_index, extract_chunks, parse_pages
from src.chunking import build_chunks
from src.retriever import Retriever


def test_cv12_cli_pipeline(pdf_path, tmp_path, pilot_pages):
    stats = extract_chunks(pdf_path, tmp_path, 8, 31)
    chunks = json.loads((tmp_path / "chunks.json").read_text(encoding="utf-8"))
    assert chunks == build_chunks(pilot_pages, pdf_path.name)
    assert stats["num_chunks"] == len(chunks)
    assert {c["page"] for c in chunks} == set(range(8, 32))


def test_page_parser():
    import argparse
    assert parse_pages("8-31") == (8, 31)
    for value in ("0-31", "31-8", "8", "8-", "8.5-31"):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_pages(value)


def test_gold_evidence_labels_are_present(pilot_pages, pdf_path):
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    chunks = build_chunks(pilot_pages, pdf_path.name)
    validate_gold(questions, chunks)
    for question in questions:
        evidence_chunk = next(c for c in chunks if c["chunk_id"] == question["gold_chunk_ids"][0])
        assert score_results(question, [evidence_chunk])
        same_page_other_text = next(c for c in chunks if c["page"] == question["expected_page"]
                                    and c["chunk_id"] not in question["gold_chunk_ids"])
        assert not score_results(question, [same_page_other_text])
    questions[0]["gold_chunk_ids"] = []
    with pytest.raises(ValueError, match="gold_chunk_ids"):
        validate_gold(questions, chunks)


@pytest.mark.real_model
def test_real_pipeline_end_to_end(pdf_path, tmp_path):
    # Rebuild the actual 24 PDF pages, not a mocked pipeline or fabricated text.
    meta = build_index(pdf_path, tmp_path, 8, 31)
    assert meta["page_range"] == [8, 31]
    assert meta["max_passage_tokens"] <= 512
    vectors = np.load(tmp_path / "embeddings.npy", allow_pickle=False)
    assert vectors.shape == (meta["num_chunks"], 384)
    assert vectors.dtype == np.float32
    index = Retriever(tmp_path, expected_page_range=(8, 31))
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    validate_gold(questions, index.chunks)
    for question in questions:
        results = index.retrieve(question["question"])
        assert len(results) == 3
        assert score_results(question, results)
    with pytest.raises(ValueError, match="đã có index"):
        extract_chunks(pdf_path, tmp_path, 8, 31)


@pytest.mark.real_model
def test_evaluation_uses_public_api_and_writes_real_report(tmp_path):
    output = tmp_path / "report.json"
    report = run_evaluation(report_path=output)
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert report["total"] == 3
    assert all(len(q["top_3"]) == 3 for q in report["questions"])
    # Acceptance test: any regression is visible, without changing questions.
    assert report["hits"] == 3
