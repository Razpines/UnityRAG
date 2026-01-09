from __future__ import annotations

from pathlib import Path
from typing import Tuple

import faiss
import numpy as np


def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors.astype("float32"))
    return index


def save_faiss(index: faiss.Index, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_faiss(path: Path) -> faiss.Index:
    return faiss.read_index(str(path))


def search_faiss(index: faiss.Index, query_vec: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
    return index.search(query_vec.astype("float32"), k)
