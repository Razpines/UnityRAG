from __future__ import annotations

import zipfile
from pathlib import Path


def safe_unzip(zip_path: Path, target_dir: Path) -> Path:
    """
    Safely extract zip contents, preventing zip-slip by validating paths.
    """
    if target_dir.exists() and any(target_dir.iterdir()):
        return target_dir

    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            extracted_path = target_dir / member.filename
            resolved_path = extracted_path.resolve()
            if target_dir.resolve() not in resolved_path.parents and target_dir.resolve() != resolved_path:
                raise ValueError(f"Unsafe path detected in zip: {member.filename}")
        zf.extractall(target_dir)
    return target_dir
