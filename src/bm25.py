"""Small in-memory BM25 Okapi index with positive IDF and Vietnamese n-grams."""

from collections import Counter

import numpy as np

from .text_utils import vietnamese_tokens


class BM25:
    def __init__(self, documents: list[str], *, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.documents = [Counter(vietnamese_tokens(text)) for text in documents]
        self.lengths = np.asarray([sum(doc.values()) for doc in self.documents], dtype=np.float32)
        self.average_length = float(self.lengths.mean()) if len(documents) else 1.0
        frequencies = Counter(term for doc in self.documents for term in doc)
        self.idf = {term: float(np.log(1 + (len(documents) - count + 0.5) / (count + 0.5)))
                    for term, count in frequencies.items()}
        self.postings: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        postings = {}
        for index, doc in enumerate(self.documents):
            for term, count in doc.items():
                postings.setdefault(term, []).append((index, count))
        for term, values in postings.items():
            array = np.asarray(values)
            self.postings[term] = (array[:, 0], array[:, 1].astype(np.float32))

    def scores(self, query: str) -> np.ndarray:
        scores = np.zeros(len(self.documents), dtype=np.float32)
        for term in set(vietnamese_tokens(query)):
            if term not in self.postings:
                continue
            indices, frequency = self.postings[term]
            norm = self.k1 * (1 - self.b + self.b * self.lengths[indices] / max(self.average_length, 1))
            scores[indices] += self.idf[term] * frequency * (self.k1 + 1) / (frequency + norm)
        return scores
