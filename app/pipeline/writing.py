from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.llm.deepseek_client import DeepSeekClient
from app.llm.prompts import build_daily_summary_prompt, build_deep_dive_prompt


def generate_daily_article(
    articles: List[Dict[str, Any]],
    date_str: str,
    client: Optional[DeepSeekClient] = None,
    *,
    min_items: int = 5,
    max_items: int = 10,
) -> Dict[str, Any]:
    """生成日常干货总结文章

    约束：
    - 输出至少 min_items 条、最多 max_items 条
    - 不允许编造未提供来源的内容
    """
    close_client = False
    if client is None:
        client = DeepSeekClient()
        close_client = True

    try:
        messages = build_daily_summary_prompt(articles, date_str, min_items=min_items, max_items=max_items)
        markdown = client.chat(messages, temperature=0.5, max_tokens=1800)
        return {
            "type": "daily_summary",
            "date": date_str,
            "markdown": markdown,
            "source_articles": articles,
        }
    finally:
        if close_client:
            client.close()


def generate_deep_dive(article: Dict[str, Any], date_str: str, client: Optional[DeepSeekClient] = None) -> Dict[str, Any]:
    """生成深度解读文章（围绕Top 1新闻）"""
    close_client = False
    if client is None:
        client = DeepSeekClient()
        close_client = True

    try:
        messages = build_deep_dive_prompt(article)
        markdown = client.chat(messages, temperature=0.6, max_tokens=3500)
        return {
            "type": "deep_dive",
            "date": date_str,
            "markdown": markdown,
            "main_article": article,
        }
    finally:
        if close_client:
            client.close()


def is_deep_dive_day(run_date: date, deep_dive_weekday: int) -> bool:
    return run_date.weekday() == deep_dive_weekday
