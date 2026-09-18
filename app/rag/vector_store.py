"""
vector_store.py

Same lightweight approach as the AQI project: TF-IDF + cosine
similarity over a small, curated corpus, rather than a full
embeddings + Chroma/FAISS pipeline. Swap in real embeddings if you
ingest the full text of India's Noise Pollution Rules or WHO's
environmental noise guidelines instead of these 6 summary passages.
"""

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SOURCES_PATH = Path(__file__).resolve().parent / "sources" / "regulations.json"


class RegulationIndex:
    def __init__(self):
        with open(SOURCES_PATH, "r") as f:
            self.docs = json.load(f)
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self.vectorizer.fit_transform([d["text"] for d in self.docs])

    def search(self, query: str, zone: str, top_k: int = 2) -> list[dict]:
        candidates = [
            (i, d) for i, d in enumerate(self.docs)
            if d["zone"] in (zone, "general")
        ]
        if not candidates:
            return []

        query_vec = self.vectorizer.transform([query])
        scored = []
        for i, doc in candidates:
            sim = cosine_similarity(query_vec, self._matrix[i])[0][0]
            scored.append((sim, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]


_index: RegulationIndex | None = None


def get_index() -> RegulationIndex:
    global _index
    if _index is None:
        _index = RegulationIndex()
    return _index


if __name__ == "__main__":
    idx = get_index()
    for r in idx.search("is this reading enough to file a complaint", "silence"):
        print(r["id"], "-", r["text"][:80], "...")
