import json
from pathlib import Path

from unity_docs_mcp.config import Config, PathsConfig
from unity_docs_mcp.index.index_cli import index
from unity_docs_mcp.index.search import HybridSearcher


def _write_chunks(path: Path) -> None:
    chunks = [
        {
            "chunk_id": "chunk-1",
            "doc_id": "manual/job-system-parallel-for-jobs",
            "source_type": "manual",
            "title": "Parallel jobs",
            "heading_path": ["Parallel jobs"],
            "origin_path": "Documentation/en/Manual/job-system-parallel-for-jobs.html",
            "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/job-system-parallel-for-jobs.html",
            "text": "Use IJobParallelFor when processing many independent elements.",
        },
        {
            "chunk_id": "chunk-2",
            "doc_id": "manual/job-system-creating-jobs",
            "source_type": "manual",
            "title": "Create and run a job",
            "heading_path": ["Create and run a job"],
            "origin_path": "Documentation/en/Manual/job-system-creating-jobs.html",
            "canonical_url": "https://docs.unity3d.com/6000.3/Documentation/Manual/job-system-creating-jobs.html",
            "text": "Schedule jobs and complete dependencies.",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in chunks:
            f.write(json.dumps(row) + "\n")


def _fts_only_config(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.paths = PathsConfig(
        root=str(tmp_path),
        raw_zip=str(tmp_path / "raw" / "UnityDocumentation.zip"),
        raw_unzipped=str(tmp_path / "raw" / "UnityDocumentation"),
        baked_dir=str(tmp_path / "baked"),
        index_dir=str(tmp_path / "index"),
    )
    cfg.index.vector = "none"
    cfg.mcp.min_score = 0.0
    return cfg


def test_index_fts_only_skips_vector_artifacts(tmp_path: Path):
    cfg = _fts_only_config(tmp_path)
    _write_chunks(tmp_path / "baked" / "chunks.jsonl")
    stats = index(cfg)

    assert stats["chunks"] == 2
    assert stats["vectors_enabled"] is False
    assert (tmp_path / "index" / "fts.sqlite").exists()
    assert not (tmp_path / "index" / "vectors.faiss").exists()
    assert not (tmp_path / "index" / "vectors_meta.jsonl").exists()


def test_search_fts_only_returns_lexical_results(tmp_path: Path):
    cfg = _fts_only_config(tmp_path)
    _write_chunks(tmp_path / "baked" / "chunks.jsonl")
    index(cfg)

    searcher = HybridSearcher(cfg, tmp_path / "index")
    results = searcher.search("IJobParallelFor", k=3)

    assert results
    assert results[0].doc_id == "manual/job-system-parallel-for-jobs"
