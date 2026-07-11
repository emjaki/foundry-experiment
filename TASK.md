# TASK.md — NCC Architectural Drawing Compliance (MVP)

Canonical specification for a deterministic, auditable engine that checks architectural PDF drawings against selected National Construction Code (NCC) requirements.

## Problem

Architectural compliance review relies on manual measurement of floor plans and cross-checking against NCC provisions. This lab automates **measurable geometry extraction** and **explicit rule evaluation** — AI assists classification and interpretation only; it never assigns compliance verdicts.

## MVP outcome

A user uploads an architectural drawing (PDF or raster export), selects an NCC rule pack, and receives a compliance report with:

- Extracted spaces, openings, dimensions, and building elements (with confidence)
- NCC knowledge citations for rule context
- Rule-level verdicts: `pass` | `fail` | `needs_checking`
- JSON + Markdown artifacts stored per run

## Pipeline contract

```text
upload → extract_geometry → retrieve_ncc_knowledge → evaluate_rules → render_report → persist
```

| Stage | Owner | Deterministic? |
|-------|-------|----------------|
| Upload + storage | API / Blob | Yes |
| Geometry extraction | Content Understanding custom analyzer | Bounded (confidence + schema) |
| NCC knowledge retrieval | Foundry IQ (minimal / extractive) | Mostly (no synthesis) |
| Verdicts | Python rules engine | Yes |
| Report render | Template from verdict JSON | Yes |

**Hard rule:** LLMs never emit pass/fail. Only `evaluate_rules.py` assigns verdicts.

## Verdict definitions

| Verdict | Meaning |
|---------|---------|
| `pass` | Rule assertion satisfied with sufficient evidence and confidence |
| `fail` | Rule assertion violated with sufficient evidence |
| `needs_checking` | Missing evidence, low extraction confidence, ambiguous scale, or unmeasurable geometry — fail closed |

## Inputs

- **Drawing:** PDF, PNG, JPEG, TIFF; max 20 MB (configurable)
- **Rule pack:** YAML file under `rules/packs/` (e.g. `ncc-accessibility-v1.yaml`)
- **Profile:** Lab metadata string (e.g. `default`, `class-2-residential`)

## Outputs (per `run_id`)

| Artifact | Description |
|----------|-------------|
| `input.*` | Original upload |
| `facts.json` | Structured geometry extraction |
| `knowledge_hits.json` | NCC retrieval citations |
| `verdicts.json` | Rule results |
| `report.json` / `report.md` | Combined report |

## Extracted facts schema

| Claim type | Fields | Purpose |
|------------|--------|---------|
| `space` | name, classification, area_m2, clear_width_mm, clear_height_mm | Rooms, corridors, circulation |
| `opening` | name, opening_type, width_mm, height_mm, swing_direction | Doors, windows |
| `dimension` | label, value_mm, axis, linked_element | Annotated dimensions on drawing |
| `building_element` | name, element_type, tread_depth_mm, riser_height_mm, ramp_gradient | Stairs, ramps, landings |

All claims carry `extraction_confidence` (0–1). Classification fields (`classification`, `opening_type`, `element_type`) may be AI-assisted but are inputs to deterministic rules only.

## Rule pack schema

See `rules/schema/rule-pack.schema.json`. Assertion types:

| Type | Use |
|------|-----|
| `dimension_gte` | Measured value must be ≥ threshold (e.g. corridor width) |
| `dimension_lte` | Measured value must be ≤ threshold (e.g. stair riser) |
| `dimension_between` | Value within min/max inclusive |
| `regex` | Label or classification pattern match |
| `knowledge_match` | NCC excerpt retrieval with required tokens |
| `always` | Unconditional (e.g. flag low-confidence claims) |

Settings:

- `min_extraction_confidence` (default 0.75)
- `default_verdict_on_missing_evidence: needs_checking`

## API endpoints (MVP)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/rule-packs` | List available packs |
| POST | `/reviews` | Multipart upload + run pipeline |
| GET | `/reviews/{run_id}` | Fetch report JSON |
| GET | `/reviews/{run_id}/markdown` | Fetch Markdown body |

## Mock modes (local lab)

| Env var | When true |
|---------|-----------|
| `USE_MOCK_EXTRACTION=true` | Return `tests/fixtures/sample_facts.json` |
| `USE_MOCK_KNOWLEDGE=true` | Search `samples/ncc/*.md` for canned citations |

## Non-goals (MVP)

- Full NCC corpus coverage
- LLM-as-judge compliance
- Structural engineering calculations
- Automatic drawing correction
- Batch queue processing
- BIM / IFC native parsing

## Azure components (target deployment)

- Microsoft Foundry + Content Understanding custom analyzer (`drawing-architecture-v1`)
- Foundry IQ on Azure AI Search (minimal / extractive) over NCC excerpts
- Blob Storage (uploads, knowledge, reports)
- Container Apps (API)
- Static Web Apps (UI + Entra ID)
- Key Vault (secrets)

## Phased delivery reference

| Phase | Focus |
|-------|-------|
| **MVP (this lab)** | Single upload → report; mock modes; NCC demo rule pack |
| V1 | Scale detection validation, admin rule-pack UI, drawing overlay |
| V2 | Batch queue, full NCC index, export to certification workflow |
