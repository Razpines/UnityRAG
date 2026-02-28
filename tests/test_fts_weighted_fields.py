from pathlib import Path

from unity_docs_mcp.index.fts import ingest_chunks, init_db, search_fts


def test_search_fts_matches_structured_fields_when_text_lacks_symbol(tmp_path: Path):
    conn = init_db(tmp_path / "fts.sqlite")
    ingest_chunks(
        conn,
        [
            (
                "chunk-scriptref",
                "scriptreference/mesh-setvertices",
                "scriptref",
                "Mesh.SetVertices",
                "Mesh/SetVertices",
                "Documentation/en/ScriptReference/Mesh.SetVertices.html",
                "https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh.SetVertices.html",
                "Updates mesh buffers efficiently.",
            ),
            (
                "chunk-manual",
                "manual/mesh-vertex-data",
                "manual",
                "Mesh vertex data",
                "Mesh vertex data",
                "Documentation/en/Manual/mesh-vertex-data.html",
                "https://docs.unity3d.com/6000.3/Documentation/Manual/mesh-vertex-data.html",
                "This section describes vertex channels and data layout.",
            ),
        ],
    )

    hits = search_fts(conn, "Mesh.SetVertices", limit=5)
    chunk_ids = [chunk_id for chunk_id, _score in hits]
    assert "chunk-scriptref" in chunk_ids


def test_search_fts_prioritizes_title_docid_matches_over_text_only(tmp_path: Path):
    conn = init_db(tmp_path / "fts.sqlite")
    ingest_chunks(
        conn,
        [
            (
                "chunk-strong",
                "scriptreference/mesh-setvertices",
                "scriptref",
                "Mesh.SetVertices",
                "Mesh/SetVertices",
                "Documentation/en/ScriptReference/Mesh.SetVertices.html",
                "https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Mesh.SetVertices.html",
                "Buffer update APIs.",
            ),
            (
                "chunk-weak",
                "manual/mesh-vertex-data",
                "manual",
                "Mesh vertex data",
                "Mesh vertex data",
                "Documentation/en/Manual/mesh-vertex-data.html",
                "https://docs.unity3d.com/6000.3/Documentation/Manual/mesh-vertex-data.html",
                "Mesh SetVertices is mentioned here in passing.",
            ),
        ],
    )

    hits = search_fts(conn, "Mesh.SetVertices", limit=5)
    assert hits
    assert hits[0][0] == "chunk-strong"
