# NCC Architectural Drawing Compliance

Deterministic, auditable engine for checking architectural PDF drawings against selected **National Construction Code (NCC)** requirements.

The system parses architectural drawings, extracts measurable geometry, and evaluates explicit NCC rules. AI is used only for classification or interpretation — it **never** assigns compliance verdicts.

## What this lab demonstrates

1. Upload an architectural drawing (PDF, PNG, JPEG, TIFF)
2. Extract spaces, openings, dimensions, and building elements via Content Understanding (mock mode included)
3. Retrieve NCC knowledge excerpts via Foundry IQ / AI Search (mock mode included)
4. Evaluate deterministic NCC compliance rules (YAML → Python engine)
5. Render JSON + Markdown report with evidence and citations
6. Simple web UI for upload and report viewing

## Prerequisites

- Python 3.11+
- Node.js 18+ (optional, for serving the static web UI locally)

## Quick start (offline)

One-time setup (from the repo root):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Terminal 1 — API** (backend on port 8000):

```bash
source .venv/bin/activate
cd api
PYTHONPATH=. uvicorn main:app --reload --port 8000
```

**Terminal 2 — Web UI** (upload form on port 5173):

```bash
python3 scripts/serve_web.py
```

Or, if you have Node.js installed:

```bash
cd web
npm start
```

Open **http://localhost:5173** (not port 8000). The API at http://localhost:8000 serves JSON only; use `/docs` or `/health` there.

Optional CLI run (no server):

```bash
source .venv/bin/activate
python scripts/run_local.py
```

With `USE_MOCK_EXTRACTION=true` (default), the pipeline returns fixture geometry so no Azure credentials are required.

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_MOCK_EXTRACTION` | `true` | Use fixture facts instead of Content Understanding |
| `USE_MOCK_KNOWLEDGE` | `true` | Use local `samples/ncc/` instead of Foundry IQ |
| `MAX_UPLOAD_BYTES` | `20971520` | Upload size limit (20 MB) |
| `DEFAULT_RULE_PACK` | `ncc-accessibility-v1` | Default NCC rule pack |

## Tests

```bash
source .venv/bin/activate
PYTHONPATH=api pytest
```

## Project layout

| Path | Purpose |
|------|---------|
| `api/` | FastAPI orchestrator and pipeline stages |
| `rules/` | NCC YAML rule packs and JSON schema |
| `web/` | Static Web App UI |
| `infra/` | Bicep modules for Azure deployment |
| `samples/ncc/` | Demo NCC knowledge-base excerpts |
| `scripts/` | Local runner and knowledge seed stub |
| `tests/` | Deterministic rules and report tests |

## Canonical spec

See `TASK.md` for scope, verdict definitions, and pipeline contract.

## Security notes

- No secrets in the repository — use `.env` locally and Key Vault in Azure
- Upload validation: content-type allowlist and max size enforced in the API
- Fail-closed verdicts when extraction confidence or measurable evidence is insufficient
