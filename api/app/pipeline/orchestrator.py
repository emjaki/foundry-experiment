from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.config import settings
from app.models import ComplianceReport, ExtractedFacts, KnowledgeHit, RuleVerdict
from app.pipeline.evaluate_rules import evaluate_rules
from app.pipeline.extract_facts import extract_facts
from app.pipeline.render_report import render_report
from app.pipeline.retrieve_knowledge import retrieve_knowledge


async def run_review_pipeline(
    drawing_path: Path,
    rule_pack_id: str,
    profile: str = "default",
    run_id: str | None = None,
) -> ComplianceReport:
    resolved_run_id = run_id or str(uuid.uuid4())

    facts = await extract_facts(drawing_path, run_id=resolved_run_id)
    knowledge_hits = await retrieve_knowledge(facts)
    verdicts, rule_pack = evaluate_rules(facts, knowledge_hits, rule_pack_id)

    report = render_report(
        run_id=resolved_run_id,
        rule_pack_id=rule_pack_id,
        rule_pack_version=str(rule_pack.get("version", "0.0.0")),
        profile=profile,
        facts=facts,
        knowledge_hits=knowledge_hits,
        verdicts=verdicts,
    )

    _persist_artifacts(resolved_run_id, drawing_path, facts, knowledge_hits, verdicts, report)
    return report


def _persist_artifacts(
    run_id: str,
    drawing_path: Path,
    facts: ExtractedFacts,
    knowledge_hits: list[KnowledgeHit],
    verdicts: list[RuleVerdict],
    report: ComplianceReport,
) -> None:
    run_dir = settings.artifacts_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if drawing_path.exists():
        target = run_dir / f"input{drawing_path.suffix or '.bin'}"
        target.write_bytes(drawing_path.read_bytes())

    (run_dir / "facts.json").write_text(
        facts.model_dump_json(indent=2), encoding="utf-8"
    )
    (run_dir / "knowledge_hits.json").write_text(
        json.dumps([hit.model_dump() for hit in knowledge_hits], indent=2),
        encoding="utf-8",
    )
    (run_dir / "verdicts.json").write_text(
        json.dumps([verdict.model_dump() for verdict in verdicts], indent=2),
        encoding="utf-8",
    )
    (run_dir / "report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    (run_dir / "report.md").write_text(report.markdown, encoding="utf-8")
