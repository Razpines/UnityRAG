from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from tqdm import tqdm

from unity_docs_mcp.bake.chunker import chunk_text_md
from unity_docs_mcp.bake.extract_manual import extract_manual
from unity_docs_mcp.bake.extract_scriptref import extract_scriptref
from unity_docs_mcp.bake.html_to_md import HtmlToTextOptions
from unity_docs_mcp.bake.link_graph import build_link_edges, doc_id_from_relpath, resolve_internal_link
from unity_docs_mcp.config import Config, config_signature, load_config
from unity_docs_mcp.paths import make_paths
from unity_docs_mcp.setup.detect_version import detect_version_info


def load_html_paths(unzipped_root: Path) -> List[Path]:
    base = unzipped_root / "Documentation" / "en"
    manual = list((base / "Manual").rglob("*.html"))
    scriptref = list((base / "ScriptReference").rglob("*.html"))
    return manual + scriptref


def bake(config: Config) -> Dict[str, int]:
    paths = make_paths(config)
    paths.ensure_dirs()

    options = HtmlToTextOptions(
        keep_images=config.bake.keep_images,
        include_figure_captions=config.bake.include_figure_captions,
    )

    html_paths = load_html_paths(paths.raw_unzipped)
    doc_map: Dict[str, Dict] = {}
    pages: List[Dict] = []

    # Precompute doc_id map
    for html_path in html_paths:
        rel = html_path.relative_to(paths.raw_unzipped)
        doc_id = doc_id_from_relpath(rel.as_posix())
        doc_map[html_path.as_posix()] = {
            "doc_id": doc_id,
            "origin_path": rel.as_posix(),
            "source_type": "scriptref" if "ScriptReference" in rel.parts else "manual",
        }

    for html_path in tqdm(html_paths, desc="Bake pages"):
        rel = html_path.relative_to(paths.raw_unzipped).as_posix()
        meta = doc_map[html_path.as_posix()]
        if meta["source_type"] == "manual":
            extracted = extract_manual(html_path, options, config.bake.drop_sections)
        else:
            extracted = extract_scriptref(html_path, options)

        text_md = extracted["text_md"]
        if len(text_md) < config.bake.min_page_chars:
            # skip pages that look empty
            continue

        links = []
        for link in extracted.get("links", []):
            resolved = resolve_internal_link(link["href_raw"], html_path, paths.raw_unzipped)
            target_doc_id = resolved["to_doc_id"] if resolved else None
            link["target_doc_id"] = target_doc_id
            links.append(link)

        page_record = {
            "doc_id": meta["doc_id"],
            "source_type": meta["source_type"],
            "title": extracted["title"],
            "canonical_url": extracted.get("canonical_url"),
            "origin_path": rel,
            "text_md": text_md,
            "metadata": {},
            "out_links": links,
        }
        pages.append(page_record)

    baked_dir = paths.baked_dir
    baked_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = baked_dir / "corpus.jsonl"
    chunks_path = baked_dir / "chunks.jsonl"
    link_graph_path = baked_dir / "link_graph.jsonl"
    manifest_path = baked_dir / "manifest.json"

    with corpus_path.open("w", encoding="utf-8") as f_corpus, chunks_path.open(
        "w", encoding="utf-8"
    ) as f_chunks:
        total_chunks = 0
        for page in pages:
            f_corpus.write(json.dumps(page, ensure_ascii=False) + "\n")
            chunks = chunk_text_md(
                doc_id=page["doc_id"],
                title=page["title"],
                text_md=page["text_md"],
                origin_path=page["origin_path"],
                canonical_url=page.get("canonical_url"),
                max_chars=config.chunking.max_chars,
                overlap=config.chunking.overlap_chars,
            )
            for chunk in chunks:
                f_chunks.write(
                    json.dumps(
                        {
                            "chunk_id": chunk.chunk_id,
                            "doc_id": chunk.doc_id,
                            "source_type": page["source_type"],
                            "title": chunk.title,
                            "heading_path": chunk.heading_path,
                            "text": chunk.text,
                            "char_start": chunk.char_start,
                            "char_end": chunk.char_end,
                            "origin_path": chunk.origin_path,
                            "canonical_url": chunk.canonical_url,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                total_chunks += 1

    edges = build_link_edges(pages)
    with link_graph_path.open("w", encoding="utf-8") as f_links:
        for edge in edges:
            f_links.write(json.dumps(edge, ensure_ascii=False) + "\n")

    version_info = detect_version_info(paths.raw_unzipped)
    manifest = {
        "unity_version": config.unity_version,
        "build_from": version_info.get("build_from"),
        "built_on": version_info.get("built_on"),
        "pages": len(pages),
        "chunks": total_chunks,
        "config_signature": config_signature(config),
    }
    with manifest_path.open("w", encoding="utf-8") as f_manifest:
        json.dump(manifest, f_manifest, indent=2)

    return {"pages": len(pages), "chunks": total_chunks}


def main() -> None:
    config = load_config()
    stats = bake(config)
    print(f"Baked {stats['pages']} pages into {stats['chunks']} chunks.")


if __name__ == "__main__":
    main()
