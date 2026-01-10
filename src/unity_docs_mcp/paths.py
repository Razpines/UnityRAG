from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import Config


@dataclass
class Paths:
    root: Path
    raw_zip: Path
    raw_unzipped: Path
    baked_dir: Path
    index_dir: Path

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.raw_unzipped.mkdir(parents=True, exist_ok=True)
        self.baked_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)


def _resolve(base_dir: Path, path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else base_dir / p


def make_paths(config: Config) -> Paths:
    paths_cfg = config.paths
    base_dir = Path(os.environ.get("UNITY_DOCS_MCP_ROOT") or Path(__file__).resolve().parents[2])
    root = _resolve(base_dir, paths_cfg.root)
    return Paths(
        root=root,
        raw_zip=_resolve(base_dir, paths_cfg.raw_zip),
        raw_unzipped=_resolve(base_dir, paths_cfg.raw_unzipped),
        baked_dir=_resolve(base_dir, paths_cfg.baked_dir),
        index_dir=_resolve(base_dir, paths_cfg.index_dir),
    )
