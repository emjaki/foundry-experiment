from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.config import FIXTURES_DIR, settings
from app.models import (
    BuildingElementClaim,
    DimensionClaim,
    ExtractedFacts,
    OpeningClaim,
    SpaceClaim,
)


def _load_mock_facts(run_id: str) -> ExtractedFacts:
    fixture_path = FIXTURES_DIR / "sample_facts.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["run_id"] = run_id
    return ExtractedFacts.model_validate(payload)


def _normalize_space(raw: dict[str, Any], index: int) -> SpaceClaim:
    return SpaceClaim(
        claim_id=raw.get("claim_id") or f"spc-{index:03d}",
        name=str(raw.get("name") or raw.get("label") or "unknown"),
        classification=raw.get("classification") or raw.get("type"),
        area_m2=_float_or_none(raw.get("area_m2") or raw.get("area")),
        clear_width_mm=_float_or_none(raw.get("clear_width_mm") or raw.get("width_mm")),
        clear_height_mm=_float_or_none(raw.get("clear_height_mm") or raw.get("height_mm")),
        extraction_confidence=float(raw.get("extraction_confidence", 0.0)),
    )


def _normalize_opening(raw: dict[str, Any], index: int) -> OpeningClaim:
    return OpeningClaim(
        claim_id=raw.get("claim_id") or f"opn-{index:03d}",
        name=str(raw.get("name") or raw.get("label") or "unknown"),
        opening_type=raw.get("opening_type") or raw.get("type"),
        width_mm=_float_or_none(raw.get("width_mm") or raw.get("width")),
        height_mm=_float_or_none(raw.get("height_mm") or raw.get("height")),
        swing_direction=raw.get("swing_direction"),
        extraction_confidence=float(raw.get("extraction_confidence", 0.0)),
    )


def _normalize_dimension(raw: dict[str, Any], index: int) -> DimensionClaim:
    return DimensionClaim(
        claim_id=raw.get("claim_id") or f"dim-{index:03d}",
        label=str(raw.get("label") or raw.get("name") or "unknown"),
        value_mm=float(raw.get("value_mm") or raw.get("value") or 0.0),
        axis=raw.get("axis"),
        linked_element=raw.get("linked_element"),
        extraction_confidence=float(raw.get("extraction_confidence", 0.0)),
    )


def _normalize_building_element(raw: dict[str, Any], index: int) -> BuildingElementClaim:
    return BuildingElementClaim(
        claim_id=raw.get("claim_id") or f"elm-{index:03d}",
        name=str(raw.get("name") or raw.get("label") or "unknown"),
        element_type=raw.get("element_type") or raw.get("type"),
        tread_depth_mm=_float_or_none(raw.get("tread_depth_mm")),
        riser_height_mm=_float_or_none(raw.get("riser_height_mm")),
        ramp_gradient=_float_or_none(raw.get("ramp_gradient")),
        extraction_confidence=float(raw.get("extraction_confidence", 0.0)),
    )


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_analyzer_result(run_id: str, payload: dict[str, Any]) -> ExtractedFacts:
    fields = payload.get("result", {}).get("contents", [{}])[0].get("fields", {})
    if not fields and "fields" in payload:
        fields = payload["fields"]

    def field_value(name: str) -> Any:
        node = fields.get(name, {})
        if isinstance(node, dict):
            return node.get("value") or node.get("content") or node.get("values")
        return node

    def field_confidence(name: str, default: float = 0.0) -> float:
        node = fields.get(name, {})
        if isinstance(node, dict) and node.get("confidence") is not None:
            return float(node["confidence"])
        return default

    spaces_raw = field_value("spaces") or []
    openings_raw = field_value("openings") or []
    dimensions_raw = field_value("dimensions") or []
    elements_raw = field_value("building_elements") or []

    spaces = [
        _normalize_space(item, idx)
        for idx, item in enumerate(spaces_raw, start=1)
        if isinstance(item, dict)
    ]
    openings = [
        _normalize_opening(item, idx)
        for idx, item in enumerate(openings_raw, start=1)
        if isinstance(item, dict)
    ]
    dimensions = [
        _normalize_dimension(item, idx)
        for idx, item in enumerate(dimensions_raw, start=1)
        if isinstance(item, dict)
    ]
    building_elements = [
        _normalize_building_element(item, idx)
        for idx, item in enumerate(elements_raw, start=1)
        if isinstance(item, dict)
    ]

    overall_confidence = max(
        [
            field_confidence("spaces"),
            field_confidence("openings"),
            field_confidence("dimensions"),
            0.0,
        ]
    )

    all_claims = spaces + openings + dimensions + building_elements
    for claim in all_claims:
        if claim.extraction_confidence == 0.0 and overall_confidence > 0:
            claim.extraction_confidence = overall_confidence

    def _title(field_name: str) -> str | None:
        node = fields.get(field_name, {})
        if isinstance(node, dict):
            return node.get("value") or node.get("content")
        if isinstance(node, str):
            return node
        return None

    return ExtractedFacts(
        run_id=run_id,
        drawing_title=_title("drawing_title"),
        drawing_type=_title("drawing_type"),
        scale=_title("scale"),
        extraction_confidence_threshold=settings.min_extraction_confidence,
        spaces=spaces,
        openings=openings,
        dimensions=dimensions,
        building_elements=building_elements,
        raw_analyzer_response=payload,
    )


async def _call_content_understanding(drawing_path: Path, run_id: str) -> ExtractedFacts:
    if not settings.cu_endpoint or not settings.cu_api_key:
        raise RuntimeError(
            "CU_ENDPOINT and CU_API_KEY are required when USE_MOCK_EXTRACTION=false"
        )

    analyze_url = (
        f"{settings.cu_endpoint.rstrip('/')}/contentunderstanding/analyzers/"
        f"{settings.cu_analyzer_id}:analyze"
        f"?api-version=2025-05-01-preview"
    )

    headers = {
        "Ocp-Apim-Subscription-Key": settings.cu_api_key,
        "x-ms-useragent": "foundry-experiment/0.1.0",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        with drawing_path.open("rb") as drawing_file:
            response = await client.post(
                analyze_url,
                headers={**headers, "Content-Type": "application/octet-stream"},
                content=drawing_file.read(),
            )
        response.raise_for_status()
        operation_location = response.headers.get("operation-location")
        if not operation_location:
            payload = response.json()
            return _parse_analyzer_result(run_id, payload)

        for _ in range(60):
            poll = await client.get(operation_location, headers=headers)
            poll.raise_for_status()
            payload = poll.json()
            status = payload.get("status", "").lower()
            if status == "succeeded":
                return _parse_analyzer_result(run_id, payload)
            if status == "failed":
                raise RuntimeError(
                    f"Content Understanding analyze failed: {payload.get('error')}"
                )

    raise TimeoutError("Content Understanding analyze operation timed out")


async def extract_facts(drawing_path: Path, run_id: str | None = None) -> ExtractedFacts:
    """Extract measurable geometry from an architectural drawing."""
    resolved_run_id = run_id or str(uuid.uuid4())

    if settings.use_mock_extraction:
        return _load_mock_facts(resolved_run_id)

    return await _call_content_understanding(drawing_path, resolved_run_id)
