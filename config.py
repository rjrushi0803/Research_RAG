"""
Configuration management for Research RAG.
Handles domain configs, LLM settings, and persistence.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional


# Default top-5 open-source publication sources
DEFAULT_SOURCES = [
    "arxiv",
    "semantic_scholar",
    "pubmed",
    "openalex",
    "core",
]

# Ollama model resource guidelines (approximate)
OLLAMA_RESOURCE_GUIDE = {
    "1B-3B": {"ram": "4-6 GB", "vram": "2-4 GB", "cpu": "4+ cores", "notes": "Runs on most machines"},
    "7B": {"ram": "8-10 GB", "vram": "6-8 GB", "cpu": "4+ cores", "notes": "Recommended minimum for quality"},
    "13B": {"ram": "16-20 GB", "vram": "10-16 GB", "cpu": "8+ cores", "notes": "Good quality, needs decent hardware"},
    "30B-34B": {"ram": "32-40 GB", "vram": "24-32 GB", "cpu": "8+ cores", "notes": "High quality, needs powerful GPU"},
    "70B": {"ram": "64+ GB", "vram": "48+ GB", "cpu": "16+ cores", "notes": "Best quality, enterprise hardware"},
}

# Supported LLM providers
LLM_PROVIDERS = {
    "ollama": {"name": "Ollama (Local)", "requires_key": False},
    "openai": {"name": "OpenAI", "requires_key": True},
    "anthropic": {"name": "Anthropic", "requires_key": True},
    "google": {"name": "Google (Gemini)", "requires_key": True},
    "qwen": {"name": "Qwen", "requires_key": True},
    "mistral": {"name": "Mistral", "requires_key": True},
}


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = ""
    model_name: str = ""
    api_key: str = ""
    base_url: str = ""  # For Ollama custom URL

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DomainConfig:
    """Configuration for a single research domain."""
    domain_name: str
    keywords: list = field(default_factory=list)
    sources: list = field(default_factory=lambda: DEFAULT_SOURCES.copy())
    custom_source_url: str = ""
    start_date: str = ""  # ISO format date string
    setup_date: str = ""  # When this domain was configured
    llm_config: dict = field(default_factory=dict)
    core_api_key: str = ""  # Optional CORE API key
    fetch_time: str = "06:00"  # Daily fetch time (HH:MM)

    def __post_init__(self):
        if not self.setup_date:
            self.setup_date = datetime.now().isoformat()
        if not self.start_date:
            # Default: 1 year ago
            one_year_ago = datetime.now() - timedelta(days=365)
            self.start_date = one_year_ago.strftime("%Y-%m-%d")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def data_dir(self):
        return os.path.join("data", self.domain_name)

    @property
    def docs_dir(self):
        return os.path.join(self.data_dir, "docs")

    @property
    def db_dir(self):
        return os.path.join(self.data_dir, "DB")

    @property
    def summaries_dir(self):
        return os.path.join(self.data_dir, "summaries")

    def ensure_directories(self):
        """Create all necessary directories for this domain."""
        for d in [self.docs_dir, self.db_dir, self.summaries_dir]:
            os.makedirs(d, exist_ok=True)


class ConfigManager:
    """Manages domain configurations with JSON persistence."""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _config_path(self, domain_name: str) -> str:
        return os.path.join(self.base_dir, domain_name, "config.json")

    def save_domain(self, config: DomainConfig):
        """Save a domain configuration to disk."""
        config.ensure_directories()
        path = self._config_path(config.domain_name)
        with open(path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

    def load_domain(self, domain_name: str) -> Optional[DomainConfig]:
        """Load a domain configuration from disk."""
        path = self._config_path(domain_name)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return DomainConfig.from_dict(data)

    def list_domains(self) -> list:
        """List all configured domain names."""
        domains = []
        if not os.path.exists(self.base_dir):
            return domains
        for name in sorted(os.listdir(self.base_dir)):
            config_path = self._config_path(name)
            if os.path.exists(config_path):
                domains.append(name)
        return domains

    def load_all_domains(self) -> list:
        """Load all domain configurations."""
        return [self.load_domain(name) for name in self.list_domains()]

    def delete_domain(self, domain_name: str):
        """Delete a domain configuration and its data."""
        import shutil
        domain_dir = os.path.join(self.base_dir, domain_name)
        if os.path.exists(domain_dir):
            shutil.rmtree(domain_dir)
