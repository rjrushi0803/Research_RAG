"""
Semantic Scholar paper fetcher using their Academic Graph API.
Provides excellent metadata and citation data.
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

import requests

from fetchers.base import BaseFetcher, Paper

logger = logging.getLogger(__name__)

API_BASE = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarFetcher(BaseFetcher):
    """Fetches papers from Semantic Scholar."""

    source_name = "semantic_scholar"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["x-api-key"] = api_key

    def fetch(
        self,
        keywords: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Paper]:
        """Fetch papers from Semantic Scholar."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        start_year = self._parse_date(start_date).year
        end_year = self._parse_date(end_date).year
        year_range = f"{start_year}-{end_year}"

        query = " ".join(keywords)
        papers = []
        offset = 0
        remaining = max_results

        while remaining > 0:
            limit = min(remaining, 100)
            params = {
                "query": query,
                "year": year_range,
                "offset": offset,
                "limit": limit,
                "fields": "title,authors,abstract,year,externalIds,url,openAccessPdf,publicationDate",
            }

            try:
                resp = self.session.get(f"{API_BASE}/paper/search", params=params, timeout=30)

                if resp.status_code == 429:
                    logger.warning("Semantic Scholar rate limit hit, waiting 60s...")
                    time.sleep(60)
                    continue

                resp.raise_for_status()
                data = resp.json()

                for item in data.get("data", []):
                    if not item.get("abstract"):
                        continue

                    authors = []
                    for a in (item.get("authors") or []):
                        if a.get("name"):
                            authors.append(a["name"])

                    pdf_url = ""
                    oap = item.get("openAccessPdf")
                    if oap and isinstance(oap, dict):
                        pdf_url = oap.get("url", "")

                    ext_ids = item.get("externalIds") or {}

                    pub_date = item.get("publicationDate") or f"{item.get('year', '')}-01-01"

                    paper = Paper(
                        title=item.get("title", "").strip(),
                        authors=authors,
                        abstract=item.get("abstract", "").strip(),
                        published_date=pub_date,
                        source_url=item.get("url", ""),
                        pdf_url=pdf_url,
                        source_name=self.source_name,
                        doi=ext_ids.get("DOI", ""),
                    )
                    papers.append(paper)

                total = data.get("total", 0)
                offset += limit
                remaining -= limit

                if offset >= total:
                    break

                time.sleep(1)  # Be polite

            except requests.exceptions.RequestException as e:
                logger.error(f"Semantic Scholar fetch error: {e}")
                break

        logger.info(f"Semantic Scholar: fetched {len(papers)} papers")
        return papers
