#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
REQUESTED_SETUP_MODE="${UNITYDOCS_SETUP_MODE:-}"
SETUP_MODE="cpu"
SETUP_DIAG_LATEST="$REPO_DIR/reports/setup/setup-diagnostics-latest.json"
VERSION_FROM_ARG=0
VERSION="6000.3"

report_failure_hint() {
  local report_version="${UNITY_DOCS_MCP_UNITY_VERSION:-${VERSION:-6000.3}}"
  echo
  echo "[setup] Setup failed. Generate diagnostics with:"
  echo "  UNITY_DOCS_MCP_UNITY_VERSION=${report_version} unitydocs report --summary setup.sh-failed --prefill-issue"
}

write_setup_diagnostics() {
  local status="$1"
  local outcome="$2"
  local diag_python="${PYTHON:-python3}"
  if ! command -v "$diag_python" >/dev/null 2>&1; then
    return 1
  fi
  PYTHONPATH="$REPO_DIR/src" "$diag_python" -m unity_docs_mcp.setup.diagnostics \
    --repo-root "$REPO_DIR" \
    --status "$status" \
    --mode "${SETUP_MODE:-}" \
    --unity-version "${VERSION:-}" \
    --config-path "${UNITY_DOCS_MCP_CONFIG:-}" \
    --outcome "$outcome" \
    --print-latest-path-only >/dev/null 2>&1
}

trap 'status=$?; if [ $status -ne 0 ]; then write_setup_diagnostics failed setup.sh-failed || true; echo "[setup] Summary: mode=${SETUP_MODE:-unknown} unity_version=${VERSION:-unknown}"; if [ -f "$SETUP_DIAG_LATEST" ]; then echo "[setup] Diagnostics snapshot: $SETUP_DIAG_LATEST"; fi; report_failure_hint; else write_setup_diagnostics success setup.sh-success || true; fi' EXIT

if [ -n "${1:-}" ]; then
  VERSION="$1"
  VERSION_FROM_ARG=1
fi

if [ -n "$REQUESTED_SETUP_MODE" ]; then
  REQUESTED_SETUP_MODE_LOWER="$(printf '%s' "$REQUESTED_SETUP_MODE" | tr '[:upper:]' '[:lower:]')"
  case "$REQUESTED_SETUP_MODE_LOWER" in
    1|cuda)
      echo "[setup] CUDA setup is temporarily disabled (WIP). Forcing CPU-only mode."
      ;;
    2|cpu)
      ;;
    *)
      echo "[setup] UNITYDOCS_SETUP_MODE currently supports CPU-only setup while CUDA is WIP. Forcing CPU-only mode."
      ;;
  esac
else
  echo "[setup] CUDA setup is temporarily disabled (WIP). Using CPU-only mode."
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

echo "[detect] Inspecting installed Unity editors..."
PYTHONPATH="$REPO_DIR/src" "$PYTHON" -m unity_docs_mcp.setup.unity_detect || true
if [ "$VERSION_FROM_ARG" -eq 0 ]; then
  SUGGESTED_VERSION="$(PYTHONPATH="$REPO_DIR/src" "$PYTHON" -m unity_docs_mcp.setup.unity_detect --suggest-only 2>/dev/null || true)"
  if [ -n "$SUGGESTED_VERSION" ]; then
    VERSION="$SUGGESTED_VERSION"
  fi
  echo
  read -r -p "[detect] Unity docs version [$VERSION]: " VERSION_CHOICE
  VERSION_CHOICE="${VERSION_CHOICE:-}"
  if [ -n "$VERSION_CHOICE" ]; then
    VERSION="$VERSION_CHOICE"
  fi
fi
echo "[detect] Using Unity docs version: $VERSION"

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
