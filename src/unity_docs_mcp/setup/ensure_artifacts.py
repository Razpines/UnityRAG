from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from unity_docs_mcp.bake.bake_cli import bake
from unity_docs_mcp.config import Config, config_signature, load_config
from unity_docs_mcp.index.index_cli import index
from unity_docs_mcp.paths import make_paths
from unity_docs_mcp.setup.download import download_zip
from unity_docs_mcp.setup.unzip import safe_unzip


def _manifest_matches(path: Path, signature: str) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        return data.get("config_signature") == signature
    except Exception:
        return False


def ensure(config: Config) -> None:
    paths = make_paths(config)
    paths.ensure_dirs()

    sig = config_signature(config)
    ran_index = False

    if not paths.raw_zip.exists():
        download_zip(config.download_url, paths.raw_zip)

    if not paths.raw_unzipped.exists() or not any(paths.raw_unzipped.iterdir()):
        safe_unzip(paths.raw_zip, paths.raw_unzipped)

    baked_manifest = paths.baked_dir / "manifest.json"
    if not _manifest_matches(baked_manifest, sig):
        print("==> Baking docs (HTML -> cleaned text + chunks)...")
        bake(config)

    index_manifest = paths.index_dir / "manifest.json"
    if not _manifest_matches(index_manifest, sig):
        print("==> Indexing docs (FTS + vectors)...")
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
