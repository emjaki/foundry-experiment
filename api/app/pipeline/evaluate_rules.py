from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from app.config import RULES_DIR
from app.models import ExtractedFacts, KnowledgeHit, RuleVerdict, VerdictStatus


@dataclass
class ClaimContext:
    claim_type: str
    claim_id: str
    payload: dict[str, Any]


def load_rule_pack(rule_pack_id: str) -> dict[str, Any]:
    path = RULES_DIR / f"{rule_pack_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Rule pack not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _iter_claims(facts: ExtractedFacts) -> list[ClaimContext]:
    claims: list[ClaimContext] = []
    for space in facts.spaces:
        claims.append(
            ClaimContext(
                claim_type="space",
                claim_id=space.claim_id,
                payload=space.model_dump(),
            )
        )
    for opening in facts.openings:
        claims.append(
            ClaimContext(
                claim_type="opening",
                claim_id=opening.claim_id,
                payload=opening.model_dump(),
            )
        )
    for dimension in facts.dimensions:
        claims.append(
            ClaimContext(
                claim_type="dimension",
                claim_id=dimension.claim_id,
                payload=dimension.model_dump(),
            )
        )
    for element in facts.building_elements:
        claims.append(
            ClaimContext(
                claim_type="building_element",
                claim_id=element.claim_id,
                payload=element.model_dump(),
            )
        )
    return claims


def _resolve_field(payload: dict[str, Any], field_path: str) -> Any:
    current: Any = payload
    for part in field_path.split("."):
        if part == "attributes" and isinstance(current, dict):
            continue
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _match_when_clause(when: dict[str, Any], claim: ClaimContext) -> bool:
    if not when:
        return True

    for key, expected in when.items():
        if key == "claim_type":
            if claim.claim_type != expected:
                return False
            continue

        if key.startswith("claim."):
            field_path = key.removeprefix("claim.")
            actual = _resolve_field(claim.payload, field_path)
            if isinstance(expected, dict):
                if "lt" in expected and not (
                    isinstance(actual, (int, float)) and actual < expected["lt"]
                ):
                    return False
                if "lte" in expected and not (
                    isinstance(actual, (int, float)) and actual <= expected["lte"]
                ):
                    return False
                if "gt" in expected and not (
                    isinstance(actual, (int, float)) and actual > expected["gt"]
                ):
                    return False
                if "gte" in expected and not (
                    isinstance(actual, (int, float)) and actual >= expected["gte"]
                ):
                    return False
                if "in" in expected and actual not in expected["in"]:
                    return False
            elif actual != expected:
                return False
            continue

        if key.startswith("claim.attributes."):
            attribute = key.removeprefix("claim.attributes.")
            actual = claim.payload.get(attribute)
            if isinstance(expected, dict) and "in" in expected:
                if actual not in expected["in"]:
                    return False
            elif actual != expected:
                return False
            continue

    return True


def _evaluate_assertion(
    assertion: dict[str, Any],
    claim: ClaimContext,
    facts: ExtractedFacts,
    knowledge_hits: list[KnowledgeHit],
    settings: dict[str, Any],
) -> tuple[bool, list[str], dict[str, Any]]:
    assert_type = assertion.get("type")
    evidence_refs: list[str] = []
    details: dict[str, Any] = {"assert_type": assert_type}

    if assert_type == "always":
        return True, evidence_refs, details

    if assert_type == "regex":
        field = assertion.get("field", "name")
        pattern = assertion.get("pattern")
        if not pattern:
            return False, evidence_refs, {**details, "error": "missing_pattern"}

        value = _resolve_field(claim.payload, field)
        if value is None:
            return False, evidence_refs, {**details, "missing_field": field}

        matched = bool(re.match(pattern, str(value)))
        details["field"] = field
        details["value"] = value
        details["pattern"] = pattern
        return matched, evidence_refs, details

    if assert_type in {"dimension_gte", "dimension_lte", "dimension_between"}:
        field = assertion.get("field")
        if not field:
            return False, evidence_refs, {**details, "error": "missing_field"}

        value = _resolve_field(claim.payload, field)
        if value is None:
            return False, evidence_refs, {**details, "missing_field": field, "unmeasurable": True}

        if not isinstance(value, (int, float)):
            return False, evidence_refs, {**details, "invalid_value": value}

        details["field"] = field
        details["measured_mm"] = value

        if assert_type == "dimension_gte":
            threshold = float(assertion.get("value", 0))
            details["required_min_mm"] = threshold
            return value >= threshold, evidence_refs, details

        if assert_type == "dimension_lte":
            threshold = float(assertion.get("value", 0))
            details["required_max_mm"] = threshold
            return value <= threshold, evidence_refs, details

        min_val = float(assertion.get("min", 0))
        max_val = float(assertion.get("max", 0))
        details["required_min_mm"] = min_val
        details["required_max_mm"] = max_val
        return min_val <= value <= max_val, evidence_refs, details

    if assert_type == "knowledge_match":
        query_template = assertion.get("query_template", "")
        query = query_template.format(**claim.payload)
        min_score = float(assertion.get("min_score", 0.0))
        must_contain = [item.lower() for item in assertion.get("must_contain", [])]

        claim_hits = [hit for hit in knowledge_hits if hit.claim_id == claim.claim_id]
        if not claim_hits:
            details["query"] = query
            return False, evidence_refs, details

        for hit in claim_hits:
            evidence_refs.append(hit.chunk_id)
            excerpt_lower = hit.excerpt.lower()
            contains_all = all(token in excerpt_lower for token in must_contain)
            if hit.score >= min_score and contains_all:
                details["query"] = query
                details["matched_hit"] = hit.chunk_id
                details["score"] = hit.score
                return True, evidence_refs, details

        details["query"] = query
        details["best_score"] = max(hit.score for hit in claim_hits)
        return False, evidence_refs, details

    return False, evidence_refs, {**details, "error": f"unsupported_assert_type:{assert_type}"}


def _resolve_verdict(
    rule: dict[str, Any],
    passed: bool,
    settings: dict[str, Any],
) -> tuple[VerdictStatus, str]:
    branch = rule.get("on_pass" if passed else "on_fail") or {}
    verdict_raw = branch.get("verdict")
    reason_code = branch.get("reason_code", "UNSPECIFIED")

    if verdict_raw:
        return VerdictStatus(verdict_raw), reason_code

    default_verdict = settings.get("default_verdict_on_missing_evidence", "needs_checking")
    if passed:
        return VerdictStatus.PASS, reason_code
    return VerdictStatus(default_verdict), reason_code


def evaluate_rules(
    facts: ExtractedFacts,
    knowledge_hits: list[KnowledgeHit],
    rule_pack_id: str,
) -> tuple[list[RuleVerdict], dict[str, Any]]:
    """Evaluate NCC YAML rules deterministically against extracted geometry."""
    rule_pack = load_rule_pack(rule_pack_id)
    pack_settings = rule_pack.get("settings", {})
    min_confidence = float(
        pack_settings.get(
            "min_extraction_confidence",
            facts.extraction_confidence_threshold,
        )
    )

    verdicts: list[RuleVerdict] = []
    claims = _iter_claims(facts)
    rules = sorted(rule_pack.get("rules", []), key=lambda item: item.get("id", ""))

    for rule in rules:
        when = rule.get("when", {})
        assertion = rule.get("assert", {})
        ncc_clause = rule.get("ncc_clause")
        matched_claims = [claim for claim in claims if _match_when_clause(when, claim)]

        if not matched_claims:
            default_verdict = pack_settings.get(
                "default_verdict_on_missing_evidence", "needs_checking"
            )
            verdicts.append(
                RuleVerdict(
                    rule_id=rule["id"],
                    category=rule.get("category", "general"),
                    severity=rule.get("severity", "info"),
                    description=rule.get("description", ""),
                    verdict=VerdictStatus(default_verdict),
                    reason_code="NO_MATCHING_CLAIMS",
                    ncc_clause=ncc_clause,
                    details={"when": when},
                )
            )
            continue

        for claim in matched_claims:
            confidence = claim.payload.get("extraction_confidence")
            if (
                confidence is not None
                and isinstance(confidence, (int, float))
                and confidence < min_confidence
                and assertion.get("type") != "always"
            ):
                verdicts.append(
                    RuleVerdict(
                        rule_id=rule["id"],
                        category=rule.get("category", "general"),
                        severity=rule.get("severity", "info"),
                        description=rule.get("description", ""),
                        verdict=VerdictStatus.NEEDS_CHECKING,
                        reason_code="LOW_EXTRACTION_CONFIDENCE",
                        ncc_clause=ncc_clause,
                        claim_id=claim.claim_id,
                        details={"confidence": confidence, "threshold": min_confidence},
                    )
                )
                continue

            passed, evidence_refs, details = _evaluate_assertion(
                assertion, claim, facts, knowledge_hits, pack_settings
            )

            if details.get("unmeasurable") and assertion.get("type", "").startswith("dimension"):
                verdicts.append(
                    RuleVerdict(
                        rule_id=rule["id"],
                        category=rule.get("category", "general"),
                        severity=rule.get("severity", "info"),
                        description=rule.get("description", ""),
                        verdict=VerdictStatus.NEEDS_CHECKING,
                        reason_code="UNMEASURABLE_GEOMETRY",
                        ncc_clause=ncc_clause,
                        claim_id=claim.claim_id,
                        evidence_refs=evidence_refs,
                        details=details,
                    )
                )
                continue

            verdict, reason_code = _resolve_verdict(rule, passed, pack_settings)

            verdicts.append(
                RuleVerdict(
                    rule_id=rule["id"],
                    category=rule.get("category", "general"),
                    severity=rule.get("severity", "info"),
                    description=rule.get("description", ""),
                    verdict=verdict,
                    reason_code=reason_code,
                    ncc_clause=ncc_clause,
                    claim_id=claim.claim_id,
                    evidence_refs=evidence_refs,
                    details=details,
                )
            )

    return verdicts, rule_pack
