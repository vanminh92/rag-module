"""Question-derived checks: requested attributes, never document facts or answers.

The checklist is independent of the generated draft. It is a lower bound on
coverage, not a guarantee that a general-language question has been understood.
The semantic verifier also checks the original question and all conditions.
"""

import re
from dataclasses import dataclass

from .text_utils import folded


@dataclass(frozen=True)
class Requirement:
    key: str
    label: str
    query: str
    answer_pattern: str = ""
    unavailable: bool = False

    def matches(self, text: str) -> bool:
        return not self.unavailable and (not self.answer_pattern or bool(re.search(self.answer_pattern, folded(text))))

    def to_dict(self):
        return {"id": self.key, "requirement": self.label, "search_query": self.query,
                "document_cannot_establish": self.unavailable}


NUMBER = r"(?:\d+(?:[,.]\d+)?|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"


def question_requirements(question: str) -> list[Requirement]:
    text = folded(question)
    requirements = []
    # Keep the subject on short attribute searches, without importing an answer.
    topics = [term for term in ("học bổng", "khuyến khích", "sư phạm", "sinh hoạt", "nghiên cứu khoa học",
                               "ký túc xá", "thư viện", "công nghệ thông tin", "rèn luyện", "cảnh báo", "buộc thôi học", "đại học", "cao đẳng", "chương trình thứ hai")
              if folded(term) in text]
    topic = " ".join(topics)
    if re.search(r"\bcntt\b", text):
        topic += " công nghệ thông tin"

    def add(key, label, pattern="", *, unavailable=False):
        requirements.append(Requirement(key, label, (topic + " " + label).strip(), pattern, unavailable))

    # These are attribute/intent names. No thresholds, source IDs or pages.
    rules = [
        ("credits", r"(?:so tin chi|bao nhieu tin chi|tin chi.*(?:dieu kien|can ra sao)|dieu kien.*tin chi)",
         "Số tín chỉ và các điều kiện tính tín chỉ", r"(?=[^\n]*(?:tich luy|dang ky|toi thieu|it nhat|tong so tin chi))[^\n]*" + NUMBER + r"\s+tin chi"),
        ("times", r"(?:may lan|bao nhieu lan|so lan)", "Số lần và các trường hợp áp dụng", r"(?:" + NUMBER + r"\s+lan|lan thu\s+" + NUMBER + r")"),
        ("months", r"(?:(?:so|may|bao nhieu|toi da)\s+thang|cap.*(?:bao lau|trong nam)|thoi gian.*(?:ho tro|sinh hoat))",
         "Thời gian cấp, số tháng trong năm học", NUMBER + r"\s+thang"),
        ("money", r"(?:(?:muc|tien|ho tro|sinh hoat).*bao nhieu(?:\s+(?:tien|dong|moi thang)|\s*[?.,;]?$)|muc ho tro|muc tien|bao nhieu moi thang|hoc phi.*bao nhieu|bao nhieu dong)",
         "Mức tiền hỗ trợ mỗi tháng", r"(?:\d[\d,.]*\s*(?:trieu\s*)?dong|\d[\d,.]*\s*trieu)"),
        ("email", r"(?:email|e-mail|hop thu|\bmail\b)", "Địa chỉ email được hỏi", r"[\w.+-]+@[\w.-]+\.[a-z]{2,}"),
        ("website", r"(?:website|trang web)", "Địa chỉ website được hỏi", r"(?:https?://[^\s]+|(?<![\w.@-])(?:www\.)?[\w-]+(?:\.[\w-]+)*\.(?:edu|com|org|vn)\b)"),
        ("discipline", r"(?:ky luat|no ky luat)", "Điều kiện kỷ luật", r"(?:ky luat|khien trach)"),
        ("conduct", r"(?:diem ren luyen|dieu kien.*ren luyen|hoc tap,? ren luyen)",
         "Điều kiện và kết quả rèn luyện", r"ren luyen"),
        ("academic", r"(?:diem hoc[, ]|dieu kien hoc tap|hoc tap,? ren luyen)",
         "Điều kiện và kết quả học tập", r"(?:(?:ket qua|diem) hoc tap|diem trung binh)"),
    ]
    for key, requested, label, pattern in rules:
        if re.search(requested, text):
            add(key, label, pattern)
    if "som nhat" in text:
        add("earliest", "Thời điểm sớm nhất được bắt đầu",
            r"(?:nam thu|hoc ky thu|tu nam|tu hoc ky|hoan thanh (?:hoc ky|nam)|\d{1,2}/\d{1,2}|" + NUMBER + r"\s+(?:ngay|thang))")
    if "ngoai ngu" in text and re.search(r"(?:ra truong|tot nghiep|dau ra)", text):
        add("language_exit", "Chuẩn đầu ra ngoại ngữ tối thiểu để xét tốt nghiệp",
            r"(?:bac\s+" + NUMBER + r"\s*/\s*" + NUMBER + r"|(?:ielts|toeic|toefl)\s+" + NUMBER + r"|trinh do\s+[abc][12])")
    if re.search(r"(?:dang ky|xep lich|thoi khoa bieu)", text):
        if re.search(r"hoc ky (?:dau|thu nhat)", text):
            add("registration_first", "Đăng ký, xếp lịch học kỳ đầu", r"hoc ky (?:dau|thu nhat|1)")
        if re.search(r"(?:tu (?:hoc )?ky|cac hoc ky sau)", text):
            add("registration_later", "Đăng ký các học kỳ tiếp theo", r"(?:tu hoc ky|hoc ky (?:thu hai|2)|hoc ky tiep theo)")

    # Personal secrets and current account/payment/availability state are not
    # established by a static handbook. Keep known public subquestions answerable.
    if "mat khau" in text and not re.search(r"(?:doi|dat lai|khoi phuc|quen|cap lai|lay lai).*mat khau", text):
        add("personal_password", "Mật khẩu cá nhân: sổ tay không cung cấp thông tin này", unavailable=True)
        # Asking for an email password is not asking for a public email address.
        requirements = [r for r in requirements if r.key != "email" or re.search(r"(?:email.*(?:va|;) |(?:va|;).*mat khau)", text)]
    if (re.search(r"(?:ca nhan toi|cua (?:toi|minh|em)).*(?:chuyen|nhan|tra|thanh toan)", text)
            or re.search(r"(?:tien|khoan ho tro).*(?:da chuyen chua|da nhan chua|vao tai khoan chua)", text)):
        add("personal_payment", "Tình trạng chuyển tiền cá nhân tại thời điểm được hỏi", unavailable=True)
    if re.search(r"(?:hien (?:tai|con)|hom nay|bay gio|con trong).*(?:cho|giuong|phong)|(?:cho|giuong|phong).*(?:hien tai|hom nay|con trong)", text):
        add("live_availability", "Số chỗ trống hiện tại: cần dữ liệu cập nhật ngoài sổ tay", unavailable=True)

    # Preserve the whole question for semantic checks, including arbitrary
    # topics and qualifiers beyond the explicitly recognized attribute checks.
    return [Requirement("main", question, question), *requirements]


def requirement_gaps(requirements: list[Requirement], claims: list[dict]) -> list[str]:
    answer = " ".join(c["text"] for c in claims)
    return ["Chưa trả lời đầy đủ: " + r.label for r in requirements if not r.matches(answer)]


def requested_public_years(question: str) -> set[str]:
    """A year on a private-status subquestion must not invalidate a public fact."""
    years = set()
    for part in re.split(r"(?i)\bvà\b|\bđồng thời\b|;", question):
        if not any(r.unavailable for r in question_requirements(part)):
            years.update(re.findall(r"\b(?:19|20)\d{2}\b", part))
    return years
