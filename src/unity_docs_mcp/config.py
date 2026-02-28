from __future__ import annotations

import os
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

UNITY_VERSION_ENV = "UNITY_DOCS_MCP_UNITY_VERSION"
_LEGACY_VERSION_KEYS = ("unity_version", "download_url", "paths")


@dataclass
class PathsConfig:
    root: str
    raw_zip: str
    raw_unzipped: str
    baked_dir: str
    index_dir: str


@dataclass
class BakeConfig:
    keep_images: bool = False
    include_figure_captions: bool = True
    drop_sections: list[str] = field(default_factory=lambda: ["Additional resources"])
    min_page_chars: int = 400


@dataclass
class ChunkConfig:
    strategy: str = "heading"
    max_chars: int = 6000
    overlap_chars: int = 300


@dataclass
class EmbedderConfig:
    provider: str = "local"
    model: str = "BAAI/bge-small-en-v1.5"
    device: str = "auto"  # auto|cpu|cuda


@dataclass
class IndexConfig:
    lexical: str = "sqlite_fts5"
    vector: str = "faiss"
    embedder: EmbedderConfig = field(default_factory=EmbedderConfig)
    rerank_enable: bool = True
    candidate_pool: int = 80


@dataclass
class MCPConfig:
    max_results_default: int = 6
    snippet_chars: int = 900
    min_score: float = 0.15
    open_max_chars: int = 12000


def _require_unity_version() -> str:
    unity_version = os.environ.get(UNITY_VERSION_ENV, "").strip()
    if unity_version:
        return unity_version
    raise ValueError(
        f"Missing required environment variable {UNITY_VERSION_ENV}. "
        "Set it to a Unity docs version (for example: 6000.3)."
    )


def _download_url_for_version(version: str) -> str:
    return f"https://cloudmedia-docs.unity3d.com/docscloudstorage/en/{version}/UnityDocumentation.zip"


def _paths_for_version(version: str) -> PathsConfig:
    base = f"data/unity/{version}"
    return PathsConfig(
        root=base,
        raw_zip=f"{base}/raw/UnityDocumentation.zip",
        raw_unzipped=f"{base}/raw/UnityDocumentation",
        baked_dir=f"{base}/baked",
        index_dir=f"{base}/index",
    )


@dataclass
class Config:
    unity_version: str = field(default_factory=_require_unity_version)
    download_url: str = field(init=False)
    paths: PathsConfig = field(init=False)
    bake: BakeConfig = field(default_factory=BakeConfig)
    chunking: ChunkConfig = field(default_factory=ChunkConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)

    def __post_init__(self) -> None:
        unity_version = (self.unity_version or "").strip()
        if not unity_version:
            raise ValueError(
                f"{UNITY_VERSION_ENV} must be a non-empty string "
                "(for example: 6000.3)."
            )
        self.unity_version = unity_version
        self.download_url = _download_url_for_version(unity_version)
        self.paths = _paths_for_version(unity_version)

    @classmethod
    def from_file(cls, path: Path | str) -> "Config":
        cfg_path = Path(path)
        base = cls(unity_version=_require_unity_version())
        if not cfg_path.exists():
            return base
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"Config file must contain a YAML mapping: {cfg_path}")
        _validate_override_keys(raw, source=cfg_path)
        return merge_config(base, raw)


def _validate_override_keys(overrides: Dict[str, Any], source: Optional[Path] = None) -> None:
    forbidden = [key for key in _LEGACY_VERSION_KEYS if key in overrides]
    if not forbidden:
        return
    where = f" in {source}" if source is not None else ""
    forbidden_list = ", ".join(forbidden)
    raise ValueError(
        f"Unsupported config keys{where}: {forbidden_list}. "
        f"Set {UNITY_VERSION_ENV} and let paths/download URL derive from that value."
    )


def merge_config(base: Config, overrides: Dict[str, Any]) -> Config:
    """
    Merge dictionary overrides into a Config instance, returning a new instance.
    """
    _validate_override_keys(overrides)
    cfg_dict: Dict[str, Any] = {
        "bake": vars(base.bake),
        "chunking": vars(base.chunking),
        "index": {
            "lexical": base.index.lexical,
            "vector": base.index.vector,
            "embedder": vars(base.index.embedder),
            "rerank_enable": base.index.rerank_enable,
            "candidate_pool": base.index.candidate_pool,
        },
        "mcp": vars(base.mcp),
    }

    def deep_update(target: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                target[key] = deep_update(target.get(key, {}), value)
            else:
                target[key] = value
        return target

    merged = deep_update(cfg_dict, overrides)

    return Config(
        unity_version=base.unity_version,
        bake=BakeConfig(**merged["bake"]),
        chunking=ChunkConfig(**merged["chunking"]),
        index=IndexConfig(
            lexical=merged["index"]["lexical"],
            vector=merged["index"]["vector"],
            embedder=EmbedderConfig(**merged["index"]["embedder"]),
            rerank_enable=merged["index"]["rerank_enable"],
            candidate_pool=merged["index"]["candidate_pool"],
        ),
        mcp=MCPConfig(**merged["mcp"]),
    )


def _repo_root() -> Path:
    root_override = os.environ.get("UNITY_DOCS_MCP_ROOT")
    if root_override:
        return Path(root_override).expanduser()
    return Path(__file__).resolve().parents[2]


def config_layer_paths(config_path: Optional[Path | str] = None) -> list[Path]:
    """
    Return config layer candidates in merge order (lowest -> highest precedence).
    """
    repo_root = _repo_root()
    env_override = os.environ.get("UNITY_DOCS_MCP_CONFIG")
    layers: list[Path] = [repo_root / "config.yaml", repo_root / "config.local.yaml"]
    if env_override:
        layers.append(Path(env_override).expanduser())
    if config_path is not None:
        layers.append(Path(config_path).expanduser())

    deduped: list[Path] = []
    seen: set[str] = set()
    for layer in layers:
        key = str(layer.resolve()) if layer.exists() else str(layer)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(layer)
    return deduped


def existing_config_layer_paths(config_path: Optional[Path | str] = None) -> list[Path]:
    return [p.resolve() for p in config_layer_paths(config_path) if p.exists()]


def load_config(config_path: Optional[Path | str] = None) -> Config:
    cfg = Config(unity_version=_require_unity_version())
    for layer in config_layer_paths(config_path):
        if not layer.exists():
            continue
        with layer.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"Config file must contain a YAML mapping: {layer}")
        _validate_override_keys(raw, source=layer)
        cfg = merge_config(cfg, raw)
    return cfg


def vector_enabled(vector_mode: str) -> bool:
    mode = (vector_mode or "").strip().lower()
    return mode not in {"", "none", "off", "disabled", "false"}


def retrieval_mode(vector_mode: str) -> str:
    return "hybrid" if vector_enabled(vector_mode) else "fts_only"


def config_signature(cfg: Config) -> str:
    """
    Stable hash representing the effective configuration to detect staleness.
    """
    as_dict = {
        "unity_version": cfg.unity_version,
        "download_url": cfg.download_url,
        "paths": vars(cfg.paths),
        "bake": vars(cfg.bake),
        "chunking": vars(cfg.chunking),
        "index": {
            "lexical": cfg.index.lexical,
            "vector": cfg.index.vector,
            "embedder": vars(cfg.index.embedder),
            "rerank_enable": cfg.index.rerank_enable,
            "candidate_pool": cfg.index.candidate_pool,
        },
        "mcp": vars(cfg.mcp),
    }
    payload = json.dumps(as_dict, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
