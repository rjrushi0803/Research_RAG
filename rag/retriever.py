"""
Retriever — semantic search with context building for LLM prompts.
"""

import logging
from typing import List, Dict, Optional

from processing.embedder import generate_query_embedding
from rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves and ranks relevant documents from the vector store."""

    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Retrieve relevant documents for a query.
        Returns list of dicts with 'text', 'metadata', 'score'.
        """
        if self.vector_store.count == 0:
            return []

        query_embedding = generate_query_embedding(query)

        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        retrieved = []
        for i in range(len(results["ids"])):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - (distance/2)
            distance = results["distances"][i]
            score = 1.0 - (distance / 2.0)

            retrieved.append({
                "text": results["documents"][i],
                "metadata": results["metadatas"][i],
                "score": score,
            })

        # Sort by score descending
        retrieved.sort(key=lambda x: x["score"], reverse=True)

        return retrieved

    def build_context(
        self,
        query: str,
        n_results: int = 5,
        max_context_length: int = 3000,
    ) -> str:
        """
        Build a context string from retrieved documents for LLM prompting.
        """
        results = self.retrieve(query, n_results=n_results)

        if not results:
            return ""

        context_parts = []
        total_length = 0

        for r in results:
            text = r["text"]
            title = r["metadata"].get("title", "Unknown")
            source = r["metadata"].get("source_name", "")
            section = r["metadata"].get("section", "")

            entry = f"[Source: {title} ({source}) - {section}]\n{text}\n"

            if total_length + len(entry) > max_context_length:
                break

            context_parts.append(entry)
            total_length += len(entry)

        return "\n---\n".join(context_parts)

    def has_relevant_documents(self, query: str, threshold: float = 0.3) -> bool:
        """Check if there are relevant documents for a query above threshold."""
        results = self.retrieve(query, n_results=1)
        if not results:
            return False
        return results[0]["score"] >= threshold
