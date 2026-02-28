import json
from pathlib import Path
from types import SimpleNamespace

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
                "doc_id": "scriptreference/rigidbody-addforce",
                "source_type": "scriptref",
                "title": "Rigidbody.AddForce",
                "text_md": "Adds a force to the rigidbody.",
                "origin_path": "Documentation/en/ScriptReference/Rigidbody.AddForce.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Rigidbody.AddForce.html",
            },
            {
                "doc_id": "manual/rigidbodiesoverview",
                "source_type": "manual",
                "title": "Introduction to rigid body physics",
                "text_md": "Mentions AddForce usage in prose.",
                "origin_path": "Documentation/en/Manual/RigidbodiesOverview.html",
                "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/RigidbodiesOverview.html",
            },
        ],
    )
    _write_jsonl(tmp_path / "baked" / "link_graph.jsonl", [])
    return ops.DocStore(cfg)


def test_resolve_symbol_matches_exact_title_and_normalized_form(monkeypatch, tmp_path: Path):
    store = _build_store(monkeypatch, tmp_path)

    exact = store.resolve_symbol("Rigidbody.AddForce", limit=3)
    normalized = store.resolve_symbol("rigidbodyaddforce", limit=3)

    assert exact
    assert exact[0]["doc_id"] == "scriptreference/rigidbody-addforce"
    assert exact[0]["match_kind"] in {"symbol_exact", "symbol_normalized"}
    assert normalized
    assert normalized[0]["doc_id"] == "scriptreference/rigidbody-addforce"


def test_resolve_symbol_falls_back_to_search(monkeypatch, tmp_path: Path):
    store = _build_store(monkeypatch, tmp_path)

    def _fake_search(query: str, k: int = 6, source_types=None):
        return [
            SimpleNamespace(doc_id="manual/rigidbodiesoverview"),
        ]

    store.search = _fake_search  # type: ignore[method-assign]
    result = store.resolve_symbol("CompletelyUnknownSymbol", limit=3)

    assert result
    assert result[0]["doc_id"] == "manual/rigidbodiesoverview"
    assert result[0]["match_kind"] == "search_fallback"
