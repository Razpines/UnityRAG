import json
from pathlib import Path

import unity_docs_mcp.setup.diagnostics as setup_diag


def test_write_setup_snapshot_writes_timestamp_and_latest(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(setup_diag, "_detect_unity_installs", lambda: [{"version": "6000.3", "path": "~/Unity"}])
    monkeypatch.setattr(setup_diag, "_nvidia_smi_summary", lambda: {"available": False})
    monkeypatch.setattr(setup_diag, "_torch_summary", lambda: {"available": True, "cuda_available": False})

    stamped, latest = setup_diag.write_setup_snapshot(
        repo_root=tmp_path,
        status="failed",
        mode="cpu",
        unity_version="6000.3",
        config_path=str(tmp_path / "config.local.yaml"),
        outcome="setup-test-failed",
    )

    assert stamped.exists()
    assert latest.exists()
    assert stamped.name.startswith("setup-diagnostics-")
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["setup_mode"] == "cpu"
    assert payload["selected_unity_docs_version"] == "6000.3"
