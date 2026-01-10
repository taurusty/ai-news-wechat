from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx


def guess_ext_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        if path.endswith(ext):
            return ext
    return ".jpg"


def safe_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5_-]+", "_", name)
    return name[:80].strip("_") or "img"


def download_image(url: str, out_path: str | Path, *, timeout: float = 30.0) -> Optional[Path]:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(url)
            if r.status_code != 200 or not r.content:
                return None
            out_path.write_bytes(r.content)
        return out_path
    except Exception:
        return None
