# OpenResearch Deployment

## Local development (no Docker)

Requirements: Python 3.11+, Node.js 20+, a Hugging Face account with an
inference provider enabled (free tier available via Groq / SambaNova).

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Set your HF token in .env (see .env.example)
#    You must also enable an inference provider at:
#    https://huggingface.co/settings/inference-providers

# 3. Frontend
cd frontend
npm install
npm run dev                            # http://localhost:5173
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend.

## Docker Compose

```bash
cp .env.example .env   # fill in HF_TOKEN and select HF model
docker compose up --build
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
- `LLM_PROVIDER` defaults to `hf`. You must enable an inference provider under
  [HF settings → Inference providers](https://huggingface.co/settings/inference-providers)
  for hosted generation to work (free tiers: Groq, SambaNova). If you deploy your
  own vLLM/TGI endpoint (self-hosted from HF weights), set `HF_BASE_URL` and the
  model stays fully Hugging Face.

## Deploy on a standard Linux VPS (Docker)

Works on any Ubuntu/Debian VPS (Hetzner, Oracle Cloud free tier, DigitalOcean, etc.).

```bash
# 1. Install Docker + compose plugin, then clone the repo
git clone https://github.com/mustafaabdullahai-dev/openresearch-langgraph.git
cd openresearch-langgraph

# 2. Configure with your HF token (never commit this file)
cp .env.example .env
vi .env        # set HF_TOKEN=..., LLM_PROVIDER=hf

# 3. Build and start (frontend :5173, backend :8000)
docker compose up --build -d
docker compose ps                 # both services healthy/running

# 4. Verify
curl http://localhost:8000/api/health          # -> {"status":"ok"}
curl http://localhost:5173                     # -> frontend HTML

# 5. (Optional) reverse proxy for TLS
#    Put Caddy/nginx in front of :5173 and :8000; add both public origins
#    to CORS_ORIGINS in .env and restart.
```

SQLite + Chroma persist on the host under `./data/` (bind-mounted). Upgrades:
`git pull && docker compose up --build -d`. Roll back with
`docker compose down && docker compose up --build -d`.

## Production notes

- Run behind a TLS-terminating proxy (nginx/Caddy) that forwards headers
  `X-Forwarded-Proto` / `X-Forwarded-For` (the FastAPI app does not add origin
  auth — put any auth in front of the API).
- Ensure the web UI and API are served from origins listed in `CORS_ORIGINS`.
- Keep `.env` out of version control; it is gitignored.
- If exposing over the internet, shift from the `duckduckgo` default or rate
  limit as needed, and review `docs/architecture.md` + `SECURITY.md`.