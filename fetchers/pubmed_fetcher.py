"""
PubMed paper fetcher using E-utilities (esearch + efetch).
Gold standard for biomedical and life sciences research.
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

import requests
from lxml import etree

from fetchers.base import BaseFetcher, Paper

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedFetcher(BaseFetcher):
    """Fetches papers from PubMed using E-utilities."""

    source_name = "pubmed"

    def __init__(self, email: str = "researcher@example.com"):
        self.email = email
        self.session = requests.Session()

    def fetch(self, keywords, start_date, end_date=None, max_results=50):
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)
        mindate = start_dt.strftime("%Y/%m/%d")
        maxdate = end_dt.strftime("%Y/%m/%d")
        query = " OR ".join(keywords)

        search_params = {
            "db": "pubmed", "term": query, "datetype": "pdat",
            "mindate": mindate, "maxdate": maxdate, "retmax": max_results,
            "retmode": "json", "email": self.email, "sort": "date",
        }

        try:
            resp = self.session.get(ESEARCH_URL, params=search_params, timeout=30)
            resp.raise_for_status()
            id_list = resp.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            time.sleep(0.5)
            fetch_params = {
                "db": "pubmed", "id": ",".join(id_list),
                "retmode": "xml", "email": self.email,
            }
            resp = self.session.get(EFETCH_URL, params=fetch_params, timeout=60)
            resp.raise_for_status()
            return self._parse_xml(resp.content)
        except Exception as e:
            logger.error(f"PubMed fetch error: {e}")
            return []

    def _parse_xml(self, xml_content):
        papers = []
        try:
            root = etree.fromstring(xml_content)
            for article in root.findall(".//PubmedArticle"):
                try:
                    title_elem = article.find(".//ArticleTitle")
                    title = "".join(title_elem.itertext()).strip() if title_elem is not None else ""

                    abstract_parts = []
                    for abs_text in article.findall(".//AbstractText"):
                        label = abs_text.get("Label", "")
                        text = "".join(abs_text.itertext()).strip()
                        abstract_parts.append(f"{label}: {text}" if label else text)
                    abstract = " ".join(abstract_parts)
                    if not abstract:
                        continue

                    authors = []
                    for author in article.findall(".//Author"):
                        last = author.findtext("LastName", "")
                        fore = author.findtext("ForeName", "")
                        if last:
                            authors.append(f"{fore} {last}".strip())

                    pub_date = article.find(".//PubDate")
                    year = pub_date.findtext("Year", "") if pub_date is not None else ""
                    month = pub_date.findtext("Month", "01") if pub_date is not None else "01"
                    day = pub_date.findtext("Day", "01") if pub_date is not None else "01"
                    month_map = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
                                 "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}
                    month = month_map.get(month, month)
                    try:
                        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                    except (ValueError, TypeError):
                        date_str = f"{year}-01-01"

                    doi = ""
                    for eid in article.findall(".//ArticleId"):
                        if eid.get("IdType") == "doi":
                            doi = eid.text or ""
                            break

                    pmid = article.findtext(".//PMID", "")
                    source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                    papers.append(Paper(
                        title=title, authors=authors, abstract=abstract,
                        published_date=date_str, source_url=source_url, pdf_url="",
                        source_name=self.source_name, doi=doi,
                    ))
                except Exception as e:
                    logger.warning(f"PubMed parse error: {e}")
        except etree.XMLSyntaxError as e:
            logger.error(f"PubMed XML error: {e}")

        logger.info(f"PubMed: fetched {len(papers)} papers")
        return papers
