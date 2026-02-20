# Repository Guidelines

## Project Structure & Modules
- Source: `src/unity_docs_mcp/` (bake, index, MCP server, setup helpers).
- Data: `data/unity/6000.3/raw` (Unity docs zip + unzip), `data/unity/6000.3/baked`, `data/unity/6000.3/index` (artifact outputs; git-ignored).
- Scripts/entrypoints: console scripts (`unitydocs-setup`, `unitydocs-bake`, `unitydocs-index`, `unitydocs-mcp`) and wrappers in `scripts/`.
- Tests: `tests/` (pytest).
- Config: tracked `config.yaml` base defaults + optional untracked `config.local.yaml` overrides. Paths resolve relative to repo by default, with `UNITY_DOCS_MCP_ROOT` as an advanced override.

## Build, Test, Run
- Create env:
  - CPU/FTS-only: `python -m venv .venv && .venv\Scripts\activate && pip install -e .[dev]`
  - CUDA/hybrid: `python -m venv .venv && .venv\Scripts\activate && pip install -e .[dev,vector]`
- Ensure artifacts: `unitydocs-setup` (downloads if missing, bakes, indexes).
- Bake only: `unitydocs-bake`.
- Index only: `unitydocs-index` (use `--dry-run` to verify device/model without embedding).
- MCP server: `unitydocs-mcp` (stdio; setup can auto-configure Codex/Claude with absolute command paths, no env vars required for default flow).
- Tests: `pytest`.

## Coding Style & Naming
- Python 3.12+, 4-space indentation, type hints throughout.
- Keep functions small; prefer explicit names (`bake_*`, `index_*`, `ensure_*`).
- Inline comments only for non-obvious logic (e.g., path resolution, CUDA selection).
- Avoid machine-specific absolute paths in committed files; rely on repo-relative defaults unless advanced env overrides are needed.

## Testing Guidelines
- Framework: pytest.
- Name tests `test_*.py` / functions `test_*`.
- Run `pytest` after pipeline changes; for long embed runs, use `--dry-run` to validate config before full index.

## Commit & PR Guidelines
- Messages: short, imperative, prefix optional scope (e.g., `fix: adapt mcp server to current fastmcp api`, `chore: log codex mcp cli setup`).
- Commit when a discrete change is stable (pipeline step, config change, bugfix); include `codex_notes.md` updates for decisions.
- PRs: describe intent, summarize testing (`pytest`, `unitydocs-setup`), mention CUDA vs CPU if relevant. Include screenshots/log snippets for MCP startup or bake/index timing when useful.

## Security & Config Tips
- Keep secrets out of repo; no tokens in config.
- Use `UNITY_DOCS_MCP_ROOT`/`UNITY_DOCS_MCP_CONFIG` only when you need advanced root/config overrides.
- For GPU: install CUDA-enabled torch in the venv (setup probes `cu128`, then `cu121`, then `cu118`) and verifies `torch.cuda.is_available()` at runtime.
