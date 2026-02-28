from __future__ import annotations

import fnmatch
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

from tqdm import tqdm


def _normalize_patterns(patterns: Sequence[str] | None) -> list[str]:
    if not patterns:
        return []
    normalized: list[str] = []
    for pattern in patterns:
        value = str(pattern).strip().replace("\\", "/").lstrip("/")
        if value:
            normalized.append(value)
    return normalized


def _glob_variants(pattern: str) -> Iterable[str]:
    # pathlib/fnmatch treat `/**/` as "one or more" directories; include a
    # zero-directory variant so `Manual/**/*.html` also matches `Manual/index.html`.
    yield pattern
    if "/**/" in pattern:
        yield pattern.replace("/**/", "/")


def _member_selected(member_name: str, include_globs: Sequence[str] | None) -> bool:
    if not include_globs:
        return True
    normalized = member_name.replace("\\", "/").lstrip("/")
    if normalized.endswith("/"):
        return False
    for pattern in include_globs:
        for variant in _glob_variants(pattern):
            if fnmatch.fnmatch(normalized, variant):
                return True
    return False


def safe_unzip(
    zip_path: Path,
    target_dir: Path,
    include_globs: Sequence[str] | None = None,
) -> Path:
    """
    Safely extract zip contents, preventing zip-slip by validating paths.
    """
    if target_dir.exists() and any(target_dir.iterdir()):
        return target_dir

    selected_globs = _normalize_patterns(include_globs)
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        selected_members = [m for m in members if _member_selected(m.filename, selected_globs)]
        print(
            f"==> Unzipping {zip_path} "
            f"({len(selected_members)}/{len(members)} files selected)..."
        )
        target_root = target_dir.resolve()
        for member in selected_members:
            extracted_path = target_dir / member.filename
            resolved_path = extracted_path.resolve()
            if target_root not in resolved_path.parents and target_root != resolved_path:
                raise ValueError(f"Unsafe path detected in zip: {member.filename}")
        bar = tqdm(total=len(selected_members), unit="file", unit_scale=False)
        for member in selected_members:
            zf.extract(member, target_dir)
            bar.update(1)
        bar.close()
    return target_dir
