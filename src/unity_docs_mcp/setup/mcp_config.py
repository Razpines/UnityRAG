from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from unity_docs_mcp.config import UNITY_VERSION_ENV


def _config_root_key(client: str) -> str:
    return "servers" if client == "codex" else "mcpServers"


def _resolve_unity_version(unity_version: Optional[str]) -> str:
    resolved = (unity_version or os.environ.get(UNITY_VERSION_ENV, "")).strip()
    if resolved:
        return resolved
    raise ValueError(
        f"Missing Unity docs version. Pass --unity-version or set {UNITY_VERSION_ENV}."
    )


def _server_config(repo_root: Path, unity_version: str) -> dict[str, Any]:
    root = repo_root.resolve()
    if os.name == "nt":
        command = root / ".venv" / "Scripts" / "unitydocs-mcp.exe"
    else:
        command = root / ".venv" / "bin" / "unitydocs-mcp"
    return {
        "command": str(command),
        "args": [],
        "env": {
            UNITY_VERSION_ENV: unity_version,
        },
    }


def default_config_paths(client: str) -> list[Path]:
    home = Path.home()
    if client == "codex":
        if os.name == "nt":
            return [home / ".codex" / "mcp.json", home / ".codex" / "mcp_config.json"]
        return [home / ".codex" / "mcp.json", home / ".config" / "codex" / "mcp.json"]

    if os.name == "nt":
        appdata = Path(os.environ.get("APPDATA") or (home / "AppData" / "Roaming"))
        return [appdata / "Claude" / "claude_desktop_config.json"]
    return [
        home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        home / ".config" / "Claude" / "claude_desktop_config.json",
    ]


def resolve_config_path(client: str, override: Optional[str] = None) -> Path:
    if override:
        return Path(override).expanduser()
    defaults = default_config_paths(client)
    for candidate in defaults:
        if candidate.exists():
            return candidate
    return defaults[0]


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")
    return parsed


def _backup_config(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.parent / f"{path.name}.bak.{stamp}"
    shutil.copy2(path, backup)
    return backup


def install_mcp_config(
    *,
    client: str,
    repo_root: Path,
    unity_version: Optional[str] = None,
    config_path: Optional[str] = None,
    server_name: str = "unity-docs",
    dry_run: bool = False,
) -> tuple[Path, Optional[Path]]:
    if client not in {"codex", "claude"}:
        raise ValueError("client must be 'codex' or 'claude'")

    target = resolve_config_path(client, config_path)
    data = _load_json_object(target)
    root_key = _config_root_key(client)
    servers = data.get(root_key, {})
    if not isinstance(servers, dict):
        raise ValueError(f"Config field '{root_key}' must be an object.")

    servers[server_name] = _server_config(
        repo_root=repo_root,
        unity_version=_resolve_unity_version(unity_version),
    )
    data[root_key] = servers

    if dry_run:
        return target, None

    target.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_config(target)
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return target, backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Install UnityRAG MCP server into Codex/Claude config.")
    parser.add_argument("--client", choices=["codex", "claude"], required=True)
    parser.add_argument("--repo-root", default=".", help="Path to UnityRAG repo root.")
    parser.add_argument(
        "--unity-version",
        default=None,
        help=f"Unity docs version to store in server env ({UNITY_VERSION_ENV}).",
    )
    parser.add_argument("--config", default=None, help="Optional explicit config file path.")
    parser.add_argument("--server-name", default="unity-docs", help="Server name in client config.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target, backup = install_mcp_config(
        client=args.client,
        repo_root=Path(args.repo_root).resolve(),
        unity_version=args.unity_version,
        config_path=args.config,
        server_name=args.server_name,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(f"[mcp-config] Dry run complete. Target: {target}")
        return

    print(f"[mcp-config] Updated {args.client} config: {target}")
    if backup:
        print(f"[mcp-config] Backup saved: {backup}")


if __name__ == "__main__":
    main()
