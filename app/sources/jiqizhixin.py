import re
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from readability import Document
import trafilatura

from app.sources.base import BaseSource, Article
from app.sources.exceptions import SourceError


class JiqizhixinSource(BaseSource):
    """机器之心 - AI新闻抓取"""

    def __init__(self, weight: float = 1.2, enabled: bool = True):
        super().__init__(base_url="https://www.jiqizhixin.com/", source_name="jiqizhixin", weight=weight, enabled=enabled)

    async def fetch_articles(self, max_items: int = 10) -> List[Article]:
        # 机器之心首页/推荐流会变，使用“资讯”聚合页更稳定（若失效再降级到首页）
        list_urls = [
            "https://www.jiqizhixin.com/",
        ]

        last_err = None
        for list_url in list_urls:
            try:
                html = await self.fetch(list_url, headers={"User-Agent": "Mozilla/5.0"})
                return await self._parse_list(html, max_items=max_items)
            except Exception as e:
                last_err = e
                continue
        raise SourceError(f"jiqizhixin list fetch failed: {last_err}")

    async def _parse_list(self, html: str, max_items: int) -> List[Article]:
        soup = BeautifulSoup(html, "lxml")
        # 尝试提取文章链接
        links = []
        for a in soup.select('a[href^="/articles/"]'):
            href = a.get("href")
            title = (a.get_text() or "").strip()
            if not href:
                continue
            url = self.make_absolute_url(href)
            if "/articles/" in url and url not in [x[0] for x in links]:
                links.append((url, title))
            if len(links) >= max_items * 2:
                break

        articles: List[Article] = []
        for url, fallback_title in links[: max_items * 2]:
            try:
                art = await self._fetch_detail(url, fallback_title=fallback_title)
                if art:
                    articles.append(art)
            except Exception:
                continue
            if len(articles) >= max_items:
                break
        return articles

    async def _fetch_detail(self, url: str, fallback_title: str = "") -> Article:
        html = await self.fetch(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html, "lxml")

        # 标题
        title = fallback_title
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
        title = title.strip()
        if not title:
            return None

        # 时间：尝试从time标签或meta提取
        publish_time = datetime.utcnow()
        time_tag = soup.find("time")
        if time_tag and (time_tag.get("datetime") or time_tag.get_text(strip=True)):
            t = time_tag.get("datetime") or time_tag.get_text(strip=True)
            try:
                publish_time = date_parser.parse(t)
            except Exception:
                pass
        else:
            meta_time = soup.find("meta", {"property": "article:published_time"})
            if meta_time and meta_time.get("content"):
                try:
                    publish_time = date_parser.parse(meta_time["content"])
                except Exception:
                    pass

        # 作者
        author = ""
        meta_author = soup.find("meta", {"name": "author"})
        if meta_author and meta_author.get("content"):
            author = meta_author["content"].strip()

        # 首图
        image_url = None
        og_img = soup.find("meta", {"property": "og:image"})
        if og_img and og_img.get("content"):
            image_url = og_img["content"].strip()

        # 正文提取：优先 trafilatura，其次 readability
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        content = (extracted or "").strip()
        if not content:
            doc = Document(html)
            content_html = doc.summary()
            content = BeautifulSoup(content_html, "lxml").get_text("\n", strip=True)

        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        summary = content[:180].replace("\n", " ") if content else ""

        return Article(
            title=title,
            url=url,
            summary=summary,
            content=content,
            publish_time=publish_time,
            source=self.source_name,
            source_name="机器之心",
            author=author,
            image_url=image_url,
            tags=[],
            extra={},
        )
