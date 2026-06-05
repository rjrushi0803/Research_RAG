"""
Embedding generation using sentence-transformers.
Default model: all-MiniLM-L6-v2 (384-dim, fast).
"""

import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"

_model_cache = {}


def get_embedding_model(model_name: str = DEFAULT_MODEL):
    """Get or create a cached embedding model."""
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {model_name}")
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def generate_embeddings(
    texts: List[str],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
    show_progress: bool = True,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Returns list of embedding vectors as plain lists (for ChromaDB).
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )

    logger.info(f"Generated {len(embeddings)} embeddings (dim={embeddings.shape[1]})")
    return embeddings.tolist()


def generate_query_embedding(
    query: str,
    model_name: str = DEFAULT_MODEL,
) -> List[float]:
    """Generate embedding for a single query string."""
    model = get_embedding_model(model_name)
    embedding = model.encode([query], normalize_embeddings=True)
    return embedding[0].tolist()
