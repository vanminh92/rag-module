"""Completeness failures must survive an overconfident LLM verifier."""

import json

import pytest

from src import config
from src.answer_requirements import question_requirements, requirement_gaps
from src.answering import AnswerGenerator
from src.document_structure import load_structure
from src.retriever import Retriever


@pytest.fixture(scope="module")
def chunks():
    index = Retriever(config.INDEX_DIR)
    metadata = load_structure(index)
    return {c["chunk_id"]: {**c, "metadata": metadata[c["chunk_id"]]} for c in index.chunks}


def chunk(chunks, suffix):
    return chunks["so_tay_sinh_vien_k50-p" + suffix]


class OverconfidentLLM:
    """Deliberately says complete even when the source selection is incomplete."""
    def __init__(self, selected, *, missing=None, omit_audit=False):
        self.selected, self.missing, self.omit_audit = selected, missing or [], omit_audit
        self.calls = []

    def __call__(self, task, system, payload, schema, **kwargs):
        self.calls.append(task)
        if task != "verify":
            return json.dumps({"selected_source_ids": self.selected, "missing_information": self.missing})
        ids = [c["claim_id"] for c in payload["claims"]]
        result = {"verdicts": [{"claim_id": c["claim_id"], "decision": "supported",
                                "supported_source_ids": [q["source_id"] for q in c["citations"]],
                                "reason": "Overconfident test double"} for c in payload["claims"]],
                  "coverage": "full", "missing_information": [],
                  "requirements": [{"requirement_id": r["id"], "covered": True, "claim_ids": ids,
                                    "reason": "Overconfident test double"} for r in payload["question_analysis"]["requirements"]]}
        if self.omit_audit:
            result.pop("requirements")
        return json.dumps(result)


def test_money_per_month_cannot_satisfy_duration(chunks):
    question = "Sinh viên sư phạm được hỗ trợ sinh hoạt bao nhiêu mỗi tháng và tối đa mấy tháng mỗi năm học?"
    amount = chunk(chunks, "144-c006")
    gaps = requirement_gaps(question_requirements(question), [{"text": amount["text"]}])
    assert any("số tháng" in gap for gap in gaps)
    llm = OverconfidentLLM(["S1"])
    result = AnswerGenerator(llm).generate(question, [amount])
    assert result.status == "partial" and "3,63" in result.answer
    assert any("số tháng" in gap for gap in result.missing_information)
    assert llm.calls.count("answer_repair") == 1


def test_both_requested_attributes_are_complete_with_actual_evidence(chunks):
    sources = [chunk(chunks, "144-c006"), chunk(chunks, "144-c007")]
    result = AnswerGenerator(OverconfidentLLM(["S1", "S2"])).generate(
        "Sinh viên sư phạm được hỗ trợ sinh hoạt bao nhiêu mỗi tháng và tối đa mấy tháng mỗi năm học?", sources)
    assert result.status == "complete" and not result.missing_information
    assert "3,63" in result.answer and "10 tháng" in result.answer
    for claim in result.claims:
        for citation in claim["citations"]:
            source = next(s for s in sources if s["chunk_id"] == citation["source_id"])
            assert source["text"][citation["start"]:citation["end"]] == citation["quote"]


def test_personal_payment_is_not_silently_omitted(chunks):
    result = AnswerGenerator(OverconfidentLLM(["S1"])).generate(
        "Mức hỗ trợ sinh hoạt mỗi tháng là bao nhiêu và tiền của cá nhân tôi tháng 11/2026 đã chuyển chưa?",
        [chunk(chunks, "144-c006")])
    assert result.status == "partial"
    assert any("chuyển tiền cá nhân" in gap for gap in result.missing_information)
    assert "đã chuyển" not in result.answer


def test_password_question_is_not_a_request_for_public_email():
    requirements = question_requirements("Cho tôi mật khẩu email sinh viên của bạn Nguyễn Văn An.")
    assert any(r.key == "personal_password" and r.unavailable for r in requirements)
    assert not any(r.key == "email" for r in requirements)


def test_credit_fee_formula_does_not_satisfy_credit_eligibility(chunks):
    requirement = next(r for r in question_requirements("Điều kiện số tín chỉ để xét học bổng?") if r.key == "credits")
    assert not requirement.matches(chunk(chunks, "073-c003")["text"])
    assert requirement.matches(chunk(chunks, "072-c003")["text"])


def test_article_numbers_cannot_satisfy_warning_count(chunks):
    requirement = next(r for r in question_requirements("Đại học chính quy bị cảnh báo mấy lần thì buộc thôi học?") if r.key == "times")
    assert not requirement.matches(chunk(chunks, "022-c007")["text"])
    assert requirement.matches(chunk(chunks, "022-c003")["text"])


def test_duplicate_selected_source_is_rendered_once(chunks):
    source = chunk(chunks, "178-c004")
    result = AnswerGenerator(OverconfidentLLM(["S1", "S1"])).generate("Email và website thư viện là gì?", [source])
    assert result.status == "complete" and len(result.claims) == 1 and len(result.sources) == 1


def test_invalid_selection_never_invents_source(chunks):
    result = AnswerGenerator(OverconfidentLLM(["S99"])).generate("Email thư viện?", [chunk(chunks, "178-c004")])
    assert result.status == "insufficient" and not result.sources


def test_verifier_cannot_erase_missing_information(chunks):
    result = AnswerGenerator(OverconfidentLLM(["S1"], missing=["Trạng thái riêng chưa được xác minh"])).generate(
        "Email thư viện?", [chunk(chunks, "178-c004")])
    assert result.status == "partial"
    assert "Trạng thái riêng chưa được xác minh" in result.missing_information


def test_verifier_must_audit_every_requirement(chunks):
    result = AnswerGenerator(OverconfidentLLM(["S1"], omit_audit=True)).generate("Email thư viện?", [chunk(chunks, "178-c004")])
    assert result.status == "insufficient" and not result.claims


def test_already_quoted_answer_is_not_reported_as_missing(chunks):
    source = chunk(chunks, "021-c012")
    result = AnswerGenerator(OverconfidentLLM(["S1"], missing=[source["text"]])).generate(
        "Ngưỡng điểm trung bình học kỳ cảnh báo học tập là bao nhiêu?", [source])
    assert result.status == "complete" and not result.missing_information


def test_second_program_answer_must_include_earliest_milestone(chunks):
    question = "Sinh viên đại học sớm nhất được đăng ký chương trình thứ hai khi nào?"
    result = AnswerGenerator(OverconfidentLLM(["S1"])).generate(question, [chunk(chunks, "028-c004")])
    assert result.status == "partial"
    assert any("sớm nhất" in gap for gap in result.missing_information)


def test_retrieved_missing_attribute_is_independently_verified(chunks):
    sources = [chunk(chunks, "144-c006"), {**chunk(chunks, "144-c007"), "selection_reason": "requested_attribute:months"}]
    llm = OverconfidentLLM(["S1"])
    result = AnswerGenerator(llm).generate(
        "Sinh viên sư phạm được hỗ trợ sinh hoạt bao nhiêu mỗi tháng và tối đa mấy tháng mỗi năm học?", sources)
    assert result.status == "complete" and "10 tháng" in result.answer
    assert result.debug["generation_attempts"][0]["attribute_sources_sent_for_verification"] == [sources[1]["chunk_id"]]
    assert llm.calls == ["answer", "verify"]


def test_attribute_retrieval_cannot_bypass_relevance_verification(chunks):
    from tests.test_open_domain import ScriptedLLM

    source = {**chunk(chunks, "144-c007"), "selection_reason": "requested_attribute:months"}
    # A schema-valid selection is still rejected when the semantic verifier
    # cannot establish relevance, including automatically offered evidence.
    class RejectingLLM(ScriptedLLM):
        def __call__(self, task, *args, **kwargs):
            if task != "verify":
                self.calls.append(task)
                return json.dumps({"selected_source_ids": [], "missing_information": []})
            return super().__call__(task, *args, **kwargs)
    result = AnswerGenerator(RejectingLLM([], relevant=False)).generate("Tối đa mấy tháng trong năm học?", [source])
    assert not result.claims and result.status == "insufficient"


def test_known_address_is_retained_when_live_capacity_is_unavailable(chunks):
    llm = OverconfidentLLM(["S1"])
    result = AnswerGenerator(llm).generate(
        "Địa chỉ văn phòng Ký túc xá ở đâu và hôm nay còn bao nhiêu giường trống?", [chunk(chunks, "180-c002")])
    assert result.status == "partial" and "351A" in result.answer
    assert any("chỗ trống" in gap for gap in result.missing_information)
    assert llm.calls


def test_pure_password_question_does_not_return_public_contacts(chunks):
    llm = OverconfidentLLM(["S1"])
    result = AnswerGenerator(llm).generate("Mật khẩu email của bạn Nguyễn Văn An là gì?", [chunk(chunks, "181-c004")])
    assert result.status == "insufficient" and not result.claims and not llm.calls


def test_milestone_paragraph_ending_in_colon_is_not_mistaken_for_heading(chunks):
    from src.answering import quote_options

    source = {**chunk(chunks, "028-c005"), "selection_reason": "requested_attribute:earliest"}
    assert source["text"].rstrip().endswith(":") and quote_options(source["text"])
    result = AnswerGenerator(OverconfidentLLM([])).generate(
        "Sinh viên đại học sớm nhất được đăng ký chương trình thứ hai khi nào?", [source])
    assert result.status == "complete" and "năm thứ hai" in result.answer


def test_old_formula_cannot_answer_actual_tuition_in_a_new_year(chunks):
    result = AnswerGenerator(OverconfidentLLM(["S1"])).generate(
        "Học phí chính xác một tín chỉ ngành Tâm lý học năm học 2026–2027 là bao nhiêu đồng?", [chunk(chunks, "073-c003")])
    assert result.status == "insufficient" and not result.claims


def test_private_payment_year_does_not_invalidate_known_public_amount():
    from src.answer_requirements import requested_public_years

    assert requested_public_years("Học phí năm học 2026–2027 là bao nhiêu?") == {"2026", "2027"}
    assert not requested_public_years("Mức hỗ trợ là bao nhiêu và tiền của cá nhân tôi tháng 11/2026 đã chuyển chưa?")


def test_both_registration_periods_are_explicitly_required():
    reqs = {r.key for r in question_requirements("Đại học chính quy: học kỳ đầu do ai xếp lịch và từ kỳ nào sinh viên phải tự đăng ký?")}
    assert {"registration_first", "registration_later"} <= reqs


def test_page_header_is_never_a_standalone_answer(chunks):
    from src.answering import quote_options

    assert not quote_options(chunk(chunks, "016-c001")["text"])


def test_joint_program_scope_excludes_other_chinese_programs(chunks):
    from src.hybrid_retriever import annotate_program_tracks, scope_matches
    from src.query_processing import explicit_constraints

    scoped = {c["chunk_id"]: c for c in annotate_program_tracks(list(chunks.values()))}
    constraints = explicit_constraints("Chương trình song ngành 2 + 2 có cơ hội nghề nghiệp gì?")
    assert constraints["program_tracks"] == ["2+2"]
    assert scope_matches(scoped["so_tay_sinh_vien_k50-p198-c002"]["metadata"], constraints)
    assert not scope_matches(scoped["so_tay_sinh_vien_k50-p197-c004"]["metadata"], constraints)
    assert not scope_matches(scoped["so_tay_sinh_vien_k50-p197-c005"]["metadata"], constraints)
    assert not explicit_constraints("2 + 2 là bao nhiêu?")["program_tracks"]


def test_citation_does_not_cross_program_heading_inside_chunk(chunks):
    from src.hybrid_retriever import annotate_program_tracks

    scoped = {c["chunk_id"]: c for c in annotate_program_tracks(list(chunks.values()))}
    source = scoped["so_tay_sinh_vien_k50-p198-c002"]
    result = AnswerGenerator(OverconfidentLLM(["S1"])).generate(
        "Chương trình quốc tế song ngành 2+2 Ngôn ngữ Trung Quốc và Giáo dục Hán ngữ Quốc tế có cơ hội nghề nghiệp gì?", [source])
    assert result.status == "complete" and result.claims[0]["text"].startswith("CHƯƠNG TRÌNH")
    citation = result.claims[0]["citations"][0]
    assert citation["start"] > 0 and source["text"][citation["start"]:citation["end"]] == citation["quote"]


def test_standalone_program_cannot_be_used_for_joint_program(chunks):
    from src.hybrid_retriever import annotate_program_tracks

    scoped = {c["chunk_id"]: c for c in annotate_program_tracks(list(chunks.values()))}
    source = scoped["so_tay_sinh_vien_k50-p197-c004"]
    result = AnswerGenerator(OverconfidentLLM(["S1"])).generate("Chương trình song ngành 2+2 có cơ hội gì?", [source])
    assert result.status == "insufficient" and not result.claims


def test_informal_department_email_gets_formal_search_terms():
    from src.query_processing import plan_query

    question = "Trong sổ tay, muốn gửi mail cho phòng CNTT thì gửi địa chỉ nào?"
    requirements = question_requirements(question)
    assert any(r.key == "email" and "công nghệ thông tin" in r.query for r in requirements)
    assert any("công nghệ thông tin" in q for q in plan_query(question).queries)


def test_email_domain_cannot_satisfy_requested_website(chunks):
    import re

    website = next(r for r in question_requirements("Website thư viện là gì?") if r.key == "website")
    email = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", chunk(chunks, "178-c004")["text"])[0]
    assert not website.matches(email)
    assert website.matches(chunk(chunks, "178-c004")["text"])


@pytest.mark.real_model
def test_language_exit_retrieves_general_minimum_not_just_one_certificate_option():
    from src.pipeline import RAGPipeline
    from src.settings import RAGSettings

    retrieval = RAGPipeline(settings=RAGSettings()).retrieve(
        "Sinh viên đại học thuộc diện áp dụng quy định ngoại ngữ cần ngoại ngữ cỡ nào mới ra trường?")
    source = next(c for c in retrieval.contexts if c["selection_reason"] == "requested_attribute:language_exit")
    assert source["chunk_id"] == "so_tay_sinh_vien_k50-p111-c006"
    assert "tối thiểu" in source["text"] and "3/6" in source["text"]
