from __future__ import annotations

from functools import lru_cache
import sys
from typing import Iterable

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str) -> SentenceTransformer:
    return SentenceTransformer(model_name, device=device)


def _select_device(preference: str) -> str:
    if preference and preference.lower() in {"cpu", "cuda"}:
        return preference.lower()
    return "cuda" if torch.cuda.is_available() else "cpu"


def embed_texts(texts: Iterable[str], model_name: str, device: str = "auto") -> np.ndarray:
    resolved_device = _select_device(device)
    cuda_info = {
        "torch_cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
    }
    print(f"[embed] using device={resolved_device} model={model_name} info={cuda_info}", file=sys.stderr)
    model = _load_model(model_name, resolved_device)
    return np.array(
        model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
    )
