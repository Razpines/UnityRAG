from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

from bs4 import BeautifulSoup


def parse_version_fields(html_text: str) -> Dict[str, Optional[str]]:
    version_info = {"build_from": None, "built_on": None}
    match = re.search(r"Built from\s+([^\s]+)\s*\.?\s*Built on:\s*([\d-]+)", html_text, re.IGNORECASE)
    if match:
        version_info["build_from"] = match.group(1)
        version_info["built_on"] = match.group(2)
    return version_info


def detect_version_info(unzipped_root: Path) -> Dict[str, Optional[str]]:
    """
    Attempt to detect build metadata from a known manual page footer.
    """
    manual_index = unzipped_root / "Documentation" / "en" / "Manual" / "index.html"
    script_index = unzipped_root / "Documentation" / "en" / "ScriptReference" / "index.html"

    target = manual_index if manual_index.exists() else script_index
    if not target.exists():
        return {"build_from": None, "built_on": None}

    with target.open("r", encoding="utf-8", errors="ignore") as f:
        html_text = f.read()
    soup = BeautifulSoup(html_text, "lxml")
    text = soup.get_text(" ", strip=True)
    return parse_version_fields(text)
