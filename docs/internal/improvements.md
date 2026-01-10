# Improvements

## Priority improvements
- Add tests for MCP tool behavior: search min_score filtering, open max_chars/full, related backlinks; cover failure modes and stable outputs.
- Implement strict idempotence for bake/index with config hashing in manifest; skip when inputs and config are unchanged.
- Build a reverse link index (incoming edges) at bake time so `related` can return inbound links reliably.
- Reconcile scope: either restore ScriptReference ingestion or document and enforce Manual-only mode as an intentional choice.
- Add a setup-level dry-run/verify mode (paths, version detection, FTS availability, embedder config) before heavy work.

## Helpful additions
- Persist `baked/manifest.json` with build_from/built_on and counts to detect upstream doc updates.
- Print resolved config (paths, device, embedder) in `unitydocs-setup` for clarity when using `UNITY_DOCS_MCP_ROOT`.
- Add a small doc_id/path map artifact to speed `open`/`list_files` lookups without scanning large JSONL.

## MCP tool UX: ease-of-use and ease-of-understanding

### Intent
- Most agents already know Unity docs; the MCP must deliver accurate, version-specific, up-to-date citations with minimal friction.
- Tools should feel like "fast, reliable citations" rather than "generic search." The API shape should reflect that.

### Current presentation (as implied by repo usage)
- Tools exist for search/open/list/related/status and artifacts are ensured on startup.
- Default search returns results/snippets, but version signaling and freshness guarantees are not emphasized.
- Querying requires some knowledge of params (source_types, path_prefix, max_chars), which can be missed by agents.

### Desired presentation to agents
- Lead with version correctness: every response should clearly state the Unity version/build, and citations should be versioned.
- Make it obvious how to ask for "latest 6000.3" vs "any version" (even if only one version exists now).
- Provide a simple mental model:
  - `search` = find best docs with citations
  - `open` = read a specific doc (full or sectioned)
  - `related` = browse context (links/siblings)
  - `list_files` = find by filename or class
  - `status` = confirm version/build and indexing state

### When to use MCP (lightweight guidance)
- Use it when you need citations, exact wording, or version-specific correctness.
- Use it for API surface questions that may have changed across versions.
- Skip it for general Unity concepts, math, or workflow advice the agent already knows.
- If unsure, do a quick `search` to verify details and cite the page.

### Gaps to close
- Lack of explicit version/built_on data in every tool response can reduce trust in freshness.
- Agents may not know when to use `open` vs `search` or how to request full text vs snippet.
- Missing ScriptReference coverage (if still Manual-only) limits API completeness.

### Proposed changes to presentation
- Add a short "agent usage" section in README (or MCP tool docstring) with examples:
  - "Use `status` first when accuracy matters; it returns version/build timestamp."
  - "Use `search` for citations; use `open` for full context."
- Include version/build fields in tool responses by default (or a `include_version=true` param).
- Standardize response envelopes: `meta` (version/build), `results`, and `debug` when requested.
- In `search`, add an optional `version` filter (even if only one version is present now).
- For `open`, add a `section` or `heading_path` filter so agents can ask for specific sections without large payloads.

## Pre-baked multi-version artifacts (to avoid local bake/index)

### Goals
- Let users pick a Unity version and start serving immediately without running bake/index.
- Keep artifacts optional so advanced users can still build locally or use custom configs.

### Packaging options
- Keep small metadata files in git (manifests, doc_id maps), but store big artifacts in Git LFS or release assets:
  - `data/unity/<ver>/baked/*.jsonl` can be large; FAISS and FTS are very large.
  - For GitHub, prefer LFS or per-version release archives (`unity-docs-<ver>-artifacts.zip`).
- Provide an `artifacts/manifest.json` registry with available versions, build_from, built_on, sizes, and hashes.

### Setup flow changes
- Add `unitydocs-setup --version <ver>` and `--list-versions` to select from pre-baked artifacts.
- If run in a TTY with no version specified, prompt to choose from the registry (with "latest" as default).
- Support `--auto` to pick the latest or match a detected installed Unity version if available.
- Do not prompt at server startup; selection should happen during setup so server remains non-interactive.

### Version selection hints
- Auto-detect hint via environment variables or common install paths (best-effort, optional).
- Always allow explicit override in config or CLI.

## Next steps
- Decide whether ScriptReference remains in scope.
- Decide whether to enforce version metadata in tool responses.
- Decide whether to ship artifacts via LFS or release archives and how to expose the registry.
