from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from app.sources.base import Article
from app.pipeline.dedup import title_simhash
from app.storage.db import ArticleDB


def persist_new_articles(db: ArticleDB, articles: List[Article], *, enable_history_dedup: bool = True) -> Tuple[List[Article], List[Article]]:
    """把文章写入DB，并返回 (to_write_articles, already_seen_articles)

    - enable_history_dedup=True：只返回“历史未见过”的新文章（默认：避免重复选题）
    - enable_history_dedup=False：即使历史见过，也会返回文章用于生成（仍会 INSERT OR IGNORE 写库）

    说明：用户实践中经常需要“每天都生成一篇”，因此主流程可以在 new=0 时自动降级用 seen 生成。
    """

    to_write: List[Article] = []
    seen: List[Article] = []

    now = datetime.now(timezone.utc).isoformat()
    for a in articles:
        already = db.has_url(a.url)
        if already:
            seen.append(a)
            if enable_history_dedup:
                continue
        else:
            db.insert_article(
                url=a.url,
                title=a.title,
                title_simhash=title_simhash(a.title),
                source=a.source,
                publish_time=a.publish_time.isoformat(),
                created_at=now,
            )
        to_write.append(a)

    return to_write, seen
