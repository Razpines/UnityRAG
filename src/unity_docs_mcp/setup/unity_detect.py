from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

SUPPORTED_DOCS_VERSIONS = ["6000.5", "6000.4", "6000.3", "6000.0"]
DEFAULT_DOCS_VERSION = "6000.3"
FALLBACK_RULE = (
    "prefer exact major.minor match; otherwise highest supported version with same major; "
    f"otherwise {DEFAULT_DOCS_VERSION}"
)


def parse_editor_version(name: str) -> Optional[str]:
    match = re.search(r"(\d{4}\.\d+)", name or "")
    return match.group(1) if match else None


def _version_key(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except Exception:
        return (0,)


def candidate_editor_roots() -> list[Path]:
    home = Path.home()
    if sys.platform.startswith("win"):
        local_app_data = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return [
            Path(r"C:\Program Files\Unity\Hub\Editor"),
            Path(r"C:\Program Files\Unity Hub\Editor"),
            local_app_data / "Unity" / "Hub" / "Editor",
        ]
    if sys.platform == "darwin":
        return [
            Path("/Applications/Unity/Hub/Editor"),
            home / "Applications" / "Unity" / "Hub" / "Editor",
        ]
    return [
        home / ".local" / "share" / "UnityHub" / "Editor",
        Path("/opt/Unity/Hub/Editor"),
    ]


def discover_unity_editors() -> list[dict[str, str]]:
    discovered: list[dict[str, str]] = []
    for root in candidate_editor_roots():
        if not root.is_dir():
            continue
        try:
            children = sorted(root.iterdir())
        except Exception:
            continue
        for child in children:
            if not child.is_dir():
                continue
            version = parse_editor_version(child.name)
            if not version:
                continue
            discovered.append(
                {
                    "version": version,
                    "path": str(child.resolve()),
                }
            )
    return sorted(discovered, key=lambda item: (_version_key(item["version"]), item["path"]), reverse=True)


def suggest_docs_version(
    detected_versions: list[str],
    supported_versions: list[str] | None = None,
    fallback_version: str = DEFAULT_DOCS_VERSION,
) -> str:
    supported = supported_versions or SUPPORTED_DOCS_VERSIONS
    supported_sorted = sorted(set(supported), key=_version_key, reverse=True)
    detected_sorted = sorted(set(detected_versions), key=_version_key, reverse=True)
    if not detected_sorted:
        return fallback_version

    for detected in detected_sorted:
        if detected in supported_sorted:
            return detected

    highest_detected = detected_sorted[0]
    detected_major = highest_detected.split(".")[0]
    same_major = [version for version in supported_sorted if version.split(".")[0] == detected_major]
    if same_major:
        return same_major[0]
    return fallback_version


def _collect() -> dict[str, object]:
    discovered = discover_unity_editors()
    detected_versions = [item["version"] for item in discovered]
    suggested = suggest_docs_version(detected_versions)
    return {
        "detected": discovered,
        "suggested": suggested,
        "supported_docs_versions": SUPPORTED_DOCS_VERSIONS,
        "fallback_rule": FALLBACK_RULE,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect local Unity installs and suggest docs version.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--suggest-only", action="store_true", help="Print only the suggested docs version.")
    args = parser.parse_args()

    payload = _collect()
    if args.suggest_only:
        print(payload["suggested"])
        return 0
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    detected = payload["detected"]
    if detected:
        print("[detect] Detected Unity editors:")
        for item in detected:
            print(f"  - {item['version']} @ {item['path']}")
    else:
        print("[detect] No local Unity editor installs detected.")
    print(f"[detect] Supported docs versions: {', '.join(payload['supported_docs_versions'])}")
    print(f"[detect] Suggested docs version: {payload['suggested']}")
    print(f"[detect] Fallback rule: {payload['fallback_rule']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
