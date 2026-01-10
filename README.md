# UnityRAG

Local, offline-ready Unity 6.3 documentation bake/index pipeline with an MCP server exposing search/open/list/related tools.

## Quickstart

1) Create env & install deps
```
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .[dev]
```

2) Ensure Unity docs artifacts exist (download+unzip are idempotent)
```
unitydocs-setup
```

3) Bake HTML to LLM-friendly corpus/chunks/link graph
```
unitydocs-bake
```

4) Build hybrid indexes (SQLite FTS5 + FAISS vectors)
```
unitydocs-index
```

5) Run MCP server (HTTP)
```
unitydocs-mcp-http
```

## Layout
- `data/unity/6000.3/raw`: UnityDocumentation.zip + unzipped HTML (not committed)
- `data/unity/6000.3/baked`: corpus.jsonl, chunks.jsonl, link_graph.jsonl, manifest.json
- `data/unity/6000.3/index`: fts.sqlite, vectors.faiss, vectors_meta.jsonl
- `src/unity_docs_mcp`: pipeline + MCP server
- `scripts/`: convenience wrappers (same as console scripts)

## MCP tools (summary)
- `unity_docs.search(query, k?, source_types?, path_prefix?, include_snippets?, debug?)`
- `unity_docs.open(doc_id?, path?, include_toc?, max_chars?)`
- `unity_docs.list_files(pattern, limit?)`
- `unity_docs.related(doc_id?, path?, mode?, limit?)`
- `unity_docs.status()`

## Configuration
Edit `config.yaml` (optional). Defaults: Unity 6.3 URL, paths under `data/unity/6000.3`, heading-based chunking, bge-small-en-v1.5 local embeddings, FAISS vectors, FTS5 lexical.

## Testing
```
pytest
```

## Notes
- Bake/index steps are idempotent: existing artifacts with matching config/version skip work.
- Link extraction ignores external and anchor-only links; internal links are normalized to doc_ids for related lookups.
- If you want CUDA for embeddings, install a CUDA-enabled torch wheel in the venv (e.g., `pip install --force-reinstall torch==2.2.2+cu121 --index-url https://download.pytorch.org/whl/cu121`). The current torch in this venv may be CPU-only.

## Codex/Claude MCP wiring (HTTP server, auto-started)
- Add a server entry pointing to the HTTP launcher inside the venv. Example (Windows):
  ```json
  {
    "servers": {
      "unity-docs": {
        "command": ".\\\\.venv\\\\Scripts\\\\unitydocs-mcp-http.exe",
        "args": [],
        "env": {
          "UNITY_DOCS_MCP_ROOT": "C:\\\\projects\\\\UnityRAG",
          "UNITY_DOCS_MCP_HOST": "127.0.0.1",
          "UNITY_DOCS_MCP_PORT": "8765"
        }
      }
    }
  }
  ```
  Alternatively, you can point to `start_server.bat` if you want a visible console window. Adjust the `UNITY_DOCS_MCP_ROOT` path to your clone; with this env the server finds `config.yaml` and data without changing the working directory. Codex/Claude will auto-start the MCP server and connect over HTTP at `http://127.0.0.1:8765/mcp`.
