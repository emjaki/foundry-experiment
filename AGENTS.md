# Agent instructions

Read `TASK.md` before implementing or changing this lab. It is the canonical spec.

## Repo role

Greenfield MVP for **NCC architectural drawing compliance checking**. Parses PDF/raster drawings, extracts measurable geometry, and evaluates explicit NCC rules deterministically.

## Implementation rules

- **Deterministic rules engine** — YAML rules evaluate facts JSON; no LLM verdicts
- **Fail closed** — use `needs_checking` when evidence or confidence is insufficient
- **Mock modes** — `USE_MOCK_EXTRACTION` and `USE_MOCK_KNOWLEDGE` must keep the lab runnable offline
- **Evidence-backed output** — verdicts cite rule IDs, reason codes, and NCC chunk references
- **No secrets in repo** — `.env.example` only; Key Vault / app settings in Azure
- **AI boundary** — Content Understanding and retrieval may classify or interpret; `evaluate_rules.py` alone assigns pass/fail

## Conventions

- Python 3.11+ under `api/`; minimal dependencies listed in `pyproject.toml`
- FastAPI for the API tier; vanilla static web UI under `web/`
- Bicep under `infra/` — storage, container app, static web app modules
- Tests under `tests/` with golden fixtures in `tests/fixtures/`

## When editing

- Match existing naming and layout
- Keep changes focused on the MVP lab scope
- Update `TASK.md` if the pipeline contract changes
