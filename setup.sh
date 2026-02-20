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

echo "[setup] Installing project dependencies..."
python -m pip install -U pip
python -m pip install -e ".[dev]"

verify_cuda_torch() {
  python - <<'PY'
import sys
import torch

print(f"[setup] torch={torch.__version__} cuda={torch.version.cuda} available={torch.cuda.is_available()}")
sys.exit(0 if (torch.cuda.is_available() and torch.version.cuda is not None) else 1)
PY
}

try_cuda_channel() {
  local channel="$1"
  echo "[setup] Trying torch from ${channel}..."
  if ! python -m pip install --force-reinstall torch --index-url "https://download.pytorch.org/whl/${channel}"; then
    echo "[setup] ${channel} install failed."
    return 1
  fi
  if ! verify_cuda_torch; then
    echo "[setup] ${channel} installed but CUDA runtime verification failed."
    return 1
  fi
  TORCH_CHANNEL="$channel"
  return 0
}

TORCH_CHANNEL=""
echo "[setup] Installing CUDA torch build (cu128 -> cu121 -> cu118)..."
if ! try_cuda_channel "cu128"; then
  if ! try_cuda_channel "cu121"; then
    if ! try_cuda_channel "cu118"; then
      echo "[setup] Failed to install a CUDA-capable torch build."
      exit 1
    fi
  fi
fi
echo "[setup] Installed torch from ${TORCH_CHANNEL} index."

export UNITY_DOCS_MCP_ROOT="$REPO_DIR"
export UNITY_DOCS_MCP_CLEANUP=1

unitydocs install --version "$VERSION"
echo "[setup] Done."
