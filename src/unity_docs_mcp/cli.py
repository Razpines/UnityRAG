from __future__ import annotations

import argparse
import os

from unity_docs_mcp.config import UNITY_VERSION_ENV, load_config
from unity_docs_mcp.doctor import main as doctor_main
from unity_docs_mcp.mcp_server import main_http
from unity_docs_mcp.report import generate_report
from unity_docs_mcp.setup.ensure_artifacts import ensure


def _cmd_install(args: argparse.Namespace) -> None:
    if args.cleanup:
        os.environ["UNITY_DOCS_MCP_CLEANUP"] = "1"
    os.environ[UNITY_VERSION_ENV] = args.version.strip()
    config = load_config()
    ensure(config)


def _cmd_mcp(_: argparse.Namespace) -> None:
    main_http()


def _cmd_doctor(args: argparse.Namespace) -> None:
    raise SystemExit(doctor_main(json_output=args.json, config_path=args.config))


def _cmd_report(args: argparse.Namespace) -> None:
    result = generate_report(
        output_dir=args.output,
        summary=args.summary,
        config_path=args.config,
        prefill_issue=args.prefill_issue,
    )
    print(f"[report] Diagnostics bundle written to: {result['report_dir']}")
    print(f"[report] Manifest: {result['manifest_path']}")
    if result["issue_url"]:
        print(f"[report] Prefilled issue URL: {result['issue_url']}")


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

    report_parser = subparsers.add_parser("report", help="Create a redacted diagnostics bundle.")
    report_parser.add_argument(
        "--output",
        default=None,
        help="Output directory for report files (default: reports/latest under repo root).",
    )
    report_parser.add_argument("--summary", default=None, help="Short problem summary for the report manifest.")
    report_parser.add_argument("--config", default=None, help="Optional config file path override.")
    report_parser.add_argument(
        "--prefill-issue",
        action="store_true",
        help="Print a prefilled GitHub issue URL that references this report.",
    )
    report_parser.set_defaults(func=_cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
