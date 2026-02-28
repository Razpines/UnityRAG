from __future__ import annotations

import sqlite3
from pathlib import Path
import re
from typing import Iterable, List, Tuple

# FTS column weights (lower bm25 score is better):
# text, doc_id, heading_path, title, chunk_id
_FTS_QUERY = (
    "SELECT chunk_id, bm25(chunks_fts, 1.0, 6.0, 3.0, 8.0, 0.0) as score "
    "FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?"
)


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT,
            source_type TEXT,
            title TEXT,
            heading_path TEXT,
            origin_path TEXT,
            canonical_url TEXT
        );
        """
    )
    # Recreate FTS table to keep schema consistent with current indexed columns.
    conn.execute("DROP TABLE IF EXISTS chunks_fts;")
    conn.execute(
        """
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            text,
            doc_id,
            heading_path,
            title,
            chunk_id UNINDEXED
        );
        """
    )
    return conn


def ingest_chunks(conn: sqlite3.Connection, rows: Iterable[Tuple[str, str, str, str, str, str, str, str]]) -> None:
    data = list(rows)
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO chunks(chunk_id, doc_id, source_type, title, heading_path, origin_path, canonical_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in data],
        )
        conn.executemany(
            "INSERT INTO chunks_fts(text, doc_id, heading_path, title, chunk_id) VALUES (?, ?, ?, ?, ?)",
            [(r[7], r[1], r[3], r[2], r[0]) for r in data],
        )


def search_fts(conn: sqlite3.Connection, query: str, limit: int = 20) -> List[Tuple[str, float]]:
    for candidate in _query_variants(query):
        try:
            cursor = conn.execute(_FTS_QUERY, (candidate, limit))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # Keep trying normalized variants if a candidate is invalid syntax.
            continue
        if rows:
            return rows
    return []


def _sanitize_fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    return " ".join(tokens)


def _split_camel_tokens(query: str) -> str:
    if not query:
        return ""
    parts: List[str] = []
    for token in query.split():
        split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", token)
        parts.extend(split.split())
    return " ".join(parts).strip()


def _query_variants(query: str) -> List[str]:
    raw = (query or "").strip()
    variants: List[str] = []
    if raw:
        variants.append(raw)

    safe_query = _sanitize_fts_query(raw)
    if safe_query:
        variants.append(safe_query)

    camel_split = _split_camel_tokens(safe_query)
    if camel_split:
        variants.append(camel_split)

    # Preserve order while deduplicating.
    deduped: List[str] = []
    seen = set()
    for variant in variants:
        if not variant or variant in seen:
            continue
        deduped.append(variant)
        seen.add(variant)
    return deduped
