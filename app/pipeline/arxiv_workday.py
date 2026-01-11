from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


@dataclass
class ArxivItem:
    title: str
    url: str
    abstract: str
    submitted_date: Optional[date]


def _parse_abs(html: str) -> Tuple[str, str, Optional[date]]:
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one('h1.title')
    title = title_el.get_text(" ", strip=True) if title_el else ""
    title = re.sub(r"^Title:\s*", "", title).strip()

    abstract_el = soup.select_one('blockquote.abstract')
    abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""
    abstract = re.sub(r"^Abstract:\s*", "", abstract).strip()

    submitted = None
    dateline = soup.select_one('div.dateline')
    if dateline:
        t = dateline.get_text(" ", strip=True)
        m = re.search(r"Submitted\s+on\s+(\d+\s+\w+\s+\d{4})", t)
        if m:
            try:
                submitted = date_parser.parse(m.group(1)).date()
            except Exception:
                submitted = None

    return title, abstract, submitted


def _is_weekday(d: date) -> bool:
    return d.weekday() < 5


def _prev_weekday(d: date) -> date:
    d = d - timedelta(days=1)
    while not _is_weekday(d):
        d = d - timedelta(days=1)
    return d


def pick_target_arxiv_date(today: date) -> date:
    """回退规则：

    - 周六/周日：取最近周五
    - 周一：默认取今天；若不足20条再回退到上周五（调用方负责判定不足后回退）
    - 周二~周五：默认取今天；不足20条回退到前一工作日

    这里先给出“初始目标日”：
    - 若 today 为周末，直接返回最近周五
    - 否则返回 today
    """
    if _is_weekday(today):
        return today
    # weekend -> last Friday
    d = today
    while not _is_weekday(d):
        d = d - timedelta(days=1)
    return d


def fetch_pastweek_items(max_abs: int = 200, timeout: float = 30.0) -> List[ArxivItem]:
    url = f"https://arxiv.org/list/cs.AI/pastweek?show={max_abs}"
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        r = client.get(url)
        r.raise_for_status()
        html = r.text

    soup = BeautifulSoup(html, "lxml")
    dts = soup.select('dl dt')

    items: List[ArxivItem] = []
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for dt in dts:
            abs_a = dt.select_one('a[href^="/abs/"]')
            if not abs_a:
                continue
            abs_url = "https://arxiv.org" + abs_a.get('href')
            try:
                abs_html = client.get(abs_url).text
                title, abstract, submitted = _parse_abs(abs_html)
                if not title:
                    continue
                items.append(ArxivItem(title=title, url=abs_url, abstract=abstract, submitted_date=submitted))
            except Exception:
                continue
            if len(items) >= max_abs:
                break

    return items


def select_arxiv_for_day(items: List[ArxivItem], target: date, need_total: int = 20) -> List[ArxivItem]:
    """从 pastweek items 中筛出目标日期的条目；如果不足 need_total，则调用方应回退 target"""
    day_items = [x for x in items if x.submitted_date == target]
    return day_items[:need_total]
