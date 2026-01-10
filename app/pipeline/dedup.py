from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from simhash import Simhash

from app.sources.base import Article


def normalize_title(title: str) -> str:
    t = (title or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def title_simhash(title: str) -> str:
    # 用Simhash的64bit值做去重指纹
    return str(Simhash(normalize_title(title)).value)


@dataclass
class DedupResult:
    kept: List[Article]
    dropped: List[Tuple[Article, str]]  # (article, reason)


def dedup_by_url(articles: List[Article]) -> DedupResult:
    seen = set()
    kept, dropped = [], []
    for a in articles:
        if a.url in seen:
            dropped.append((a, "duplicate_url"))
            continue
        seen.add(a.url)
        kept.append(a)
    return DedupResult(kept=kept, dropped=dropped)


def dedup_by_title_simhash(articles: List[Article], max_hamming: int = 3) -> DedupResult:
    kept: List[Article] = []
    dropped: List[Tuple[Article, str]] = []

    kept_hashes: List[Simhash] = []
    for a in articles:
        sh = Simhash(normalize_title(a.title))
        dup = False
        for existing in kept_hashes:
            if sh.distance(existing) <= max_hamming:
                dup = True
                break
        if dup:
            dropped.append((a, "duplicate_title_simhash"))
        else:
            kept.append(a)
            kept_hashes.append(sh)

    return DedupResult(kept=kept, dropped=dropped)
