from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

import numpy as np
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_texts(texts: Iterable[str], model_name: str) -> np.ndarray:
    model = _load_model(model_name)
    return np.array(model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True))
