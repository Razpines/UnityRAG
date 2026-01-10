from __future__ import annotations

import zipfile
from pathlib import Path

from tqdm import tqdm


def safe_unzip(zip_path: Path, target_dir: Path) -> Path:
    """
    Safely extract zip contents, preventing zip-slip by validating paths.
    """
    if target_dir.exists() and any(target_dir.iterdir()):
        return target_dir

    print(f"==> Unzipping {zip_path}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        for member in members:
            extracted_path = target_dir / member.filename
            resolved_path = extracted_path.resolve()
            if target_dir.resolve() not in resolved_path.parents and target_dir.resolve() != resolved_path:
                raise ValueError(f"Unsafe path detected in zip: {member.filename}")
        bar = tqdm(total=len(members), unit="file", unit_scale=False)
        for member in members:
            zf.extract(member, target_dir)
            bar.update(1)
        bar.close()
    return target_dir
