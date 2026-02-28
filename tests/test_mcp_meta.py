from types import SimpleNamespace

import unity_docs_mcp.mcp_server as mcp_server
from unity_docs_mcp.config import Config


class _FakeDocStore:
    def __init__(self) -> None:
        self.config = Config()
        self._available_source_types = ["manual"]

    def search(self, query: str, k: int = 6, source_types=None):
        return [
            SimpleNamespace(
                chunk_id="chunk-1",
                doc_id="manual/job-system-parallel-for-jobs",
                title="Parallel jobs",
                heading_path=["Parallel jobs"],
                snippet="Use IJobParallelFor and Schedule(length, batchCount).",
                origin_path="Documentation/en/Manual/job-system-parallel-for-jobs.html",
                source_type="manual",
                score=0.42,
                canonical_url="https://docs.unity3d.com/6000.3/Documentation/Manual/job-system-parallel-for-jobs.html",
            )
        ]

    def open_doc(self, doc_id=None, path=None):
        if doc_id == "missing":
            return None
        return SimpleNamespace(
            doc_id="manual/job-system-parallel-for-jobs",
            title="Parallel jobs",
            source_type="manual",
            origin_path="Documentation/en/Manual/job-system-parallel-for-jobs.html",
            canonical_url="https://docs.unity3d.com/6000.3/Documentation/Manual/job-system-parallel-for-jobs.html",
            text_md="ParallelFor jobs split work into batches.",
        )

    def list_files(self, pattern: str, limit: int = 20):
        return [
            SimpleNamespace(
                doc_id="manual/job-system-parallel-for-jobs",
                title="Parallel jobs",
                source_type="manual",
                origin_path="Documentation/en/Manual/job-system-parallel-for-jobs.html",
                canonical_url="https://docs.unity3d.com/6000.3/Documentation/Manual/job-system-parallel-for-jobs.html",
            )
        ]

    def related(
        self,
        doc_id: str,
        limit: int = 10,
        mode: str = "outgoing",
        exclude_doc_ids=None,
        exclude_source_types=None,
    ):
        docs = [
            SimpleNamespace(
                doc_id="manual/job-system-creating-jobs",
                title="Create and run a job",
                source_type="manual",
                origin_path="Documentation/en/Manual/job-system-creating-jobs.html",
                canonical_url="https://docs.unity3d.com/6000.3/Documentation/Manual/job-system-creating-jobs.html",
            ),
            SimpleNamespace(
                doc_id="manual/glossary",
                title="Glossary",
                source_type="manual",
                origin_path="Documentation/en/Manual/Glossary.html",
                canonical_url="https://docs.unity3d.com/6000.3/Documentation/Manual/Glossary.html",
            ),
        ]
        excluded_docs = set(exclude_doc_ids or [])
        excluded_sources = {s.lower() for s in (exclude_source_types or [])}
        filtered = [
            d
            for d in docs
            if d.doc_id not in excluded_docs and d.source_type.lower() not in excluded_sources
        ]
        return filtered[:limit]

    def available_source_types(self):
        return list(self._available_source_types)

    def known_source_types(self):
        return ["manual", "scriptref"]

    def source_type_counts(self):
        return {"docs": {"manual": 1}, "chunks": {"manual": 1}}


def _install_fake_docstore(monkeypatch):
    fake = _FakeDocStore()
    monkeypatch.setattr(mcp_server, "_get_docstore", lambda: fake)
    return fake


def test_search_includes_meta(monkeypatch):
    _install_fake_docstore(monkeypatch)
    result = mcp_server.search("IJobParallelFor batch size", k=3)
    assert isinstance(result, list)
    assert result
    assert result[0]["doc_id"] == "manual/job-system-parallel-for-jobs"
    assert result[0]["meta"]["unity_version"] == "6000.3"
    assert result[0]["meta"]["retrieval_mode"] == "hybrid"


def test_search_meta_reports_fts_only_when_vector_disabled(monkeypatch):
    fake = _install_fake_docstore(monkeypatch)
    fake.config.index.vector = "none"
    result = mcp_server.search("IJobParallelFor batch size", k=3)
    assert result[0]["meta"]["retrieval_mode"] == "fts_only"


def test_open_includes_meta_even_when_missing(monkeypatch):
    _install_fake_docstore(monkeypatch)
    found = mcp_server.open(doc_id="manual/job-system-parallel-for-jobs")
    missing = mcp_server.open(doc_id="missing")
    assert found["meta"]["unity_version"] == "6000.3"
    assert "doc_id" in found
    assert missing["meta"]["unity_version"] == "6000.3"
    assert missing["error"] == "not_found"
    assert missing["attempted"]["doc_id"] == "missing"


def test_search_invalid_source_types_returns_actionable_error(monkeypatch):
    _install_fake_docstore(monkeypatch)
    result = mcp_server.search("Rigidbody.AddForce", source_types="scripting")
    assert result["error"] == "invalid_source_types"
    assert result["invalid_source_types"] == ["scripting"]
    assert "manual" in result["available_source_types"]


def test_search_unavailable_source_types_returns_actionable_error(monkeypatch):
    _install_fake_docstore(monkeypatch)
    result = mcp_server.search("Rigidbody.AddForce", source_types="scriptref")
    assert result["error"] == "invalid_source_types"
    assert result["invalid_source_types"] == []
    assert result["unavailable_source_types"] == ["scriptref"]


def test_search_debug_returns_results_and_debug_block(monkeypatch):
    _install_fake_docstore(monkeypatch)
    result = mcp_server.search("IJobParallelFor batch size", k=3, debug=True)
    assert "results" in result
    assert "debug" in result
    assert result["debug"]["query"] == "IJobParallelFor batch size"
    assert result["debug"]["result_count"] == 1
    assert result["results"][0]["doc_id"] == "manual/job-system-parallel-for-jobs"


def test_list_files_and_related_include_meta(monkeypatch):
    _install_fake_docstore(monkeypatch)
    files = mcp_server.list_files("*parallel-for*")
    rel = mcp_server.related("manual/job-system-parallel-for-jobs")
    assert files and rel
    assert files[0]["meta"]["unity_version"] == "6000.3"
    assert rel[0]["meta"]["unity_version"] == "6000.3"


def test_related_supports_path_mode_and_glossary_exclusion(monkeypatch):
    _install_fake_docstore(monkeypatch)
    rel = mcp_server.related(
        path="Documentation/en/Manual/job-system-parallel-for-jobs.html",
        mode="bidirectional",
        exclude_glossary=True,
    )
    assert rel
    assert all(item["doc_id"] != "manual/glossary" for item in rel)


def test_related_rejects_invalid_mode(monkeypatch):
    _install_fake_docstore(monkeypatch)
    rel = mcp_server.related(doc_id="manual/job-system-parallel-for-jobs", mode="sideways")
    assert rel["error"] == "invalid_mode"
    assert "outgoing" in rel["allowed_modes"]


def test_status_includes_meta_and_manifest_fields(monkeypatch):
    _install_fake_docstore(monkeypatch)

    def _fake_read_manifest(path):
        as_str = str(path).replace("\\", "/")
        if as_str.endswith("/baked/manifest.json"):
            return {"build_from": "local-zip", "built_on": "2026-02-20"}
        if as_str.endswith("/index/manifest.json"):
            return {"chunks": 14310}
        return {}

    monkeypatch.setattr(mcp_server, "_read_manifest", _fake_read_manifest)
    status = mcp_server.status()
    assert status["meta"]["unity_version"] == "6000.3"
    assert status["meta"]["build_from"] == "local-zip"
    assert status["meta"]["built_on"] == "2026-02-20"
    assert "paths" in status
    assert "index_manifest" in status
    assert status["available_source_types"] == ["manual"]
    assert status["source_type_counts"]["docs"]["manual"] == 1
    assert status["coverage_warnings"]
