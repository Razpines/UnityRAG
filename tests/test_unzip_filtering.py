import zipfile
from pathlib import Path

import pytest

from unity_docs_mcp.setup.unzip import safe_unzip


def _write_zip(path: Path, members: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, body in members.items():
            zf.writestr(name, body)


def test_safe_unzip_extracts_only_selected_manual_html(tmp_path: Path):
    zip_path = tmp_path / "UnityDocumentation.zip"
    target_dir = tmp_path / "unzipped"
    _write_zip(
        zip_path,
        {
            "Documentation/en/Manual/index.html": "<html>manual index</html>",
            "Documentation/en/Manual/Sub/page.html": "<html>manual page</html>",
            "Documentation/en/Manual/readme.txt": "not html",
            "Documentation/en/ScriptReference/index.html": "<html>script ref</html>",
        },
    )

    safe_unzip(
        zip_path,
        target_dir,
        include_globs=[
            "Documentation/en/Manual/*.html",
            "Documentation/en/Manual/**/*.html",
        ],
    )

    assert (target_dir / "Documentation" / "en" / "Manual" / "index.html").exists()
    assert (target_dir / "Documentation" / "en" / "Manual" / "Sub" / "page.html").exists()
    assert not (target_dir / "Documentation" / "en" / "Manual" / "readme.txt").exists()
    assert not (target_dir / "Documentation" / "en" / "ScriptReference" / "index.html").exists()


def test_safe_unzip_keeps_zip_slip_protection(tmp_path: Path):
    zip_path = tmp_path / "UnityDocumentation.zip"
    target_dir = tmp_path / "unzipped"
    _write_zip(
        zip_path,
        {
            "../escape.txt": "bad",
        },
    )

    with pytest.raises(ValueError, match="Unsafe path detected"):
        safe_unzip(zip_path, target_dir)
