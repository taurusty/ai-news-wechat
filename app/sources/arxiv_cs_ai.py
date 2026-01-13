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

        方案A：解析 list 页的 <h3> 日期标题，只抓取对应日期的 <dl> 内容。
        """
        url = "https://arxiv.org/list/cs.AI/recent"
        html = await self.fetch(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html, "lxml")

        # 1) 在 list 页找到目标日期对应分组：解析所有 <h3> 文本为日期，不依赖字符串硬匹配
        def _parse_h3_date(text: str) -> Optional[date]:
            t = (text or "").strip()
            # arXiv 的 h3 往往长这样："Mon, 12 Jan 2026 (showing first 50 of 120 entries )"
            # 先截断括号后缀，再做 fuzzy parse，避免解析失败
            t = t.split("(", 1)[0].strip()
            try:
                return date_parser.parse(t, fuzzy=True).date()
            except Exception:
                return None

        h3 = None
        for h in soup.find_all("h3"):
            d = _parse_h3_date(h.get_text(" ", strip=True))
            if d == target_date:
                h3 = h
                break

        if not h3:
            h3_texts = [x.get_text(" ", strip=True) for x in soup.find_all("h3")][:12]
            print(f"[INFO] 在 arXiv list 页面未找到日期分组 {target_date}，页面前12个h3={h3_texts}")
            return []

        # 2) h3 在 dl#articles 内部，收集该 h3 之后、下一个 h3 之前的所有 dt/dd 对
        candidates = []
        
        # 从 h3 开始遍历后续的兄弟节点
        current = h3.find_next_sibling()
        while current:
            # 如果遇到下一个 h3，停止
            if current.name == 'h3':
                break
            
            # 收集 dt 和对应的 dd
            if current.name == 'dt':
                dt = current
                dd = dt.find_next_sibling('dd')
                if dd:
                    candidates.append((dt, dd))
            
            current = current.find_next_sibling()
        
        print(f"[INFO] 日期 {target_date} 收集到 {len(candidates)} 个候选论文链接")
        
        # 3. 从 dt/dd 对中提取链接、标题、发布时间
        paper_data = []
        for dt, dd in candidates:
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

                # 解析提交日期，作为 publish_time
                publish_time = datetime.now()
                dateline_el = dd.select_one('.list-dateline')
                if dateline_el:
                    submitted_text = dateline_el.get_text(strip=True)
                    m = re.search(r"\(Submitted on (.*?)\)", submitted_text)
                    if m:
                        try:
                            publish_time = date_parser.parse(m.group(1))
                        except Exception:
                            pass

                paper_data.append((abs_url, title, publish_time))
            except Exception:
                continue

        print(f"[INFO] 日期 {target_date} 成功解析 {len(paper_data)} 篇论文信息")

        # 4. 并发抓取摘要信息
        import asyncio
        semaphore = asyncio.Semaphore(5)

        async def fetch_one(abs_url: str, title: str, pub_time: datetime) -> Optional[Article]:
            async with semaphore:
                try:
                    abs_html = await self.fetch(abs_url, headers={"User-Agent": "Mozilla/5.0"})
                    abs_soup = BeautifulSoup(abs_html, "lxml")

                    abstract_el = abs_soup.select_one('blockquote.abstract')
                    abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""
                    abstract = re.sub(r"^Abstract:\s*", "", abstract).strip()

                    return Article(
                        title=title,
                        url=abs_url,
                        summary=abstract[:220] if abstract else "",
                        content=abstract,
                        publish_time=pub_time,
                        source=self.source_name,
                        source_name="arXiv cs.AI",
                        author="",
                        image_url=None,
                        tags=[],
                        extra={},
                    )
                except Exception:
                    return None

        tasks = [fetch_one(url, title, ptime) for url, title, ptime in paper_data[:need_count]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        articles = [r for r in results if isinstance(r, Article)]

        print(f"[INFO] 日期 {target_date} 成功抓取 {len(articles)} 篇文章")
        return articles
