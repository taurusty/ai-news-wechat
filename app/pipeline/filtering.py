import re
from typing import Iterable, List

from app.sources.base import Article


def normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def keyword_filter(articles: Iterable[Article], keywords_any: List[str], keywords_not: List[str]) -> List[Article]:
    kw_any = [k.lower() for k in (keywords_any or []) if k]
    kw_not = [k.lower() for k in (keywords_not or []) if k]

    out: List[Article] = []
    for a in articles:
        hay = (normalize_text(a.title) + " " + normalize_text(a.summary) + " " + normalize_text(a.content[:500])).lower()
        if kw_any and not any(k in hay for k in kw_any):
            continue
        if kw_not and any(k in hay for k in kw_not):
            continue
        out.append(a)
    return out
