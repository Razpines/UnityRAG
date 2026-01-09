from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from unity_docs_mcp.config import Config
from unity_docs_mcp.index.embed import embed_texts
from unity_docs_mcp.index.fts import search_fts
from unity_docs_mcp.index.vector_store import load_faiss, search_faiss


@dataclass
class SearchResult:
    chunk_id: str
    doc_id: str
    title: str
    heading_path: List[str]
    snippet: str
    origin_path: str
    source_type: str
    score: float
    canonical_url: Optional[str]


class HybridSearcher:
    def __init__(self, config: Config, base_path: Path):
        self.config = config
        self.fts_conn = sqlite3.connect(str(base_path / "fts.sqlite"))
        self.faiss_index = load_faiss(base_path / "vectors.faiss")
        self.vector_meta = self._load_vector_meta(base_path / "vectors_meta.jsonl")
        self.chunk_meta = self._load_chunk_meta(base_path.parent / "baked" / "chunks.jsonl")
        self.embed_model = config.index.embedder.model
        self.embed_device = config.index.embedder.device

    def _load_vector_meta(self, path: Path) -> List[str]:
        ids: List[str] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    ids.append(row["chunk_id"])
        return ids

    def _load_chunk_meta(self, path: Path) -> Dict[str, Dict]:
        meta: Dict[str, Dict] = {}
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                meta[row["chunk_id"]] = row
        return meta

    def _make_snippet(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    def search(
        self,
        query: str,
        k: int = 6,
        source_types: Optional[List[str]] = None,
        snippet_chars: Optional[int] = None,
    ) -> List[SearchResult]:
        snippet_len = snippet_chars or self.config.mcp.snippet_chars
        lexical_hits = search_fts(self.fts_conn, query, limit=self.config.index.candidate_pool)
        lexical_scores = {cid: 1.0 / (idx + 1) for idx, (cid, _) in enumerate(lexical_hits)}

        query_vec = embed_texts([query], model_name=self.embed_model, device=self.embed_device)
        distances, indices = search_faiss(self.faiss_index, query_vec, k=self.config.index.candidate_pool)
        vector_scores: Dict[str, float] = {}
        for rank, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.vector_meta):
                continue
            cid = self.vector_meta[idx]
            vector_scores[cid] = float(distances[0][rank])

        combined: List[SearchResult] = []
        seen = set()
        # combine lexical first order
        for cid, _ in lexical_hits:
            meta = self.chunk_meta.get(cid)
            if not meta:
                continue
            if source_types and meta.get("source_type") not in source_types:
                continue
            score = 0.4 * lexical_scores.get(cid, 0) + 0.6 * vector_scores.get(cid, 0)
            if cid in seen:
                continue
            seen.add(cid)
            combined.append(
                SearchResult(
                    chunk_id=cid,
                    doc_id=meta["doc_id"],
                    title=meta["title"],
                    heading_path=meta.get("heading_path", []),
                    snippet=self._make_snippet(meta["text"], snippet_len),
                    origin_path=meta.get("origin_path", ""),
                    source_type=meta.get("source_type", ""),
                    score=score,
                    canonical_url=meta.get("canonical_url"),
                )
            )

        # add vector-only hits if needed
        for cid, vscore in vector_scores.items():
            if cid in seen:
                continue
            meta = self.chunk_meta.get(cid)
            if not meta:
                continue
            if source_types and meta.get("source_type") not in source_types:
                continue
            score = 0.6 * vscore
            seen.add(cid)
            combined.append(
                SearchResult(
                    chunk_id=cid,
                    doc_id=meta["doc_id"],
                    title=meta["title"],
                    heading_path=meta.get("heading_path", []),
                    snippet=self._make_snippet(meta["text"], snippet_len),
                    origin_path=meta.get("origin_path", ""),
                    source_type=meta.get("source_type", ""),
                    score=score,
                    canonical_url=meta.get("canonical_url"),
                )
            )

        combined.sort(key=lambda x: x.score, reverse=True)
        return combined[:k]
