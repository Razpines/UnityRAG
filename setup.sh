#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"

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

CUDA_SELECTED=0
if command -v nvidia-smi >/dev/null 2>&1; then
  CUDA_VER="$(nvidia-smi --query-gpu=cuda_version --format=csv,noheader 2>/dev/null | head -n1 | tr -d ' ')"
  CUDA_MAJOR="${CUDA_VER%%.*}"
  CUDA_MINOR="${CUDA_VER#*.}"
  if [ -n "$CUDA_VER" ] && [ "$CUDA_MAJOR" -ge 12 ] && [ "$CUDA_MINOR" -ge 1 ]; then
    echo "[setup] Detected CUDA $CUDA_VER. Installing torch cu121..."
    python -m pip install --force-reinstall torch==2.2.2+cu121 --index-url https://download.pytorch.org/whl/cu121
    CUDA_SELECTED=1
  elif [ -n "$CUDA_VER" ] && [ "$CUDA_MAJOR" -eq 11 ] && [ "$CUDA_MINOR" -ge 8 ]; then
    echo "[setup] Detected CUDA $CUDA_VER. Installing torch cu118..."
    python -m pip install --force-reinstall torch==2.2.2+cu118 --index-url https://download.pytorch.org/whl/cu118
    CUDA_SELECTED=1
  fi
fi

if [ "$CUDA_SELECTED" -eq 0 ]; then
  printf "\033[33m[setup] WARNING: No compatible CUDA version detected. Using CPU embeddings; initial indexing may be slow.\033[0m\n"
fi

python -m pip install -U pip
python -m pip install -e ".[dev]"

export UNITY_DOCS_MCP_ROOT="$REPO_DIR"
export UNITY_DOCS_MCP_CLEANUP=1

unitydocs install --version "$VERSION"
echo "[setup] Done."
