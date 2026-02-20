# Developer Notes

This file contains the advanced, developer-oriented details that were removed from the top-level README.

## Layout
- `data/unity/6000.3/raw`: UnityDocumentation.zip + unzipped HTML (not committed)
- `data/unity/6000.3/baked`: corpus.jsonl, chunks.jsonl, link_graph.jsonl, manifest.json
- `data/unity/6000.3/index`: fts.sqlite, vectors.faiss, vectors_meta.jsonl
- `src/unity_docs_mcp`: pipeline + MCP server
- `scripts/`: convenience wrappers (same as console scripts)

## Where files are stored / disk usage
- Zip file: `data/unity/<version>/raw/UnityDocumentation.zip`
- Unzipped HTML: `data/unity/<version>/raw/UnityDocumentation/`
- Baked artifacts: `data/unity/<version>/baked/`
- Index artifacts: `data/unity/<version>/index/`

Typical sizes (approx):
- Zip: ~743 MB (removed after setup completes)
- Unzipped HTML: ~1.0 GB (removed after setup completes)
- Baked JSONL: ~300-700 MB
- Indexes (FTS + vectors): ~1-4 GB

Reset a version:
- Windows: `rmdir /s /q data\unity\6000.3`
- macOS/Linux: `rm -rf data/unity/6000.3`

## MCP tools (summary)
- `unity_docs.search(query, k?, source_types?, path_prefix?, include_snippets?, debug?)`
- `unity_docs.open(doc_id?, path?, include_toc?, max_chars?)`
- `unity_docs.list_files(pattern, limit?)`
- `unity_docs.related(doc_id?, path?, mode?, limit?)`
- `unity_docs.status()`

## Configuration
Edit `config.yaml` (optional). Defaults: Unity 6.3 URL, paths under `data/unity/6000.3`, heading-based chunking, bge-small-en-v1.5 local embeddings, FAISS vectors, FTS5 lexical.

## Examples
- `examples/codex_mcp_config.json` (Windows)
- `examples/claude_desktop_config.json` (Windows)
- `examples/codex_mcp_config_unix.json` (macOS/Linux)
- `examples/claude_desktop_config_unix.json` (macOS/Linux)

## Troubleshooting
- `faiss-cpu` install fails: ensure you are on Python 3.12 and install with `pip install faiss-cpu`. On some platforms, use conda or build from source.
- Setup scripts are CUDA-only now: `setup.bat` and `setup.sh` try torch channels in order (`cu128`, `cu121`, `cu118`) and accept a channel only if `torch.cuda.is_available()` is true at runtime.
- If one channel installs but CUDA runtime is unavailable, setup automatically falls back to the next channel.
- If all channels fail runtime validation, setup exits (no CPU fallback in setup scripts).
- Search returns garbage: delete `data/unity/<version>/baked` and re-run `unitydocs-bake` to validate extraction quality.
- Port already used: set `UNITY_DOCS_MCP_PORT` (and `UNITY_DOCS_MCP_HOST` if needed).
- Download blocked or slow: download UnityDocumentation.zip manually, place it under `data/unity/<version>/raw/`, then re-run setup.
- `python` not found: install Python 3.12+ or run `setup.bat` to use the repo-local portable Python.
- Data artifacts accidentally tracked: run `python scripts/check_no_data_tracked.py` and remove listed files from git.

## Testing
```
pytest
```

## Notes
- Bake/index steps are idempotent: existing artifacts with matching config/version skip work.
- Link extraction ignores external and anchor-only links; internal links are normalized to doc_ids for related lookups.

## Codex/Claude MCP wiring (HTTP server, auto-started)
- Add a server entry pointing to the HTTP launcher inside the venv. Example (Windows):
  ```json
  {
    "servers": {
      "unity-docs": {
        "command": ".\\.venv\\Scripts\\unitydocs-mcp-http.exe",
        "args": [],
        "env": {
          "UNITY_DOCS_MCP_ROOT": "C:\\projects\\UnityRAG",
          "UNITY_DOCS_MCP_HOST": "127.0.0.1",
          "UNITY_DOCS_MCP_PORT": "8765"
        }
      }
    }
  }
  ```
  Alternatively, you can point to `start_server.bat` or `start_server.sh` if you want a visible console window. Adjust the `UNITY_DOCS_MCP_ROOT` path to your clone; with this env the server finds `config.yaml` and data without changing the working directory. Codex/Claude will auto-start the MCP server and connect over HTTP at `http://127.0.0.1:8765/mcp`.
