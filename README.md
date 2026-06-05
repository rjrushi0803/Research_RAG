# 🔬 Research RAG

**AI-powered research paper discovery, summarization, and Q&A for the research community.**

Research and technology move at a relentless pace. Staying current with the latest publications across your field is a full-time job on its own. **Research RAG** solves this by automatically fetching papers from the top open-access academic sources every day, storing them in a searchable vector database, and giving you LLM-powered summaries and a domain-specific chat interface — all running locally through a sleek Flask UI.

---

## ✨ What It Does

| Capability | Description |
|:---|:---|
| **Multi-Source Paper Fetching** | Pulls papers from **arXiv, Semantic Scholar, PubMed, OpenAlex, and CORE** — the top 5 open-access publication APIs |
| **Automated Daily Discovery** | Scheduled job fetches new papers at **6:00 AM daily** using APScheduler |
| **Smart Deduplication** | Removes duplicates via DOI exact matching and fuzzy title similarity (>90% threshold) |
| **Vector Embedding & Storage** | Chunks papers and embeds them using `sentence-transformers` into a persistent **ChromaDB** vector database |
| **LLM-Powered Summaries** | Generates structured summaries (abstract, methodology, key results) for each paper — viewable for the last 2 days, auto-cleaned after 3 |
| **RAG Chat Interface** | Ask domain-specific questions grounded in your paper collection, with session memory for multi-turn conversations |
| **Multi-Domain Support** | Configure multiple research domains — each gets its own data store, embeddings, summaries, and chat |
| **6 LLM Providers** | Unified LLM interface supporting **Ollama (local), OpenAI, Anthropic, Google Gemini, Qwen, and Mistral** |
| **Premium Dark UI** | Glassmorphism-styled Flask interface with micro-animations and responsive layout |

---

## 🖥️ System / Hardware Requirements

### Minimum Requirements

| Component | Requirement |
|:---|:---|
| **OS** | Linux, macOS, or Windows (WSL recommended) |
| **Python** | 3.11 or higher |
| **RAM** | 4 GB minimum (8 GB recommended) |
| **Disk** | 2 GB free for dependencies + space for paper data |
| **Network** | Internet connection required for fetching papers and cloud LLM APIs |

### For Local LLM (Ollama)

If you plan to run LLMs locally via Ollama, hardware requirements scale with model size:

| Model Size | RAM | VRAM (GPU) | CPU | Notes |
|:---|:---|:---|:---|:---|
| 1B–3B | 4–6 GB | 2–4 GB | 4+ cores | Runs on most machines |
| 7B | 8–10 GB | 6–8 GB | 4+ cores | Recommended minimum for quality |
| 13B | 16–20 GB | 10–16 GB | 8+ cores | Good quality, needs decent hardware |
| 30B–34B | 32–40 GB | 24–32 GB | 8+ cores | High quality, needs powerful GPU |
| 70B | 64+ GB | 48+ GB | 16+ cores | Best quality, enterprise hardware |

> **Note:** GPU is optional. Ollama can run on CPU-only machines, but inference will be significantly slower.

### For Cloud LLM Providers

If using OpenAI, Anthropic, Google, Qwen, or Mistral — no GPU needed. You only need a valid API key for your chosen provider.

---

## 📦 Installation

### Prerequisites

- **Python 3.11+** installed on your system
- **[uv](https://docs.astral.sh/uv/)** — the fast Python package manager

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/rjrushi0803/Research_RAG.git
cd Research_RAG

# 2. Create the virtual environment and install all dependencies
uv sync

# 3. (Optional) Verify the installation
uv run python -c "import flask; import chromadb; import litellm; print('All dependencies OK')"
```

That's it. `uv sync` reads the `pyproject.toml`, creates a `.venv`, installs Python 3.11 if needed, and locks all 140+ dependencies.

### Reproducing the Environment

A `requirements.txt` is included for pip-based reproducibility:

```bash
# Alternative: using pip in any virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Optional: Install Ollama (for local LLMs)

If you want to run LLMs locally instead of using cloud APIs:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (example: Llama 3.1 8B)
ollama pull llama3.1

# Verify it's running
ollama list
```

---

## ⚙️ Setup

### 1. Start the Application

```bash
uv run python app.py
```

The app starts on **http://localhost:5001** with the daily scheduler active.

### 2. Create Your First Domain

Open your browser to `http://localhost:5001` and click **"+ Create Domain"**. The 3-step setup wizard will walk you through:

#### Step 1 — Domain Information
- **Domain Name**: A short identifier (e.g., `machine-learning`, `genomics`, `quantum-computing`)
- **Keywords**: 5 comma-separated terms that define your research interest (e.g., `transformer, attention mechanism, LLM, fine-tuning, RLHF`)
- **Custom Publication URL** *(optional)*: A specific journal or source URL
- **Start Date** *(optional)*: How far back to fetch papers (default: 1 year)

#### Step 2 — Publication Sources
Select which open-access APIs to fetch from:
- ✅ **arXiv** — Preprints (CS, Physics, Math, AI)
- ✅ **Semantic Scholar** — AI-driven paper discovery
- ✅ **PubMed** — Biomedical & life sciences
- ✅ **OpenAlex** — Broad academic metadata (CC0, no key needed)
- ☐ **CORE** — Full-text open access (requires free API key from [core.ac.uk](https://core.ac.uk/services/api))

#### Step 3 — LLM Configuration
Choose your LLM provider for summaries and chat:

| Provider | What You Need |
|:---|:---|
| **Ollama (Local)** | Ollama installed + a pulled model. The app auto-detects installed models. |
| **OpenAI** | API key from [platform.openai.com](https://platform.openai.com) |
| **Anthropic** | API key from [console.anthropic.com](https://console.anthropic.com) |
| **Google Gemini** | API key from [aistudio.google.com](https://aistudio.google.com) |
| **Qwen** | API key from DashScope |
| **Mistral** | API key from [console.mistral.ai](https://console.mistral.ai) |

### 3. Trigger Initial Paper Fetch

After setup, click **"⚡ Fetch Now"** on your domain card to start the first paper ingestion. This will:
1. Query all selected sources for papers matching your keywords
2. Deduplicate results across sources
3. Save paper metadata to `./data/<domain>/docs/`
4. Chunk and embed papers into ChromaDB at `./data/<domain>/DB/`
5. Generate LLM summaries (if LLM is configured)

> The first fetch may take a few minutes depending on the number of sources and papers found.

---

## 🚀 How to Use

### Dashboard

The home page (`/`) shows all your configured domains as cards with:
- Paper count, summary count, and number of active sources
- Quick-action buttons: **Open**, **Fetch Now**, **LLM Settings**

### Paper Summaries

Inside each domain view (left panel), you'll see:
- **Today's papers** and **yesterday's papers** — each with a structured summary containing:
  - 📝 Abstract summary
  - 🔬 Methodology overview
  - 📊 Key results / contributions
- Click any paper title to open the original source
- Summaries older than 3 days are automatically removed

### RAG Chat

The right panel provides a domain-specific chat interface:

```
You: What are the latest advances in transformer architectures?
Assistant: Based on the recent papers in your collection, several key advances...

You: How does flash attention improve training efficiency?
Assistant: According to [Paper Title], flash attention reduces memory usage by...

You: exit()
[Session ended]
```

**Key behaviors:**
- Questions are answered using **RAG retrieval** from your paper database
- If no relevant papers are found, the assistant responds: *"I don't have reference to your query so I don't know."*
- **Session memory** maintains context across multiple questions
- Type **`exit()`** to end the chat session

### Automatic Daily Fetching

Once set up, the system automatically:
- ⏰ Fetches new papers at **6:00 AM daily** for all domains
- 🔄 Deduplicates against previously stored papers
- 📥 Embeds new papers into the vector database
- 📝 Generates summaries for newly fetched papers
- 🗑️ Cleans up summaries older than 3 days

### Managing Multiple Domains

You can create as many domains as needed. Each domain maintains:
- Its own keyword set and source configuration
- Separate paper storage at `./data/<domain>/docs/`
- Independent vector database at `./data/<domain>/DB/`
- Domain-specific summaries at `./data/<domain>/summaries/`
- Its own LLM configuration (you can mix providers across domains)

### Updating LLM Configuration

To change the LLM provider or model for an existing domain:
1. Click **"⚙️ LLM"** on the domain card
2. Select a new provider, enter the API key / model name
3. Click **"💾 Save Configuration"**

---

## 📄 License

This project is open source. Feel free to use, modify, and distribute.
