from pathlib import Path

import unity_docs_mcp.config as config_mod


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_config_merges_repo_base_and_local(monkeypatch, tmp_path: Path):
    _write(
        tmp_path / "config.yaml",
        """
unity_version: "6000.3"
paths:
  root: "data/unity/6000.3"
index:
  vector: "faiss"
""".strip()
        + "\n",
    )
    _write(
        tmp_path / "config.local.yaml",
        """
index:
  vector: "none"
""".strip()
        + "\n",
    )
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.delenv("UNITY_DOCS_MCP_CONFIG", raising=False)

    cfg = config_mod.load_config()
    assert cfg.unity_version == "6000.3"
    assert cfg.paths.root == "data/unity/6000.3"
    assert cfg.index.vector == "none"


def test_load_config_env_override_applies_after_local(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "unity_version: \"6000.3\"\n")
    _write(tmp_path / "config.local.yaml", "unity_version: \"6000.4\"\n")
    env_cfg = tmp_path / "env.yaml"
    _write(env_cfg, "unity_version: \"6000.5\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_CONFIG", str(env_cfg))

    cfg = config_mod.load_config()
    assert cfg.unity_version == "6000.5"


def test_load_config_explicit_path_has_highest_precedence(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "unity_version: \"6000.3\"\n")
    env_cfg = tmp_path / "env.yaml"
    explicit_cfg = tmp_path / "explicit.yaml"
    _write(env_cfg, "unity_version: \"6000.4\"\n")
    _write(explicit_cfg, "unity_version: \"6000.0\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_CONFIG", str(env_cfg))

    cfg = config_mod.load_config(explicit_cfg)
    assert cfg.unity_version == "6000.0"


def test_load_config_uses_unity_docs_mcp_root_for_base_layers(monkeypatch, tmp_path: Path):
    _write(
        tmp_path / "config.yaml",
        """
paths:
  root: "data/unity/from-root-override"
index:
  vector: "none"
""".strip()
        + "\n",
    )
    monkeypatch.setenv("UNITY_DOCS_MCP_ROOT", str(tmp_path))
    monkeypatch.delenv("UNITY_DOCS_MCP_CONFIG", raising=False)

    cfg = config_mod.load_config()
    assert cfg.paths.root == "data/unity/from-root-override"
    assert cfg.index.vector == "none"
