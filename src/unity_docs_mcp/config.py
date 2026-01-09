from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class PathsConfig:
    root: str = "data/unity/6000.3"
    raw_zip: str = "data/unity/6000.3/raw/UnityDocumentation.zip"
    raw_unzipped: str = "data/unity/6000.3/raw/UnityDocumentation"
    baked_dir: str = "data/unity/6000.3/baked"
    index_dir: str = "data/unity/6000.3/index"


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


@dataclass
class Config:
    unity_version: str = "6000.3"
    download_url: str = (
        "https://cloudmedia-docs.unity3d.com/docscloudstorage/en/6000.3/UnityDocumentation.zip"
    )
    paths: PathsConfig = field(default_factory=PathsConfig)
    bake: BakeConfig = field(default_factory=BakeConfig)
    chunking: ChunkConfig = field(default_factory=ChunkConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)

    @classmethod
    def from_file(cls, path: Path | str) -> "Config":
        cfg_path = Path(path)
        if not cfg_path.exists():
            return cls()
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return merge_config(cls(), raw)


def merge_config(base: Config, overrides: Dict[str, Any]) -> Config:
    """
    Merge dictionary overrides into a Config instance, returning a new instance.
    """
    cfg_dict: Dict[str, Any] = {
        "unity_version": base.unity_version,
        "download_url": base.download_url,
        "paths": vars(base.paths),
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
        unity_version=merged["unity_version"],
        download_url=merged["download_url"],
        paths=PathsConfig(**merged["paths"]),
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


def load_config(config_path: Optional[Path | str] = None) -> Config:
    if config_path is None:
        config_path = Path("config.yaml")
    return Config.from_file(config_path)


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
