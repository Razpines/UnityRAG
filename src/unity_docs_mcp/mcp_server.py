from __future__ import annotations

import json
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from unity_docs_mcp.config import load_config
from unity_docs_mcp.setup.ensure_artifacts import ensure
from unity_docs_mcp.tools.ops import DocStore

app = FastMCP("unity-docs")

_docstore: Optional[DocStore] = None


def _get_docstore() -> DocStore:
    """
    FastMCP version in this environment lacks startup hooks, so we lazily
    initialize on first tool call and keep a singleton for reuse.
    """
    global _docstore
    if _docstore is None:
        config = load_config()
        ensure(config)
        _docstore = DocStore(config)
    return _docstore


@app.tool()
def search(query: str, k: int = 6, source_types: Optional[List[str]] = None) -> List[dict]:
    docstore = _get_docstore()
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
        }
        for r in results
    ]


@app.tool()
def open(doc_id: Optional[str] = None, path: Optional[str] = None, max_chars: Optional[int] = None) -> dict:
    docstore = _get_docstore()
    record = docstore.open_doc(doc_id=doc_id, path=path)
    if not record:
        return {}
    text = record.text_md
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "..."
    return {
        "doc_id": record.doc_id,
        "title": record.title,
        "source_type": record.source_type,
        "origin_path": record.origin_path,
        "canonical_url": record.canonical_url,
        "text": text,
    }


@app.tool()
def list_files(pattern: str, limit: int = 20) -> List[dict]:
    docstore = _get_docstore()
    matches = docstore.list_files(pattern=pattern, limit=limit)
    return [
        {
            "doc_id": m.doc_id,
            "title": m.title,
            "source_type": m.source_type,
            "origin_path": m.origin_path,
            "canonical_url": m.canonical_url,
        }
        for m in matches
    ]


@app.tool()
def related(doc_id: str, limit: int = 10) -> List[dict]:
    docstore = _get_docstore()
    neighbors = docstore.related(doc_id=doc_id, limit=limit)
    return [
        {
            "doc_id": n.doc_id,
            "title": n.title,
            "source_type": n.source_type,
            "origin_path": n.origin_path,
            "canonical_url": n.canonical_url,
        }
        for n in neighbors
    ]


@app.tool()
def status() -> dict:
    docstore = _get_docstore()
    config = docstore.config
    from unity_docs_mcp.paths import make_paths

    paths = make_paths(config)
    baked_manifest = {}
    index_manifest = {}
    if (paths.baked_dir / "manifest.json").exists():
        baked_manifest = json.loads((paths.baked_dir / "manifest.json").read_text())
    if (paths.index_dir / "manifest.json").exists():
        index_manifest = json.loads((paths.index_dir / "manifest.json").read_text())
    return {
        "paths": vars(config.paths),
        "unity_version": config.unity_version,
        "embedder": vars(config.index.embedder),
        "baked_manifest": baked_manifest,
        "index_manifest": index_manifest,
    }


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
