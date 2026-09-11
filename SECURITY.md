# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities. Instead,
report them privately to the maintainers by email. You should receive a reply
within 48 hours with the next steps.

Please include:

- Affected version(s)
- A description of the vulnerability and its impact
- Steps to reproduce
- Any proof-of-concept

We follow coordinated disclosure: please give us time to fix and release a
patch before publishing details.

## Scope

This project is a **local, single-user research assistant**. It is designed to
run on your own machine or a trusted private network; it is **not** a
multi-tenant web service. If you expose it beyond your trusted network, review
the notes below and add your own authentication/rate limiting in front of it.

## Security posture

### Inputs / SSRF

- Source fetching validates every URL against private address spaces
  (loopback, link-local, RFC 1918) and cloud metadata ranges before connecting
  — see `app/services/sources/processor.py`.
- Uploads accept only a small allowlist of extensions (txt, md, pdf, docx) with
  a strict size limit (`app/services/security.py`).
- API request bodies are length-limited via pydantic `Field(max_length=...)`.

### Secrets

- No API keys are committed. Keys live in `.env`, which is gitignored.
- The default search provider (DuckDuckGo) requires no key.
- No secrets are logged. Do not add logging of request bodies or headers.

### CORS

- Allowed origins are configured via `CORS_ORIGINS` (comma-separated).
- Wildcard origins are not allowed together with credentialed requests.

### Dependency hygiene

- CI runs `ruff`, `mypy`, and `pytest` on every push/PR.
- Pin or lock dependencies for reproducible production builds (see the
  backend `requirements.txt` / frontend `package-lock.json`).

## Local model trust

The LLM runs locally via Ollama. Prompts and fetched web content are passed to
the model — treat the model's output as unverified. Reports always surface
their sources so claims can be checked. Web content is treated as untrusted
data (not as instructions).