from __future__ import annotations

import argparse
import os

from unity_docs_mcp.config import Config, PathsConfig
from unity_docs_mcp.doctor import main as doctor_main
from unity_docs_mcp.mcp_server import main_http
from unity_docs_mcp.setup.ensure_artifacts import ensure


def _config_for_version(version: str) -> Config:
    base = Config()
    base.unity_version = version
    base.download_url = (
        f"https://cloudmedia-docs.unity3d.com/docscloudstorage/en/{version}/UnityDocumentation.zip"
    )
    base.paths = PathsConfig(
        root=f"data/unity/{version}",
        raw_zip=f"data/unity/{version}/raw/UnityDocumentation.zip",
        raw_unzipped=f"data/unity/{version}/raw/UnityDocumentation",
        baked_dir=f"data/unity/{version}/baked",
        index_dir=f"data/unity/{version}/index",
    )
    return base


def _cmd_install(args: argparse.Namespace) -> None:
    if args.cleanup:
        os.environ["UNITY_DOCS_MCP_CLEANUP"] = "1"
    config = _config_for_version(args.version)
    ensure(config)


def _cmd_mcp(_: argparse.Namespace) -> None:
    main_http()


def _cmd_doctor(args: argparse.Namespace) -> None:
    raise SystemExit(doctor_main(json_output=args.json, config_path=args.config))


def main() -> None:
    parser = argparse.ArgumentParser(prog="unitydocs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Download, bake, and index docs.")
    install_parser.add_argument("--version", default="6000.3", help="Unity docs version (e.g., 6000.3).")
    install_parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove raw zip and unzipped docs after indexing.",
    )
    install_parser.set_defaults(func=_cmd_install)

    mcp_parser = subparsers.add_parser("mcp", help="Start the HTTP MCP server.")
    mcp_parser.set_defaults(func=_cmd_mcp)

    doctor_parser = subparsers.add_parser("doctor", help="Run preflight diagnostics.")
    doctor_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    doctor_parser.add_argument("--config", default=None, help="Optional config file path override.")
    doctor_parser.set_defaults(func=_cmd_doctor)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
