# UnityRAG

[![CI](https://github.com/Razpines/UnityRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/Razpines/UnityRAG/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/Razpines/UnityRAG)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![GitHub Stars](https://img.shields.io/github/stars/Razpines/UnityRAG?style=social)](https://github.com/Razpines/UnityRAG/stargazers)

Local Unity documentation RAG + MCP server for coding agents.

UnityRAG grounds Codex and Claude answers in official Unity offline docs for your selected version, with citations from local artifacts.

MCP tools: `search` / `open` / `related` / `list_files` / `status`

## Quick Start

1. Run setup.

```bash
# Windows
setup.bat

# macOS/Linux
bash setup.sh
```

Setup will prompt you for:
- Retrieval mode: `CUDA` (hybrid) or `CPU-only` (FTS-only)
- MCP client auto-config: `Codex`, `Claude Desktop`, `Both`, or `Skip`
- Setup writes machine-local overrides to `config.local.yaml` (untracked), while `config.yaml` remains tracked defaults.

2. Restart your agent.

3. Test:
- "How do I schedule an `IJobParallelFor` with batch size?"
- "Open `Mesh.SetVertices` and show related docs."

If you chose `Skip`, configure manually using files in `examples/` with an absolute `unitydocs-mcp` path plus `UNITY_DOCS_MCP_ROOT` and `UNITY_DOCS_MCP_CONFIG`.

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

Optional advanced overrides:
- `UNITY_DOCS_MCP_ROOT`
- `UNITY_DOCS_MCP_CONFIG`
- `UNITY_DOCS_MCP_HOST`
- `UNITY_DOCS_MCP_PORT`

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
