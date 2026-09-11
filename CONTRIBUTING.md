# Contributing

Thanks for your interest in OpenResearch. This document outlines how to
contribute smoothly.

## Getting started

1. Fork the repository and clone it.
2. Follow `README.md` → Quick Start to set up the backend and frontend.
3. Read `docs/architecture.md` for the system design and `docs/development.md`
   for the phase status and local commands.

## Development workflow

- Keep the backend fully offline-testable: `pytest` must pass without a
  network connection or a running model. Use the fakes in `backend/tests/fakes.py`.
- Redesign the progress stream (SSE) carefully — the streaming endpoint and the
  frontend progress UI depend on the event shapes in
  `app/services/progress.py`.

### Backend

```bash
cd backend && source .venv/bin/activate
ruff check app tests
ruff format --check app tests
mypy app
pytest -q
```

All four must pass before opening a PR.

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

## Code style

- Python: ruff (line length 88), type hints everywhere, no comments that state
  the obvious.
- TypeScript/React: standard ESLint + Prettier configuration shipped in the repo.

## Commit messages

Prefer short, conventional commits (e.g. `fix: correct source dedupe`,
`feat: add Tavily provider`). Keep history clean.

## Opening a pull request

- Describe what the change does and why.
- Note any manual testing you performed (and the model/version used).
- If the change touches the graph workflow, mention which state fields or
  conditional edges it affects.

## Reporting bugs

Open an issue with steps to reproduce, expected vs. actual behavior, and your
environment (OS, Python/Node versions). Include any relevant logs, removing
anything sensitive.

## Security issues

Do **not** open an issue. Follow the process in `SECURITY.md`.

## Code of conduct

All contributors are expected to follow `CODE_OF_CONDUCT.md`.