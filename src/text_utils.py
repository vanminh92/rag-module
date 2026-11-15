"""Vietnamese syllables plus overlapping compounds, without a remote tokenizer.

Vietnamese spaces separate syllables, not necessarily words. Keeping syllables
and 2/3-syllable n-grams lets BM25 match compounds without a domain dictionary.
Accents are retained for scoring. Accent folding is used only for intent/aliases.
"""

import re
import unicodedata


def canonical(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def folded(text: str) -> str:
    value = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return "".join(char for char in value if not unicodedata.combining(char))


STOPWORDS = set("và là của các có được cho trong với những một người khi thì từ đến theo về hay hoặc nào bao nhiêu không phải bị tôi em mình cần muốn hỏi hãy biết tại sao thế nào này đó để cũng sẽ đã đang quá".split())


def syllables(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", canonical(text).casefold(), re.UNICODE)


def content_terms(text: str) -> set[str]:
    return {token for token in syllables(text) if token not in STOPWORDS}


def vietnamese_tokens(text: str) -> list[str]:
    words = syllables(text)
    tokens = [word for word in words if word not in STOPWORDS]
    for size in (2, 3):
        tokens.extend("_".join(words[i:i + size]) for i in range(len(words) - size + 1)
                      if all(w not in STOPWORDS for w in words[i:i + size]))
    return tokens


def audience_qualifiers(text: str) -> list[str]:
    value = folded(text)
    qualifiers = ["năm cuối", "khuyết tật", "hộ nghèo", "hộ cận nghèo", "dân tộc thiểu số"]
    found = [term for term in qualifiers if folded(term) in value]
    if "sinh vien su pham" in value:
        found.append("sư phạm")
    return found


def metric_concepts(text: str) -> set[str]:
    """Formal metric names, not answers: distinguish nearby numeric attributes.

    Both a chat verifier and a general NLI model can conflate these near-synonyms.
    No thresholds, regulations, questions or source IDs are encoded here.
    """
    value = folded(text)
    prefix = r"\bdiem\s+(?:trung binh\s+(?:chung\s+)?)?"
    patterns = {"semester_average": prefix + r"hoc ky\b", "cumulative_average": prefix + r"tich luy\b",
                "year_average": prefix + r"nam hoc\b", "conduct": r"\bdiem ren luyen\b",
                "scholarship": r"\bdiem hoc bong\b", "course": r"\bdiem hoc phan\b"}
    return {name for name, pattern in patterns.items() if re.search(pattern, value)}


def education_actions(text: str, *, colloquial=False) -> set[str]:
    """Terminology only: pausing, withdrawing and expulsion are different acts."""
    value = folded(text)
    actions = set()
    if re.search(r"\b(?:nghi hoc tam thoi|tam nghi hoc)\b", value):
        actions.add("temporary_leave")
    if re.search(r"\b(?:xin thoi hoc|duoc thoi hoc|thoi hoc vi ly do ca nhan)\b", value):
        actions.add("withdrawal")
    if re.search(r"\b(?:buoc thoi hoc|bi duoi hoc)\b", value):
        actions.add("expulsion")
    if (colloquial and not actions and "bao luu" in value
            and not any(term in value for term in ("ket qua", "tin chi", "thoi hoc"))):
        actions.add("temporary_leave")
    return actions
