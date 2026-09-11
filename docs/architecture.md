# Architecture

> _Living document — updated as the system evolves through its phases._

## Overview

OpenResearch is a monorepo split into a FastAPI backend (LangGraph research workflow)
and a React frontend. Intelligence is provided by Hugging Face hosted inference (no
local model required), with a hash-based embedding fallback for non-semantic retrieval.

## Backend structure

```
backend/app/
├── api/          → FastAPI routers
├── agents/       → specialized agents + prompt templates
├── graph/        → LangGraph state, nodes, edges, workflow builder
├── models/       → SQLAlchemy ORM models
├── schemas/      → Pydantic request/response schemas
├── services/     → search, source processing, vector store, LLM provider registry
├── tools/        → tool wrappers usable by agents
├── database/     → engine/session management
├── config/       → settings (env-based)
└── main.py       → FastAPI app assembly
```

## Layers

1. **API layer** — HTTP interface, validation, streaming (SSE), error mapping.
2. **Orchestration layer** — LangGraph graph with typed `ResearchState`, nodes that
   each mutate a slice of state, conditional edges that drive the iterative loop.
3. **Agent layer** — stateless workers: a single node may delegate to multiple agents.
4. **Provider layer** — abstractions so LLM, search, embeddings, and vector storage
are swappable (HF hosted → self-hosted vLLM/TGI, DuckDuckGo → Tavily, ChromaDB → another
vector DB).

## Data flow

`User → React → FastAPI → LangGraph (planner → researcher → analyzer → checker →
critic → writer → reviewer) → report + citations → frontend`.

See [langgraph.md](langgraph.md) for the graph itself.