from __future__ import annotations

import os
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = LAB_ROOT / "rules" / "packs"
SAMPLES_DIR = LAB_ROOT / "samples"
FIXTURES_DIR = LAB_ROOT / "tests" / "fixtures"
ANALYZER_SCHEMA_PATH = (
    LAB_ROOT / "api" / "app" / "analyzers" / "drawing-architecture-v1.json"
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    artifacts_dir: Path = Path(os.getenv("ARTIFACTS_DIR", str(LAB_ROOT / "artifacts")))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    allowed_content_types: frozenset[str] = frozenset(
        {"image/png", "image/jpeg", "image/jpg", "image/tiff", "application/pdf"}
    )

    use_mock_extraction: bool = _env_bool("USE_MOCK_EXTRACTION", True)
    use_mock_knowledge: bool = _env_bool("USE_MOCK_KNOWLEDGE", True)

    cu_endpoint: str | None = os.getenv("CU_ENDPOINT")
    cu_api_key: str | None = os.getenv("CU_API_KEY")
    cu_analyzer_id: str = os.getenv("CU_ANALYZER_ID", "drawing-architecture-v1")

    search_endpoint: str | None = os.getenv("SEARCH_ENDPOINT")
    search_api_key: str | None = os.getenv("SEARCH_API_KEY")
    knowledge_base_name: str = os.getenv("KNOWLEDGE_BASE_NAME", "ncc-compliance-kb")

    default_rule_pack: str = os.getenv("DEFAULT_RULE_PACK", "ncc-accessibility-v1")
    min_extraction_confidence: float = float(
        os.getenv("MIN_EXTRACTION_CONFIDENCE", "0.75")
    )


settings = Settings()
