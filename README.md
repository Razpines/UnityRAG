# UnityRAG

UnityRAG is a local Unity docs assistant for Codex/Claude that provides accurate, versioned citations from Unity's official offline documentation.

MCP tools: `search` / `open` / `related` / `list_files` / `status`

## Quick Start (recommended)

1) Run setup
- Windows: double-click `setup.bat` (or run it in a terminal).
- macOS/Linux: `bash setup.sh`
- This downloads the Unity offline docs, builds the local index, and cleans up raw files to save space.

2) Add the MCP server to your agent
- Codex: copy `examples/codex_mcp_config.json` into your Codex MCP config.
- Codex CLI: use `codex mcp ...` to add a server (see Codex CLI docs for exact syntax).
- Claude Desktop: copy `examples/claude_desktop_config.json` into your Claude config.
- Update the `UNITY_DOCS_MCP_ROOT` path to your clone.
- macOS/Linux: use `start_server.sh` and the `*_unix.json` examples.

3) Restart your agent
- It will auto-start the HTTP MCP server and connect at `http://127.0.0.1:8765/mcp`.

4) Try it
Ask: "How do I schedule an IJobParallelFor with batch size?"

The model should call `unity_docs.search`, then cite the results.

## Why this exists
- Problem: Unity MCPs and model knowledge can be stale; this uses the official Unity offline docs for your chosen version.
- What it does: Downloads Unity's offline docs zip, bakes HTML -> clean text chunks, builds a hybrid index (FTS + vectors), and serves MCP tools.
- What it doesn't do: No web crawling; no docs shipped in this repo.

## One-command path
```
unitydocs install --version 6000.3
unitydocs mcp
```
Under the hood this runs download, bake, and index idempotently. Then start the HTTP MCP server.

## Content & licensing
This project does not include Unity documentation. On setup, it downloads Unity's official offline documentation zip and builds local artifacts on your machine.

Unity states that code snippets are under the Unity Companion License, and other Manual/Scripting Reference content is under CC BY-NC-ND 4.0.
Do not commit `data/` artifacts to public repos.

## Advanced docs
- [docs/README.md](docs/README.md)

## About
I’m a solo indie developer and I use coding agents every day. I built UnityRAG because quick, reliable doc lookups (especially for the newest Unity 6.3 features) were missing, and I wanted a frictionless way to cite the official docs.  
More projects: https://razpines.github.io
