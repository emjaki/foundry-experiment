from __future__ import annotations

from collections import Counter

from app.models import ComplianceReport, ExtractedFacts, KnowledgeHit, RuleVerdict, utc_now


def _summary_counts(verdicts: list[RuleVerdict]) -> dict[str, int]:
    counts = Counter(verdict.verdict.value for verdict in verdicts)
    return {
        "pass": counts.get("pass", 0),
        "fail": counts.get("fail", 0),
        "needs_checking": counts.get("needs_checking", 0),
        "total": len(verdicts),
    }


def render_markdown(
    run_id: str,
    rule_pack_id: str,
    rule_pack_version: str,
    profile: str,
    facts: ExtractedFacts,
    knowledge_hits: list[KnowledgeHit],
    verdicts: list[RuleVerdict],
) -> str:
    summary = _summary_counts(verdicts)
    lines = [
        "# NCC Architectural Drawing Compliance Report",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Rule pack:** `{rule_pack_id}` v{rule_pack_version}",
        f"- **Profile:** `{profile}`",
        f"- **Drawing:** {facts.drawing_title or 'Unknown'}",
        f"- **Drawing type:** {facts.drawing_type or 'Unknown'}",
        f"- **Scale:** {facts.scale or 'Not detected'}",
        "",
        "## Summary",
        "",
        f"- Pass: **{summary['pass']}**",
        f"- Fail: **{summary['fail']}**",
        f"- Needs checking: **{summary['needs_checking']}**",
        "",
        "## Verdicts",
        "",
        "| Rule | NCC clause | Verdict | Severity | Claim | Reason |",
        "|------|------------|---------|----------|-------|--------|",
    ]

    for verdict in verdicts:
        lines.append(
            "| {rule_id} | {ncc_clause} | {verdict} | {severity} | {claim_id} | {reason_code} |".format(
                rule_id=verdict.rule_id,
                ncc_clause=verdict.ncc_clause or "-",
                verdict=verdict.verdict.value,
                severity=verdict.severity,
                claim_id=verdict.claim_id or "-",
                reason_code=verdict.reason_code,
            )
        )

    lines.extend(["", "## NCC citations", ""])
    if not knowledge_hits:
        lines.append("_No NCC knowledge hits returned._")
    else:
        for hit in knowledge_hits:
            lines.append(
                f"- `{hit.claim_id}` → {hit.source_url} (score {hit.score:.2f}): {hit.excerpt}"
            )

    lines.extend(["", "## Extracted spaces", ""])
    for space in facts.spaces:
        width = (
            f"{space.clear_width_mm:.0f} mm"
            if space.clear_width_mm is not None
            else "unmeasured"
        )
        lines.append(
            f"- `{space.claim_id}` **{space.name}** "
            f"({space.classification or 'unclassified'}, width {width}, "
            f"confidence {space.extraction_confidence:.2f})"
        )

    lines.extend(["", "## Extracted openings", ""])
    for opening in facts.openings:
        width = (
            f"{opening.width_mm:.0f} mm"
            if opening.width_mm is not None
            else "unmeasured"
        )
        lines.append(
            f"- `{opening.claim_id}` **{opening.name}** "
            f"({opening.opening_type or 'unknown'}, width {width}, "
            f"confidence {opening.extraction_confidence:.2f})"
        )

    lines.extend(["", "## Building elements", ""])
    if not facts.building_elements:
        lines.append("_No building elements extracted._")
    else:
        for element in facts.building_elements:
            lines.append(
                f"- `{element.claim_id}` **{element.name}** "
                f"({element.element_type or 'unknown'}, "
                f"confidence {element.extraction_confidence:.2f})"
            )

    return "\n".join(lines) + "\n"


def render_report(
    run_id: str,
    rule_pack_id: str,
    rule_pack_version: str,
    profile: str,
    facts: ExtractedFacts,
    knowledge_hits: list[KnowledgeHit],
    verdicts: list[RuleVerdict],
) -> ComplianceReport:
    markdown = render_markdown(
        run_id,
        rule_pack_id,
        rule_pack_version,
        profile,
        facts,
        knowledge_hits,
        verdicts,
    )
    return ComplianceReport(
        run_id=run_id,
        created_at=utc_now(),
        rule_pack_id=rule_pack_id,
        rule_pack_version=rule_pack_version,
        profile=profile,
        summary=_summary_counts(verdicts),
        facts=facts,
        knowledge_hits=knowledge_hits,
        verdicts=verdicts,
        markdown=markdown,
    )
