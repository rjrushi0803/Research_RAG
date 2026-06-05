"""
Base fetcher class and Paper dataclass.
All paper fetchers inherit from BaseFetcher.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional
import hashlib
import json


@dataclass
class Paper:
    """Represents a single research paper."""
    title: str
    authors: List[str]
    abstract: str
    published_date: str  # ISO format
    source_url: str
    pdf_url: str = ""
    source_name: str = ""
    doi: str = ""
    methodology: str = ""
    results: str = ""
    full_text: str = ""

    @property
    def paper_id(self) -> str:
        """Generate a unique ID from title hash."""
        return hashlib.sha256(self.title.lower().strip().encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, filepath: str):
        """Save paper metadata to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Paper":
        """Load paper metadata from a JSON file."""
        with open(filepath, "r") as f:
            return cls.from_dict(json.load(f))


class BaseFetcher(ABC):
    """Abstract base class for all paper fetchers."""

    source_name: str = "base"

    @abstractmethod
    def fetch(
        self,
        keywords: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Paper]:
        """
        Fetch papers matching the given keywords within a date range.

        Args:
            keywords: List of search keywords.
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format (defaults to today).
            max_results: Maximum number of papers to return.

        Returns:
            List of Paper objects.
        """
        pass

    def _build_query(self, keywords: List[str]) -> str:
        """Build a search query string from keywords."""
        return " OR ".join(keywords)

    def _parse_date(self, date_str: str) -> datetime:
        """Parse a date string to datetime."""
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {date_str}")
