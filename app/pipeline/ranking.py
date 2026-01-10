from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from app.sources.base import Article


@dataclass
class ScoredArticle:
    article: Article
    score: float


def freshness_score(publish_time: datetime) -> float:
    # 越新分越高：按小时衰减
    now = datetime.now(timezone.utc)
    pt = publish_time
    if pt.tzinfo is None:
        pt = pt.replace(tzinfo=timezone.utc)
    hours = max(0.0, (now - pt).total_seconds() / 3600.0)
    return max(0.0, 1.0 - hours / 48.0)  # 48小时外趋近0


def score_articles(articles: List[Article], source_weights: dict[str, float]) -> List[ScoredArticle]:
    scored: List[ScoredArticle] = []
    for a in articles:
        w = source_weights.get(a.source, 1.0)
        s = 0.6 * w + 0.4 * freshness_score(a.publish_time)
        scored.append(ScoredArticle(article=a, score=s))
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
