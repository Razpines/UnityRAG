import json
from pathlib import Path

import unity_docs_mcp.doctor as doctor
from unity_docs_mcp.config import Config


def _isolate_config_root(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text("index:\n  vector: \"none\"\n", encoding="utf-8")
    monkeypatch.setenv("UNITY_DOCS_MCP_ROOT", str(tmp_path))
    monkeypatch.delenv("UNITY_DOCS_MCP_CONFIG", raising=False)


def test_doctor_report_has_stable_shape(monkeypatch, tmp_path: Path):
    _isolate_config_root(monkeypatch, tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_PORT", "0")
    report = doctor.run_doctor()
    assert set(report.keys()) == {"generated_at", "overall", "counts", "checks"}
    assert set(report["counts"].keys()) == {"pass", "warn", "fail"}
    assert report["overall"] in {"pass", "warn", "fail"}
    check_ids = {c["id"] for c in report["checks"]}
    assert check_ids == {
        "config_source",
        "paths",
        "dependencies",
        "embedder_device",
        "mcp_port",
        "artifacts",
    }
    assert all(c["status"] in {"pass", "warn", "fail"} for c in report["checks"])


def test_doctor_exit_nonzero_on_blocking_failure(monkeypatch, tmp_path: Path):
    _isolate_config_root(monkeypatch, tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_PORT", "0")
    original = doctor._check_dependencies
    monkeypatch.setattr(
        doctor,
        "_check_dependencies",
        lambda _cfg: doctor.CheckResult(
            id="dependencies",
            status="fail",
            message="forced failure",
            details={},
        ),
    )
    report = doctor.run_doctor()
    assert report["counts"]["fail"] >= 1
    assert doctor.exit_code_from_report(report) == 1
    monkeypatch.setattr(doctor, "_check_dependencies", original)


def test_doctor_main_json_output(monkeypatch, capsys, tmp_path: Path):
    _isolate_config_root(monkeypatch, tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_PORT", "0")
    code = doctor.main(json_output=True)
    captured = capsys.readouterr().out
    parsed = json.loads(captured)
    assert isinstance(parsed, dict)
    assert "checks" in parsed
    assert code in {0, 1}


def test_doctor_skips_vector_dependencies_in_fts_only_mode(monkeypatch):
    cfg = Config()
    cfg.index.vector = "none"
    result = doctor._check_dependencies(cfg)
    assert result.status == "pass"
    assert "FTS-only mode" in result.message
