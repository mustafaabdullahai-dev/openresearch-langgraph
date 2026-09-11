# OpenResearch

**An open-source multi-agent AI research assistant built with LangGraph and local LLMs.**

OpenResearch takes a research question, plans the investigation, searches the web,
collects and analyzes sources, fact-checks claims, iterates on gaps, and produces a
structured, cited report — orchestrated entirely by a LangGraph state machine running
on an open-weight model (Ollama + Qwen3). No OpenAI or Anthropic keys required.

---

## Features

- **Multi-agent architecture** — query analyzer, research planner, search agent,
  source analyzer, fact checker, research critic, report writer, and reviewer.
- **Iterative research loop** — the graph evaluates evidence coverage and re-searches
  until a satisfactory answer is reached (bounded by `MAX_RESEARCH_ITERATIONS`).
- **LangGraph orchestration** — typed state, conditional edges, checkpointing, and
  error recovery.
- **Free-first by design** — local LLMs via Ollama, DuckDuckGo search by default, and
  optional pluggable providers (e.g. Tavily) that never gate core functionality.
- **Citation-first reporting** — every factual claim maps back to a collected source.
- **RAG-ready** — document upload, chunking, embeddings, and vector search (ChromaDB).
- **FastAPI backend** — typed schemas, streaming progress, health endpoint, SQLite
  persistence (PostgreSQL-ready).
- **Modern frontend** — React + TypeScript + Tailwind, dark/light mode, live research
  progress, and a graph visualization of the workflow.

## Architecture

```mermaid
flowchart TD
    User[User] --> FE[React Frontend]
    FE --> API[FastAPI API]
    API --> LG[LangGraph Orchestrator]
    LG --> QA[Query Analyzer]
    LG --> RP[Research Planner]
    LG --> RA[Researcher]
    LG --> SA[Source Analyzer]
    LG --> FC[Fact Checker]
    LG --> RC[Research Critic]
    LG --> RW[Report Writer]
    RA --> SP[Search Provider]
    RP --> SP
    SP --> SR[Source Processor]
    SR --> Chroma[(ChromaDB)]
    LG --> O[Ollama]
    O --> M[Qwen3 / configurable model]
```

## Tech Stack

| Layer      | Technology                                              |
| ---------- | ------------------------------------------------------- |
| Orchestration | LangGraph, LangChain                                |
| Backend    | Python, FastAPI, SQLAlchemy, SQLite                      |
| LLM        | Ollama + Qwen3 (open weights, local)                     |
| Search     | DuckDuckGo (default), Tavily (optional)                  |
| Storage    | SQLite, ChromaDB                                         |
| Frontend   | React, TypeScript, Tailwind CSS, Vite                    |
| Ops        | Docker, GitHub Actions, Ruff, MyPy, Pytest               |

## Quick Start

Requirements: **Python 3.11+**, **Node.js 20+**, **Docker** (optional), **Git**, **Ollama**.

```bash
git clone <repository-url>
cd openresearch-langgraph

# 1. Install the local model
ollama pull qwen3:8b
ollama serve
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Copy `.env.example` to `.env` and adjust values as needed.

### Docker Compose

```bash
cp .env.example .env
docker compose up --build          # frontend:5173, backend:8000
# optional containerized LLM: docker compose --profile ollama up --build
```

See [`docs/deployment.md`](docs/deployment.md) for details.

## Project Status

All 23 phases complete. See [`docs/development.md`](docs/development.md).

- [x] Phase 1 — Project initialization (repo, backend & frontend skeletons, config)
- [x] Phase 2 — Ollama + model provider integration
- [x] Phases 3–17 — LangGraph workflow, agents, API, frontend, RAG
- [x] Phases 18–23 — Tests, Docker, CI/CD, documentation, deployment

## Contributing & Security

- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md) — report vulnerabilities privately

## License

[MIT](LICENSE)