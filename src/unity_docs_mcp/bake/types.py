from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PageRecord:
    doc_id: str
    source_type: str
    title: str
    canonical_url: Optional[str]
    origin_path: str
    text_md: str
    metadata: Dict[str, str] = field(default_factory=dict)
    out_links: List[Dict[str, str]] = field(default_factory=list)
