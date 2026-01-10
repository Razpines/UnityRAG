from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import requests
from tqdm import tqdm


def download_zip(url: str, destination: Path, overwrite: bool = False, progress: bool = True) -> Path:
    """
    Download the UnityDocumentation zip if it does not already exist.
    """
    if destination.exists() and not overwrite:
        return destination

    print(f"==> Downloading offline docs from {url}...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        chunk_size = 8192
        bar = tqdm(total=total, unit="B", unit_scale=True, disable=not progress)
        with destination.open("wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
        bar.close()
    return destination
