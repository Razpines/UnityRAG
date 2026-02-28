import unity_docs_mcp.setup.unity_detect as unity_detect


def test_parse_editor_version_extracts_major_minor():
    assert unity_detect.parse_editor_version("6000.3.14f1") == "6000.3"
    assert unity_detect.parse_editor_version("Unity-2022.3.9f1") == "2022.3"
    assert unity_detect.parse_editor_version("not-a-version") is None


def test_suggest_docs_version_prefers_exact_match():
    suggested = unity_detect.suggest_docs_version(["6000.4", "6000.3"])
    assert suggested == "6000.4"


def test_suggest_docs_version_falls_back_to_same_major():
    suggested = unity_detect.suggest_docs_version(["6000.9"])
    assert suggested == "6000.5"


def test_suggest_docs_version_falls_back_to_default_when_major_missing():
    suggested = unity_detect.suggest_docs_version(["2022.3"])
    assert suggested == unity_detect.DEFAULT_DOCS_VERSION
