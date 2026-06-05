"""
CORE API fetcher — world's largest open-access full-text collection.
Requires a free API key from https://core.ac.uk/services/api
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

import requests
from fetchers.base import BaseFetcher, Paper

logger = logging.getLogger(__name__)
API_BASE = "https://api.core.ac.uk/v3"


class COREFetcher(BaseFetcher):
    source_name = "core"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def fetch(self, keywords, start_date, end_date=None, max_results=50):
        if not self.api_key:
            logger.warning("CORE API key not provided, skipping CORE fetch")
            return []

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        query = " OR ".join(keywords)
        papers = []
        offset = 0

        while len(papers) < max_results:
            limit = min(max_results - len(papers), 100)
            payload = {
                "q": query,
                "offset": offset,
                "limit": limit,
                "exclude": ["fullText"],
            }

            try:
                resp = self.session.post(
                    f"{API_BASE}/search/works", json=payload, timeout=30
                )
                if resp.status_code == 429:
                    time.sleep(10)
                    continue
                resp.raise_for_status()
                data = resp.json()

                results = data.get("results", [])
                if not results:
                    break

                for item in results:
                    abstract = item.get("abstract", "")
                    if not abstract:
                        continue

                    pub_date = item.get("publishedDate") or item.get("yearPublished", "")
                    if isinstance(pub_date, int):
                        pub_date = f"{pub_date}-01-01"

                    # Filter by date range
                    try:
                        pd = self._parse_date(pub_date[:10])
                        sd = self._parse_date(start_date)
                        ed = self._parse_date(end_date)
                        if pd < sd or pd > ed:
                            continue
                    except (ValueError, IndexError):
                        pass

                    authors = []
                    for a in (item.get("authors") or []):
                        name = a.get("name", "")
                        if name:
                            authors.append(name)

                    dl_url = item.get("downloadUrl", "")
                    papers.append(Paper(
                        title=item.get("title", "").strip(),
                        authors=authors,
                        abstract=abstract.strip(),
                        published_date=str(pub_date)[:10],
                        source_url=item.get("sourceFulltextUrls", [""])[0] if item.get("sourceFulltextUrls") else "",
                        pdf_url=dl_url if dl_url else "",
                        source_name=self.source_name,
                        doi=item.get("doi", ""),
                    ))

                offset += limit
                if offset >= data.get("totalHits", 0):
                    break
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                logger.error(f"CORE fetch error: {e}")
                break

        logger.info(f"CORE: fetched {len(papers)} papers")
        return papers[:max_results]
