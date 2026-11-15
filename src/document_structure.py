"""Versioned metadata sidecar; never modifies the original chunks or E5 vectors.

Headings come from original PDF line boundaries. Inheritance is conservative:
article/clause identities include a regulation ID, so article 12 in a different
regulation is never an adjacent context. Physical page numbers remain unchanged.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .chunking import normalize_text
from .document_loader import load_document
from .text_utils import canonical, folded

STRUCTURE_VERSION = 5
EVENTS = re.compile(r"(?m)^[ \t]*(?P<heading>(?:Phần\s+[IVX\d]+|Chương\s+[IVX\d]+|"
                    r"Điều\s+\d+\.|\d+\.[ \t]+|[a-zđ]\)[ \t]+)[^\n]*)", re.IGNORECASE)


def _levels(text: str) -> list[str]:
    # The institution's name is not an academic-level constraint.
    value = folded(text).replace("truong dai hoc", "truong")
    return [key for key, term in (("university", "dai hoc"), ("college", "cao dang")) if term in value]


def _modes(text: str) -> list[str]:
    value = folded(text)
    return [key for key, term in (("regular", "chinh quy"), ("part_time", "vua lam vua hoc")) if term in value]


def annotate_structure(pages: list[dict], chunks: list[dict]) -> dict[str, dict]:
    by_page = {}
    for chunk in chunks:
        by_page.setdefault(chunk["page"], []).append(chunk)
    state = dict(document_id="section-1", regulation="", part="", chapter="", article="", article_title="",
                 clause="", clause_title="", item="", item_title="", levels=[], modes=[], document_modes=[], dates=[])
    result = {}
    for page in pages:
        number, raw = page["page"], page["text"]
        full = normalize_text(raw)
        matches = list(EVENTS.finditer(raw))
        events = []
        event_cursor = 0
        for event_number, match in enumerate(matches):
            title = canonical(match["heading"])
            position = full.find(title, event_cursor)
            if position < 0:
                continue
            event_cursor = position + len(title)
            if folded(title).startswith("dieu "):
                end = matches[event_number + 1].start() if event_number + 1 < len(matches) else len(raw)
                title = canonical(raw[match.start():end])[:250]
            events.append((position, title))
        # A new Article 1 signals a new regulation, including when numbering restarts.
        new_regulation = re.search(r"(?m)^\s*Điều\s+1\.", raw)
        if new_regulation:
            intro = canonical(raw[:new_regulation.start()])
            title_match = re.search(r"(?:QUY CHẾ|QUY ĐỊNH|NGHỊ ĐỊNH)\b(.+?)(?:\(|Chương|CHƯƠNG|$)", intro)
            inherited_title = state["regulation"] if state["document_id"].startswith("document-") and not state["article"] else ""
            title = canonical(title_match.group(0))[:350] if title_match else inherited_title or intro[-350:]
            # Use the regulation title, not the university's letterhead, to infer scope.
            state.update(document_id=f"regulation-p{number:03d}", regulation=title,
                         chapter="", article="", article_title="", clause="", clause_title="", item="", item_title="",
                         levels=_levels(title), modes=_modes(title), document_modes=_modes(title),
                         dates=re.findall(r"\b\d{1,2}\s*(?:/|tháng)\s*\d{1,2}\s*(?:/|năm)\s*\d{4}\b", intro))
        elif (marker := re.search(r"(?m)^\s*(?:THÔNG BÁO|HƯỚNG DẪN|QUY TRÌNH|QUY CHẾ|QUY ĐỊNH|NGHỊ ĐỊNH)\s*$", raw)):
            title = canonical(raw[marker.start():])[:500]
            state.update(document_id=f"document-p{number:03d}", regulation=title, chapter="", article="", article_title="",
                         clause="", clause_title="", item="", item_title="", levels=_levels(title),
                         modes=_modes(title), document_modes=_modes(title), dates=[])
        # Tables/diagrams are not reconstructed. Flag risky extraction instead of guessing cells.
        table_risk = bool(re.search(r"(?i)(?:thang điểm|khung điểm|\bTT\s|\bSTT\s|thời gian học tập chuẩn|"
                                    r"chứng chỉ/|sơ đồ|lưu đồ|danh sách các nhà bảo tàng|danh sách các di tích)", full))
        event_index = 0
        cursor = 0

        def apply_event(title):
            value = folded(title)
            if value.startswith("phan "):
                state.update(part=title, chapter="", article="", article_title="", clause="", clause_title="", item="", item_title="")
                if not new_regulation:
                    state.update(document_id=f"section-p{number:03d}", regulation="", levels=[], modes=[], document_modes=[], dates=[])
            elif value.startswith("chuong "):
                state["chapter"] = title
            elif value.startswith("dieu "):
                article = re.match(r"Điều\s+(\d+)", title, re.IGNORECASE)[1]
                state.update(article=article, article_title=title, clause="", clause_title="", item="", item_title="",
                             modes=_modes(title) or state["document_modes"])
            elif re.match(r"\d+\.", title):
                state.update(clause=re.match(r"(\d+)", title)[1], clause_title=title[:200], item="", item_title="")
                if re.search(r"(?i)đối với hình thức đào tạo", title):
                    state["modes"] = _modes(title) or state["document_modes"]
            else:
                state.update(item=title.split(")", 1)[0], item_title=title[:200])

        for chunk in by_page.get(number, []):
            start = full.find(chunk["text"], max(0, cursor - 100))
            if start < 0:
                raise ValueError(f"Không xác định được vị trí chunk {chunk['chunk_id']} trong PDF")
            cursor = start + len(chunk["text"])
            while event_index < len(events) and events[event_index][0] <= start:
                _, title = events[event_index]
                apply_event(title)
                event_index += 1
            levels = list(state["levels"])
            explicit = re.search(r"(?i)^\d*\.?\s*Sinh viên (?:trình độ )?(đại học|cao đẳng)(?: sư phạm)?\b", chunk["text"])
            if explicit:
                levels = _levels(explicit[0])
            result[chunk["chunk_id"]] = {key: value for key, value in state.items() if key != "document_modes"}
            result[chunk["chunk_id"]].update(
                levels=levels, page=number, source=chunk["source"],
                article_key=f"{state['document_id']}:a{state['article']}" if state["article"] else "",
                table_risk=table_risk,
                extraction_warnings=["Văn bản bảng/sơ đồ được trích xuất tuyến tính; chưa xác minh quan hệ hàng/cột."] if table_risk else [],
            )
        # Part/chapter headings may be inside a final chunk rather than at its
        # start. Still inherit them on the next physical page.
        for _, title in events[event_index:]:
            apply_event(title)
    return result


def load_structure(index) -> dict[str, dict]:
    """Validate the sidecar against chunk/source hashes; regenerate stale metadata."""
    target = index.index_dir / "structure.json"
    signature = {"structure_version": STRUCTURE_VERSION,
                 "source_sha256": index.meta["source_sha256"], "chunks_sha256": index.meta["chunks_sha256"]}
    try:
        stored = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(stored, dict) and all(stored.get(key) == value for key, value in signature.items()):
            metadata = stored["metadata"]
            digest = hashlib.sha256(json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            if (isinstance(metadata, dict) and stored.get("metadata_sha256") == digest
                    and set(metadata) == {c["chunk_id"] for c in index.chunks}
                    and all(isinstance(metadata[c["chunk_id"]], dict)
                            and metadata[c["chunk_id"]].get("page") == c["page"]
                            and metadata[c["chunk_id"]].get("source") == c["source"] for c in index.chunks)):
                return metadata
    except (OSError, ValueError, KeyError, TypeError):
        pass
    first, last = index.meta["page_range"]
    metadata = annotate_structure(load_document(index.source_path, first, last), index.chunks)
    # Atomic sidecar replacement. Read-only deployments can use metadata in memory.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=index.index_dir, prefix=".structure-", delete=False) as stream:
            temporary = Path(stream.name)
            digest = hashlib.sha256(json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            json.dump({**signature, "metadata_sha256": digest, "metadata": metadata}, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, target)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return metadata
