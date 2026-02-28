import json
from pathlib import Path

from unity_docs_mcp.report import generate_report


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_generate_report_writes_bundle_and_prefilled_issue_url(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "index:\n  vector: \"none\"\n")
    _write(tmp_path / "config.local.yaml", "auth_token: \"super-secret\"\n")
    _write(tmp_path / "setup.log", "authorization=abc123\nnormal line\n")
    monkeypatch.setenv("UNITY_DOCS_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("UNITY_DOCS_MCP_PORT", "0")
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.3")

    result = generate_report(summary="setup failed", prefill_issue=True)

    report_dir = Path(result["report_dir"])
    assert report_dir.exists()
    assert (report_dir / "report.json").exists()
    assert (report_dir / "doctor_report.json").exists()
    assert (report_dir / "effective_config.json").exists()
    assert "issues/new?" in (result["issue_url"] or "")

    redacted_cfg = (report_dir / "config_layers" / "config.local.yaml.redacted.yaml").read_text(
        encoding="utf-8"
    )
    assert "<redacted>" in redacted_cfg

    copied_log = (report_dir / "logs" / "setup.log").read_text(encoding="utf-8")
    assert "authorization=<redacted>" in copied_log


def test_generate_report_survives_invalid_config(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "unity_version: \"6000.3\"\n")
    monkeypatch.setenv("UNITY_DOCS_MCP_ROOT", str(tmp_path))
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.3")
    monkeypatch.setenv("UNITY_DOCS_MCP_PORT", "0")

    result = generate_report(summary="bad config")
    report_dir = Path(result["report_dir"])
    effective = json.loads((report_dir / "effective_config.json").read_text(encoding="utf-8"))
    doctor = json.loads((report_dir / "doctor_report.json").read_text(encoding="utf-8"))

    assert "error" in effective
    assert "Unsupported config keys" in effective["error"]
    assert "error" in doctor
