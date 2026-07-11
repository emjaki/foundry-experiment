from __future__ import annotations

import pytest

from app.models import ExtractedFacts
from app.pipeline.evaluate_rules import evaluate_rules
from app.pipeline.retrieve_knowledge import _mock_knowledge_hits


@pytest.mark.parametrize(
    "rule_id, claim_id, expected_verdict, expected_reason",
    [
        ("NCC-D3D14-001", "spc-001", "pass", "CORRIDOR_WIDTH_COMPLIANT"),
        ("NCC-D3D14-001", "spc-002", "fail", "CORRIDOR_WIDTH_INSUFFICIENT"),
        ("NCC-D2D12-001", "opn-001", "pass", "DOOR_WIDTH_COMPLIANT"),
        ("NCC-D2D12-001", "opn-002", "fail", "DOOR_WIDTH_INSUFFICIENT"),
        ("NCC-D3D3-001", "elm-001", "pass", "STAIR_RISER_COMPLIANT"),
        ("NCC-D3D3-001", "elm-002", "fail", "STAIR_RISER_EXCEEDS_MAX"),
        ("NCC-D3D3-002", "elm-002", "fail", "STAIR_TREAD_INSUFFICIENT"),
        ("NCC-EXT-001", "spc-004", "needs_checking", "LOW_EXTRACTION_CONFIDENCE"),
    ],
)
def test_evaluate_rules_expected_verdicts(
    sample_facts,
    rule_pack_id,
    rule_id,
    claim_id,
    expected_verdict,
    expected_reason,
):
    facts = ExtractedFacts.model_validate(sample_facts)
    knowledge_hits = _mock_knowledge_hits(facts)
    verdicts, _ = evaluate_rules(facts, knowledge_hits, rule_pack_id)

    matched = [
        verdict
        for verdict in verdicts
        if verdict.rule_id == rule_id and verdict.claim_id == claim_id
    ]
    assert matched, f"No verdict for {rule_id} / {claim_id}"
    verdict = matched[0]
    assert verdict.verdict.value == expected_verdict
    assert verdict.reason_code == expected_reason


def test_evaluate_rules_is_deterministic(sample_facts, rule_pack_id):
    facts = ExtractedFacts.model_validate(sample_facts)
    knowledge_hits = _mock_knowledge_hits(facts)

    first, _ = evaluate_rules(facts, knowledge_hits, rule_pack_id)
    second, _ = evaluate_rules(facts, knowledge_hits, rule_pack_id)

    first_payload = [verdict.model_dump() for verdict in first]
    second_payload = [verdict.model_dump() for verdict in second]
    assert first_payload == second_payload


def test_corridor_knowledge_citation_found(sample_facts, rule_pack_id):
    facts = ExtractedFacts.model_validate(sample_facts)
    knowledge_hits = _mock_knowledge_hits(facts)
    verdicts, _ = evaluate_rules(facts, knowledge_hits, rule_pack_id)

    corridor_kb = [
        verdict
        for verdict in verdicts
        if verdict.rule_id == "NCC-KB-001" and verdict.claim_id == "spc-001"
    ]
    assert corridor_kb
    assert corridor_kb[0].verdict.value == "pass"
    assert corridor_kb[0].reason_code == "NCC_CITATION_FOUND"
