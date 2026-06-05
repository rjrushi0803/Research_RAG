"""
Document chunking with configurable size and overlap.
Preserves section boundaries where possible.
"""

import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 512  # tokens (approximate by words)
DEFAULT_OVERLAP = 50      # tokens overlap


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List[str]:
    """
    Split text into overlapping chunks, respecting sentence boundaries.
    """
    if not text.strip():
        return []

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        word_count = len(sentence.split())

        if current_length + word_count > chunk_size and current_chunk:
            chunk_text_str = " ".join(current_chunk)
            chunks.append(chunk_text_str)

            # Keep overlap
            overlap_chunk = []
            overlap_len = 0
            for s in reversed(current_chunk):
                s_len = len(s.split())
                if overlap_len + s_len > overlap:
                    break
                overlap_chunk.insert(0, s)
                overlap_len += s_len

            current_chunk = overlap_chunk
            current_length = overlap_len

        current_chunk.append(sentence)
        current_length += word_count

    # Last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def chunk_paper(paper_dict: Dict, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[Dict]:
    """
    Chunk a paper into sections with metadata.
    Returns list of dicts with 'text' and 'metadata' keys.
    """
    sections = []

    # Abstract
    abstract = paper_dict.get("abstract", "")
    if abstract:
        sections.append(("abstract", abstract))

    # Full text if available
    full_text = paper_dict.get("full_text", "")
    if full_text:
        sections.append(("full_text", full_text))

    result = []
    for section_name, text in sections:
        text_chunks = chunk_text(text, chunk_size=chunk_size)
        for i, chunk in enumerate(text_chunks):
            result.append({
                "text": chunk,
                "metadata": {
                    "title": paper_dict.get("title", ""),
                    "section": section_name,
                    "chunk_index": i,
                    "source_url": paper_dict.get("source_url", ""),
                    "published_date": paper_dict.get("published_date", ""),
                    "source_name": paper_dict.get("source_name", ""),
                },
            })

    return result
