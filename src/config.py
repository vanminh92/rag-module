"""Shared defaults. Paths work even when Code 2 has another working directory."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "so_tay_sinh_vien_k50.pdf"
INDEX_DIR = Path(os.environ.get("RAG_INDEX_DIR", PROJECT_ROOT / "data" / "processed"))
MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
CHUNK_SIZE_CHARS = 500
CHUNK_OVERLAP_CHARS = 100
MAX_MODEL_TOKENS = 512
EMBEDDING_DIM = 384
TOP_K_DEFAULT = 3
CHUNK_STRATEGY = "pdf-clause-windows-v1"
INDEX_VERSION = 2
