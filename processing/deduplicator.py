"""
Deduplication of fetched papers using fuzzy title matching and DOI exact match.
"""

import logging
from typing import List
from rapidfuzz import fuzz
from fetchers.base import Paper

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 90  # Fuzzy match threshold (0-100)


def deduplicate_papers(papers: List[Paper], existing_papers: List[Paper] = None) -> List[Paper]:
    """
    Remove duplicate papers based on:
    1. Exact DOI match
    2. Fuzzy title similarity (>90%)
    """
    if existing_papers is None:
        existing_papers = []

    seen_dois = set()
    seen_titles = []
    unique_papers = []

    # Index existing papers
    for p in existing_papers:
        if p.doi:
            seen_dois.add(p.doi.lower().strip())
        seen_titles.append(p.title.lower().strip())

    for paper in papers:
        # Check DOI
        if paper.doi:
            doi_lower = paper.doi.lower().strip()
            if doi_lower in seen_dois:
                continue
            seen_dois.add(doi_lower)

        # Check title similarity
        title_lower = paper.title.lower().strip()
        is_duplicate = False
        for seen_title in seen_titles:
            if fuzz.ratio(title_lower, seen_title) >= SIMILARITY_THRESHOLD:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_titles.append(title_lower)
            unique_papers.append(paper)

    removed = len(papers) - len(unique_papers)
    if removed > 0:
        logger.info(f"Deduplication: removed {removed} duplicates, {len(unique_papers)} unique")

    return unique_papers
