from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import ExtractedFacts
from app.pipeline.evaluate_rules import evaluate_rules
from app.pipeline.render_report import render_markdown, render_report
from app.pipeline.retrieve_knowledge import _mock_knowledge_hits


@pytest.fixture
def expected_report_summary() -> dict[str, int]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "expected_report.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload["summary"]


def test_render_report_summary(sample_facts, rule_pack_id, expected_report_summary):
    facts = ExtractedFacts.model_validate(sample_facts)
    knowledge_hits = _mock_knowledge_hits(facts)
    verdicts, rule_pack = evaluate_rules(facts, knowledge_hits, rule_pack_id)

    report = render_report(
        run_id="fixture-run-001",
        rule_pack_id=rule_pack_id,
        rule_pack_version=str(rule_pack.get("version", "1.0.0")),
        profile="default",
        facts=facts,
        knowledge_hits=knowledge_hits,
        verdicts=verdicts,
    )

    assert report.summary == expected_report_summary
    assert report.summary["total"] == len(verdicts)
    assert "NCC Architectural Drawing Compliance Report" in report.markdown


def test_render_markdown_contains_verdict_table(sample_facts, rule_pack_id):
    facts = ExtractedFacts.model_validate(sample_facts)
    knowledge_hits = _mock_knowledge_hits(facts)
    verdicts, rule_pack = evaluate_rules(facts, knowledge_hits, rule_pack_id)

    markdown = render_markdown(
        run_id="fixture-run-001",
        rule_pack_id=rule_pack_id,
        rule_pack_version=str(rule_pack.get("version", "1.0.0")),
        profile="default",
        facts=facts,
        knowledge_hits=knowledge_hits,
        verdicts=verdicts,
    )

    assert "| Rule | NCC clause | Verdict | Severity | Claim | Reason |" in markdown
    assert "NCC-D3D14-001" in markdown
    assert "CORRIDOR_WIDTH_INSUFFICIENT" in markdown
