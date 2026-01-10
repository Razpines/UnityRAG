# Contributing

Thanks for contributing! This project focuses on reliable local Unity docs RAG and MCP tooling.

## Development setup
1) Create venv and install deps:
```
python -m venv .venv
```
Activate and install:
```
Windows: .\.venv\Scripts\activate
macOS/Linux: source .venv/bin/activate
pip install -e .[dev]
```

2) Run tests:
```
pytest
```

## Hooks (recommended)
To prevent committing Unity docs artifacts, enable the repo hooks:
```
git config core.hooksPath .githooks
```

## Guidelines
- Keep functions small and explicit; prefer `ensure_*`, `bake_*`, `index_*` naming.
- Avoid committing anything under `data/`.
- Include brief notes in `docs/codex_notes.md` for significant decisions.
