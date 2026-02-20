from __future__ import annotations

from functools import lru_cache
import sys
from typing import Iterable

import numpy as np


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError(
            "sentence-transformers is required for vector indexing/search. Install with the 'vector' extra."
        ) from exc
    return SentenceTransformer(model_name, device=device)


def _torch_module():
    try:
        import torch
    except Exception as exc:
        raise RuntimeError("torch is required for vector indexing/search. Install with the 'vector' extra.") from exc
    return torch


def _select_device(preference: str) -> str:
    if preference and preference.lower() in {"cpu", "cuda"}:
        return preference.lower()
    torch = _torch_module()
    return "cuda" if torch.cuda.is_available() else "cpu"


def embed_texts(texts: Iterable[str], model_name: str, device: str = "auto") -> np.ndarray:
    torch = _torch_module()
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
