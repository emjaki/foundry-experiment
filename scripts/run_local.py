#!/usr/bin/env python3
"""Run the NCC compliance pipeline locally without starting the API server."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[1]
API_DIR = LAB_ROOT / "api"
sys.path.insert(0, str(API_DIR))

from app.pipeline.orchestrator import run_review_pipeline  # noqa: E402


async def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Run NCC architectural drawing compliance pipeline locally"
    )
    parser.add_argument(
        "--drawing",
        type=Path,
        default=LAB_ROOT / "samples" / "placeholder.pdf",
        help="Path to architectural drawing (mock mode ignores content)",
    )
    parser.add_argument(
        "--rule-pack",
        default="ncc-accessibility-v1",
        help="Rule pack id (filename stem under rules/packs/)",
    )
    parser.add_argument("--profile", default="default")
    parser.add_argument(
        "--output",
        type=Path,
        default=LAB_ROOT / "artifacts" / "local-run",
        help="Directory to write report artifacts",
    )
    args = parser.parse_args()

    if not args.drawing.exists():
        args.drawing.parent.mkdir(parents=True, exist_ok=True)
        args.drawing.write_bytes(b"%PDF-1.4\n% mock drawing for local pipeline\n")

    report = await run_review_pipeline(
        drawing_path=args.drawing,
        rule_pack_id=args.rule_pack,
        profile=args.profile,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (args.output / "report.md").write_text(report.markdown, encoding="utf-8")

    print(json.dumps(report.summary, indent=2))
    print(f"Report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
