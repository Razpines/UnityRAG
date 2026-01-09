from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    heading_path: List[str]
    text: str
    char_start: int
    char_end: int
    origin_path: str
    canonical_url: str | None


def stable_chunk_id(doc_id: str, heading_path: List[str], ordinal: int) -> str:
    base = f"{doc_id}|{'/'.join(heading_path)}|{ordinal}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def chunk_text_md(
    doc_id: str,
    title: str,
    text_md: str,
    origin_path: str,
    canonical_url: str | None,
    max_chars: int = 6000,
    overlap: int = 300,
) -> List[Chunk]:
    """
    Split markdown-ish text into heading-aware chunks.
    """
    lines = text_md.splitlines()
    heading_path: List[str] = []
    buffer: List[str] = []
    chunks: List[Chunk] = []
    current_chars = 0
    ordinal = 0

    def flush_buffer(current_heading: List[str]):
        nonlocal buffer, current_chars, ordinal
        if not buffer:
            return
        text = "\n".join(buffer).strip()
        if not text:
            buffer = []
            return
        start = current_chars
        end = start + len(text)
        chunk_id = stable_chunk_id(doc_id, current_heading, ordinal)
        ordinal += 1
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                title=title,
                heading_path=list(current_heading),
                text=text,
                char_start=start,
                char_end=end,
                origin_path=origin_path,
                canonical_url=canonical_url,
            )
        )
        current_chars = end
        # carry overlap
        if overlap > 0:
            overlap_text = text[-overlap:]
            buffer = [overlap_text] if overlap_text else []
        else:
            buffer = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            flush_buffer(heading_path)
            level = len(stripped.split()[0])
            title_part = stripped[level:].strip()
            if len(heading_path) >= level:
                heading_path = heading_path[: level - 1]
            heading_path.append(title_part)
            buffer.append(stripped)
            continue

        buffer.append(stripped)
        if sum(len(p) + 1 for p in buffer) >= max_chars:
            flush_buffer(heading_path)

    flush_buffer(heading_path)
    return chunks
