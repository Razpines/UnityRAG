# Developer Notes

This file contains the advanced, developer-oriented details that were removed from the top-level README.

## Layout
- `data/unity/<version>/raw`: UnityDocumentation.zip + unzipped HTML (not committed)
- `data/unity/<version>/baked`: corpus.jsonl, chunks.jsonl, link_graph.jsonl, manifest.json
- `data/unity/<version>/index`: always `fts.sqlite`; plus `vectors.faiss` and `vectors_meta.jsonl` in hybrid mode
- `src/unity_docs_mcp`: pipeline + MCP server
- `scripts/`: convenience wrappers (same as console scripts)

## Where files are stored / disk usage
- Zip file: `data/unity/<version>/raw/UnityDocumentation.zip`
- Unzipped HTML: `data/unity/<version>/raw/UnityDocumentation/` (currently Manual HTML pages only)
- Baked artifacts: `data/unity/<version>/baked/`
- Index artifacts: `data/unity/<version>/index/`

Typical sizes (approx):
- Zip: ~743 MB (removed after setup completes)
- Unzipped HTML: ~1.0 GB (removed after setup completes)
- Baked JSONL: ~300-700 MB
- Indexes (FTS + vectors): ~1-4 GB

Reset a version:
- Windows: `rmdir /s /q data\unity\<version>`
- macOS/Linux: `rm -rf data/unity/<version>`

## MCP tools (summary)
- `unity_docs.search(query, k?, source_types?, group_by?, debug?)`
- `unity_docs.resolve_symbol(symbol, limit?)`
- `unity_docs.open(doc_id?, path?, max_chars?, full?)`
- `unity_docs.list_files(pattern, limit?)`
- `unity_docs.related(doc_id?, path?, mode?, limit?, exclude_doc_ids?, exclude_source_types?, exclude_glossary?)`
- `unity_docs.status()`

Notes:
- `search(...)` defaults to `group_by="doc"` (one result per doc). Use `group_by="chunk"` for raw chunk-level results.
- `search(...)` returns a list for normal successful calls. It returns a structured object for `debug=true`, invalid `group_by`, or invalid/unavailable `source_types`.
- `open(...)` returns a structured `{ error: "not_found", ... }` object when the document cannot be resolved.
- `related(...)` returns a structured error for invalid modes or unresolved `doc_id`/`path`.

Example response metadata (present in all tools):
```json
{
  "meta": {
    "unity_version": "6000.3",
    "index_mode": { "lexical": "sqlite_fts5", "vector": "faiss" },
    "retrieval_mode": "hybrid",
    "build_from": "local-zip",
    "built_on": "2026-02-20"
  }
}
```

## Configuration
- `config.yaml`: tracked base defaults.
- `config.local.yaml`: optional untracked local overrides written by setup.
- Effective config is layered in this order: `config.yaml` -> `config.local.yaml` -> `UNITY_DOCS_MCP_CONFIG` -> explicit `--config`.
- Unity version is required at runtime via `UNITY_DOCS_MCP_UNITY_VERSION`; version/path/download values are derived from this env var.
- Set `index.vector: "none"` in local overrides for explicit FTS-only mode.

## Examples
- `examples/codex_mcp_config.json` (Windows)
- `examples/claude_desktop_config.json` (Windows)
- `examples/codex_mcp_config_unix.json` (macOS/Linux)
- `examples/claude_desktop_config_unix.json` (macOS/Linux)

## Troubleshooting
- Run preflight diagnostics first:
  - `unitydocs doctor`
  - `unitydocs doctor --json` (for structured bug reports/automation)
  - `unitydocs doctor --json --with-setup-snapshot` (include latest setup snapshot reference)
  - `unitydocs report --summary <short-problem> --prefill-issue` (writes a redacted support bundle)
- Setup scripts now prompt for mode:
  - `CUDA`: installs `.[dev,vector]`, then validates CUDA torch (`cu128 -> cu121 -> cu118` fallback).
  - `CPU-only`: installs `.[dev]` and configures `index.vector: none` (FTS-only, no vector deps).
- Setup writes mode into repo-local `config.local.yaml` and writes `UNITY_DOCS_MCP_UNITY_VERSION` into generated MCP client configs.
- If all CUDA channels fail runtime validation, CUDA mode exits; rerun setup and choose CPU-only if desired.
- Search returns garbage: delete `data/unity/<version>/baked` and re-run `unitydocs-bake` to validate extraction quality.
- Port already used: set `UNITY_DOCS_MCP_PORT` (and `UNITY_DOCS_MCP_HOST` if needed).
- Download blocked or slow: download UnityDocumentation.zip manually, place it under `data/unity/<version>/raw/`, then re-run setup.
- `python` not found: install Python 3.12+ or run `setup.bat` to use the repo-local portable Python.
- Data artifacts accidentally tracked: run `python scripts/check_no_data_tracked.py` and remove listed files from git.
- Setup snapshots are written under `reports/setup/` as:
  - `setup-diagnostics-<timestamp>.json`
  - `setup-diagnostics-latest.json`

## How To Report
- Generate a bundle:
  - `unitydocs report --summary "setup failed on CUDA validation" --prefill-issue`
- Attach/share files from `reports/latest` (or your `--output` directory).
- The report includes:
  - redacted config layers
  - effective config / doctor JSON
  - environment + system snapshot
  - copied local setup logs when present

## Testing
```
pytest
```

Optional real-doc extraction integration tests:
```
UNITYDOCS_E2E=1 pytest tests/test_extraction.py
```
These require local Unity raw docs under `data/unity/<version>/raw/UnityDocumentation`.

## Notes
- Bake/index steps are idempotent: existing artifacts with matching config/version skip work.
- Link extraction ignores external and anchor-only links; internal links are normalized to doc_ids for related lookups.

## Codex/Claude MCP wiring (stdio MCP, auto-started)
- Setup can auto-configure Codex/Claude MCP files now (recommended).
- If you need manual wiring, use the repo venv `unitydocs-mcp` entrypoint with an absolute path. Example (Windows):
  ```json
  {
    "servers": {
      "unity-docs": {
        "command": "C:\\projects\\UnityRAG\\.venv\\Scripts\\unitydocs-mcp.exe",
        "args": [],
        "env": {
          "UNITY_DOCS_MCP_UNITY_VERSION": "6000.3"
        }
      }
    }
  }
  ```
  macOS/Linux equivalent command: `/path/to/UnityRAG/.venv/bin/unitydocs-mcp`.
- Include `UNITY_DOCS_MCP_UNITY_VERSION` in MCP server `env` for reliable startup.
- Optional advanced overrides remain available via `UNITY_DOCS_MCP_ROOT` / `UNITY_DOCS_MCP_CONFIG`.
