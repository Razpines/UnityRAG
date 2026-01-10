from __future__ import annotations

import subprocess
import sys


BLOCKED_PREFIXES = ("data/",)
BLOCKED_SUFFIXES = (".faiss", "fts.sqlite")
BLOCKED_SUBSTRINGS = ("/baked/", "/index/")
BLOCKED_JSONL = ".jsonl"


def _git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _is_blocked(path: str) -> bool:
    if path.startswith(BLOCKED_PREFIXES):
        return True
    if path.endswith(BLOCKED_SUFFIXES):
        return True
    if path.endswith(BLOCKED_JSONL) and any(part in path for part in BLOCKED_SUBSTRINGS):
        return True
    return False


def main() -> int:
    tracked = _git_ls_files()
    blocked = [p for p in tracked if _is_blocked(p)]
    if blocked:
        print("Blocked artifacts detected in git index:")
        for p in blocked:
            print(f"  - {p}")
        print("Remove these files from git and keep artifacts under data/ untracked.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
