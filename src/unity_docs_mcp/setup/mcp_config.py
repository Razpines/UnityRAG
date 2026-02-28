from __future__ import annotations

import argparse
import json
import os
import re
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
            return [home / ".codex" / "config.toml", home / ".codex" / "mcp.json", home / ".codex" / "mcp_config.json"]
        return [home / ".codex" / "config.toml", home / ".codex" / "mcp.json", home / ".config" / "codex" / "mcp.json"]

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


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", key):
        return key
    return _toml_string(key)


def _server_block_toml(*, server_name: str, config: dict[str, Any]) -> str:
    args = config.get("args", [])
    env = config.get("env", {})
    args_str = ", ".join(_toml_string(str(item)) for item in args)
    env_parts = [f"{_toml_key(str(k))} = {_toml_string(str(v))}" for k, v in env.items()]
    env_str = "{ " + ", ".join(env_parts) + " }"
    lines = [
        f"[mcp_servers.{_toml_key(server_name)}]",
        "enabled = true",
        f"command = {_toml_string(str(config.get('command', '')))}",
        f"args = [{args_str}]",
        f"env = {env_str}",
    ]
    return "\n".join(lines) + "\n"


def _upsert_codex_toml_server(*, path: Path, server_name: str, config: dict[str, Any]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block = _server_block_toml(server_name=server_name, config=config)
    name_esc = re.escape(server_name)
    pattern = re.compile(rf"^\[mcp_servers\.(?:{name_esc}|\"{name_esc}\")\]\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match:
        start = match.start()
        next_header = re.search(r"^\[", text[match.end() :], flags=re.MULTILINE)
        end = match.end() + next_header.start() if next_header else len(text)
        replacement = block if block.endswith("\n") else block + "\n"
        new_text = text[:start] + replacement + text[end:].lstrip("\n")
    else:
        separator = "\n" if text and not text.endswith("\n") else ""
        new_text = text + separator + ("\n" if text else "") + block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")


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
    server_cfg = _server_config(
        repo_root=repo_root,
        unity_version=_resolve_unity_version(unity_version),
    )

    if dry_run:
        return target, None

    backup = _backup_config(target)
    if client == "codex" and target.suffix.lower() == ".toml":
        _upsert_codex_toml_server(path=target, server_name=server_name, config=server_cfg)
        return target, backup

    data = _load_json_object(target)
    root_key = _config_root_key(client)
    servers = data.get(root_key, {})
    if not isinstance(servers, dict):
        raise ValueError(f"Config field '{root_key}' must be an object.")

    servers[server_name] = server_cfg
    data[root_key] = servers
    target.parent.mkdir(parents=True, exist_ok=True)
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
