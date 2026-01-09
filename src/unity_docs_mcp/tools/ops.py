from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from unity_docs_mcp.config import Config
from unity_docs_mcp.index.search import HybridSearcher
from unity_docs_mcp.paths import make_paths


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
        self.link_index = self._load_links(self.paths.baked_dir / "link_graph.jsonl")
        self.searcher = HybridSearcher(config, self.paths.index_dir)

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

    def open_doc(self, doc_id: Optional[str] = None, path: Optional[str] = None) -> Optional[DocRecord]:
        target_id = doc_id
        if not target_id and path:
            # derive doc_id from relative path
            target_id = path.replace("\\", "/")
            target_id = target_id.replace(".html", "")
            target_id = target_id.lower()
        if not target_id:
            return None
        return self.corpus.get(target_id)

    def list_files(self, pattern: str, limit: int = 20) -> List[DocRecord]:
        matches: List[DocRecord] = []
        for doc in self.corpus.values():
            if fnmatch.fnmatch(doc.origin_path, pattern) or pattern.lower() in doc.doc_id.lower():
                matches.append(doc)
            if len(matches) >= limit:
                break
        return matches

    def related(self, doc_id: str, limit: int = 10) -> List[DocRecord]:
        neighbors = self.link_index.get(doc_id, [])[:limit]
        return [self.corpus[n] for n in neighbors if n in self.corpus]

    def search(self, query: str, k: int = 6, source_types: Optional[List[str]] = None) -> List:
        return self.searcher.search(query=query, k=k, source_types=source_types)
