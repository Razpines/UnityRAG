from pathlib import Path

from unity_docs_mcp.bake.extract_manual import extract_manual
from unity_docs_mcp.bake.extract_scriptref import extract_scriptref
from unity_docs_mcp.bake.html_to_md import HtmlToTextOptions


def test_manual_extraction_smoke():
    sample = Path("data/unity/6000.3/raw/UnityDocumentation/Documentation/en/Manual/index.html")
    assert sample.exists(), "Manual index missing; ensure Unity docs present"
    res = extract_manual(sample, HtmlToTextOptions(), drop_sections_list=[])
    assert len(res["text_md"]) > 200


def test_scriptref_extraction_smoke():
    sample = Path(
        "data/unity/6000.3/raw/UnityDocumentation/Documentation/en/ScriptReference/Unity.Jobs.IJobParallelFor.html"
    )
    assert sample.exists(), "ScriptReference sample missing; ensure Unity docs present"
    res = extract_scriptref(sample, HtmlToTextOptions())
    assert "IJobParallelFor" in res["title"]
    assert len(res["text_md"]) > 200
