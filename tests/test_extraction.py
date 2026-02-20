import os
from pathlib import Path

import pytest

from unity_docs_mcp.bake.extract_manual import extract_manual
from unity_docs_mcp.bake.extract_scriptref import extract_scriptref
from unity_docs_mcp.bake.html_to_md import HtmlToTextOptions

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REAL_DOCS_ROOT = Path("data/unity/6000.3/raw/UnityDocumentation/Documentation/en")
ENABLE_E2E = os.environ.get("UNITYDOCS_E2E") == "1"


def test_manual_extraction_smoke():
    sample = FIXTURES_DIR / "manual_index.html"
    assert sample.exists(), "Fixture missing"
    res = extract_manual(sample, HtmlToTextOptions(), drop_sections_list=[])
    assert "Create and run a job" in res["title"]
    assert len(res["text_md"]) > 200


def test_scriptref_extraction_smoke():
    sample = FIXTURES_DIR / "scriptref_iJobParallelFor.html"
    assert sample.exists(), "Fixture missing"
    res = extract_scriptref(sample, HtmlToTextOptions())
    assert "IJobParallelFor" in res["title"]
    assert len(res["text_md"]) > 200


@pytest.mark.skipif(not ENABLE_E2E, reason="set UNITYDOCS_E2E=1 to run real-doc integration tests")
def test_manual_extraction_real_docs():
    sample = REAL_DOCS_ROOT / "Manual/index.html"
    if not sample.exists():
        pytest.skip("Manual docs not present under data/unity/6000.3/raw")
    res = extract_manual(sample, HtmlToTextOptions(), drop_sections_list=[])
    assert len(res["text_md"]) > 200


@pytest.mark.skipif(not ENABLE_E2E, reason="set UNITYDOCS_E2E=1 to run real-doc integration tests")
def test_scriptref_extraction_real_docs():
    sample = REAL_DOCS_ROOT / "ScriptReference/Unity.Jobs.IJobParallelFor.html"
    if not sample.exists():
        pytest.skip("ScriptReference docs not present under data/unity/6000.3/raw")
    res = extract_scriptref(sample, HtmlToTextOptions())
    assert "IJobParallelFor" in res["title"]
    assert len(res["text_md"]) > 200
