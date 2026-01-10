# UnityRAG

[![CI](https://img.shields.io/github/actions/workflow/status/Razpines/UnityRAG/ci.yml?label=CI)](https://github.com/Razpines/UnityRAG/actions)
[![License](https://img.shields.io/github/license/Razpines/UnityRAG)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/unity-docs-mcp?label=PyPI)](https://pypi.org/project/unity-docs-mcp/)

Local, offline-ready Unity 6.3 documentation bake/index pipeline with an MCP server exposing search/open/list/related tools.

MCP tools: `search` / `open` / `related` / `list_files` / `status`

## Why this exists
- Problem: Unity MCPs and model knowledge can be stale; this uses the official Unity offline docs for your chosen version.
- What it does: Downloads Unity’s offline docs zip, bakes HTML -> clean text chunks, builds a hybrid index (FTS + vectors), and serves MCP tools.
- What it doesn’t do: No web crawling; no docs shipped in this repo.

## One-command path (recommended)
```
unitydocs install --version 6000.3
unitydocs mcp
```
Under the hood this runs download, bake, and index idempotently, then starts the HTTP MCP server.

## Quickstart (manual steps)

1) Create env & install deps
```
python -m venv .venv
```

2) Activate venv
```
Windows: .\.venv\Scripts\activate
macOS/Linux: source .venv/bin/activate
```

3) Install deps
```
pip install -e .[dev]
```

4) Ensure Unity docs artifacts exist (download+unzip are idempotent)
```
unitydocs-setup
```

5) Bake HTML to LLM-friendly corpus/chunks/link graph
```
unitydocs-bake
```

6) Build hybrid indexes (SQLite FTS5 + FAISS vectors)
```
unitydocs-index
```

7) Run MCP server (HTTP)
```
unitydocs-mcp-http
```

## 30-second smoke test
Ask Codex/Claude:
“How do I schedule an IJobParallelFor with batch size?”

The model should call `unity_docs.search`, then cite the results.

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

Typical sizes vary by version and model:
- Zip: ~1-2 GB
- Unzipped HTML: ~4-6 GB
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
- `examples/codex_mcp_config.json`
- `examples/claude_desktop_config.json`

## Content & licensing
This project does not include Unity documentation. On setup, it downloads Unity’s official offline documentation zip and builds local artifacts on your machine.

Unity states that code snippets are under the Unity Companion License, and other Manual/Scripting Reference content is under CC BY-NC-ND 4.0.
Do not commit `data/` artifacts to public repos.

## Troubleshooting
- `faiss-cpu` install fails: ensure you are on Python 3.12 and install with `pip install faiss-cpu`. On some platforms, use conda or build from source.
- CPU-only torch: install a CUDA-enabled wheel (e.g., `pip install --force-reinstall torch==2.2.2+cu121 --index-url https://download.pytorch.org/whl/cu121`).
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
  Alternatively, you can point to `start_server.bat` if you want a visible console window. Adjust the `UNITY_DOCS_MCP_ROOT` path to your clone; with this env the server finds `config.yaml` and data without changing the working directory. Codex/Claude will auto-start the MCP server and connect over HTTP at `http://127.0.0.1:8765/mcp`.
