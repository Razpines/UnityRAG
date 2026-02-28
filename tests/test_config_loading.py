from pathlib import Path

import pytest

import unity_docs_mcp.config as config_mod


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_config_merges_repo_base_and_local(monkeypatch, tmp_path: Path):
    _write(
        tmp_path / "config.yaml",
        """
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
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.3")

    cfg = config_mod.load_config()
    assert cfg.unity_version == "6000.3"
    assert cfg.paths.root == "data/unity/6000.3"
    assert cfg.index.vector == "none"


def test_load_config_derives_url_and_paths_from_env(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "index:\n  vector: \"none\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.5")

    cfg = config_mod.load_config()
    assert cfg.unity_version == "6000.5"
    assert cfg.download_url.endswith("/6000.5/UnityDocumentation.zip")
    assert cfg.paths.root == "data/unity/6000.5"
    assert cfg.paths.raw_zip == "data/unity/6000.5/raw/UnityDocumentation.zip"
    assert cfg.paths.raw_unzipped == "data/unity/6000.5/raw/UnityDocumentation"
    assert cfg.paths.baked_dir == "data/unity/6000.5/baked"
    assert cfg.paths.index_dir == "data/unity/6000.5/index"


def test_load_config_requires_unity_version_env(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "index:\n  vector: \"none\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.delenv("UNITY_DOCS_MCP_UNITY_VERSION", raising=False)

    with pytest.raises(ValueError, match="UNITY_DOCS_MCP_UNITY_VERSION"):
        config_mod.load_config()


def test_load_config_rejects_legacy_version_keys(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "unity_version: \"6000.3\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.3")

    with pytest.raises(ValueError, match="Unsupported config keys"):
        config_mod.load_config()


def test_load_config_env_override_applies_after_local(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "index:\n  vector: \"faiss\"\n")
    _write(tmp_path / "config.local.yaml", "index:\n  vector: \"none\"\n")
    env_cfg = tmp_path / "env.yaml"
    _write(env_cfg, "index:\n  vector: \"faiss\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_CONFIG", str(env_cfg))

    cfg = config_mod.load_config()
    assert cfg.index.vector == "faiss"


def test_load_config_explicit_path_has_highest_precedence(monkeypatch, tmp_path: Path):
    _write(tmp_path / "config.yaml", "index:\n  vector: \"faiss\"\n")
    env_cfg = tmp_path / "env.yaml"
    explicit_cfg = tmp_path / "explicit.yaml"
    _write(env_cfg, "index:\n  vector: \"none\"\n")
    _write(explicit_cfg, "index:\n  vector: \"faiss\"\n")
    monkeypatch.setattr(config_mod, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("UNITY_DOCS_MCP_CONFIG", str(env_cfg))

    cfg = config_mod.load_config(explicit_cfg)
    assert cfg.index.vector == "faiss"


def test_load_config_uses_unity_docs_mcp_root_for_base_layers(monkeypatch, tmp_path: Path):
    _write(
        tmp_path / "config.yaml",
        """
index:
  vector: "none"
""".strip()
        + "\n",
    )
    monkeypatch.setenv("UNITY_DOCS_MCP_ROOT", str(tmp_path))
    monkeypatch.delenv("UNITY_DOCS_MCP_CONFIG", raising=False)
    monkeypatch.setenv("UNITY_DOCS_MCP_UNITY_VERSION", "6000.4")

    cfg = config_mod.load_config()
    assert cfg.paths.root == "data/unity/6000.4"
    assert cfg.index.vector == "none"
