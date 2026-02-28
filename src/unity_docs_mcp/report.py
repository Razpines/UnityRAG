from __future__ import annotations

import json
import os
import platform
import re
import shutil
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import yaml

from unity_docs_mcp.config import config_layer_paths, load_config
from unity_docs_mcp.doctor import run_doctor

_SENSITIVE_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "cookie",
)
_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)\b(token|secret|password|api[_-]?key|authorization)\b\s*[:=]\s*([^\s,;]+)"
)
_TRACKED_ENV_VARS = [
    "UNITY_DOCS_MCP_UNITY_VERSION",
    "UNITY_DOCS_MCP_ROOT",
    "UNITY_DOCS_MCP_CONFIG",
    "UNITY_DOCS_MCP_HOST",
    "UNITY_DOCS_MCP_PORT",
    "UNITY_DOCS_MCP_CLEANUP",
    "UNITYDOCS_SETUP_MODE",
]


def _repo_root() -> Path:
    override = os.environ.get("UNITY_DOCS_MCP_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _is_sensitive_key(key: str) -> bool:
    key_norm = key.lower()
    return any(marker in key_norm for marker in _SENSITIVE_KEY_PARTS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                redacted[str(key)] = "<redacted>"
            else:
                redacted[str(key)] = _redact_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_TEXT_PATTERN.sub(r"\1=<redacted>", value)
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dumped = yaml.safe_dump(payload, sort_keys=True, allow_unicode=False)
    path.write_text(dumped, encoding="utf-8")


def _collect_env_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in _TRACKED_ENV_VARS:
        raw = os.environ.get(key)
        if raw is None:
            continue
        snapshot[key] = "<redacted>" if _is_sensitive_key(key) else raw
    return snapshot


def _collect_logs(repo_root: Path, out_dir: Path) -> list[str]:
    candidate_paths: list[Path] = []
    for candidate in [
        repo_root / "setup.log",
        repo_root / "setup-errors.log",
        repo_root / "logs",
    ]:
        if not candidate.exists():
            continue
        if candidate.is_file():
            candidate_paths.append(candidate)
        else:
            candidate_paths.extend(sorted(candidate.glob("*.log")))

    copied: list[str] = []
    for src in sorted({p.resolve() for p in candidate_paths}):
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")
        redacted_text = _SENSITIVE_TEXT_PATTERN.sub(r"\1=<redacted>", text)
        dst = out_dir / "logs" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(redacted_text, encoding="utf-8")
        copied.append(str(src))
    return copied


def _build_issue_url(summary: str, report_dir: Path) -> str:
    title = summary if summary else "UnityRAG diagnostics report"
    body = (
        "## Summary\n"
        f"{summary or 'Describe the problem'}\n\n"
        "## Diagnostics\n"
        "- I generated a diagnostics bundle with `unitydocs report`.\n"
        f"- Local bundle path: `{report_dir}`\n"
        "- I can attach the bundle contents on request.\n"
    )
    query = urlencode({"title": title, "body": body})
    return f"https://github.com/Razpines/UnityRAG/issues/new?{query}"


def generate_report(
    *,
    output_dir: Optional[str] = None,
    summary: Optional[str] = None,
    config_path: Optional[str] = None,
    prefill_issue: bool = False,
) -> dict[str, Any]:
    repo_root = _repo_root()
    out_path = Path(output_dir).expanduser() if output_dir else (repo_root / "reports" / "latest")
    if not out_path.is_absolute():
        out_path = (repo_root / out_path).resolve()

    if out_path.exists():
        shutil.rmtree(out_path, ignore_errors=True)
    out_path.mkdir(parents=True, exist_ok=True)

    layer_meta: list[dict[str, Any]] = []
    for layer in config_layer_paths(config_path):
        exists = layer.exists()
        resolved = layer.resolve() if exists else layer
        item = {"path": str(resolved), "exists": exists}
        layer_meta.append(item)
        if not exists:
            continue
        try:
            parsed = yaml.safe_load(layer.read_text(encoding="utf-8")) or {}
            parsed = parsed if isinstance(parsed, dict) else {"raw": str(parsed)}
        except Exception as exc:
            parsed = {"read_error": str(exc)}
        _write_yaml(out_path / "config_layers" / f"{layer.name}.redacted.yaml", _redact_value(parsed))

    load_error: Optional[str] = None
    effective_config: Optional[dict[str, Any]] = None
    try:
        cfg = load_config(config_path)
        effective_config = _redact_value(
            {
                "unity_version": cfg.unity_version,
                "download_url": cfg.download_url,
                "paths": asdict(cfg.paths),
                "bake": asdict(cfg.bake),
                "chunking": asdict(cfg.chunking),
                "index": {
                    "lexical": cfg.index.lexical,
                    "vector": cfg.index.vector,
                    "embedder": asdict(cfg.index.embedder),
                    "rerank_enable": cfg.index.rerank_enable,
                    "candidate_pool": cfg.index.candidate_pool,
                },
                "mcp": asdict(cfg.mcp),
            }
        )
    except Exception as exc:
        load_error = str(exc)

    doctor_error: Optional[str] = None
    doctor_report: Optional[dict[str, Any]] = None
    try:
        doctor_report = run_doctor(config_path=config_path)
    except Exception as exc:
        doctor_error = str(exc)

    copied_logs = _collect_logs(repo_root, out_path)

    _write_json(out_path / "environment.json", _redact_value(_collect_env_snapshot()))
    _write_json(
        out_path / "system.json",
        {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "repo_root": str(repo_root),
        },
    )
    _write_json(out_path / "config_layers.json", layer_meta)
    _write_json(out_path / "effective_config.json", effective_config or {"error": load_error})
    _write_json(out_path / "doctor_report.json", doctor_report or {"error": doctor_error})

    manifest = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary or "",
        "config_path_override": config_path,
        "load_config_error": load_error,
        "doctor_error": doctor_error,
        "logs_copied": copied_logs,
    }
    _write_json(out_path / "report.json", manifest)

    issue_url = _build_issue_url(summary or "UnityRAG diagnostics report", out_path) if prefill_issue else None
    return {
        "report_dir": str(out_path),
        "manifest_path": str(out_path / "report.json"),
        "issue_url": issue_url,
    }
