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
[2026-01-10 02:28] Updated config/paths resolution to work without changing working dir: load_config searches env UNITY_DOCS_MCP_CONFIG and repo root; make_paths anchors relative paths using env UNITY_DOCS_MCP_ROOT or repo root. README shows Codex config using UNITY_DOCS_MCP_ROOT.
[2026-01-10 02:35] Added Codex CLI MCP server entry (unity-docs) pointing to .venv\\Scripts\\unitydocs-mcp.exe with UNITY_DOCS_MCP_ROOT=C:\\projects\\UnityRAG to auto-start without changing working directory.
[2026-01-10 02:40] Fixed MCP server for current mcp package (no on_startup hook) by lazy-initializing DocStore per tool; unitydocs-mcp now runs without handshake failure.
[2026-01-10 02:50] Added streamable HTTP entrypoint (unitydocs-mcp-http) with env-configurable host/port for external MCP clients and easier log visibility; defaults to 127.0.0.1:8765/mcp.
[2026-01-10 02:55] Added start_server.bat to activate .venv, set UNITY_DOCS_MCP_ROOT, and launch unitydocs-mcp-http with optional port arg for visible logs.
[2026-01-10 03:10] Added MCP min_score filter to suppress nonsense search results, improved link resolution for link_graph, and switched HTTP server to Windows selector loop to reduce WinError 10054 log noise.
[2026-01-10 03:20] Improved MCP UX: sanitize FTS queries to avoid punctuation errors, allow source_types as string or list, and add open_max_chars/full mode to reduce partial-doc surprises.
[2026-01-10 03:30] Ensure artifacts now runs at server start (stdio and HTTP) with an internal guard; tool calls no longer trigger bake/index unless startup didn't run.
[2026-01-10 04:00] Added improvements.md capturing repo improvement ideas and MCP tool UX guidance, including when to use MCP vs skip for general knowledge.
[2026-01-10 04:05] Decision: do not distribute pre-baked/indexed artifacts due to Unity docs CC BY-NC-ND; keep bake/index client-side.
[2026-01-10 04:10] Implemented setup.bat for interactive version selection (6000.5/6000.4/6000.3/6000.0) with default 6000.3 and guidance that 2022 and older are likely well-known by LLMs.
[2026-01-10 04:12] Added Unity Hub version hint detection (env vars or Hub install path scan) to preselect version.
[2026-01-10 04:15] Added progress and status prints: download banner, unzip progress bar, bake/index stage messages; added cleanup to remove raw zip/unzipped docs after successful indexing when setup sets UNITY_DOCS_MCP_CLEANUP=1.
[2026-01-10 04:18] Added embedding progress bar for indexing via SentenceTransformer show_progress_bar.
[2026-01-10 04:20] setup.bat now creates .venv if missing, installs deps, checks free disk space, and supports optional repo-local portable Python 3.12 download (only if no 3.12 found).
[2026-01-10 04:25] Added banner.txt and setup.bat displays banner; added colored output helpers and success/failure pauses for user-visible setup flow.
[2026-01-10 04:30] Fixed setup.bat path normalization and removed where-python probing to avoid Windows path/volume label errors.
[2026-02-20 15:25] Carry-forward rules: setup scripts are CUDA-only and must never silently fall back to CPU torch.
[2026-02-20 15:25] CUDA channel fallback must be runtime-verified (torch.cuda.is_available + torch.version.cuda), not install-success only.
[2026-02-20 15:25] MCP stdio stability: keep setup/embed diagnostics off stdout (stderr only) to avoid transport/protocol breakage.
[2026-02-20 15:25] Ensure flow: avoid forcing raw zip/unzip when baked/index artifacts are already valid for current config signature.
[2026-02-20 15:45] CI policy decision: default tests must be deterministic and not depend on untracked Unity raw docs under data/.
[2026-02-20 15:45] Extraction coverage moved to committed HTML fixtures; real-doc extraction tests remain optional behind UNITYDOCS_E2E=1.
[2026-02-20 15:45] PR #7 merged to main with fixture-based extraction tests and green Windows/Ubuntu CI.
[2026-02-20 15:45] Started issue #2 implementation plan: add unitydocs doctor with human/json output, preflight diagnostics, and non-zero exit on blocking failures.
[2026-02-20 16:10] Decision update: support CPU-only environments via explicit FTS-only mode (index.vector=none) while keeping CUDA hybrid as default for full semantic retrieval.
[2026-02-20 16:10] setup.bat/setup.sh now prompt for CUDA vs CPU-only and install dependency sets accordingly (. [dev,vector] vs . [dev]); FTS-only path skips torch/sentence-transformers/faiss runtime logic.
[2026-02-20 16:15] Setup mode/version selection now persists into repo config.yaml (not temp-only) so MCP startup uses the same retrieval mode after setup.
[2026-02-20 15:35] Reduced onboarding friction: setup now prompts for Codex/Claude MCP auto-config and writes client config entries automatically via unity_docs_mcp.setup.mcp_config.
[2026-02-20 17:50] MCP auto-config now writes absolute repo venv stdio command (`unitydocs-mcp`) plus UNITY_DOCS_MCP_ROOT/UNITY_DOCS_MCP_CONFIG env to avoid CWD-dependent startup failures across projects.
