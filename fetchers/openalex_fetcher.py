"""
OpenAlex paper fetcher — free, CC0-licensed academic metadata.
No API key required for basic use.
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

import requests
from fetchers.base import BaseFetcher, Paper

logger = logging.getLogger(__name__)
API_BASE = "https://api.openalex.org"


class OpenAlexFetcher(BaseFetcher):
    source_name = "openalex"

    def __init__(self, email: str = "researcher@example.com"):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"ResearchRAG/1.0 (mailto:{email})"

    def fetch(self, keywords, start_date, end_date=None, max_results=50):
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        query = " ".join(keywords)
        papers = []
        cursor = "*"

        while len(papers) < max_results:
            per_page = min(max_results - len(papers), 50)
            params = {
                "search": query,
                "filter": f"from_publication_date:{start_date},to_publication_date:{end_date}",
                "sort": "publication_date:desc",
                "per_page": per_page,
                "cursor": cursor,
            }

            try:
                resp = self.session.get(f"{API_BASE}/works", params=params, timeout=30)
                if resp.status_code == 429:
                    time.sleep(5)
                    continue
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    # Get abstract from inverted index
                    abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))
                    if not abstract:
                        continue

                    authors = []
                    for auth in (item.get("authorships") or []):
                        name = auth.get("author", {}).get("display_name", "")
                        if name:
                            authors.append(name)

                    # Get best open access URL
                    pdf_url = ""
                    oa = item.get("open_access", {})
                    if oa.get("oa_url"):
                        pdf_url = oa["oa_url"]

                    papers.append(Paper(
                        title=item.get("title", "").strip(),
                        authors=authors,
                        abstract=abstract,
                        published_date=item.get("publication_date", ""),
                        source_url=item.get("id", ""),
                        pdf_url=pdf_url,
                        source_name=self.source_name,
                        doi=item.get("doi", ""),
                    ))

                cursor = data.get("meta", {}).get("next_cursor")
                if not cursor:
                    break
                time.sleep(0.2)

            except requests.exceptions.RequestException as e:
                logger.error(f"OpenAlex fetch error: {e}")
                break

        logger.info(f"OpenAlex: fetched {len(papers)} papers")
        return papers[:max_results]

    @staticmethod
    def _reconstruct_abstract(inverted_index):
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        return " ".join(w for _, w in word_positions)
