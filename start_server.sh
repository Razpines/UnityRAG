#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[start_server] venv not found at $VENV_DIR/bin/activate"
  exit 1
fi

export UNITY_DOCS_MCP_ROOT="$REPO_DIR"

if [ -n "${1:-}" ]; then
  export UNITY_DOCS_MCP_PORT="$1"
fi

source "$VENV_DIR/bin/activate"
unitydocs-mcp-http
