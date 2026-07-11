from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

LAB_ROOT = Path(__file__).resolve().parents[1]
API_DIR = LAB_ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture
def sample_facts() -> dict:
    fixture_path = LAB_ROOT / "tests" / "fixtures" / "sample_facts.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture
def rule_pack_id() -> str:
    return "ncc-accessibility-v1"
