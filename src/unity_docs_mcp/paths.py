from __future__ import annotations

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


def make_paths(config: Config) -> Paths:
    paths_cfg = config.paths
    root = Path(paths_cfg.root)
    return Paths(
        root=root,
        raw_zip=Path(paths_cfg.raw_zip),
        raw_unzipped=Path(paths_cfg.raw_unzipped),
        baked_dir=Path(paths_cfg.baked_dir),
        index_dir=Path(paths_cfg.index_dir),
    )
