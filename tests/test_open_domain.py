"""Regression checks for lost evidence, incorrect scope and fabricated citations."""

import json
from dataclasses import replace

import pytest

from evaluation.run_benchmark import BENCHMARK_DIR, retrieval_metrics, summarize, validate_dataset
from src import config
from src.answering import AnswerGenerator, Claim, EvidenceQuote, coverage_gaps, locate_quote, validate_evidence
from src.bm25 import BM25
from src.document_structure import load_structure
from src.hybrid_retriever import deduplicate, reciprocal_rank_fusion, scope_matches
from src.pipeline import RAGPipeline
from src.query_processing import plan_query
from src.retriever import Retriever
from src.settings import RAGSettings
from src.text_utils import vietnamese_tokens


@pytest.fixture(scope="module")
def real_index():
    return Retriever(config.INDEX_DIR)


@pytest.fixture(scope="module")
def metadata(real_index):
    return load_structure(real_index)


@pytest.fixture
def credit_chunk(real_index, metadata):
    chunk = next(c for c in real_index.chunks if c["page"] == 8 and "15 giờ học lý thuyết" in c["text"])
    return {**chunk, "metadata": metadata[chunk["chunk_id"]]}


def draft(text, quote, *, source_id="S1", status="complete", missing=None):
    return {"status": status, "claims": [{"text": text, "citations": [{"source_id": source_id, "quote": quote}]}],
            "missing_information": missing or []}


class ScriptedLLM:
    def __init__(self, answers, *, supported=True, relevant=True):
        self.answers = iter(answers)
        self.supported, self.relevant = supported, relevant
        self.calls = []

    def __call__(self, task, system, payload, schema, **kwargs):
        self.calls.append(task)
        if task == "verify":
            return json.dumps({"verdicts": [{"claim_id": c["claim_id"],
                                            "decision": "supported" if self.supported and self.relevant else "unsupported" if self.relevant else "irrelevant",
                                            "supported_source_ids": list(dict.fromkeys(q["source_id"] for q in c["citations"])),
                                            "reason": "test verdict"} for c in payload["claims"]],
                               "coverage": "full", "missing_information": []}, ensure_ascii=False)
        return json.dumps(next(self.answers), ensure_ascii=False)


def test_vietnamese_compounds_and_accents():
    tokens = vietnamese_tokens("Buộc thôi học và học bổng")
    assert "buộc_thôi_học" in tokens and "học_bổng" in tokens
    assert "va" not in tokens and "buoc" not in tokens
    bm25 = BM25(["Buộc thôi học", "Học bổng khuyến khích học tập"])
    assert bm25.scores("buộc thôi học")[0] > bm25.scores("buộc thôi học")[1]
    assert (bm25.scores("khôngcótừnày") == 0).all()


def test_rrf_uses_ranks_and_does_not_double_count_duplicates():
    fused = reciprocal_rank_fusion([[2, 1, 1], [1, 2]])
    assert fused[1] == pytest.approx(fused[2])
    assert fused[1] == pytest.approx(1 / 61 + 1 / 62)


def test_query_variants_retain_constraints_and_original():
    question = "Năm 2024, cao đẳng vừa làm vừa học bị đuổi học sau 2 lần cảnh báo không?"
    plan = plan_query(question)
    assert plan.queries[0] == question
    assert any("buộc thôi học" in query for query in plan.queries)
    assert plan.constraints["levels"] == ["college"]
    assert plan.constraints["modes"] == ["part_time"]
    for query in plan.queries[1:]:
        assert all(term in query for term in ("2024", "cao đẳng", "vừa làm vừa học", "2"))
    assert len(plan.queries) <= 4


def test_llm_rewrite_is_optional_and_never_replaces_original():
    def rewriter(*args, **kwargs):
        return json.dumps({"normalized": "Sai ý nghĩa", "intent": "compare", "queries": ["xử lý học vụ"],
                           "subquestions": ["cảnh báo", "thôi học"]})

    plan = plan_query("Đại học chính quy bị đuổi học khi nào?", llm=rewriter)
    assert plan.original == plan.queries[0]
    assert "Sai ý nghĩa" not in plan.queries
    assert plan.complex


def test_rewriting_fallback_on_invalid_json():
    plan = plan_query("Học phần tiên quyết là gì?", llm=lambda *a, **k: "invalid")
    assert plan.queries and plan.warnings


def test_real_regulation_scope_and_cross_page_inheritance(metadata):
    key = "so_tay_sinh_vien_k50-p"
    assert metadata[key + "008-c006"]["levels"] == ["university"]
    assert metadata[key + "032-c006"]["levels"] == ["college"]
    assert metadata[key + "022-c003"]["article"] == "12"
    assert metadata[key + "022-c003"]["modes"] == ["regular"]
    assert metadata[key + "022-c014"]["modes"] == ["part_time"]
    assert metadata[key + "099-c008"]["levels"] == ["college"]
    assert metadata[key + "178-c004"]["article"] == ""
    assert metadata[key + "178-c004"]["modes"] == []
    assert metadata[key + "021-c003"]["table_risk"]


def test_scope_filter_does_not_confuse_college_and_university(metadata):
    constraints = plan_query("Sinh viên đại học chính quy bị buộc thôi học khi nào?").constraints
    assert scope_matches(metadata["so_tay_sinh_vien_k50-p022-c003"], constraints)
    assert not scope_matches(metadata["so_tay_sinh_vien_k50-p047-c003"], constraints)
    assert not scope_matches(metadata["so_tay_sinh_vien_k50-p022-c014"], constraints)


def test_dedup_keeps_identical_text_for_different_academic_levels(credit_chunk):
    other = {**credit_chunk, "chunk_id": "other", "metadata": {**credit_chunk["metadata"], "levels": ["college"]}}
    assert len(deduplicate([credit_chunk, credit_chunk, other])) == 2


def test_exact_quote_located_and_paraphrase_rejected(credit_chunk):
    quote = "15 giờ học lý thuyết và 30 giờ tự học, chuẩn bị cá nhân có hướng dẫn"
    located = locate_quote(quote.replace(" và ", "\n và "), credit_chunk["text"])
    assert located["quote"] == quote
    assert credit_chunk["text"][located["start"]:located["end"]] == quote
    assert locate_quote("16 giờ học lý thuyết và 30 giờ tự học", credit_chunk["text"]) is None
    assert locate_quote("15", credit_chunk["text"]) is None


def test_citation_id_alone_cannot_validate_claim(credit_chunk):
    claim = Claim(text="Một tín chỉ có 999 giờ lý thuyết.", citations=[EvidenceQuote(source_id="S1", quote=credit_chunk["text"])])
    _, errors = validate_evidence(claim, {"S1": credit_chunk}, {})
    assert any("số liệu" in error for error in errors)


def test_repeated_question_is_never_accepted_as_answer(credit_chunk):
    reply = draft("Một tín chỉ có bao nhiêu giờ?", credit_chunk["text"])
    result = AnswerGenerator(ScriptedLLM([reply] * 2)).generate("Một tín chỉ có bao nhiêu giờ?", [credit_chunk])
    assert not result.claims and result.status == "insufficient"


def test_clause_number_does_not_support_numeric_fact(real_index):
    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p022-c007")
    claim = Claim(text="Sinh viên bị buộc thôi học sau 4 lần cảnh báo.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {})
    assert any("số liệu" in error for error in errors)


def test_specific_audience_cannot_be_generalized(real_index):
    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p072-c004")
    claim = Claim(text="Sinh viên cần đăng ký từ 6 tín chỉ để được xét học bổng.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {})
    assert any("năm cuối" in error for error in errors)


def test_claim_of_missing_information_cannot_cite_positive_rule(credit_chunk):
    reply = draft("Không có thông tin về số giờ của một tín chỉ trong tài liệu.", credit_chunk["text"])
    result = AnswerGenerator(ScriptedLLM([reply] * 2)).generate("Tín chỉ có bao nhiêu giờ?", [credit_chunk])
    assert not result.claims and not result.sources


def test_same_number_does_not_allow_changing_metric(real_index):
    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p021-c013")
    claim = Claim(text="Điểm trung bình học kỳ dưới 1,4 đối với sinh viên năm thứ hai.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {}, question="Ngưỡng điểm trung bình học kỳ?")
    assert any("loại chỉ số" in error for error in errors)


def test_permission_does_not_prove_obligation(real_index, metadata):
    identifier = "so_tay_sinh_vien_k50-p009-c005"
    source = {**next(c for c in real_index.chunks if c["chunk_id"] == identifier), "metadata": metadata[identifier]}
    claim = Claim(text="Sinh viên hệ chính quy cần tự chọn học phần trong nhóm khoa xác định trước.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {})
    assert any("quyền lựa chọn" in error for error in errors)


def test_withdrawing_does_not_prove_temporary_leave(real_index):
    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p026-c007")
    claim = Claim(text="Sinh viên nghỉ học tạm thời được bảo lưu kết quả học tập đã tích lũy.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {}, question="Bảo lưu vì việc riêng có tính vào thời gian học không?")
    assert any("loại thủ tục" in error for error in errors)


def test_irrelevant_numeric_citation_is_dropped(real_index, metadata):
    identifiers = ["so_tay_sinh_vien_k50-p022-c003", "so_tay_sinh_vien_k50-p022-c004"]
    sources = [{**next(c for c in real_index.chunks if c["chunk_id"] == identifier), "metadata": metadata[identifier]}
               for identifier in identifiers]
    reply = draft("Sinh viên bị buộc thôi học nếu bị cảnh báo học tập đến lần thứ tư tính từ đầu khóa.", sources[1]["text"], source_id="S2")
    reply["claims"][0]["citations"].append({"source_id": "S1", "quote": sources[0]["text"]})
    result = AnswerGenerator(ScriptedLLM([reply] * 2)).generate("Cảnh báo mấy lần thì bị buộc thôi học?", sources)
    assert len(result.sources) == 1 and result.sources[0]["chunk_id"] == identifiers[1]
    assert result.status == "partial"


def test_source_pruning_rechecks_all_support_constraints(real_index, metadata):
    identifiers = ["so_tay_sinh_vien_k50-p021-c012", "so_tay_sinh_vien_k50-p022-c003"]
    sources = [{**next(c for c in real_index.chunks if c["chunk_id"] == identifier), "metadata": metadata[identifier]}
               for identifier in identifiers]
    reply = draft("Sinh viên bị buộc thôi học nếu điểm trung bình học kỳ đạt dưới 0,8.", sources[0]["text"])
    reply["claims"][0]["citations"].append({"source_id": "S2", "quote": sources[1]["text"]})
    result = AnswerGenerator(ScriptedLLM([reply] * 2)).generate("Điểm trung bình học kỳ thấp có bị buộc thôi học không?", sources)
    assert not result.claims and not result.sources


def test_notification_title_keeps_disability_scope(real_index, metadata):
    identifier = "so_tay_sinh_vien_k50-p160-c006"
    source = {**next(c for c in real_index.chunks if c["chunk_id"] == identifier), "metadata": metadata[identifier]}
    assert "khuyết tật" in source["metadata"]["regulation"]
    claim = Claim(text="Học bổng khuyến khích học tập được cấp không quá 10 tháng mỗi năm học.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {}, question="Học bổng khuyến khích được cấp bao lâu?")
    assert any("khuyết tật" in error for error in errors)


def test_institutional_duties_are_not_student_obligations(real_index, metadata):
    source = next({**c, "metadata": metadata[c["chunk_id"]]} for c in real_index.chunks
                  if "tư vấn, tổ chức cho sinh viên" in c["text"].casefold())
    claim = Claim(text="Sinh viên có nghĩa vụ tư vấn, tổ chức cho sinh viên thực hiện Luật Bảo hiểm y tế.",
                  citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {}, question="Sinh viên có nghĩa vụ gì?")
    assert any("nghĩa vụ sinh viên" in error for error in errors)


def test_alternative_poverty_categories_do_not_require_both(real_index, metadata):
    identifier = "so_tay_sinh_vien_k50-p160-c006"
    source = {**next(c for c in real_index.chunks if c["chunk_id"] == identifier), "metadata": metadata[identifier]}
    claim = Claim(text="Sinh viên khuyết tật thuộc hộ nghèo được hưởng hỗ trợ không quá 10 tháng mỗi năm học.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {}, question="Sinh viên khuyết tật thuộc hộ nghèo được hỗ trợ trong bao lâu?")
    assert not errors


def test_from_semester_is_not_misread_as_ordinal_four(real_index):
    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p015-c011")
    claim = Claim(text="Học kỳ thứ hai của khóa học.", citations=[EvidenceQuote(source_id="S1", quote=source["text"])])
    _, errors = validate_evidence(claim, {"S1": source}, {}, question="Từ học kỳ nào sinh viên tự đăng ký?")
    assert not errors


def test_substring_that_drops_negation_still_requires_entailment(real_index):
    from src.text_utils import audience_qualifiers

    source = next(c for c in real_index.chunks if "không được" in c["text"]
                  and len(c["text"].split("không ", 1)[1].split()) > 15 and not audience_qualifiers(c["text"]))
    # Negative test derived from actual source, without changing its quotation.
    text = source["text"].split("không ", 1)[1]
    reply = draft(text, source["text"])
    checks = []
    def checker(*args):
        checks.append(args)
        return {"supported": False, "scores": {"contradiction": 0.99}}
    result = AnswerGenerator(ScriptedLLM([reply] * 2), entailment=checker).generate("Giải thích quy định này.", [source])
    assert checks and not result.claims


def test_short_answer_expansion_rechecks_requested_metric(real_index):
    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p021-c013")
    reply = draft("1,4", source["text"])
    result = AnswerGenerator(ScriptedLLM([reply] * 2)).generate("Điểm trung bình học kỳ là bao nhiêu?", [source])
    assert not result.claims


def test_sibling_conditions_trigger_partial_coverage(real_index, metadata):
    identifiers = ["so_tay_sinh_vien_k50-p022-c003", "so_tay_sinh_vien_k50-p022-c004"]
    sources = [{**next(c for c in real_index.chunks if c["chunk_id"] == identifier), "metadata": metadata[identifier]}
               for identifier in identifiers]
    gaps = coverage_gaps("Đại học chính quy bị cảnh báo mấy lần thì buộc thôi học?",
                         [{"text": sources[1]["text"], "citations": [{"source_id": "S2"}]}], {"S1": sources[0], "S2": sources[1]})
    assert any(sources[0]["text"] in gap for gap in gaps)


def test_nli_can_veto_chat_verifier(credit_chunk):
    reply = draft("Một tín chỉ lý thuyết gồm 15 giờ trên lớp và 30 giờ tự học có hướng dẫn.", credit_chunk["text"])
    checker = lambda *a: {"supported": False, "scores": {"neutral": 0.9}}
    result = AnswerGenerator(ScriptedLLM([reply] * 2), entailment=checker).generate("Tín chỉ lý thuyết được tính ra sao?", [credit_chunk])
    assert not result.claims


@pytest.mark.real_model
def test_local_nli_checks_negation_with_real_source(real_index, metadata):
    from src.entailment import evidence_premise, get_entailment

    source = next(c for c in real_index.chunks if c["chunk_id"] == "so_tay_sinh_vien_k50-p009-c007")
    nli = get_entailment()
    positive = "Sinh viên phải tích lũy học phần tiên quyết trước khi học các học phần khác có liên quan."
    negative = "Sinh viên không cần tích lũy học phần tiên quyết trước khi học các học phần khác có liên quan."
    assert nli.check(source["text"], positive)["supported"]
    assert not nli.check(source["text"], negative)["supported"]
    premise = evidence_premise(source["text"], metadata[source["chunk_id"]])
    assert nli.check(premise, "Sinh viên đại học phải tích lũy học phần tiên quyết trước khi học các học phần khác có liên quan.")["supported"]


def test_missing_source_ids_get_one_repair_without_invented_sources(credit_chunk):
    valid = draft("Một tín chỉ lý thuyết gồm 15 giờ trên lớp và 30 giờ tự học có hướng dẫn.", credit_chunk["text"])
    llm = ScriptedLLM([{"answer": "15 giờ", "source_ids": []}, valid])
    result = AnswerGenerator(llm).generate("Một tín chỉ lý thuyết có bao nhiêu giờ?", [credit_chunk])
    assert result.status == "complete"
    assert llm.calls == ["answer", "answer_repair", "verify"]
    assert result.sources[0]["page"] == 8
    assert result.claims[0]["citations"][0]["source_id"] == credit_chunk["chunk_id"]


def test_two_missing_citation_responses_remain_insufficient(credit_chunk):
    llm = ScriptedLLM([{"answer": "15 giờ", "source_ids": []}] * 2)
    result = AnswerGenerator(llm).generate("Một tín chỉ có bao nhiêu giờ?", [credit_chunk])
    assert result.status == "insufficient" and not result.sources
    assert llm.calls == ["answer", "answer_repair"]


@pytest.mark.parametrize("supported,relevant", [(False, True), (True, False)])
def test_semantic_support_and_relevance_required(credit_chunk, supported, relevant):
    reply = draft("Một tín chỉ lý thuyết có 15 giờ học.", credit_chunk["text"])
    llm = ScriptedLLM([reply] * 2, supported=supported, relevant=relevant)
    result = AnswerGenerator(llm).generate("Câu hỏi cần được chứng minh", [credit_chunk])
    assert result.status == "insufficient" and not result.sources
    assert llm.calls.count("answer_repair") == 1


def test_unsupported_claim_removed_but_supported_part_preserved(credit_chunk):
    reply = draft("Một tín chỉ lý thuyết có 15 giờ học.", credit_chunk["text"])
    reply["claims"].append({"text": "Học phí là 999 đồng.", "citations": [{"source_id": "S1", "quote": credit_chunk["text"]}]})
    llm = ScriptedLLM([reply] * 2)
    result = AnswerGenerator(llm).generate("Tín chỉ và học phí là bao nhiêu?", [credit_chunk])
    assert result.status == "partial" and len(result.claims) == 1
    assert "999" not in result.answer and result.missing_information


def test_invalid_ids_never_bound_to_nearest_source(credit_chunk):
    reply = draft("Một tín chỉ có 15 giờ học.", credit_chunk["text"], source_id="S99")
    result = AnswerGenerator(ScriptedLLM([reply] * 2)).generate("Tín chỉ?", [credit_chunk])
    assert not result.sources and result.status == "insufficient"


def test_benchmark_integrity_and_evidence_group_scoring(real_index):
    rows = json.loads((BENCHMARK_DIR / "dev.json").read_text())
    validate_dataset(rows, real_index, BENCHMARK_DIR)
    question = next(row for row in rows if row["id"] == "D09")
    results = [c for c in real_index.chunks if c["chunk_id"] == question["evidence"][0]["gold_chunk_ids"][0]]
    assert retrieval_metrics(question, results)["recall_at_5"] == 0.5
    results[0] = {**results[0], "text": "Không chứa bằng chứng"}
    assert retrieval_metrics(question, results)["recall_at_5"] == 0


def test_quality_metrics_are_not_fabricated_for_unreviewed_answers():
    report = {"systems": ["hybrid"], "results": [{"id": "Q", "system": "hybrid", "answerability": "full",
              "retrieval_metrics": {"recall_at_5": 1, "recall_at_10": 1, "mrr_at_10": 1},
              "context_evidence_recall": 1, "elapsed_seconds": 1, "python_peak_rss_mib": 1}]}
    summary = summarize(report)["hybrid"]
    assert summary["correct_complete_rate"] is None
    assert summary["wrong_citation_rate"] is None
    assert summary["correct_refusal_rate"] is None


@pytest.mark.real_model
def test_advanced_retrieval_caps_rounds_preserves_scope_and_budget():
    pipeline = RAGPipeline(settings=RAGSettings())
    result = pipeline.retrieve("Đại học chính quy bị cảnh báo mấy lần thì bị đuổi học?")
    assert any(c["chunk_id"] == "so_tay_sinh_vien_k50-p022-c003" for c in result.contexts)
    assert result.plan.complex and len(result.contexts) <= 8
    assert sum(c["estimated_tokens"] for c in result.contexts) <= 2200
    assert all(scope_matches(c["metadata"], result.plan.constraints) for c in result.contexts)
    second = pipeline.retriever.search_more(result, ["điều kiện buộc thôi học"])
    third = pipeline.retriever.search_more(second, ["thử lần nữa"])
    assert len(second.rounds) == 2 and third is second
    assert all(len(q[method]) <= 20 for r in second.rounds for q in r["queries"] for method in ("dense", "bm25"))


def test_settings_reject_unbounded_retrieval():
    with pytest.raises(ValueError):
        replace(RAGSettings(), max_rounds=3)
    with pytest.raises(ValueError):
        replace(RAGSettings(), complex_contexts=9)
