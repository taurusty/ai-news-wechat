from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.llm.deepseek_client import DeepSeekClient
from app.llm.prompts import (
    build_daily_summary_prompt,
    build_starmarket_prompt,
    build_arxiv_prompt,
)


def generate_column_content(
    column_name: str,
    articles: List[Dict[str, Any]],
    date_str: str,
    client: DeepSeekClient,
    *,
    min_items: int,
    max_items: int,
) -> Optional[Dict[str, Any]]:
    """根据栏目名称，分发到不同的生成函数"""
    if "每日简报" in column_name or "每日资讯" in column_name:
        return generate_daily_article(
            articles, date_str, client, min_items=min_items, max_items=max_items
        )
    elif "科创热点" in column_name or "科创头条" in column_name:
        return generate_starmarket_column(
            articles, date_str, client, min_items=min_items, max_items=max_items
        )
    elif "学术动态" in column_name:
        return generate_arxiv_column(
            articles, date_str, client, min_items=min_items, max_items=max_items
        )
    else:
        print(f"[WARN] Unknown column name: {column_name}, skipping LLM generation.")
        return None


def generate_daily_article(
    articles: List[Dict[str, Any]],
    date_str: str,
    client: DeepSeekClient,
    *,
    min_items: int = 5,
    max_items: int = 10,
) -> Dict[str, Any]:
    """生成“每日资讯”栏目"""
    messages = build_daily_summary_prompt(
        articles, date_str, min_items=min_items, max_items=max_items
    )
    markdown = client.chat(messages, temperature=0.5, max_tokens=1800)
    return {
        "type": "daily_news",
        "name": "每日简报",
        "date": date_str,
        "markdown": markdown,
        "source_articles": articles,
    }


def generate_starmarket_column(
    articles: List[Dict[str, Any]],
    date_str: str,
    client: DeepSeekClient,
    *,
    min_items: int = 5,
    max_items: int = 10,
) -> Dict[str, Any]:
    """生成“科创头条”栏目"""
    messages = build_starmarket_prompt(
        articles, date_str, min_items=min_items, max_items=max_items
    )
    markdown = client.chat(messages, temperature=0.5, max_tokens=2200)
    return {
        "type": "star_market",
        "name": "科创热点",
        "date": date_str,
        "markdown": markdown,
        "source_articles": articles,
    }


def generate_arxiv_column(
    articles: List[Dict[str, Any]],
    date_str: str,
    client: DeepSeekClient,
    *,
    min_items: int = 10,
    max_items: int = 10,
) -> Dict[str, Any]:
    """生成“学术动态”栏目，从20篇论文中精选10篇"""
    messages = build_arxiv_prompt(
        articles, date_str, select_count=min_items
    )
    markdown = client.chat(messages, temperature=0.4, max_tokens=4000)
    return {
        "type": "arxiv_papers",
        "name": "学术动态",
        "date": date_str,
        "markdown": markdown,
        "source_articles": articles, # Here we pass all 20, the LLM does the selection
    }
