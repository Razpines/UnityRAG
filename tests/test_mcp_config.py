import json
from pathlib import Path

import pytest

from unity_docs_mcp.setup.mcp_config import install_mcp_config


def _launcher_relpath() -> Path:
    import os

    if os.name == "nt":
        return Path(".venv") / "Scripts" / "unitydocs-mcp.exe"
    return Path(".venv") / "bin" / "unitydocs-mcp"


def test_install_mcp_config_creates_new_file(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    launcher = repo_root / _launcher_relpath()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("echo hi\n", encoding="utf-8")
    cfg_path = tmp_path / "codex_mcp.json"

    target, backup = install_mcp_config(
        client="codex",
        repo_root=repo_root,
        unity_version="6000.3",
        config_path=str(cfg_path),
    )

    assert target == cfg_path
    assert backup is None
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "servers" in data
    assert "unity-docs" in data["servers"]
    assert data["servers"]["unity-docs"]["command"] == str(launcher.resolve())
    assert data["servers"]["unity-docs"]["args"] == []
    assert data["servers"]["unity-docs"]["env"]["UNITY_DOCS_MCP_UNITY_VERSION"] == "6000.3"


def test_install_mcp_config_preserves_other_servers_and_creates_backup(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    launcher = repo_root / _launcher_relpath()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("echo hi\n", encoding="utf-8")
    cfg_path = tmp_path / "claude_desktop_config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "other-server": {"command": "C:/bin/other.exe", "args": []},
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    target, backup = install_mcp_config(
        client="claude",
        repo_root=repo_root,
        unity_version="6000.4",
        config_path=str(cfg_path),
    )

    assert target == cfg_path
    assert backup is not None
    assert backup.exists()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "other-server" in data["mcpServers"]
    assert "unity-docs" in data["mcpServers"]
    assert data["mcpServers"]["unity-docs"]["command"] == str(launcher.resolve())
    assert data["mcpServers"]["unity-docs"]["env"]["UNITY_DOCS_MCP_UNITY_VERSION"] == "6000.4"


def test_install_mcp_config_rejects_invalid_root_section(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    launcher = repo_root / _launcher_relpath()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("echo hi\n", encoding="utf-8")
    cfg_path = tmp_path / "broken.json"
    cfg_path.write_text(json.dumps({"servers": []}), encoding="utf-8")

    with pytest.raises(ValueError):
        install_mcp_config(
            client="codex",
            repo_root=repo_root,
            unity_version="6000.3",
            config_path=str(cfg_path),
        )


def test_install_mcp_config_requires_unity_version(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    launcher = repo_root / _launcher_relpath()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("echo hi\n", encoding="utf-8")
    cfg_path = tmp_path / "codex_mcp.json"
    monkeypatch.delenv("UNITY_DOCS_MCP_UNITY_VERSION", raising=False)

    with pytest.raises(ValueError, match="UNITY_DOCS_MCP_UNITY_VERSION"):
        install_mcp_config(
            client="codex",
            repo_root=repo_root,
            config_path=str(cfg_path),
        )


def test_install_mcp_config_updates_codex_toml_block(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    launcher = repo_root / _launcher_relpath()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("echo hi\n", encoding="utf-8")
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        """
model = "gpt-5.3-codex"

[mcp_servers.unity-docs]
command = "C:\\\\old\\\\unitydocs-mcp.exe"
args = []
env = { UNITY_DOCS_MCP_CONFIG = "C:\\\\old\\\\config.local.yaml" }
enabled = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    target, backup = install_mcp_config(
        client="codex",
        repo_root=repo_root,
        unity_version="6000.5",
        config_path=str(cfg_path),
    )

    assert target == cfg_path
    assert backup is not None
    assert backup.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert '[mcp_servers.unity-docs]' in text
    assert 'UNITY_DOCS_MCP_UNITY_VERSION = "6000.5"' in text
    assert 'UNITY_DOCS_MCP_CONFIG' not in text


def test_install_mcp_config_appends_codex_toml_block_when_missing(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    launcher = repo_root / _launcher_relpath()
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("echo hi\n", encoding="utf-8")
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('model = "gpt-5.3-codex"\n', encoding="utf-8")

    install_mcp_config(
        client="codex",
        repo_root=repo_root,
        unity_version="6000.3",
        config_path=str(cfg_path),
    )

    text = cfg_path.read_text(encoding="utf-8")
    assert 'model = "gpt-5.3-codex"' in text
    assert '[mcp_servers.unity-docs]' in text
    assert 'UNITY_DOCS_MCP_UNITY_VERSION = "6000.3"' in text
