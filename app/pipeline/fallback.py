from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

from app.storage.db import ArticleDB


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def fill_with_previous_day(*, db_path: Path, selected_today: List[Dict[str, Any]], min_items: int, max_items: int, run_date: date) -> List[Dict[str, Any]]:
    """如果当天不足 min_items，则从前一天（严格：前24-48小时范围内）补齐。

    约束：
    - 只补“数据库里真实存在的URL”（即历史抓取过的文章）
    - 只补不在 selected_today 中的URL

    注意：DB里只保存了 url/title/source/publish_time 等轻字段，
    因此这里补齐会优先从 output/前一天/sources_preview.json 找 content/summary/image_url；
    若找不到，则仅能补齐 url/title/source/publish_time，不会用于LLM写作（避免无内容瞎写）。
    """

    if len(selected_today) >= min_items:
        return selected_today[:max_items]

    need = min_items - len(selected_today)

    # 查询前一天 48 小时内的 URL（避免跨太久）
    since = datetime.combine(run_date - timedelta(days=2), datetime.min.time(), tzinfo=timezone.utc)
    until = datetime.combine(run_date, datetime.min.time(), tzinfo=timezone.utc)

    db = ArticleDB(db_path)
    try:
        recent_urls = db.get_recent_urls(since_iso=_iso(since), limit=300)
    finally:
        db.close()

    existing = {a.get("url") for a in selected_today if a.get("url")}

    # 只取前一天范围内的（我们DB没存until过滤，先靠 publish_time>=since，再在文件里二次过滤）
    candidates = [u for u in recent_urls if u and u not in existing]

    # 从 output 目录尝试恢复更完整字段（summary/content/image_url）
    out_dir = Path("./output")
    prev_day = (run_date - timedelta(days=1)).isoformat()
    prev_preview = out_dir / prev_day / "sources_preview.json"
    prev_map: Dict[str, Dict[str, Any]] = {}
    if prev_preview.exists():
        try:
            import json

            data = json.loads(prev_preview.read_text(encoding="utf-8"))
            for a in data:
                url = a.get("url")
                if url:
                    prev_map[url] = a
        except Exception:
            prev_map = {}

    filled: List[Dict[str, Any]] = list(selected_today)

    for u in candidates:
        if len(filled) >= max_items:
            break
        if need <= 0:
            break
        if u in prev_map:
            filled.append(prev_map[u])
            need -= 1

    # 如果仍不足，不再硬补（避免无内容瞎写）
    return filled[:max_items]
