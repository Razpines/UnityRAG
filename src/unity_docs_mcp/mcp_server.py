from __future__ import annotations

import contextlib
import json
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from unity_docs_mcp.config import load_config
from unity_docs_mcp.setup.ensure_artifacts import ensure
from unity_docs_mcp.tools.ops import DocStore

app = FastMCP("unity-docs")

_docstore: Optional[DocStore] = None
_ensured: bool = False


def _get_docstore() -> DocStore:
    """
    FastMCP version in this environment lacks startup hooks, so we lazily
    initialize on first tool call and keep a singleton for reuse.
    """
    global _docstore
    global _ensured
    if _docstore is None:
        config = load_config()
        if not _ensured:
            with contextlib.redirect_stdout(sys.stderr):
                ensure(config)
            _ensured = True
        _docstore = DocStore(config)
    return _docstore


def _ensure_startup() -> None:
    global _ensured
    if _ensured:
        return
    config = load_config()
    with contextlib.redirect_stdout(sys.stderr):
        ensure(config)
    _ensured = True


def _read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _retrieval_mode(vector_mode: str) -> str:
    mode = (vector_mode or "").strip().lower()
    if mode in {"", "none", "off", "disabled", "false"}:
        return "fts_only"
    return "hybrid"


def _response_meta(docstore: DocStore, baked_manifest: Optional[dict] = None) -> dict:
    cfg = docstore.config
    meta = {
        "unity_version": cfg.unity_version,
        "index_mode": {
            "lexical": cfg.index.lexical,
            "vector": cfg.index.vector,
        },
        "retrieval_mode": _retrieval_mode(cfg.index.vector),
    }
    baked = baked_manifest or {}
    build_from = baked.get("build_from")
    built_on = baked.get("built_on")
    if build_from is not None:
        meta["build_from"] = build_from
    if built_on is not None:
        meta["built_on"] = built_on
    return meta


@app.tool()
def search(
    query: str,
    k: int = 6,
    source_types: Optional[List[str] | str] = None,
) -> List[dict]:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    if isinstance(source_types, str):
        source_types = [s.strip() for s in source_types.split(",") if s.strip()]
    results = docstore.search(query=query, k=k, source_types=source_types)
    return [
        {
            "chunk_id": r.chunk_id,
            "doc_id": r.doc_id,
            "title": r.title,
            "heading_path": r.heading_path,
            "snippet": r.snippet,
            "origin_path": r.origin_path,
            "source_type": r.source_type,
            "score": r.score,
            "canonical_url": r.canonical_url,
            "meta": meta,
        }
        for r in results
    ]


@app.tool()
def open(
    doc_id: Optional[str] = None,
    path: Optional[str] = None,
    max_chars: Optional[int] = None,
    full: bool = False,
) -> dict:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    record = docstore.open_doc(doc_id=doc_id, path=path)
    if not record:
        return {"meta": meta}
    text = record.text_md
    if not full:
        cap = max_chars if max_chars is not None else docstore.config.mcp.open_max_chars
        if cap and len(text) > cap:
            text = text[:cap] + "..."
    return {
        "doc_id": record.doc_id,
        "title": record.title,
        "source_type": record.source_type,
        "origin_path": record.origin_path,
        "canonical_url": record.canonical_url,
        "text": text,
        "meta": meta,
    }


@app.tool()
def list_files(pattern: str, limit: int = 20) -> List[dict]:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    matches = docstore.list_files(pattern=pattern, limit=limit)
    return [
        {
            "doc_id": m.doc_id,
            "title": m.title,
            "source_type": m.source_type,
            "origin_path": m.origin_path,
            "canonical_url": m.canonical_url,
            "meta": meta,
        }
        for m in matches
    ]


@app.tool()
def related(doc_id: str, limit: int = 10) -> List[dict]:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    neighbors = docstore.related(doc_id=doc_id, limit=limit)
    return [
        {
            "doc_id": n.doc_id,
            "title": n.title,
            "source_type": n.source_type,
            "origin_path": n.origin_path,
            "canonical_url": n.canonical_url,
            "meta": meta,
        }
        for n in neighbors
    ]


@app.tool()
def status() -> dict:
    docstore = _get_docstore()
    config = docstore.config
    from unity_docs_mcp.paths import make_paths

    paths = make_paths(config)
    baked_manifest = _read_manifest(paths.baked_dir / "manifest.json")
    index_manifest = _read_manifest(paths.index_dir / "manifest.json")
    return {
        "meta": _response_meta(docstore, baked_manifest=baked_manifest),
        "paths": vars(config.paths),
        "unity_version": config.unity_version,
        "embedder": vars(config.index.embedder),
        "baked_manifest": baked_manifest,
        "index_manifest": index_manifest,
    }


def main() -> None:
    _ensure_startup()
    app.run()


def main_http() -> None:
    _ensure_startup()
    host = os.environ.get("UNITY_DOCS_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("UNITY_DOCS_MCP_PORT", "8765"))
    app.settings.host = host
    app.settings.port = port
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print(f"[unitydocs-mcp] starting streamable HTTP server on {host}:{port}/mcp")
    app.run(transport="streamable-http")


if __name__ == "__main__":
    main()
