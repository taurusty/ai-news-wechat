import re
from datetime import datetime, date, timedelta
from typing import List, Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.sources.base import BaseSource, Article


def _is_weekday(d: date) -> bool:
    """判断是否为工作日（周一到周五）"""
    return d.weekday() < 5


def _prev_weekday(d: date) -> date:
    """获取前一个工作日"""
    d = d - timedelta(days=1)
    while not _is_weekday(d):
        d = d - timedelta(days=1)
    return d


class ArxivCsAiSource(BaseSource):
    """arXiv cs.AI recent 列表抓取

    规则：
    - 周一至周五从 https://arxiv.org/list/cs.AI/recent 抓取
    - 抓取当天的前20篇文章（通过 submitted_date 判断）
    - 如果当天不足20篇，则回溯到前一天继续抓取
    - 只抓取 abs 页的标题/摘要/链接，不下载PDF
    """

    def __init__(self, weight: float = 1.0, enabled: bool = True):
        super().__init__(base_url="https://arxiv.org/", source_name="arxiv_cs_ai", weight=weight, enabled=enabled)

    async def fetch_articles(self, max_items: int = 20) -> List[Article]:
        """抓取当天的前20篇，不足则回溯前一天"""
        target_date = datetime.now().date()
        
        # 如果不是工作日，取最近的工作日
        if not _is_weekday(target_date):
            target_date = _prev_weekday(target_date)
        
        articles = await self._fetch_for_date(target_date, max_items)
        
        # 如果当天不足20篇，回溯到前一天
        if len(articles) < max_items:
            prev_date = _prev_weekday(target_date)
            print(f"[INFO] 当天({target_date})只有{len(articles)}篇，回溯到前一天({prev_date})补充")
            prev_articles = await self._fetch_for_date(prev_date, max_items - len(articles))
            articles.extend(prev_articles)
        
        print(f"[INFO] arXiv 最终抓取到 {len(articles)} 篇文章（目标日期: {target_date}）")
        return articles[:max_items]

    async def _fetch_for_date(self, target_date: date, need_count: int) -> List[Article]:
        """抓取指定日期的文章
        
        优化：先批量获取所有候选的 abs_url，然后并发抓取（但限制并发数避免过载）
        """
        url = "https://arxiv.org/list/cs.AI/recent"
        html = await self.fetch(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html, "lxml")

        # arXiv recent 页面结构：dt (id) + dd (meta)
        dts = soup.select('dl dt')
        dds = soup.select('dl dd')
        pairs = list(zip(dts, dds))

        # 第一步：先收集所有候选的 URL 和标题（不访问 abs 页）
        candidates = []
        for dt, dd in pairs[:need_count * 4]:  # 多收集一些候选
            try:
                abs_a = dt.select_one('a[href^="/abs/"]')
                if not abs_a:
                    continue
                abs_url = self.make_absolute_url(abs_a.get('href'))

                title_el = dd.select_one('.list-title')
                title = (title_el.get_text(" ", strip=True) if title_el else "")
                title = re.sub(r"^Title:\s*", "", title).strip()
                if not title:
                    continue
                    
                candidates.append((abs_url, title))
            except Exception:
                continue

        print(f"[INFO] 收集到 {len(candidates)} 个候选论文链接")

        # 第二步：并发抓取 abs 页面（限制并发数）
        import asyncio
        semaphore = asyncio.Semaphore(5)  # 最多5个并发请求
        
        async def fetch_one(abs_url: str, title: str) -> Optional[Article]:
            async with semaphore:
                try:
                    abs_html = await self.fetch(abs_url, headers={"User-Agent": "Mozilla/5.0"})
                    abs_soup = BeautifulSoup(abs_html, "lxml")

                    abstract_el = abs_soup.select_one('blockquote.abstract')
                    abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""
                    abstract = re.sub(r"^Abstract:\s*", "", abstract).strip()

                    # 解析提交日期
                    submitted_date = None
                    publish_time = datetime.utcnow()
                    dateline = abs_soup.select_one('div.dateline')
                    if dateline and dateline.get_text(strip=True):
                        t = dateline.get_text(" ", strip=True)
                        m = re.search(r"Submitted\s+on\s+(\d+\s+\w+\s+\d{4})", t)
                        if m:
                            try:
                                publish_time = date_parser.parse(m.group(1))
                                submitted_date = publish_time.date()
                            except Exception:
                                pass

                    # 只保留目标日期的文章
                    if submitted_date != target_date:
                        return None

                    image_url = None
                    content = abstract
                    summary = abstract[:220] if abstract else ""

                    return Article(
                        title=title,
                        url=abs_url,
                        summary=summary,
                        content=content,
                        publish_time=publish_time,
                        source=self.source_name,
                        source_name="arXiv cs.AI",
                        author="",
                        image_url=image_url,
                        tags=[],
                        extra={},
                    )
                except Exception as e:
                    return None

        # 并发抓取
        tasks = [fetch_one(url, title) for url, title in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = []
        for r in results:
            if isinstance(r, Article):
                articles.append(r)
                if len(articles) >= need_count:
                    break

        print(f"[INFO] 日期 {target_date} 找到 {len(articles)} 篇文章（检查了 {len(candidates)} 个候选）")
        return articles
