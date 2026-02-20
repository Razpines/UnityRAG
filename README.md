# UnityRAG

[![CI](https://github.com/Razpines/UnityRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/Razpines/UnityRAG/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/Razpines/UnityRAG)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![GitHub Stars](https://img.shields.io/github/stars/Razpines/UnityRAG?style=social)](https://github.com/Razpines/UnityRAG/stargazers)

Local Unity documentation RAG + MCP server for coding agents.

UnityRAG grounds Codex and Claude answers in official Unity offline docs for your selected version, with citations from local artifacts.

MCP tools: `search` / `open` / `related` / `list_files` / `status`

## Quick Start

1. Run setup (recommended).
- Windows: double-click `setup.bat` (or run it in a terminal).
- macOS/Linux: `bash setup.sh`
- Setup prompts for mode:
  - `CUDA` (hybrid retrieval: FTS + vectors)
  - `CPU-only` (FTS-only retrieval, no transformers/faiss)
- Setup writes the selected version/mode into local `config.yaml` so MCP startup uses the same retrieval mode.
- This downloads the Unity offline docs, builds the selected local index, and cleans up raw files to save space.

```bash
# Windows
setup.bat

# macOS/Linux
bash setup.sh
```

2. Configure your agent with files in `examples/`.
- Codex: `examples/codex_mcp_config.json`
- Claude Desktop: `examples/claude_desktop_config.json`
- macOS/Linux: `*_unix.json` variants

Set:
- `UNITY_DOCS_MCP_ROOT` to your local clone path
- `UNITY_DOCS_MCP_HOST=127.0.0.1`
- `UNITY_DOCS_MCP_PORT=8765`

3. Restart your agent and run a prompt:
- "How do I schedule an `IJobParallelFor` with batch size?"
- "Open `Mesh.SetVertices` and show related docs."

If setup fails, run:

```bash
unitydocs doctor
unitydocs doctor --json
```

## Why UnityRAG

- Uses official Unity offline docs for versioned retrieval.
- Hybrid retrieval with SQLite FTS and FAISS vectors, or explicit FTS-only mode for CPU-only setups.
- Local-first artifacts and server operation.
- Idempotent download, bake, and index steps.

## Manual and Advanced Setup

For development and debugging, use manual setup and server start:

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .[dev]
# For CUDA/hybrid installs, use:
# pip install -e .[dev,vector]
unitydocs install --version 6000.3 --cleanup
unitydocs mcp
```

Notes:
- In `CUDA` mode, setup scripts enforce CUDA torch and fail if no working CUDA runtime is detected.
- In `CPU-only` mode, setup configures `index.vector: none` and skips vector dependencies.

## Commands

```bash
unitydocs install --version 6000.3
unitydocs mcp
unitydocs doctor
unitydocs-bake
unitydocs-index --dry-run
pytest
```

## Contributing

- Read `CONTRIBUTING.md`.

## Docs

- Developer details: `docs/README.md`

## Content and Licensing

This project does not include Unity documentation. During setup, it downloads Unity's official offline docs and builds local artifacts on your machine.

Unity states code snippets are under the Unity Companion License, while other Manual and Scripting Reference content is under CC BY-NC-ND 4.0.

Do not commit `data/` artifacts.

## About

Built by an indie developer using coding agents daily, focused on reliable Unity citations over stale model memory.

More projects: https://razpines.github.io
