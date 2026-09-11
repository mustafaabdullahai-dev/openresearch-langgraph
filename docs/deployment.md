# OpenResearch Deployment

## Local development (no Docker)

Requirements: Python 3.11+, Node.js 20+, Ollama.

```bash
# 1. Models
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000/docs

# 3. Frontend
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend.

## Docker Compose

```bash
cp .env.example .env

# Ollama on the host (default)
docker compose up --build

# Ollama in a container
docker compose --profile ollama up --build
# then set OLLAMA_BASE_URL=http://ollama:11434 in .env and restart
```

- Frontend: http://localhost:5173 (nginx serves the build and proxies `/api` to
  the backend; `proxy_buffering off` keeps SSE streaming working).
- Backend API docs: http://localhost:8000/docs
- Data (SQLite DB + Chroma) persists in `./data/` on the host.

## Environment variables

See `.env.example`. Key notes:

- `SEARCH_PROVIDER=duckduckgo` works with no key. `tavily` requires
  `TAVILY_API_KEY`.
- Set `CORS_ORIGINS` to the browser origin(s) that will call the API
  (comma-separated). Wildcard is not used with credentialed requests.
- `DATABASE_URL` and `VECTOR_DB_PATH` are relative to the backend working
  directory; in Docker these point at `/app/data`.

## Production notes

- Run behind a TLS-terminating proxy (nginx/Caddy) that forwards headers
  `X-Forwarded-Proto` / `X-Forwarded-For` (the FastAPI app does not add origin
  auth — put any auth in front of the API).
- Ensure the web UI and API are served from origins listed in `CORS_ORIGINS`.
- Keep `.env` out of version control; it is gitignored.
- If exposing over the internet, shift from the `duckduckgo` default or rate
  limit as needed, and review `docs/architecture.md` + `SECURITY.md`.