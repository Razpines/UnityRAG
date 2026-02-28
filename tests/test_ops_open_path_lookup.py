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


def test_open_doc_accepts_origin_path_round_trip(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(ops, "HybridSearcher", _FakeSearcher)
    cfg = _cfg(tmp_path)
    _write_jsonl(
        tmp_path / "baked" / "corpus.jsonl",
        [
            {
                "doc_id": "manual/rigidbodiesoverview",
                "source_type": "manual",
                "title": "Introduction to rigid body physics",
                "text_md": "Body text",
                "origin_path": "Documentation/en/Manual/RigidbodiesOverview.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/RigidbodiesOverview.html",
            }
        ],
    )
    _write_jsonl(tmp_path / "baked" / "link_graph.jsonl", [])

    store = ops.DocStore(cfg)

    record = store.open_doc(path="Documentation/en/Manual/RigidbodiesOverview.html")
    assert record is not None
    assert record.doc_id == "manual/rigidbodiesoverview"

    # Alternate path spellings should also map to the same corpus doc.
    record2 = store.open_doc(path="documentation\\en\\manual\\rigidbodiesoverview.html")
    assert record2 is not None
    assert record2.doc_id == "manual/rigidbodiesoverview"


def test_open_doc_accepts_canonical_url_lookup(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(ops, "HybridSearcher", _FakeSearcher)
    cfg = _cfg(tmp_path)
    _write_jsonl(
        tmp_path / "baked" / "corpus.jsonl",
        [
            {
                "doc_id": "manual/class-rigidbody",
                "source_type": "manual",
                "title": "Rigidbody component reference",
                "text_md": "Body text",
                "origin_path": "Documentation/en/Manual/class-Rigidbody.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/class-Rigidbody.html",
            }
        ],
    )
    _write_jsonl(tmp_path / "baked" / "link_graph.jsonl", [])

    store = ops.DocStore(cfg)
    record = store.open_doc(path="https://docs.unity3d.com/6000.3/Documentation/Manual/class-Rigidbody.html")

    assert record is not None
    assert record.doc_id == "manual/class-rigidbody"
