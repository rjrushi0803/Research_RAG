"""
ChromaDB vector store operations.
Persistent storage at ./data/<domain>/DB with per-domain collections.
"""

import logging
import os
from typing import List, Dict, Optional

import chromadb

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages ChromaDB collections for a domain."""

    def __init__(self, db_path: str, collection_name: str = "papers"):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"VectorStore initialized at {db_path}, collection={collection_name}")

    @property
    def count(self) -> int:
        return self.collection.count()

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict],
    ):
        """
        Add documents to the vector store with deduplication.
        Skips IDs that already exist.
        """
        if not ids:
            return

        # Filter out existing IDs
        existing = set()
        try:
            result = self.collection.get(ids=ids)
            existing = set(result["ids"])
        except Exception:
            pass

        new_ids = []
        new_embeddings = []
        new_documents = []
        new_metadatas = []

        for i, doc_id in enumerate(ids):
            if doc_id not in existing:
                new_ids.append(doc_id)
                new_embeddings.append(embeddings[i])
                new_documents.append(documents[i])
                new_metadatas.append(metadatas[i])

        if not new_ids:
            logger.info("No new documents to add (all duplicates)")
            return

        # Batch upsert (ChromaDB supports up to 5461 at a time)
        batch_size = 5000
        for start in range(0, len(new_ids), batch_size):
            end = start + batch_size
            self.collection.add(
                ids=new_ids[start:end],
                embeddings=new_embeddings[start:end],
                documents=new_documents[start:end],
                metadatas=new_metadatas[start:end],
            )

        logger.info(f"Added {len(new_ids)} new documents (skipped {len(existing)} existing)")

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> Dict:
        """
        Query the vector store for similar documents.
        Returns dict with 'ids', 'documents', 'metadatas', 'distances'.
        """
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self.count) if self.count > 0 else 1,
        }
        if where:
            kwargs["where"] = where

        try:
            results = self.collection.query(**kwargs)
            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else [],
            }
        except Exception as e:
            logger.error(f"Query error: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

    def delete_collection(self):
        """Delete the entire collection."""
        try:
            self.client.delete_collection(self.collection.name)
            logger.info(f"Deleted collection {self.collection.name}")
        except Exception as e:
            logger.error(f"Delete error: {e}")
