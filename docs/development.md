# Development

## Phase progress

| Phase | Status |
| ----- | ------ |
| 1 · Project initialization | ✅ Done |
| 2 · LLM provider integration | ✅ Done |
| 3 · LangGraph state + base graph | ✅ Done |
| 4 · Query Analyzer | ✅ Done |
| 5 · Research Planner | ✅ Done |
| 6 · Search providers | ✅ Done |
| 7 · Source processing | ✅ Done |
| 8 · Fact checker | ✅ Done |
| 9 · Research critic | ✅ Done |
| 10 · Iterative loop | ✅ Done |
| 11 · Report generator | ✅ Done |
| 12 · Report reviewer | ✅ Done |
| 13 · Persistence/checkpointing | ✅ Done |
| 14 · FastAPI research endpoints | ✅ Done |
| 15 · React frontend | ✅ Done |
| 16 · Streaming/progress UI | ✅ Done |
| 17 · RAG / document upload | ✅ Done |
| 18 · Tests | ✅ Done |
| 19 · Docker | ✅ Done |
| 20 · GitHub Actions | ✅ Done |
| 21 · Security hardening | ✅ Done |
| 22 · README & docs | ✅ Done |
| 23 · Deployment preparation | ✅ Done |

## Local commands

### Backend

```bash
cd backend && source .venv/bin/activate
ruff check app tests
ruff format --check app tests
mypy app
pytest -q
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
npm run dev                     # http://localhost:5173
```

## Test isolation

Environment is redirected at import time in `tests/conftest.py` so tests never
touch real data:

- `DATABASE_URL` → a temp SQLite file
- `VECTOR_DB_PATH` → a temp chroma directory
- `LLM_PROVIDER` → `hf` (Hugging Face hosted inference)
- `HF_TOKEN` → empty string so any accidental live call fails fast

The graph tests run fully offline against fakes (`tests/fakes.py`). No test
requires a network connection or a running model.