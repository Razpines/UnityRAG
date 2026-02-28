#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
SETUP_MODE="${UNITYDOCS_SETUP_MODE:-}"

report_failure_hint() {
  local report_version="${UNITY_DOCS_MCP_UNITY_VERSION:-${VERSION:-6000.3}}"
  echo
  echo "[setup] Setup failed. Generate diagnostics with:"
  echo "  UNITY_DOCS_MCP_UNITY_VERSION=${report_version} unitydocs report --summary setup.sh-failed --prefill-issue"
}

trap 'status=$?; if [ $status -ne 0 ]; then report_failure_hint; fi' EXIT

detect_version() {
  if [ -n "${UNITY_VERSION:-}" ]; then
    echo "$UNITY_VERSION"
    return
  fi
  if [ -n "${UNITY_EDITOR_VERSION:-}" ]; then
    echo "$UNITY_EDITOR_VERSION"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import os, re, pathlib, sys
paths = [
    "/Applications/Unity/Hub/Editor",
    os.path.expanduser("~/Applications/Unity/Hub/Editor"),
    os.path.join(os.environ.get("HOME",""), ".local", "share", "UnityHub", "Editor"),
]
versions = set()
for base in paths:
    p = pathlib.Path(base)
    if p.is_dir():
        for child in p.iterdir():
            if child.is_dir():
                m = re.search(r"(\\d{4}\\.\\d+)", child.name)
                if m:
                    versions.add(m.group(1))
if versions:
    def key(v): return tuple(int(x) for x in v.split("."))
    sys.stdout.write(sorted(versions, key=key)[-1])
PY
  fi
}

if [ -n "${1:-}" ]; then
  VERSION="$1"
else
  DETECTED="$(detect_version || true)"
  if [ -n "$DETECTED" ]; then
    VERSION="$DETECTED"
  else
    VERSION="6000.3"
  fi
fi

if [ -z "$SETUP_MODE" ]; then
  echo
  echo "[detect] Select setup mode:"
  echo "  1) CUDA (hybrid retrieval: FTS + vectors)"
  echo "  2) CPU-only (FTS-only retrieval; no transformers/faiss)"
  read -r -p "Mode [1]: " MODE_CHOICE
  MODE_CHOICE="${MODE_CHOICE:-1}"
  MODE_CHOICE_LOWER="$(printf '%s' "$MODE_CHOICE" | tr '[:upper:]' '[:lower:]')"
  case "$MODE_CHOICE_LOWER" in
    1|cuda) SETUP_MODE="cuda" ;;
    2|cpu) SETUP_MODE="cpu" ;;
    *)
      echo "[setup] Invalid mode selection."
      exit 1
      ;;
  esac
else
  SETUP_MODE_LOWER="$(printf '%s' "$SETUP_MODE" | tr '[:upper:]' '[:lower:]')"
  case "$SETUP_MODE_LOWER" in
    1|cuda) SETUP_MODE="cuda" ;;
    2|cpu) SETUP_MODE="cpu" ;;
    *)
      echo "[setup] UNITYDOCS_SETUP_MODE must be cuda or cpu."
      exit 1
      ;;
  esac
fi

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

echo "[bootstrap] Preparing virtual environment and dependencies..."
PYTHONPATH="$REPO_DIR/src" "$PYTHON" -m unity_docs_mcp.setup.bootstrap \
  --repo-root "$REPO_DIR" \
  --venv "$VENV_DIR" \
  --mode "$SETUP_MODE"

source "$VENV_DIR/bin/activate"

export UNITY_DOCS_MCP_ROOT="$REPO_DIR"
export UNITY_DOCS_MCP_CLEANUP=1
export UNITY_DOCS_MCP_UNITY_VERSION="$VERSION"
CFG_PATH="$REPO_DIR/config.local.yaml"
VECTOR_MODE="faiss"
if [ "$SETUP_MODE" = "cpu" ]; then
  VECTOR_MODE="none"
fi
cat >"$CFG_PATH" <<EOF
index:
  lexical: "sqlite_fts5"
  vector: "$VECTOR_MODE"
EOF
export UNITY_DOCS_MCP_CONFIG="$CFG_PATH"

echo "[artifacts] Ensuring local docs artifacts..."
python -c "from unity_docs_mcp.setup.ensure_artifacts import main; main()"

MCP_CLIENT="${UNITYDOCS_MCP_CLIENT:-}"
if [ -z "$MCP_CLIENT" ]; then
  echo
  echo "[mcp] Auto-configure MCP client now?"
  echo "  1) Codex (recommended)"
  echo "  2) Claude Desktop"
  echo "  3) Both"
  echo "  4) Skip"
  read -r -p "Choice [1]: " MCP_CHOICE
  MCP_CHOICE="${MCP_CHOICE:-1}"
  MCP_CHOICE_LOWER="$(printf '%s' "$MCP_CHOICE" | tr '[:upper:]' '[:lower:]')"
  case "$MCP_CHOICE_LOWER" in
    1|codex) MCP_CLIENT="codex" ;;
    2|claude) MCP_CLIENT="claude" ;;
    3|both) MCP_CLIENT="both" ;;
    4|skip|none) MCP_CLIENT="skip" ;;
    *)
      echo "[setup] Invalid MCP client selection, skipping auto-config."
      MCP_CLIENT="skip"
      ;;
  esac
else
  MCP_CLIENT_LOWER="$(printf '%s' "$MCP_CLIENT" | tr '[:upper:]' '[:lower:]')"
  case "$MCP_CLIENT_LOWER" in
    codex|claude|both|skip|none) MCP_CLIENT="$MCP_CLIENT_LOWER" ;;
    *)
      echo "[setup] UNITYDOCS_MCP_CLIENT must be codex|claude|both|skip. Skipping auto-config."
      MCP_CLIENT="skip"
      ;;
  esac
fi

if [ "$MCP_CLIENT" = "none" ]; then
  MCP_CLIENT="skip"
fi

echo "[detect] Using Unity docs version: $VERSION"
if [ "$MCP_CLIENT" = "codex" ] || [ "$MCP_CLIENT" = "both" ]; then
  if ! python -m unity_docs_mcp.setup.mcp_config --client codex --repo-root "$REPO_DIR" --unity-version "$VERSION"; then
    echo "[setup] Warning: failed to auto-configure Codex MCP."
  fi
fi
if [ "$MCP_CLIENT" = "claude" ] || [ "$MCP_CLIENT" = "both" ]; then
  if ! python -m unity_docs_mcp.setup.mcp_config --client claude --repo-root "$REPO_DIR" --unity-version "$VERSION"; then
    echo "[setup] Warning: failed to auto-configure Claude MCP."
  fi
fi

echo "[setup] Done."
