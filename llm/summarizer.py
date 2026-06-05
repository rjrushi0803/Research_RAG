"""
Paper summarizer — generates structured summaries using the configured LLM.
Outputs: paper name, abstract summary, methodology overview, key results.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from config import DomainConfig, LLMConfig
from llm.provider import chat_completion

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """You are a research paper summarizer. Given the following paper details, provide a concise structured summary.

Paper Title: {title}
Authors: {authors}
Abstract: {abstract}

Provide a JSON response with these fields:
- "title": the paper title
- "abstract_summary": 2-3 sentence summary of the abstract
- "methodology": key methodology described (if identifiable from abstract, else "Not available from abstract")
- "key_results": main findings or contributions (if identifiable, else "Not available from abstract")

Return ONLY valid JSON, no markdown formatting."""


def summarize_paper(paper_dict: Dict, llm_config: LLMConfig) -> Dict:
    """Generate a structured summary for a single paper."""
    prompt = SUMMARY_PROMPT.format(
        title=paper_dict.get("title", ""),
        authors=", ".join(paper_dict.get("authors", [])[:5]),
        abstract=paper_dict.get("abstract", ""),
    )

    messages = [
        {"role": "system", "content": "You are a precise research paper summarizer. Always respond with valid JSON."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = chat_completion(llm_config, messages, temperature=0.2, max_tokens=1024)

        # Parse JSON from response
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])

        summary = json.loads(response)
        summary["source_url"] = paper_dict.get("source_url", "")
        summary["published_date"] = paper_dict.get("published_date", "")
        summary["source_name"] = paper_dict.get("source_name", "")
        return summary

    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Summary parse error for '{paper_dict.get('title', '')}': {e}")
        return {
            "title": paper_dict.get("title", ""),
            "abstract_summary": paper_dict.get("abstract", "")[:500],
            "methodology": "Summary generation failed",
            "key_results": "Summary generation failed",
            "source_url": paper_dict.get("source_url", ""),
            "published_date": paper_dict.get("published_date", ""),
            "source_name": paper_dict.get("source_name", ""),
        }


def summarize_papers(papers: List[Dict], llm_config: LLMConfig) -> List[Dict]:
    """Summarize a batch of papers."""
    summaries = []
    for i, paper in enumerate(papers):
        logger.info(f"Summarizing paper {i+1}/{len(papers)}: {paper.get('title', '')[:60]}")
        summary = summarize_paper(paper, llm_config)
        summaries.append(summary)
    return summaries


def save_summaries(summaries: List[Dict], domain_config: DomainConfig, date_str: str = None):
    """Save summaries to domain's summaries directory."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    summaries_dir = domain_config.summaries_dir
    os.makedirs(summaries_dir, exist_ok=True)

    filepath = os.path.join(summaries_dir, f"{date_str}.json")
    with open(filepath, "w") as f:
        json.dump(summaries, f, indent=2)

    logger.info(f"Saved {len(summaries)} summaries to {filepath}")


def load_summaries(domain_config: DomainConfig, date_str: str) -> List[Dict]:
    """Load summaries for a specific date."""
    filepath = os.path.join(domain_config.summaries_dir, f"{date_str}.json")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)


def get_recent_summaries(domain_config: DomainConfig, days: int = 2) -> Dict[str, List[Dict]]:
    """Get summaries for the last N days (default: 2 days shown, 3 days kept)."""
    result = {}
    today = datetime.now()

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        summaries = load_summaries(domain_config, date_str)
        if summaries:
            result[date_str] = summaries

    return result


def cleanup_old_summaries(domain_config: DomainConfig, keep_days: int = 3):
    """Remove summaries older than keep_days."""
    summaries_dir = domain_config.summaries_dir
    if not os.path.exists(summaries_dir):
        return

    cutoff = datetime.now() - timedelta(days=keep_days)

    for filename in os.listdir(summaries_dir):
        if not filename.endswith(".json"):
            continue
        date_str = filename.replace(".json", "")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                os.remove(os.path.join(summaries_dir, filename))
                logger.info(f"Removed old summary: {filename}")
        except ValueError:
            continue
