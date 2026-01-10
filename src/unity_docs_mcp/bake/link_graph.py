from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional


def doc_id_from_relpath(rel_path: str) -> str:
    cleaned = rel_path.replace("\\", "/")
    cleaned = re.sub(r"^Documentation/en/", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(".html", "")
    cleaned = cleaned.replace(" ", "-")
    return cleaned.lower()


def resolve_internal_link(href: str, origin_path: Path, unzipped_root: Path) -> Optional[Dict[str, str]]:
    if href.startswith("http://") or href.startswith("https://") or href.startswith("mailto:"):
        return None
    if href.startswith("#"):
        return None
    clean_href = href.split("#", 1)[0].split("?", 1)[0]
    if not clean_href:
        return None
    if clean_href.startswith("/"):
        rel_root = clean_href.lstrip("/")
        target = (unzipped_root / "Documentation" / "en" / rel_root).resolve()
    elif clean_href.lower().startswith(("manual/", "scriptreference/")):
        target = (unzipped_root / "Documentation" / "en" / clean_href).resolve()
    else:
        target = (origin_path.parent / clean_href).resolve()
    try:
        rel = target.relative_to(unzipped_root)
    except ValueError:
        return None
    if target.suffix.lower() != ".html":
        return None
    doc_id = doc_id_from_relpath(rel.as_posix())
    return {"from_path": origin_path, "to_path": rel.as_posix(), "to_doc_id": doc_id, "href_raw": href}


def build_link_edges(pages: List[Dict]) -> List[Dict[str, str]]:
    edges: List[Dict[str, str]] = []
    for page in pages:
        doc_id = page["doc_id"]
        for link in page.get("out_links", []):
            target = link.get("target_doc_id")
            if target:
                edges.append(
                    {
                        "from_doc_id": doc_id,
                        "to_doc_id": target,
                        "href_text": link.get("href_text", ""),
                        "href_raw": link.get("href_raw", ""),
                    }
                )
    return edges
