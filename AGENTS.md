# Repository Guidelines

This guide equips contributors to navigate, build, and extend the **MCP RAG** code-search server backed by Azure Cognitive Search & OpenAI.

---

## Project Structure & Modules
- `mcprag/` — server entry-point, runtime `Config`, orchestration logic.
- `enhanced_rag/` — indexing, retrieval, ranking, and Azure/MCP integrations (lazy-loaded).
- `tests/` — extensive pytest suite (`test_*.py`, fixtures).
- `docs/` — design notes & integration guides; CI pipelines under `.github/workflows/`.
- Root helpers: `deploy_indexer.py`, `mcp_server_wrapper.sh`, Node parser `parse_js.mjs`.

## Build / Test / Dev Loop
```bash
# install deps
pip install -r requirements.txt

# quality gates
flake8 .
mypy *.py enhanced_rag/ --ignore-missing-imports

# unit tests
pytest tests/ -v --cov=. --cov-report=term-missing

# run server
python -m mcprag       # http://localhost:8001

# docker (optional)
docker build -t mcprag:test .
docker run -p 8001:8001 --env-file .env mcprag:test
```
Node tooling: `npm ci && node parse_js.mjs` (optional AST parsing).

## Coding Style & Conventions
- Python 3.9-3.11, 4-space indents, type hints, docstrings on public APIs.
- Naming: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants.
- Import order: stdlib → third-party → local (`isort .`).
- Long lines permitted by policy but favour readability.

## Testing Guidelines
- Framework: `pytest` + `pytest-mock`; coverage threshold enforced in CI.
- Locate tests under `tests/` using `test_*.py` naming.
- Mock network/Azure calls to keep runs offline & <60 s.

## Commit & Pull Requests
- **Commits:** imperative present – `fix(server): handle empty query`.
- **PRs:** provide description, linked issues, screenshots/logs if UX changes, and update docs/tests. CI (lint, type, tests, Docker, security) must pass.

## Security & Configuration
- Secrets live in `.env` (git-ignored). Mirror new keys to `.env.example`.
- Required vars: `ACS_ENDPOINT`, `ACS_ADMIN_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`.
- Configuration layers:
  - `mcprag/config.py` — thin runtime shim; validates base env vars and forwards a subset to the pipeline.
  - `enhanced_rag/core/config.py` — Pydantic model with hundreds of tunables; env overrides or JSON via `ENHANCED_RAG_CONFIG`.
  - `enhanced_rag/azure_integration/config.py` — REST-API automation settings for index/schema tasks.
- Keyring fallback: if `ACS_ADMIN_KEY`/`AZURE_OPENAI_KEY` are absent, the server checks your OS keyring.

## Architecture Overview
`mcprag/server.py` bootstraps the server and conditionally imports **enhanced_rag** tools.
Each optional capability is guarded by a try/except with a feature flag, allowing graceful degradation when dependencies are absent.

To add a new tool:
1. Implement it under `enhanced_rag/…`.
2. Add a guarded import & flag in `mcprag/server.py`.
3. Expose config via `Config` and document any new env vars.
4. Add unit tests and update this guide.

### Tool Registration Flow
`mcprag/mcp/tools/__init__.py` aggregates category-specific helpers (`register_search_tools`, `register_generation_tools`, …).  To expose a new tool:
1. Add a sub-module under `mcprag/mcp/tools/`.
2. Provide `register_<your_tool>_tools(mcp, server)` that calls `mcp.tool` decorators.
3. Import that function in `__init__.py` so it joins the registry on server start.

### RAG Pipeline Internals (FYI)
`enhanced_rag/pipeline.py` orchestrates context extraction ➜ query enhancement ➜ multi-stage retrieval ➜ ranking ➜ response generation.  It consumes the Pydantic `Config` above and lazy-loads optional modules like vector search or learning; most contributors only interact with the public `RAGPipeline` API.

---
Need help? Ping a maintainer in `#mcprag-dev` or explore docs/ for deep dives.
