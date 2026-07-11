from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_CHECKING = "needs_checking"


class SpaceClaim(BaseModel):
    claim_id: str
    name: str
    classification: str | None = None
    area_m2: float | None = None
    clear_width_mm: float | None = None
    clear_height_mm: float | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class OpeningClaim(BaseModel):
    claim_id: str
    name: str
    opening_type: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    swing_direction: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class DimensionClaim(BaseModel):
    claim_id: str
    label: str
    value_mm: float
    axis: str | None = None
    linked_element: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class BuildingElementClaim(BaseModel):
    claim_id: str
    name: str
    element_type: str | None = None
    tread_depth_mm: float | None = None
    riser_height_mm: float | None = None
    ramp_gradient: float | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class ExtractedFacts(BaseModel):
    run_id: str
    drawing_title: str | None = None
    drawing_type: str | None = None
    scale: str | None = None
    extraction_confidence_threshold: float = 0.75
    spaces: list[SpaceClaim] = Field(default_factory=list)
    openings: list[OpeningClaim] = Field(default_factory=list)
    dimensions: list[DimensionClaim] = Field(default_factory=list)
    building_elements: list[BuildingElementClaim] = Field(default_factory=list)
    raw_analyzer_response: dict[str, Any] | None = None


class KnowledgeHit(BaseModel):
    claim_id: str
    query: str
    source_url: str
    chunk_id: str
    excerpt: str
    score: float = Field(ge=0.0, le=1.0)


class RuleVerdict(BaseModel):
    rule_id: str
    category: str
    severity: str
    description: str
    verdict: VerdictStatus
    reason_code: str
    ncc_clause: str | None = None
    claim_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ComplianceReport(BaseModel):
    run_id: str
    created_at: datetime
    rule_pack_id: str
    rule_pack_version: str
    profile: str
    summary: dict[str, int]
    facts: ExtractedFacts
    knowledge_hits: list[KnowledgeHit]
    verdicts: list[RuleVerdict]
    markdown: str


class ReviewStatusResponse(BaseModel):
    run_id: str
    status: str
    report: ComplianceReport | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
