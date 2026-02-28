import pytest


@pytest.fixture(autouse=True)
def _default_unity_version_env(monkeypatch):
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.3")
