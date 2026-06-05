"""Paper fetcher modules for various academic sources."""

from fetchers.base import Paper, BaseFetcher
from fetchers.arxiv_fetcher import ArxivFetcher
from fetchers.semantic_scholar import SemanticScholarFetcher
from fetchers.pubmed_fetcher import PubMedFetcher
from fetchers.core_fetcher import COREFetcher
from fetchers.openalex_fetcher import OpenAlexFetcher

FETCHER_MAP = {
    "arxiv": ArxivFetcher,
    "semantic_scholar": SemanticScholarFetcher,
    "pubmed": PubMedFetcher,
    "core": COREFetcher,
    "openalex": OpenAlexFetcher,
}


def get_fetcher(source_name: str, **kwargs) -> BaseFetcher:
    """Get a fetcher instance by source name."""
    fetcher_cls = FETCHER_MAP.get(source_name)
    if fetcher_cls is None:
        raise ValueError(f"Unknown source: {source_name}. Available: {list(FETCHER_MAP.keys())}")
    return fetcher_cls(**kwargs)
