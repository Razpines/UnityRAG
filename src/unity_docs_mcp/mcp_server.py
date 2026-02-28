from __future__ import annotations

import contextlib
import json
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

from mcp.server.fastmcp import FastMCP

from unity_docs_mcp.config import load_config, retrieval_mode
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


def _response_meta(docstore: DocStore, baked_manifest: Optional[dict] = None) -> dict:
    cfg = docstore.config
    meta = {
        "unity_version": cfg.unity_version,
        "index_mode": {
            "lexical": cfg.index.lexical,
            "vector": cfg.index.vector,
        },
        "retrieval_mode": retrieval_mode(cfg.index.vector),
    }
    baked = baked_manifest or {}
    build_from = baked.get("build_from")
    built_on = baked.get("built_on")
    if build_from is not None:
        meta["build_from"] = build_from
    if built_on is not None:
        meta["built_on"] = built_on
    return meta


def _parse_source_types(source_types: Optional[List[str] | str]) -> Optional[List[str]]:
    if source_types is None:
        return None
    if isinstance(source_types, str):
        values = [s.strip().lower() for s in source_types.split(",") if s.strip()]
    else:
        values = [str(s).strip().lower() for s in source_types if str(s).strip()]
    return values or None


def _parse_string_list(values: Optional[List[str] | str]) -> Optional[List[str]]:
    if values is None:
        return None
    if isinstance(values, str):
        parsed = [item.strip() for item in values.split(",") if item.strip()]
    else:
        parsed = [str(item).strip() for item in values if str(item).strip()]
    return parsed or None


def _serialize_search_results(results: list[Any], meta: dict) -> List[dict]:
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
def search(
    query: str,
    k: int = 6,
    source_types: Optional[List[str] | str] = None,
    debug: bool = False,
) -> List[dict] | dict:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    parsed_source_types = _parse_source_types(source_types)
    available_source_types = docstore.available_source_types()
    known_source_types = docstore.known_source_types()

    invalid_source_types = []
    unavailable_source_types = []
    if parsed_source_types:
        requested_set = set(parsed_source_types)
        known_set = set(known_source_types)
        available_set = set(available_source_types)
        invalid_source_types = sorted(requested_set - known_set)
        unavailable_source_types = sorted((requested_set & known_set) - available_set)

    if invalid_source_types or unavailable_source_types:
        message_parts = []
        if invalid_source_types:
            message_parts.append(f"Unsupported source_types: {', '.join(invalid_source_types)}")
        if unavailable_source_types:
            message_parts.append(f"Requested source_types not present in this index: {', '.join(unavailable_source_types)}")
        return {
            "error": "invalid_source_types",
            "message": ". ".join(message_parts),
            "requested_source_types": parsed_source_types or [],
            "invalid_source_types": invalid_source_types,
            "unavailable_source_types": unavailable_source_types,
            "known_source_types": known_source_types,
            "available_source_types": available_source_types,
            "results": [],
            "meta": meta,
        }

    results = docstore.search(query=query, k=k, source_types=parsed_source_types)
    serialized = _serialize_search_results(results, meta)
    if not debug:
        return serialized
    return {
        "results": serialized,
        "meta": meta,
        "debug": {
            "query": query,
            "k": k,
            "requested_source_types": parsed_source_types or [],
            "available_source_types": available_source_types,
            "known_source_types": known_source_types,
            "retrieval_mode": meta["retrieval_mode"],
            "result_count": len(serialized),
        },
    }


@app.tool()
def resolve_symbol(symbol: str, limit: int = 5) -> dict:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    symbol_text = (symbol or "").strip()
    if not symbol_text:
        return {
            "error": "invalid_symbol",
            "message": "symbol must be a non-empty string.",
            "meta": meta,
        }
    matches = docstore.resolve_symbol(symbol=symbol_text, limit=limit)
    return {
        "symbol": symbol_text,
        "results": [{**m, "meta": meta} for m in matches],
        "meta": meta,
    }


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
        return {
            "error": "not_found",
            "attempted": {"doc_id": doc_id, "path": path},
            "meta": meta,
        }
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
def related(
    doc_id: Optional[str] = None,
    path: Optional[str] = None,
    mode: str = "outgoing",
    limit: int = 10,
    exclude_doc_ids: Optional[List[str] | str] = None,
    exclude_source_types: Optional[List[str] | str] = None,
    exclude_glossary: bool = False,
) -> List[dict] | dict:
    docstore = _get_docstore()
    meta = _response_meta(docstore)
    resolved_doc_id = doc_id
    if not resolved_doc_id and path:
        record = docstore.open_doc(path=path)
        if record:
            resolved_doc_id = record.doc_id
    if not resolved_doc_id:
        return {
            "error": "not_found",
            "message": "Provide a valid doc_id or path.",
            "attempted": {"doc_id": doc_id, "path": path},
            "meta": meta,
        }

    mode_norm = (mode or "outgoing").strip().lower()
    allowed_modes = {"outgoing", "incoming", "bidirectional"}
    if mode_norm not in allowed_modes:
        return {
            "error": "invalid_mode",
            "message": f"Unsupported mode: {mode}",
            "allowed_modes": sorted(allowed_modes),
            "meta": meta,
        }

    parsed_exclude_doc_ids = _parse_string_list(exclude_doc_ids) or []
    parsed_exclude_source_types = [s.lower() for s in (_parse_string_list(exclude_source_types) or [])]
    if exclude_glossary:
        parsed_exclude_doc_ids.extend(["manual/glossary", "scriptreference/glossary"])

    neighbors = docstore.related(
        doc_id=resolved_doc_id,
        limit=limit,
        mode=mode_norm,
        exclude_doc_ids=parsed_exclude_doc_ids,
        exclude_source_types=parsed_exclude_source_types,
    )
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
    available_source_types = docstore.available_source_types()
    source_type_counts = docstore.source_type_counts()
    coverage_warnings: list[str] = []
    if "scriptref" not in set(available_source_types):
        coverage_warnings.append(
            "scriptref source type is not present in the loaded corpus/index; API symbol lookup coverage may be incomplete"
        )
    return {
        "meta": _response_meta(docstore, baked_manifest=baked_manifest),
        "paths": vars(config.paths),
        "unity_version": config.unity_version,
        "embedder": vars(config.index.embedder),
        "baked_manifest": baked_manifest,
        "index_manifest": index_manifest,
        "available_source_types": available_source_types,
        "source_type_counts": source_type_counts,
        "coverage_warnings": coverage_warnings,
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
