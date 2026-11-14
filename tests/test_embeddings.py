import numpy as np
import pytest

from src.chunking import build_chunks
from src.embeddings import get_embedder, prepare_texts, validate_vectors


def test_prefixes_use_real_text(pilot_pages):
    text = pilot_pages[0]["text"]
    assert prepare_texts([text], "passage") == ["passage: " + text.strip()]
    assert prepare_texts([text], "query") == ["query: " + text.strip()]


@pytest.mark.parametrize("texts,kind", [([], "passage"), ([" "], "query"), ([None], "query"), ([""], "other")])
def test_invalid_embedding_input(texts, kind):
    with pytest.raises(ValueError):
        prepare_texts(texts, kind)


@pytest.mark.real_model
def test_actual_e5_prefix_shape_and_normalization(encoder, pilot_pages):
    text = build_chunks(pilot_pages[:1], "so_tay_sinh_vien_k50.pdf")[0]["text"]
    passages = encoder.encode_passages([text])
    queries = encoder.encode_query(text)
    direct = encoder.model.encode(["passage: " + text], normalize_embeddings=True,
                                  convert_to_numpy=True, prompt="")
    assert np.allclose(passages, direct, atol=1e-6)
    direct_query = encoder.model.encode(["query: " + text], normalize_embeddings=True,
                                        convert_to_numpy=True, prompt="")[0]
    assert np.allclose(queries, direct_query, atol=1e-6)
    assert passages.shape == (1, 384)
    assert queries.shape == (384,)
    assert passages.dtype == np.float32
    assert np.isclose(np.linalg.norm(queries), 1.0, atol=1e-4)
    assert encoder is get_embedder()


@pytest.mark.real_model
def test_no_silent_token_truncation(encoder, pilot_pages):
    text = pilot_pages[0]["text"] * 4
    assert encoder.token_lengths([text], "passage")[0] > 512
    with pytest.raises(ValueError, match="Không cắt âm thầm"):
        encoder.encode_passages([text])
    with pytest.raises(ValueError, match="Không cắt âm thầm"):
        encoder.encode_query(text)
    chunks = build_chunks(pilot_pages, "so_tay_sinh_vien_k50.pdf")
    assert max(encoder.token_lengths([c["text"] for c in chunks], "passage")) <= 512


@pytest.mark.real_model
def test_vector_errors_from_real_embeddings(real_vectors):
    assert validate_vectors(real_vectors, len(real_vectors)) is real_vectors
    for invalid in [real_vectors[:, :-1], real_vectors.astype(np.float64), real_vectors * 0, real_vectors * 2]:
        with pytest.raises(ValueError):
            validate_vectors(invalid, len(real_vectors))
    for value in (np.nan, np.inf):
        invalid = real_vectors.copy()
        invalid[0, 0] = value
        with pytest.raises(ValueError, match="NaN/Inf"):
            validate_vectors(invalid, len(real_vectors))
