# UnityRAG

[![CI](https://github.com/Razpines/UnityRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/Razpines/UnityRAG/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/Razpines/UnityRAG)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![GitHub Stars](https://img.shields.io/github/stars/Razpines/UnityRAG?style=social)](https://github.com/Razpines/UnityRAG/stargazers)

Local Unity documentation RAG + MCP server for coding agents.

UnityRAG grounds Codex and Claude answers in official Unity offline docs for your selected version, with citations from local artifacts.

MCP tools: `search` / `open` / `related` / `list_files` / `status`

## Quick Start

1. Install dependencies and build artifacts.

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .[dev]
unitydocs install --version 6000.3 --cleanup
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

Development/debug option:

```bash
unitydocs mcp
```

Use this when you want direct server logs/prints in your terminal instead of agent-managed auto-start.

If setup fails, run:

```bash
unitydocs doctor
unitydocs doctor --json
```

## Why UnityRAG

- Uses official Unity offline docs for versioned retrieval.
- Hybrid retrieval with SQLite FTS and FAISS vectors.
- Local-first artifacts and server operation.
- Idempotent download, bake, and index steps.

## One-Command Setup Scripts

- Windows: `setup.bat`
- macOS/Linux: `bash setup.sh`

These scripts install dependencies, download docs, bake chunks, index, and clean raw files.

Note: `setup.bat` and `setup.sh` enforce CUDA runtime validation and fail if no working CUDA torch build is available.

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
- Roadmap: `ROADMAP.md`.

## Docs

- Developer details: `docs/README.md`

## Content and Licensing

This project does not include Unity documentation. During setup, it downloads Unity's official offline docs and builds local artifacts on your machine.

Unity states code snippets are under the Unity Companion License, while other Manual and Scripting Reference content is under CC BY-NC-ND 4.0.

Do not commit `data/` artifacts.

## About

Built by an indie developer using coding agents daily, focused on reliable Unity citations over stale model memory.

More projects: https://razpines.github.io
