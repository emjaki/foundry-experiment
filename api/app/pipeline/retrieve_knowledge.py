from __future__ import annotations

import re
from pathlib import Path

import httpx

from app.config import SAMPLES_DIR, settings
from app.models import ExtractedFacts, KnowledgeHit


def _load_ncc_corpus() -> list[tuple[str, str, str]]:
    ncc_dir = SAMPLES_DIR / "ncc"
    corpus: list[tuple[str, str, str]] = []
    if not ncc_dir.exists():
        return corpus

    for path in sorted(ncc_dir.glob("*.md")):
        if path.name.upper() == "README.MD" or path.stem.lower() == "readme":
            continue
        text = path.read_text(encoding="utf-8")
        corpus.append((path.name, f"file://samples/ncc/{path.name}", text))
    return corpus


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "intro"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.removeprefix("## ").strip().lower()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections


def _best_excerpt(query: str, text: str, max_len: int = 280) -> str:
    """Pick the section or paragraph most relevant to the query."""
    sections = _split_sections(text)
    if sections:
        best_title, best_body = max(
            sections,
            key=lambda item: _score_excerpt(query, f"{item[0]} {item[1]}"),
        )
        if best_body:
            return best_body[:max_len]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return text.strip()[:max_len]

    return max(paragraphs, key=lambda p: _score_excerpt(query, p))[:max_len]


def _tokens_overlap(query_tokens: set[str], excerpt_tokens: set[str]) -> int:
    overlap = 0
    for query_token in query_tokens:
        if query_token in excerpt_tokens:
            overlap += 1
            continue
        if any(
            excerpt_token.startswith(query_token)
            or query_token.startswith(excerpt_token)
            or query_token.rstrip("s") == excerpt_token.rstrip("s")
            for excerpt_token in excerpt_tokens
        ):
            overlap += 1
    return overlap


def _score_excerpt(query: str, excerpt: str) -> float:
    stopwords = {"ncc", "requirement", "for", "minimum", "requirements", "the", "a", "an"}
    query_tokens = {
        token
        for token in re.findall(r"[a-z0-9-]+", query.lower())
        if token and token not in stopwords
    }
    excerpt_tokens = {
        token for token in re.findall(r"[a-z0-9-]+", excerpt.lower()) if token
    }
    if not query_tokens:
        return 0.0
    overlap = _tokens_overlap(query_tokens, excerpt_tokens)
    return min(1.0, overlap / len(query_tokens))


def _build_queries(facts: ExtractedFacts) -> list[tuple[str, str]]:
    """Return (claim_id, query) pairs for NCC retrieval."""
    queries: list[tuple[str, str]] = []

    for space in facts.spaces:
        classification = space.classification or "space"
        queries.append(
            (space.claim_id, f"NCC requirement for {classification}: {space.name}")
        )

    for opening in facts.openings:
        opening_type = opening.opening_type or "opening"
        queries.append(
            (opening.claim_id, f"NCC minimum dimensions for {opening_type}: {opening.name}")
        )

    for element in facts.building_elements:
        element_type = element.element_type or "element"
        queries.append(
            (element.claim_id, f"NCC {element_type} requirements: {element.name}")
        )

    return queries


def _mock_knowledge_hits(facts: ExtractedFacts) -> list[KnowledgeHit]:
    corpus = _load_ncc_corpus()
    hits: list[KnowledgeHit] = []

    for claim_id, query in _build_queries(facts):
        best_score = 0.0
        best_match: tuple[str, str, str] | None = None

        for filename, source_url, text in corpus:
            score = _score_excerpt(query, text)
            if score > best_score:
                best_score = score
                best_match = (filename, source_url, text)

        if best_match is None:
            continue

        _, source_url, text = best_match
        excerpt = _best_excerpt(query, text)
        section_score = _score_excerpt(query, excerpt)
        hits.append(
            KnowledgeHit(
                claim_id=claim_id,
                query=query,
                source_url=source_url,
                chunk_id=f"{best_match[0]}#L1",
                excerpt=excerpt,
                score=max(section_score, 0.85 if "ncc_ref:" in excerpt.lower() else 0.4),
            )
        )

    return hits


async def _call_foundry_iq(facts: ExtractedFacts) -> list[KnowledgeHit]:
    if not settings.search_endpoint or not settings.search_api_key:
        raise RuntimeError(
            "SEARCH_ENDPOINT and SEARCH_API_KEY are required when USE_MOCK_KNOWLEDGE=false"
        )

    hits: list[KnowledgeHit] = []
    search_url = (
        f"{settings.search_endpoint.rstrip('/')}/knowledgebases/"
        f"{settings.knowledge_base_name}/retrieve"
        f"?api-version=2025-11-01-preview"
    )
    headers = {
        "api-key": settings.search_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for claim_id, query in _build_queries(facts):
            body = {
                "messages": [{"role": "user", "content": query}],
                "retrievalReasoningEffort": "minimal",
                "outputMode": "extractive",
            }
            response = await client.post(search_url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

            for idx, reference in enumerate(payload.get("references", []), start=1):
                hits.append(
                    KnowledgeHit(
                        claim_id=claim_id,
                        query=query,
                        source_url=str(reference.get("source_url") or reference.get("url")),
                        chunk_id=str(reference.get("chunk_id") or f"chunk-{idx}"),
                        excerpt=str(reference.get("content") or reference.get("excerpt") or ""),
                        score=float(reference.get("score") or 0.0),
                    )
                )

    return hits


async def retrieve_knowledge(facts: ExtractedFacts) -> list[KnowledgeHit]:
    """Retrieve NCC knowledge hits for extracted geometry claims."""
    if settings.use_mock_knowledge:
        return _mock_knowledge_hits(facts)

    return await _call_foundry_iq(facts)
