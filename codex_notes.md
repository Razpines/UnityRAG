[2026-01-10 00:00] Started UnityRAG build with Python-only stack for bake/index/MCP to keep single runtime per requirements.
[2026-01-10 00:00] UnityDocumentation.zip already present and unzipped; will treat setup step as idempotent and skip download unless missing.
[2026-01-10 00:00] Embedding provider preference not specified; defaulting to local sentence-transformers model (bge-small-en-v1.5) to avoid external APIs unless requested.
[2026-01-10 00:00] Plan: git init here, create GitHub repo UnityRAG via gh, and push; will make iterative commits per milestones.
[2026-01-10 00:01] Initialized git repository with main branch to prepare for incremental commits.
[2026-01-10 00:02] Will move existing UnityDocumentation.zip and unzipped folder into data/unity/6000.3/raw to align with planned default paths.
[2026-01-10 00:03] Moved UnityDocumentation.zip and unzipped UnityDocumentation into data/unity/6000.3/raw for consistent artifact locations.
[2026-01-10 00:04] Chose dependency stack: bs4+lxml for HTML parsing, requests for download, sqlite FTS5, faiss-cpu + sentence-transformers (bge-small-en-v1.5) for embeddings, pytest for tests.
[2026-01-10 00:06] User clarified dependencies are unrestricted; will spin up .venv as needed and ensure gh remote set + frequent commits/pushes.
[2026-01-10 00:07] Created local virtual environment (.venv) for isolating dependencies.
[2026-01-10 00:09] Added README/config defaults and pyproject dependency list (including mcp) to align with documented plan.
[2026-01-10 00:12] Tried installing mcp==1.25.0 into .venv; installation failed with WinError 32 on pywin32 file lock. Will retry later or work around if needed.
[2026-01-10 00:18] Implemented bake pipeline (manual/scriptref extractors, chunking, link graph, manifest) and ensured idempotent ensure_artifacts orchestration.
[2026-01-10 00:18] Added hybrid index scaffolding (FTS/FAISS building), DocStore utilities, MCP server skeleton with tools search/open/list/related/status.
[2026-01-10 00:20] Created GitHub repo UnityRAG via gh with origin remote pointing to https://github.com/Razpines/UnityRAG.
[2026-01-10 00:22] Committed initial scaffold and pipeline; pushed to origin/main.
[2026-01-10 00:28] Installed runtime deps into .venv (bs4, lxml, requests, pytest, etc.) and editable package; mcp 1.25.0 now present after earlier lock error.
[2026-01-10 00:28] Ran pytest tests/test_extraction.py successfully (2 tests passed).
