from __future__ import annotations

import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import RULES_DIR, settings
from app.models import ComplianceReport, ReviewStatusResponse
from app.pipeline.orchestrator import run_review_pipeline

app = FastAPI(
    title="NCC Architectural Drawing Compliance API",
    version="0.1.0",
    description="Deterministic pipeline for NCC architectural drawing compliance reviews",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_upload(file: UploadFile, content: bytes) -> None:
    if not file.content_type or file.content_type not in settings.allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported content type. Allowed: "
                + ", ".join(sorted(settings.allowed_content_types))
            ),
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds max size of {settings.max_upload_bytes} bytes",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty upload")


def _load_report(run_id: str) -> ComplianceReport | None:
    report_path = settings.artifacts_dir / run_id / "report.json"
    if not report_path.exists():
        return None
    return ComplianceReport.model_validate_json(report_path.read_text(encoding="utf-8"))


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "NCC Architectural Drawing Compliance API",
        "docs": "/docs",
        "health": "/health",
        "web_ui": "http://localhost:5173",
        "note": "The upload UI runs separately on port 5173 (cd web && npm start).",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/rule-packs")
async def list_rule_packs() -> dict[str, list[str]]:
    packs = sorted(path.stem for path in RULES_DIR.glob("*.yaml"))
    return {"rule_packs": packs}


@app.post("/reviews", response_model=ReviewStatusResponse)
async def create_review(
    file: UploadFile = File(...),
    rule_pack: str = Form(default=settings.default_rule_pack),
    profile: str = Form(default="default"),
    notes: str | None = Form(default=None),
) -> ReviewStatusResponse:
    content = await file.read()
    _validate_upload(file, content)

    run_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    try:
        report = await run_review_pipeline(
            drawing_path=temp_path,
            rule_pack_id=rule_pack,
            profile=profile,
            run_id=run_id,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    if notes:
        notes_path = settings.artifacts_dir / run_id / "notes.txt"
        notes_path.write_text(notes, encoding="utf-8")

    return ReviewStatusResponse(run_id=run_id, status="completed", report=report)


@app.get("/reviews/{run_id}", response_model=ReviewStatusResponse)
async def get_review(run_id: str) -> ReviewStatusResponse:
    if not run_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run_id")

    report = _load_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewStatusResponse(run_id=run_id, status="completed", report=report)


@app.get("/reviews/{run_id}/markdown")
async def get_review_markdown(run_id: str) -> JSONResponse:
    markdown_path = settings.artifacts_dir / run_id / "report.md"
    if not markdown_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return JSONResponse({"markdown": markdown_path.read_text(encoding="utf-8")})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
