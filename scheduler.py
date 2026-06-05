"""
APScheduler-based daily paper fetching scheduler.
Runs at 6:00 AM daily for each configured domain.
"""

import logging
import os
import json
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import ConfigManager, DomainConfig, LLMConfig
from fetchers import get_fetcher
from fetchers.base import Paper
from processing.deduplicator import deduplicate_papers
from processing.chunker import chunk_paper
from processing.embedder import generate_embeddings
from rag.vectorstore import VectorStore
from llm.summarizer import summarize_papers, save_summaries, cleanup_old_summaries

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def fetch_and_process_domain(domain_config: DomainConfig):
    """
    Full pipeline for a single domain:
    1. Fetch papers from all sources
    2. Deduplicate
    3. Store paper metadata
    4. Generate embeddings and add to vector DB
    5. Generate summaries
    6. Cleanup old summaries
    """
    logger.info(f"Starting daily fetch for domain: {domain_config.domain_name}")

    today = datetime.now().strftime("%Y-%m-%d")

    # Load existing papers for dedup
    existing_papers = _load_existing_papers(domain_config)

    # 1. Fetch from all configured sources
    all_papers = []
    for source_name in domain_config.sources:
        try:
            kwargs = {}
            if source_name == "core" and domain_config.core_api_key:
                kwargs["api_key"] = domain_config.core_api_key
            elif source_name == "core" and not domain_config.core_api_key:
                logger.info("Skipping CORE (no API key)")
                continue

            fetcher = get_fetcher(source_name, **kwargs)
            papers = fetcher.fetch(
                keywords=domain_config.keywords,
                start_date=domain_config.start_date,
                end_date=today,
                max_results=30,
            )
            all_papers.extend(papers)
            logger.info(f"  {source_name}: {len(papers)} papers")
        except Exception as e:
            logger.error(f"  {source_name} error: {e}")

    if not all_papers:
        logger.info(f"No new papers found for {domain_config.domain_name}")
        return

    # 2. Deduplicate
    unique_papers = deduplicate_papers(all_papers, existing_papers)

    if not unique_papers:
        logger.info("All papers were duplicates, nothing new to process")
        return

    logger.info(f"Processing {len(unique_papers)} unique new papers")

    # 3. Store paper metadata as JSON
    docs_dir = domain_config.docs_dir
    os.makedirs(docs_dir, exist_ok=True)
    for paper in unique_papers:
        filepath = os.path.join(docs_dir, f"{paper.paper_id}.json")
        paper.save(filepath)

    # 4. Chunk and embed
    all_chunks = []
    for paper in unique_papers:
        chunks = chunk_paper(paper.to_dict())
        all_chunks.extend(chunks)

    if all_chunks:
        texts = [c["text"] for c in all_chunks]
        embeddings = generate_embeddings(texts, show_progress=False)

        ids = [f"{c['metadata']['title'][:30]}_{c['metadata']['chunk_index']}"
               for c in all_chunks]
        # Make IDs unique by adding hash
        import hashlib
        ids = [hashlib.sha256(f"{id}_{t[:50]}".encode()).hexdigest()[:16]
               for id, t in zip(ids, texts)]

        metadatas = [c["metadata"] for c in all_chunks]

        vs = VectorStore(domain_config.db_dir)
        vs.add_documents(ids, embeddings, texts, metadatas)
        logger.info(f"Vector store now has {vs.count} documents")

    # 5. Generate summaries (only if LLM is configured)
    llm_conf = domain_config.llm_config
    if llm_conf and llm_conf.get("provider") and llm_conf.get("model_name"):
        llm_config = LLMConfig.from_dict(llm_conf)
        paper_dicts = [p.to_dict() for p in unique_papers]
        summaries = summarize_papers(paper_dicts, llm_config)
        save_summaries(summaries, domain_config, today)

    # 6. Cleanup old summaries (keep 3 days)
    cleanup_old_summaries(domain_config, keep_days=3)

    logger.info(f"Daily fetch complete for {domain_config.domain_name}")


def _load_existing_papers(domain_config: DomainConfig):
    """Load previously stored papers for deduplication."""
    papers = []
    docs_dir = domain_config.docs_dir
    if not os.path.exists(docs_dir):
        return papers

    for fname in os.listdir(docs_dir):
        if fname.endswith(".json"):
            try:
                paper = Paper.load(os.path.join(docs_dir, fname))
                papers.append(paper)
            except Exception:
                continue
    return papers


def run_all_domains():
    """Run fetch for all configured domains."""
    cm = ConfigManager()
    for domain_name in cm.list_domains():
        domain_config = cm.load_domain(domain_name)
        if domain_config:
            try:
                fetch_and_process_domain(domain_config)
            except Exception as e:
                logger.error(f"Error processing {domain_name}: {e}")


def start_scheduler():
    """Start the background scheduler for daily paper fetching at 6 AM."""
    if scheduler.running:
        return

    scheduler.add_job(
        run_all_domains,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_fetch",
        name="Daily paper fetch for all domains",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily fetch at 06:00 AM")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
