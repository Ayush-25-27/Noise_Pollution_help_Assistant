"""
rag_retrieval_tool.py

Thin wrapper the orchestrator calls — keeps app.rag.vector_store's
internals (TF-IDF today, potentially embeddings + Chroma later) out
of the agent's own logic.
"""

from app.rag.vector_store import get_index


def retrieve_regulations(query: str, zone: str, top_k: int = 2) -> list[str]:
    index = get_index()
    results = index.search(query=query, zone=zone, top_k=top_k)
    return [r["text"] for r in results]
