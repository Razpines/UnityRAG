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
[2026-01-10 00:35] Added *.egg-info to .gitignore and removed editable install metadata to keep repo clean before push.
[2026-01-10 00:40] Decision: run unitydocs-setup (ensure) to perform bake and index with default config into data/unity/6000.3; expect embeddings download (bge-small-en-v1.5) and FAISS/FTS artifacts.
[2026-01-10 00:41] unitydocs-setup failed: missing numpy import; need to install full deps (numpy, faiss-cpu, sentence-transformers) into .venv before rerun.
[2026-01-10 00:44] Installed numpy, faiss-cpu, sentence-transformers (and torch/scikit-learn deps) into .venv to satisfy bake/index requirements.
[2026-01-10 00:50] unitydocs-setup ran bake but index failed: model id sentence-transformers/bge-small-en-v1.5 not found (HF 404). Need to switch embedder to BAAI/bge-small-en-v1.5 and rerun ensure.
[2026-01-10 00:53] Switched embedder model to BAAI/bge-small-en-v1.5 in config/defaults; rerunning ensure was interrupted, need to re-run unitydocs-setup to finish indexing.
[2026-01-10 00:56] Added embedder device auto-detection (CUDA if available) with runtime print; config exposes embedder.device and defaults to auto. Updated index/search to pass device through.
[2026-01-10 01:05] unitydocs-setup rerun timed out mid-bake (timeout limit hit); need to rerun bake/index with higher timeout using new embedder model BAAI/bge-small-en-v1.5 and CUDA auto-detect.
[2026-01-10 01:14] Improved performance: bake now uses ProcessPoolExecutor with lxml parser via BeautifulSoup, parallel extraction/chunking; embedder uses auto device (prefers CUDA) and logs device/model.
[2026-01-10 01:21] Updated bake to only ingest Manual HTMLs (print count) and set source_type=manual; Manual HTML count: 3426.
[2026-01-10 01:24] Fixed NameError in bake (missing chunks_accum init) after parallelization refactor.
[2026-01-10 01:30] User ran parallel bake (Manual-only) successfully; completed in ~11 seconds.
[2026-01-10 01:37] Added CUDA debug logging in embed_texts and a --dry-run flag to index_cli to check device/model without embedding.
[2026-01-10 01:45] CUDA check: embed_texts reports device=cpu, torch_cuda_available=False, torch build 2.9.1+cpu; need CUDA-enabled torch wheel to use GPU.
[2026-01-10 01:52] Torch in .venv is CPU-only (2.9.1+cpu). Documented installing CUDA torch; pyproject unchanged (torch stays transient).
[2026-01-10 02:05] User wants CUDA; will recreate venv with Python 3.12 to allow CUDA torch wheels (PyTorch not available for 3.13).
[2026-01-10 02:15] Recreated .venv with Python 3.12, installed torch 2.2.2+cu121 and downgraded numpy to 1.26.4 for compatibility; torch now reports cuda available (12.1).
[2026-01-10 02:20] Added mcp.config.json with relative server command (.\\.venv\\Scripts\\unitydocs-mcp.exe) for Codex auto-start.
[2026-01-10 02:24] Removed repo-level mcp.config.json (machine-specific). Will document Codex setup in README instead.
