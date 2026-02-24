# Contributing

Thanks for contributing to UnityRAG.

This project focuses on reliable local Unity docs retrieval and MCP tooling quality.

## Development Setup

1. Create a virtual environment.

```bash
python -m venv .venv
```

2. Activate and install dependencies.

```bash
# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e .[dev]
```

3. Run tests.

```bash
pytest
```

## First Contribution Path

1. Pick an issue labeled `good first issue` or `help wanted`.
2. Confirm expected behavior in the issue thread before coding.
3. Keep changes focused and include tests where behavior changes.
4. Open a PR with a clear summary and test evidence.

## Hooks (Recommended)

To block accidental commits of large generated artifacts:

```bash
git config core.hooksPath .githooks
```

## Guidelines

- Keep functions small and explicit; prefer `ensure_*`, `bake_*`, `index_*` naming.
- Avoid committing anything under `data/`.
- Use type hints consistently.
- Add notes to `docs/internal/codex_notes.md` for significant implementation decisions.

## Pull Requests

- Keep PRs scoped to one objective.
- Include what changed, why it changed, and how you validated it.
- Mention platform details if relevant (Windows/macOS/Linux, CUDA vs CPU).
