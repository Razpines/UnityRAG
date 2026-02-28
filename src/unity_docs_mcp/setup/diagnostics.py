from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _redact_path(value: str) -> str:
    if not value:
        return value
    home = str(Path.home()).replace("\\", "/")
    normalized = value.replace("\\", "/")
    if home and normalized.lower().startswith(home.lower()):
        return "~" + normalized[len(home) :]
    return normalized


def _repo_root(repo_root: str) -> Path:
    return Path(repo_root).expanduser().resolve()


def _detect_unity_installs() -> list[dict[str, str]]:
    bases: list[Path] = []
    if sys.platform.startswith("win"):
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        bases.extend(
            [
                Path(r"C:\Program Files\Unity\Hub\Editor"),
                Path(r"C:\Program Files\Unity Hub\Editor"),
                local_app_data / "Unity" / "Hub" / "Editor",
            ]
        )
    elif sys.platform == "darwin":
        bases.extend(
            [
                Path("/Applications/Unity/Hub/Editor"),
                Path.home() / "Applications" / "Unity" / "Hub" / "Editor",
            ]
        )
    else:
        bases.extend(
            [
                Path.home() / ".local" / "share" / "UnityHub" / "Editor",
                Path("/opt/Unity/Hub/Editor"),
            ]
        )

    found: list[dict[str, str]] = []
    version_re = re.compile(r"^(\d{4}\.\d+)")
    for base in bases:
        if not base.is_dir():
            continue
        try:
            for child in sorted(base.iterdir()):
                if not child.is_dir():
                    continue
                match = version_re.match(child.name)
                if not match:
                    continue
                found.append(
                    {
                        "version": match.group(1),
                        "path": _redact_path(str(child.resolve())),
                    }
                )
        except Exception:
            continue
    return found


def _nvidia_smi_summary() -> dict[str, Any]:
    cmd = ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
    except FileNotFoundError:
        return {"available": False, "error": "nvidia-smi not found"}
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    if result.returncode != 0:
        return {
            "available": False,
            "error": (result.stderr or result.stdout).strip()[:300],
            "return_code": result.returncode,
        }
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "gpu_count": len(lines),
        "summary": lines[:4],
    }


def _torch_summary() -> dict[str, Any]:
    try:
        import torch  # type: ignore
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    return {
        "available": True,
        "version": getattr(torch, "__version__", None),
        "torch_cuda_version": getattr(torch.version, "cuda", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
    }


def build_setup_snapshot(
    *,
    repo_root: Path,
    status: str,
    mode: str,
    unity_version: str,
    config_path: str,
    outcome: str,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "outcome": outcome,
        "setup_mode": mode,
        "selected_unity_docs_version": unity_version,
        "system": {
            "os": platform.platform(),
            "shell": os.environ.get("SHELL") or os.environ.get("ComSpec") or "",
            "python_version": sys.version,
            "python_executable": _redact_path(sys.executable),
        },
        "paths": {
            "repo_dir": _redact_path(str(repo_root)),
            "effective_config_path": _redact_path(config_path) if config_path else "",
        },
        "detected_unity_installs": _detect_unity_installs(),
        "cuda_checks": {
            "nvidia_smi": _nvidia_smi_summary(),
            "torch": _torch_summary(),
        },
    }


def write_setup_snapshot(
    *,
    repo_root: Path,
    status: str,
    mode: str,
    unity_version: str,
    config_path: str,
    outcome: str,
) -> tuple[Path, Path]:
    snapshot = build_setup_snapshot(
        repo_root=repo_root,
        status=status,
        mode=mode,
        unity_version=unity_version,
        config_path=config_path,
        outcome=outcome,
    )
    out_dir = repo_root / "reports" / "setup"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    stamped = out_dir / f"setup-diagnostics-{timestamp}.json"
    latest = out_dir / "setup-diagnostics-latest.json"

    payload = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    stamped.write_text(payload, encoding="utf-8")
    shutil.copy2(stamped, latest)
    return stamped, latest


def main() -> int:
    parser = argparse.ArgumentParser(description="Write setup diagnostics snapshot.")
    parser.add_argument("--repo-root", required=True, help="Repository root path.")
    parser.add_argument("--status", required=True, choices=["started", "success", "failed"])
    parser.add_argument("--mode", default="", help="Selected setup mode (cpu/cuda).")
    parser.add_argument("--unity-version", default="", help="Selected Unity docs version.")
    parser.add_argument("--config-path", default="", help="Effective config path.")
    parser.add_argument("--outcome", default="", help="Short status message.")
    parser.add_argument(
        "--print-latest-path-only",
        action="store_true",
        help="Print only the latest snapshot path for script consumption.",
    )
    args = parser.parse_args()

    try:
        stamped, latest = write_setup_snapshot(
            repo_root=_repo_root(args.repo_root),
            status=args.status,
            mode=args.mode,
            unity_version=args.unity_version,
            config_path=args.config_path,
            outcome=args.outcome,
        )
    except Exception as exc:
        print(f"[setup-diagnostics] ERROR: {exc}", file=sys.stderr)
        return 1

    if args.print_latest_path_only:
        print(str(latest))
    else:
        print(f"[setup-diagnostics] wrote {stamped}")
        print(f"[setup-diagnostics] latest {latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
