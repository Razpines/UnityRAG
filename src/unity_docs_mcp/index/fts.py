from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple


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
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            doc_id UNINDEXED,
            heading_path UNINDEXED,
            title UNINDEXED,
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
    cursor = conn.execute(
        "SELECT chunk_id, bm25(chunks_fts) as score FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?",
        (query, limit),
    )
    return cursor.fetchall()
