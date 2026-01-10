#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
VERSION="${1:-6000.3}"

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON=python3.12
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "[setup] Python 3.12+ is required."
  exit 1
fi

"$PYTHON" - <<'PY'
import sys
sys.exit(0 if sys.version_info >= (3, 12) else 1)
PY

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[setup] Creating venv at $VENV_DIR..."
  "$PYTHON" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install -U pip
python -m pip install -e ".[dev]"

export UNITY_DOCS_MCP_ROOT="$REPO_DIR"
export UNITY_DOCS_MCP_CLEANUP=1

unitydocs install --version "$VERSION"
echo "[setup] Done."
