"""Verify the UI's document/page links against the existing chunk catalog."""

import json
from pathlib import Path


def read_catalog(path):
    return {source["chunk_id"]: source for source in json.loads(Path(path).read_text(encoding="utf-8"))}


def validated_sources(sources, catalog, filename, page_count):
    valid, errors, seen = [], [], set()
    for number, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            errors.append(f"Nguồn [{number}] không có metadata hợp lệ.")
            continue
        identifier = source.get("chunk_id")
        original = catalog.get(identifier)
        if (not original or source.get("source") != filename or type(source.get("page")) is not int
                or not 1 <= source["page"] <= page_count
                or any(source.get(k) != original[k] for k in ("source", "page", "text"))):
            errors.append(f"Nguồn [{number}] không khớp tài liệu/index; không tạo liên kết PDF.")
            continue
        if identifier not in seen:
            valid.append({**source, "ui_number": number})
            seen.add(identifier)
    return valid, errors


def verified_claim_sources(claim, sources):
    by_id = {s["chunk_id"]: s for s in sources}
    result = []
    citations = claim.get("citations", [])
    for citation in citations:
        source = by_id.get(citation.get("source_id"))
        quote = " ".join(str(citation.get("quote", "")).split())
        if not source or not quote or quote not in " ".join(source["text"].split()):
            return []
        if source not in result:
            result.append(source)
    return result
