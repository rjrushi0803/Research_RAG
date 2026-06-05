"""
arXiv paper fetcher using the arxiv Python library.
Supports date range filtering via submittedDate query.
"""

import time
import logging
from typing import List, Optional
from datetime import datetime

import arxiv

from fetchers.base import BaseFetcher, Paper

logger = logging.getLogger(__name__)


class ArxivFetcher(BaseFetcher):
    """Fetches papers from arXiv."""

    source_name = "arxiv"

    def __init__(self):
        self.client = arxiv.Client(
            page_size=50,
            delay_seconds=3.0,  # Rate limiting
            num_retries=3,
        )

    def fetch(
        self,
        keywords: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Paper]:
        """Fetch papers from arXiv matching keywords within date range."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Build arXiv query with date range
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        date_from = start_dt.strftime("%Y%m%d0000")
        date_to = end_dt.strftime("%Y%m%d2359")

        keyword_query = " OR ".join([f"all:{kw}" for kw in keywords])
        query = f"({keyword_query}) AND submittedDate:[{date_from} TO {date_to}]"

        logger.info(f"arXiv query: {query}")

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []
        try:
            for result in self.client.results(search):
                paper = Paper(
                    title=result.title.strip(),
                    authors=[a.name for a in result.authors],
                    abstract=result.summary.strip(),
                    published_date=result.published.strftime("%Y-%m-%d"),
                    source_url=result.entry_id,
                    pdf_url=result.pdf_url or "",
                    source_name=self.source_name,
                    doi=result.doi or "",
                )
                papers.append(paper)
        except Exception as e:
            logger.error(f"arXiv fetch error: {e}")

        logger.info(f"arXiv: fetched {len(papers)} papers")
        return papers
