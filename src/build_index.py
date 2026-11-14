"""Build document artifacts. --chunks-only runs CV12 without downloading a model."""

import argparse
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .chunking import build_chunks, normalize_text
from .config import (CHUNK_OVERLAP_CHARS, CHUNK_SIZE_CHARS, CHUNK_STRATEGY, EMBEDDING_DIM,
                     INDEX_DIR, INDEX_VERSION, INPUT_PATH, MAX_MODEL_TOKENS, MODEL_NAME)
from .document_loader import load_document


def parse_pages(value: str) -> tuple[int, int]:
    if not re.fullmatch(r"[1-9]\d*-[1-9]\d*", value):
        raise argparse.ArgumentTypeError("Dùng --pages START-END, ví dụ 8-31 (1-based inclusive)")
    start, end = map(int, value.split("-"))
    if start > end:
        raise argparse.ArgumentTypeError("Trang bắt đầu phải <= trang kết thúc")
    return start, end


def extract_chunks(
    input_path: str | Path, index_dir: str | Path,
    start_page: int | None = None, end_page: int | None = None,
) -> dict:
    pages = load_document(input_path, start_page, end_page)
    chunks = build_chunks(pages, Path(input_path).name)
    output = Path(index_dir)
    # Avoid overwriting just one part of an existing CV13 index.
    if any((output / name).exists() for name in ("embeddings.npy", "index_meta.json")):
        raise ValueError("Thư mục đã có index. Chọn --out khác cho --chunks-only hoặc build lại đầy đủ")
    output.mkdir(parents=True, exist_ok=True)
    (output / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stats = {"text_pages": len(pages), "raw_chars": sum(len(p["text"]) for p in pages),
             "num_chunks": len(chunks), "output": str(output / "chunks.json")}
    logging.getLogger(__name__).info("CV12: %s", stats)
    return stats


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_index(
    input_path: str | Path, index_dir: str | Path,
    start_page: int | None = None, end_page: int | None = None,
) -> dict:
    """Create all artifacts from the same PDF snapshot; commit metadata last."""
    import numpy as np
    from pypdf import PdfReader

    from .embeddings import get_embedder

    source = Path(input_path).resolve()
    output = Path(index_dir).resolve()
    # Validate before loading/downloading any model.
    source_hash = file_sha256(source)
    pages = load_document(source, start_page, end_page)
    with source.open("rb") as stream:
        reader = PdfReader(stream)
        if reader.is_encrypted:
            reader.decrypt("")
        total_pages = len(reader.pages)
    selected = [start_page or 1, end_page or total_pages]
    chunks = build_chunks(pages, source.name)
    encoder = get_embedder()
    lengths = encoder.token_lengths([c["text"] for c in chunks], "passage")
    vectors = encoder.encode_passages([c["text"] for c in chunks], show_progress=True)
    if file_sha256(source) != source_hash:
        raise ValueError("PDF thay đổi trong khi build; hãy chạy lại với PDF ổn định")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".build-", dir=output) as temporary:
        staging = Path(temporary)
        (staging / "chunks.json").write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        np.save(staging / "embeddings.npy", vectors, allow_pickle=False)
        meta = {
            "source": source.name, "source_sha256": source_hash,
            "source_path": Path(os.path.relpath(source, output)).as_posix(),
            "page_range": selected, "total_pdf_pages": total_pages,
            "text_pages": len(pages),
            "empty_pages": sorted(set(range(selected[0], selected[1] + 1)) - {p["page"] for p in pages}),
            "raw_chars": sum(len(p["text"]) for p in pages),
            "normalized_chars": sum(len(normalize_text(p["text"])) for p in pages),
            "model_name": MODEL_NAME, "model_revision": encoder.revision,
            "embedding_dim": EMBEDDING_DIM, "num_chunks": len(chunks),
            "chunk_size_chars": CHUNK_SIZE_CHARS, "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
            "chunk_strategy": CHUNK_STRATEGY,
            "max_model_tokens": MAX_MODEL_TOKENS, "max_passage_tokens": max(lengths),
            "index_version": INDEX_VERSION, "build_timestamp": datetime.now(timezone.utc).isoformat(),
            "chunks_sha256": file_sha256(staging / "chunks.json"),
            "embeddings_sha256": file_sha256(staging / "embeddings.npy"),
        }
        (staging / "index_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        for name in ("chunks.json", "embeddings.npy", "index_meta.json"):
            os.replace(staging / name, output / name)
    logging.getLogger(__name__).info("CV13 index: %s", json.dumps(meta, ensure_ascii=False))
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--out", type=Path, default=INDEX_DIR)
    parser.add_argument("--pages", type=parse_pages)
    parser.add_argument("--chunks-only", action="store_true", help="CV12: chỉ trích xuất và lưu chunks.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    start, end = args.pages or (None, None)
    try:
        builder = extract_chunks if args.chunks_only else build_index
        stats = builder(args.input, args.out, start, end)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Lỗi: {exc}\n")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
