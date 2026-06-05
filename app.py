"""
Research RAG — Flask Application
Main entry point with all routes for the research paper RAG system.
"""

import os
import json
import logging
import threading
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv

from config import ConfigManager, DomainConfig, LLMConfig, LLM_PROVIDERS
from llm.provider import get_ollama_models, chat_completion, configure_provider, get_model_string
from llm.summarizer import get_recent_summaries
from rag.vectorstore import VectorStore
from rag.retriever import Retriever
from processing.embedder import generate_query_embedding
from chat.session import session_manager
from scheduler import start_scheduler, fetch_and_process_domain

load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "research-rag-secret-key-change-me")

# Config manager
cm = ConfigManager()


# ── Dashboard ──────────────────────────────────────────────

@app.route("/")
def dashboard():
    domains = cm.load_all_domains()
    paper_counts = {}
    summary_counts = {}

    for d in domains:
        docs_dir = d.docs_dir
        if os.path.exists(docs_dir):
            paper_counts[d.domain_name] = len([f for f in os.listdir(docs_dir) if f.endswith(".json")])
        else:
            paper_counts[d.domain_name] = 0

        summaries = get_recent_summaries(d, days=2)
        summary_counts[d.domain_name] = sum(len(v) for v in summaries.values())

    return render_template(
        "dashboard.html",
        domains=domains,
        paper_counts=paper_counts,
        summary_counts=summary_counts,
    )


# ── Setup ──────────────────────────────────────────────────

@app.route("/setup", methods=["GET"])
def setup_page():
    return render_template("setup.html")


@app.route("/setup", methods=["POST"])
def setup_create():
    domain_name = request.form.get("domain_name", "").strip().lower().replace(" ", "-")
    keywords_raw = request.form.get("keywords", "")
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    sources = request.form.getlist("sources") or ["arxiv", "semantic_scholar", "pubmed", "openalex"]
    custom_url = request.form.get("custom_source_url", "").strip()
    start_date = request.form.get("start_date", "").strip()
    core_api_key = request.form.get("core_api_key", "").strip()

    # LLM config
    provider = request.form.get("llm_provider", "").strip()
    model_name = request.form.get("model_name", "").strip()
    api_key = request.form.get("api_key", "").strip()
    base_url = request.form.get("ollama_base_url", "http://localhost:11434").strip()

    if not domain_name or not keywords:
        flash("Domain name and keywords are required", "danger")
        return redirect(url_for("setup_page"))

    if cm.load_domain(domain_name):
        flash(f"Domain '{domain_name}' already exists", "warning")
        return redirect(url_for("setup_page"))

    llm_config = {}
    if provider and model_name:
        llm_config = LLMConfig(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url if provider == "ollama" else "",
        ).to_dict()

    config = DomainConfig(
        domain_name=domain_name,
        keywords=keywords,
        sources=sources,
        custom_source_url=custom_url,
        start_date=start_date,
        core_api_key=core_api_key,
        llm_config=llm_config,
    )

    cm.save_domain(config)
    flash(f"Domain '{domain_name}' created successfully!", "success")
    return redirect(url_for("domain_view", domain_name=domain_name))


# ── Domain View ────────────────────────────────────────────

@app.route("/domain/<domain_name>")
def domain_view(domain_name):
    domain = cm.load_domain(domain_name)
    if not domain:
        flash("Domain not found", "danger")
        return redirect(url_for("dashboard"))

    summaries = get_recent_summaries(domain, days=2)

    return render_template(
        "domain.html",
        domain=domain,
        summaries=summaries,
    )


# ── Chat Endpoint ──────────────────────────────────────────

@app.route("/domain/<domain_name>/chat", methods=["POST"])
def chat_endpoint(domain_name):
    domain = cm.load_domain(domain_name)
    if not domain:
        return jsonify({"error": "Domain not found"}), 404

    data = request.get_json()
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Check LLM config
    llm_conf = domain.llm_config
    if not llm_conf or not llm_conf.get("provider") or not llm_conf.get("model_name"):
        return jsonify({"error": "LLM not configured. Go to Settings → LLM to set up."})

    llm_config = LLMConfig.from_dict(llm_conf)

    # Get or create session
    session = session_manager.get_or_create(session_id, domain_name)

    # Build RAG context
    context = ""
    try:
        vs = VectorStore(domain.db_dir)
        if vs.count > 0:
            retriever = Retriever(vs)
            context = retriever.build_context(message, n_results=5)
    except Exception as e:
        logger.warning(f"Retrieval error: {e}")

    # Build messages
    system_msg = (
        f"You are a research assistant for the domain '{domain_name}'. "
        f"Answer questions based on the provided research paper context. "
        f"If the context doesn't contain relevant information, say: "
        f"\"I don't have reference to your query so I don't know.\"\n"
    )

    if context:
        system_msg += f"\n---\nRelevant Research Context:\n{context}\n---\n"

    messages = [{"role": "system", "content": system_msg}]

    # Add session history
    for msg in session.get_messages():
        if msg["role"] != "system":
            messages.append(msg)

    messages.append({"role": "user", "content": message})

    try:
        response = chat_completion(llm_config, messages, temperature=0.4, max_tokens=2048)

        # Save to session
        session.add_message("user", message)
        session.add_message("assistant", response)

        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": f"LLM error: {str(e)}"})


# ── LLM Setup ─────────────────────────────────────────────

@app.route("/llm-setup/<domain_name>", methods=["GET"])
def llm_setup_page(domain_name):
    domain = cm.load_domain(domain_name)
    if not domain:
        flash("Domain not found", "danger")
        return redirect(url_for("dashboard"))

    return render_template("llm_setup.html", domain=domain, providers=LLM_PROVIDERS)


@app.route("/llm-setup/<domain_name>", methods=["POST"])
def llm_setup_save(domain_name):
    domain = cm.load_domain(domain_name)
    if not domain:
        flash("Domain not found", "danger")
        return redirect(url_for("dashboard"))

    provider = request.form.get("llm_provider", "").strip()
    model_name = request.form.get("model_name", "").strip()
    api_key = request.form.get("api_key", "").strip()
    base_url = request.form.get("ollama_base_url", "http://localhost:11434").strip()

    domain.llm_config = LLMConfig(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url if provider == "ollama" else "",
    ).to_dict()

    cm.save_domain(domain)
    flash("LLM configuration saved!", "success")
    return redirect(url_for("domain_view", domain_name=domain_name))


# ── Fetch Trigger ──────────────────────────────────────────

@app.route("/fetch/<domain_name>")
def fetch_trigger(domain_name):
    domain = cm.load_domain(domain_name)
    if not domain:
        flash("Domain not found", "danger")
        return redirect(url_for("dashboard"))

    # Run in background thread
    thread = threading.Thread(
        target=fetch_and_process_domain,
        args=(domain,),
        daemon=True,
    )
    thread.start()

    flash(f"Paper fetching started for '{domain_name}'. This may take a few minutes.", "info")
    return redirect(url_for("domain_view", domain_name=domain_name))


# ── API Endpoints ──────────────────────────────────────────

@app.route("/api/ollama-models")
def api_ollama_models():
    models = get_ollama_models()
    return jsonify({"models": models})


# ── Main ───────────────────────────────────────────────────

if __name__ == "__main__":
    start_scheduler()
    app.run(host="0.0.0.0", port=5001, debug=True)
