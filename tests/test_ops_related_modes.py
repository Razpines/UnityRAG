import json
from pathlib import Path

from unity_docs_mcp.config import Config, PathsConfig
from unity_docs_mcp.tools import ops


class _FakeSearcher:
    def __init__(self, config, base_path):
        self.config = config
        self.base_path = base_path
        self.chunk_meta = {}

    def search(self, query: str, k: int = 6, source_types=None):
        return []


def _cfg(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.paths = PathsConfig(
        root=str(tmp_path),
        raw_zip=str(tmp_path / "raw" / "UnityDocumentation.zip"),
        raw_unzipped=str(tmp_path / "raw" / "UnityDocumentation"),
        baked_dir=str(tmp_path / "baked"),
        index_dir=str(tmp_path / "index"),
    )
    return cfg


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _build_store(monkeypatch, tmp_path: Path) -> ops.DocStore:
    monkeypatch.setattr(ops, "HybridSearcher", _FakeSearcher)
    cfg = _cfg(tmp_path)
    _write_jsonl(
        tmp_path / "baked" / "corpus.jsonl",
        [
            {
                "doc_id": "manual/a",
                "source_type": "manual",
                "title": "A",
                "text_md": "A",
                "origin_path": "Documentation/en/Manual/A.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/A.html",
            },
            {
                "doc_id": "manual/b",
                "source_type": "manual",
                "title": "B",
                "text_md": "B",
                "origin_path": "Documentation/en/Manual/B.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/B.html",
            },
            {
                "doc_id": "manual/c",
                "source_type": "manual",
                "title": "C",
                "text_md": "C",
                "origin_path": "Documentation/en/Manual/C.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/C.html",
            },
            {
                "doc_id": "manual/glossary",
                "source_type": "manual",
                "title": "Glossary",
                "text_md": "G",
                "origin_path": "Documentation/en/Manual/Glossary.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/Glossary.html",
            },
        ],
    )
    _write_jsonl(
        tmp_path / "baked" / "link_graph.jsonl",
        [
            {"from_doc_id": "manual/a", "to_doc_id": "manual/b"},
            {"from_doc_id": "manual/a", "to_doc_id": "manual/b"},  # duplicate
            {"from_doc_id": "manual/a", "to_doc_id": "manual/glossary"},
            {"from_doc_id": "manual/c", "to_doc_id": "manual/a"},
            {"from_doc_id": "manual/b", "to_doc_id": "manual/a"},
        ],
    )
    return ops.DocStore(cfg)


def test_related_outgoing_dedupes_neighbors(monkeypatch, tmp_path: Path):
    store = _build_store(monkeypatch, tmp_path)
    docs = store.related("manual/a", mode="outgoing", limit=10)

    assert [d.doc_id for d in docs] == ["manual/b", "manual/glossary"]


def test_related_incoming_and_bidirectional_modes(monkeypatch, tmp_path: Path):
    store = _build_store(monkeypatch, tmp_path)
    incoming = store.related("manual/a", mode="incoming", limit=10)
    bidirectional = store.related("manual/a", mode="bidirectional", limit=10)

    assert [d.doc_id for d in incoming] == ["manual/c", "manual/b"]
    assert [d.doc_id for d in bidirectional] == ["manual/b", "manual/glossary", "manual/c"]


def test_related_supports_exclusion_filters(monkeypatch, tmp_path: Path):
    store = _build_store(monkeypatch, tmp_path)
    docs = store.related(
        "manual/a",
        mode="outgoing",
        limit=10,
        exclude_doc_ids=["manual/glossary"],
        exclude_source_types=["manual"],
    )
    assert docs == []
