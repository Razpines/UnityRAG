from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from unity_docs_mcp.config import Config
from unity_docs_mcp.index.search import HybridSearcher
from unity_docs_mcp.paths import make_paths

_DEFAULT_SOURCE_TYPES = ("manual", "scriptref")


@dataclass
class DocRecord:
    doc_id: str
    source_type: str
    title: str
    text_md: str
    origin_path: str
    canonical_url: Optional[str]


class DocStore:
    def __init__(self, config: Config):
        self.config = config
        self.paths = make_paths(config)
        self.corpus = self._load_corpus(self.paths.baked_dir / "corpus.jsonl")
        self._origin_path_index = self._build_origin_path_index(self.corpus)
        self._canonical_url_index = self._build_canonical_url_index(self.corpus)
        self._doc_source_type_counts = self._count_source_types(self.corpus.values())
        self.link_index = self._load_links(self.paths.baked_dir / "link_graph.jsonl")
        self.reverse_link_index = self._build_reverse_links(self.link_index)
        self.searcher = HybridSearcher(config, self.paths.index_dir)
        self._chunk_source_type_counts = self._count_source_types(getattr(self.searcher, "chunk_meta", {}).values())

    def _load_corpus(self, path: Path) -> Dict[str, DocRecord]:
        records: Dict[str, DocRecord] = {}
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                records[row["doc_id"]] = DocRecord(
                    doc_id=row["doc_id"],
                    source_type=row["source_type"],
                    title=row["title"],
                    text_md=row["text_md"],
                    origin_path=row.get("origin_path", ""),
                    canonical_url=row.get("canonical_url"),
                )
        return records

    def _load_links(self, path: Path) -> Dict[str, List[str]]:
        links: Dict[str, List[str]] = {}
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                links.setdefault(row["from_doc_id"], []).append(row["to_doc_id"])
        return links

    @staticmethod
    def _build_reverse_links(links: Dict[str, List[str]]) -> Dict[str, List[str]]:
        reverse_links: Dict[str, List[str]] = {}
        for from_doc, neighbors in links.items():
            for to_doc in neighbors:
                reverse_links.setdefault(to_doc, []).append(from_doc)
        return reverse_links

    def _build_origin_path_index(self, records: Dict[str, DocRecord]) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for doc in records.values():
            if not doc.origin_path:
                continue
            index[doc.origin_path] = doc.doc_id
            index[self._normalize_path_lookup_key(doc.origin_path)] = doc.doc_id
        return index

    def _build_canonical_url_index(self, records: Dict[str, DocRecord]) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for doc in records.values():
            if doc.canonical_url:
                index[doc.canonical_url.strip()] = doc.doc_id
        return index

    @staticmethod
    def _normalize_path_lookup_key(path: str) -> str:
        return path.strip().replace("\\", "/").lower()

    @staticmethod
    def _maybe_doc_id_from_path(path: str) -> Optional[str]:
        cleaned = path.strip().replace("\\", "/")
        if not cleaned:
            return None
        if cleaned.lower().startswith(("http://", "https://")):
            return None
        if "/" in cleaned and cleaned.lower().startswith("documentation/en/"):
            cleaned = cleaned[len("Documentation/en/") :]
        if cleaned.lower().endswith(".html"):
            cleaned = cleaned[:-5]
        if "/" not in cleaned:
            return None
        return cleaned.replace(" ", "-").lower()

    @staticmethod
    def _count_source_types(rows) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            if isinstance(row, dict):
                source_type = row.get("source_type", "")
            else:
                source_type = getattr(row, "source_type", "")
            if not source_type:
                continue
            counts[source_type] = counts.get(source_type, 0) + 1
        return counts

    def open_doc(self, doc_id: Optional[str] = None, path: Optional[str] = None) -> Optional[DocRecord]:
        if doc_id:
            # Prefer exact doc_id match first to preserve current behavior.
            record = self.corpus.get(doc_id) or self.corpus.get(doc_id.strip().lower())
            if record:
                return record

        if path:
            path_key_exact = path.strip()
            if path_key_exact in self._canonical_url_index:
                record = self.corpus.get(self._canonical_url_index[path_key_exact])
                if record:
                    return record

            normalized_path = self._normalize_path_lookup_key(path)
            target_id = self._origin_path_index.get(path_key_exact) or self._origin_path_index.get(normalized_path)
            if target_id:
                record = self.corpus.get(target_id)
                if record:
                    return record

            maybe_doc_id = self._maybe_doc_id_from_path(path)
            if maybe_doc_id:
                record = self.corpus.get(maybe_doc_id)
                if record:
                    return record

        return None

    def list_files(self, pattern: str, limit: int = 20) -> List[DocRecord]:
        matches: List[DocRecord] = []
        for doc in self.corpus.values():
            if fnmatch.fnmatch(doc.origin_path, pattern) or pattern.lower() in doc.doc_id.lower():
                matches.append(doc)
            if len(matches) >= limit:
                break
        return matches

    def related(
        self,
        doc_id: str,
        limit: int = 10,
        mode: str = "outgoing",
        exclude_doc_ids: Optional[List[str]] = None,
        exclude_source_types: Optional[List[str]] = None,
    ) -> List[DocRecord]:
        exclude_doc_ids_set = set(exclude_doc_ids or [])
        exclude_source_types_set = {s.lower() for s in (exclude_source_types or [])}

        mode_norm = (mode or "outgoing").strip().lower()
        if mode_norm == "outgoing":
            candidates = self.link_index.get(doc_id, [])
        elif mode_norm == "incoming":
            candidates = self.reverse_link_index.get(doc_id, [])
        elif mode_norm == "bidirectional":
            candidates = self.link_index.get(doc_id, []) + self.reverse_link_index.get(doc_id, [])
        else:
            return []

        seen = set()
        related_docs: List[DocRecord] = []
        for neighbor_id in candidates:
            if neighbor_id in seen:
                continue
            seen.add(neighbor_id)
            if neighbor_id in exclude_doc_ids_set:
                continue
            doc = self.corpus.get(neighbor_id)
            if not doc:
                continue
            if doc.source_type.lower() in exclude_source_types_set:
                continue
            related_docs.append(doc)
            if len(related_docs) >= limit:
                break
        return related_docs

    def search(self, query: str, k: int = 6, source_types: Optional[List[str]] = None) -> List:
        return self.searcher.search(query=query, k=k, source_types=source_types)

    def available_source_types(self) -> List[str]:
        all_types = set(self._doc_source_type_counts) | set(self._chunk_source_type_counts)
        return sorted(all_types)

    def known_source_types(self) -> List[str]:
        return sorted(set(_DEFAULT_SOURCE_TYPES) | set(self.available_source_types()))

    def source_type_counts(self) -> Dict[str, Dict[str, int]]:
        return {
            "docs": dict(sorted(self._doc_source_type_counts.items())),
            "chunks": dict(sorted(self._chunk_source_type_counts.items())),
        }
