from __future__ import annotations

import importlib
import json
import os
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from unity_docs_mcp.config import Config, config_signature, load_config, vector_enabled
from unity_docs_mcp.paths import make_paths


@dataclass
class CheckResult:
    id: str
    status: str  # pass|warn|fail
    message: str
    details: dict[str, Any]


def _resolve_config_path(config_path: Optional[Path | str] = None) -> Optional[Path]:
    env_override = os.environ.get("UNITY_DOCS_MCP_CONFIG")
    candidates: list[Path] = []
    if config_path is not None:
        candidates.append(Path(config_path))
    if env_override:
        candidates.append(Path(env_override))
    candidates.append(Path("config.yaml"))
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "config.yaml")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _check_config_source(config_path: Optional[Path]) -> CheckResult:
    if config_path is None:
        return CheckResult(
            id="config_source",
            status="warn",
            message="No config file found; using built-in defaults.",
            details={"config_path": None},
        )
    return CheckResult(
        id="config_source",
        status="pass",
        message=f"Using config file: {config_path}",
        details={"config_path": str(config_path)},
    )


def _check_paths(cfg: Config) -> CheckResult:
    paths = make_paths(cfg)
    details = {
        "root": str(paths.root),
        "raw_zip": str(paths.raw_zip),
        "raw_unzipped": str(paths.raw_unzipped),
        "baked_dir": str(paths.baked_dir),
        "index_dir": str(paths.index_dir),
        "root_exists": paths.root.exists(),
        "raw_zip_exists": paths.raw_zip.exists(),
        "raw_unzipped_exists": paths.raw_unzipped.exists(),
        "baked_dir_exists": paths.baked_dir.exists(),
        "index_dir_exists": paths.index_dir.exists(),
    }
    root_parent = paths.root.parent
    if not root_parent.exists():
        return CheckResult(
            id="paths",
            status="warn",
            message=f"Resolved root parent does not exist yet: {root_parent}",
            details=details,
        )
    return CheckResult(
        id="paths",
        status="pass",
        message="Resolved data paths successfully.",
        details=details,
    )


def _import_optional(module_name: str) -> tuple[bool, Optional[str], Optional[str]]:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", None)
        return True, version, None
    except Exception as exc:
        return False, None, str(exc)


def _check_dependencies(cfg: Config) -> CheckResult:
    if not vector_enabled(cfg.index.vector):
        return CheckResult(
            id="dependencies",
            status="pass",
            message="FTS-only mode enabled; skipping vector dependency checks.",
            details={"vector_enabled": False},
        )

    checks = {
        "sentence_transformers": _import_optional("sentence_transformers"),
        "faiss": _import_optional("faiss"),
        "torch": _import_optional("torch"),
    }
    missing = [name for name, (ok, _, _) in checks.items() if not ok]
    details = {
        "vector_enabled": True,
        "vector_mode": cfg.index.vector,
        "imports": {
            name: {"ok": ok, "version": version, "error": error}
            for name, (ok, version, error) in checks.items()
        },
    }
    if missing:
        return CheckResult(
            id="dependencies",
            status="fail",
            message=f"Missing/invalid vector dependencies: {', '.join(missing)}",
            details=details,
        )
    return CheckResult(
        id="dependencies",
        status="pass",
        message="Vector dependencies import successfully.",
        details=details,
    )


def _check_embedder_device(cfg: Config) -> CheckResult:
    if not vector_enabled(cfg.index.vector):
        return CheckResult(
            id="embedder_device",
            status="pass",
            message="FTS-only mode enabled; skipping embedder/CUDA checks.",
            details={"vector_enabled": False, "vector_mode": cfg.index.vector},
        )

    ok, _, err = _import_optional("torch")
    if not ok:
        return CheckResult(
            id="embedder_device",
            status="fail",
            message="Torch is unavailable; cannot validate embedder/device readiness.",
            details={"error": err},
        )
    import torch

    preference = (cfg.index.embedder.device or "auto").lower()
    resolved = preference if preference in {"cpu", "cuda"} else ("cuda" if torch.cuda.is_available() else "cpu")
    details = {
        "preference": preference,
        "resolved_device": resolved,
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
        "model": cfg.index.embedder.model,
    }
    if resolved == "cuda" and not torch.cuda.is_available():
        return CheckResult(
            id="embedder_device",
            status="fail",
            message="Configured CUDA device is unavailable at runtime.",
            details=details,
        )
    if resolved == "cpu":
        return CheckResult(
            id="embedder_device",
            status="warn",
            message="Embedder is currently CPU-only; indexing/search may be slow.",
            details=details,
        )
    return CheckResult(
        id="embedder_device",
        status="pass",
        message="CUDA embedder/device is ready.",
        details=details,
    )


def _check_mcp_port() -> CheckResult:
    host = os.environ.get("UNITY_DOCS_MCP_HOST", "127.0.0.1")
    port_raw = os.environ.get("UNITY_DOCS_MCP_PORT", "8765")
    try:
        port = int(port_raw)
    except ValueError:
        return CheckResult(
            id="mcp_port",
            status="fail",
            message=f"Invalid UNITY_DOCS_MCP_PORT value: {port_raw}",
            details={"host": host, "port": port_raw},
        )

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except OSError as exc:
        return CheckResult(
            id="mcp_port",
            status="fail",
            message=f"MCP host/port is unavailable: {host}:{port}",
            details={"host": host, "port": port, "error": str(exc)},
        )
    finally:
        sock.close()

    return CheckResult(
        id="mcp_port",
        status="pass",
        message=f"MCP host/port appears available: {host}:{port}",
        details={"host": host, "port": port},
    )


def _safe_manifest(path: Path) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text()), None
    except Exception as exc:
        return None, str(exc)


def _check_artifacts(cfg: Config) -> CheckResult:
    paths = make_paths(cfg)
    expected_sig = config_signature(cfg)
    baked_path = paths.baked_dir / "manifest.json"
    index_path = paths.index_dir / "manifest.json"
    baked_manifest, baked_error = _safe_manifest(baked_path)
    index_manifest, index_error = _safe_manifest(index_path)
    details: dict[str, Any] = {
        "baked_manifest_path": str(baked_path),
        "index_manifest_path": str(index_path),
        "baked_manifest_exists": baked_path.exists(),
        "index_manifest_exists": index_path.exists(),
        "expected_config_signature": expected_sig,
    }
    if baked_error or index_error:
        if baked_error:
            details["baked_manifest_error"] = baked_error
        if index_error:
            details["index_manifest_error"] = index_error
        return CheckResult(
            id="artifacts",
            status="fail",
            message="One or more manifests exist but could not be parsed.",
            details=details,
        )

    baked_sig = baked_manifest.get("config_signature") if baked_manifest else None
    index_sig = index_manifest.get("config_signature") if index_manifest else None
    details["baked_signature"] = baked_sig
    details["index_signature"] = index_sig
    details["baked_signature_matches"] = baked_sig == expected_sig if baked_sig else False
    details["index_signature_matches"] = index_sig == expected_sig if index_sig else False

    if baked_manifest and index_manifest and baked_sig == expected_sig and index_sig == expected_sig:
        return CheckResult(
            id="artifacts",
            status="pass",
            message="Baked/index manifests are present and match current config signature.",
            details=details,
        )
    return CheckResult(
        id="artifacts",
        status="warn",
        message="Artifacts are missing or stale; run setup/index as needed.",
        details=details,
    )


def run_doctor(config_path: Optional[Path | str] = None) -> dict[str, Any]:
    cfg_path = _resolve_config_path(config_path)
    cfg = load_config(config_path)
    checks = [
        _check_config_source(cfg_path),
        _check_paths(cfg),
        _check_dependencies(cfg),
        _check_embedder_device(cfg),
        _check_mcp_port(),
        _check_artifacts(cfg),
    ]
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    overall = "fail" if counts["fail"] else ("warn" if counts["warn"] else "pass")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "counts": counts,
        "checks": [asdict(c) for c in checks],
    }


def exit_code_from_report(report: dict[str, Any]) -> int:
    return 1 if report.get("counts", {}).get("fail", 0) else 0


def print_human_report(report: dict[str, Any]) -> None:
    status_order = {"fail": 0, "warn": 1, "pass": 2}
    checks = sorted(report.get("checks", []), key=lambda c: status_order.get(c["status"], 99))
    for check in checks:
        print(f"[{check['status'].upper()}] {check['id']}: {check['message']}")
    counts = report.get("counts", {})
    print(
        "Summary: "
        f"pass={counts.get('pass', 0)} "
        f"warn={counts.get('warn', 0)} "
        f"fail={counts.get('fail', 0)} "
        f"overall={report.get('overall', 'unknown')}"
    )


def main(json_output: bool = False, config_path: Optional[str] = None) -> int:
    report = run_doctor(config_path=config_path)
    if json_output:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report)
    return exit_code_from_report(report)
