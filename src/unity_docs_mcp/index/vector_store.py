from __future__ import annotations

from pathlib import Path
from typing import Any, Tuple

import numpy as np


def _import_faiss() -> Any:
    try:
        import faiss
    except Exception as exc:
        raise RuntimeError("FAISS is required for vector indexing/search. Install with the 'vector' extra.") from exc
    return faiss


def build_faiss_index(vectors: np.ndarray) -> Any:
    faiss = _import_faiss()
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors.astype("float32"))
    return index


def save_faiss(index: Any, path: Path) -> None:
    faiss = _import_faiss()
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_faiss(path: Path) -> Any:
    faiss = _import_faiss()
    return faiss.read_index(str(path))


def search_faiss(index: Any, query_vec: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
    return index.search(query_vec.astype("float32"), k)
