from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from tqdm import tqdm

from unity_docs_mcp.config import Config, config_signature, load_config
from unity_docs_mcp.index.embed import embed_texts
from unity_docs_mcp.index.fts import ingest_chunks, init_db
from unity_docs_mcp.index.vector_store import build_faiss_index, save_faiss
from unity_docs_mcp.paths import make_paths


def load_chunks(chunks_path: Path) -> List[Dict]:
    items = []
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            items.append(json.loads(line))
    return items


def index(config: Config, dry_run: bool = False) -> Dict[str, int]:
    paths = make_paths(config)
    baked_dir = paths.baked_dir
    chunks_path = baked_dir / "chunks.jsonl"
    if not chunks_path.exists():
        raise FileNotFoundError("chunks.jsonl not found; run bake first.")

    chunks = load_chunks(chunks_path)
    fts_db = paths.index_dir / "fts.sqlite"
    if dry_run:
        print(
            f"[dry-run] Loaded {len(chunks)} chunks. Would embed with model={config.index.embedder.model} "
            f"device={config.index.embedder.device}"
        )
        return {"chunks": len(chunks)}

    conn = init_db(fts_db)
    ingest_chunks(
        conn,
        (
            (
                c["chunk_id"],
                c["doc_id"],
                c["source_type"],
                c["title"],
                "/".join(c.get("heading_path", [])),
                c.get("origin_path", ""),
                c.get("canonical_url", "") or "",
                c["text"],
            )
            for c in chunks
        ),
    )

    embed_texts_list = [
        f"{c['title']} {' '.join(c.get('heading_path', []))} {c['text']}" for c in chunks
    ]
    vectors = embed_texts(
        embed_texts_list,
        model_name=config.index.embedder.model,
        device=config.index.embedder.device,
    )
    index = build_faiss_index(vectors.astype("float32"))
    save_faiss(index, paths.index_dir / "vectors.faiss")

    meta_path = paths.index_dir / "vectors_meta.jsonl"
    paths.index_dir.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f_meta:
        for c in chunks:
            f_meta.write(json.dumps({"chunk_id": c["chunk_id"], "doc_id": c["doc_id"]}) + "\n")

    manifest_path = paths.index_dir / "manifest.json"
    manifest = {
        "chunks": len(chunks),
        "config_signature": config_signature(config),
    }
    with manifest_path.open("w", encoding="utf-8") as f_manifest:
        json.dump(manifest, f_manifest, indent=2)

    return {"chunks": len(chunks)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Load chunks and report device/model, then exit.")
    args = parser.parse_args()

    config = load_config()
    stats = index(config, dry_run=args.dry_run)
    print(f"Indexed {stats['chunks']} chunks.")


if __name__ == "__main__":
    main()
