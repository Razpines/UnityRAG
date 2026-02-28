from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from unity_docs_mcp.bake.bake_cli import bake
from unity_docs_mcp.config import Config, config_signature, load_config, vector_enabled
from unity_docs_mcp.index.index_cli import index
from unity_docs_mcp.paths import make_paths
from unity_docs_mcp.setup.download import download_zip
from unity_docs_mcp.setup.unzip import safe_unzip

_BAKE_INPUT_GLOBS = [
    "Documentation/en/Manual/*.html",
    "Documentation/en/Manual/**/*.html",
]


def _manifest_matches(path: Path, signature: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        return data.get("config_signature") == signature
    except Exception:
        return False


def _raw_docs_ready(raw_unzipped: Path) -> bool:
    return (raw_unzipped / "Documentation" / "en" / "Manual" / "index.html").is_file()


def _recover_unzip(
    download_url: str,
    raw_zip: Path,
    raw_unzipped: Path,
    include_globs: list[str],
    error: Exception,
) -> None:
    print(f"[setup] Unzip failed ({error}). Re-downloading zip and retrying once...")
    if raw_unzipped.exists():
        shutil.rmtree(raw_unzipped, ignore_errors=True)
    if raw_zip.exists():
        raw_zip.unlink()
    download_zip(download_url, raw_zip, overwrite=True)
    safe_unzip(raw_zip, raw_unzipped, include_globs=include_globs)


def ensure(config: Config) -> None:
    paths = make_paths(config)
    paths.ensure_dirs()

    sig = config_signature(config)
    ran_index = False

    baked_manifest = paths.baked_dir / "manifest.json"
    baked_matches = _manifest_matches(baked_manifest, sig)
    if not baked_matches:
        if not paths.raw_zip.exists():
            download_zip(config.download_url, paths.raw_zip)

        if not _raw_docs_ready(paths.raw_unzipped):
            if paths.raw_unzipped.exists():
                shutil.rmtree(paths.raw_unzipped, ignore_errors=True)
            try:
                safe_unzip(paths.raw_zip, paths.raw_unzipped, include_globs=_BAKE_INPUT_GLOBS)
            except Exception as unzip_error:
                _recover_unzip(
                    config.download_url,
                    paths.raw_zip,
                    paths.raw_unzipped,
                    include_globs=_BAKE_INPUT_GLOBS,
                    error=unzip_error,
                )

        print("==> Baking docs (HTML -> cleaned text + chunks)...")
        bake(config)
        baked_matches = True

    index_manifest = paths.index_dir / "manifest.json"
    if not _manifest_matches(index_manifest, sig):
        if vector_enabled(config.index.vector):
            print("==> Indexing docs (FTS + vectors)...")
        else:
            print("==> Indexing docs (FTS only)...")
        index(config)
        ran_index = True

    if os.environ.get("UNITY_DOCS_MCP_CLEANUP") == "1" and ran_index:
        cleaned = False
        if paths.raw_zip.exists():
            paths.raw_zip.unlink()
            cleaned = True
        if paths.raw_unzipped.exists():
            shutil.rmtree(paths.raw_unzipped, ignore_errors=True)
            cleaned = True
        if cleaned:
            print("==> Cleaned up raw zip and unzipped docs to save space.")


def main() -> None:
    config = load_config()
    ensure(config)
    print("Artifacts ensured.")


if __name__ == "__main__":
    main()
