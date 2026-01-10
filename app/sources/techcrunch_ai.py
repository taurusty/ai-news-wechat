import re
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import trafilatura
from readability import Document

from app.sources.base import BaseSource, Article


class TechCrunchAISource(BaseSource):
    """TechCrunch AI频道抓取"""

    def __init__(self, weight: float = 1.1, enabled: bool = True):
        super().__init__(base_url="https://techcrunch.com/", source_name="techcrunch_ai", weight=weight, enabled=enabled)

    async def fetch_articles(self, max_items: int = 10) -> List[Article]:
        list_url = "https://techcrunch.com/category/artificial-intelligence/"
        html = await self.fetch(list_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html, "lxml")

        links = []
        for a in soup.select('a[href]'):
            href = a.get('href')
            if not href:
                continue
            if href.startswith('https://techcrunch.com/'):
                url = href
            elif href.startswith('/'):
                url = self.make_absolute_url(href)
            else:
                continue

            # TechCrunch文章一般是 https://techcrunch.com/2026/01/01/.../
            if not re.search(r"techcrunch\.com/\d{4}/\d{2}/\d{2}/", url):
                continue

            title = (a.get_text() or "").strip()
            if len(title) < 8:
                continue

            if url not in [u for u, _ in links]:
                links.append((url, title))
            if len(links) >= max_items * 3:
                break

        articles: List[Article] = []
        for url, title in links[: max_items * 3]:
            try:
                art = await self._fetch_detail(url, fallback_title=title)
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

        title = fallback_title
        h1 = soup.find('h1')
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
        title = title.strip()
        if not title:
            return None

        publish_time = datetime.utcnow()
        meta_time = soup.find('meta', {"property": "article:published_time"})
        if meta_time and meta_time.get('content'):
            try:
                publish_time = date_parser.parse(meta_time['content'])
            except Exception:
                pass
        else:
            time_tag = soup.find('time')
            if time_tag:
                t = time_tag.get('datetime') or time_tag.get_text(strip=True)
                if t:
                    try:
                        publish_time = date_parser.parse(t)
                    except Exception:
                        pass

        author = ""
        meta_author = soup.find('meta', {"name": "author"})
        if meta_author and meta_author.get('content'):
            author = meta_author['content'].strip()

        image_url = None
        og_img = soup.find('meta', {"property": "og:image"})
        if og_img and og_img.get('content'):
            image_url = og_img['content'].strip()

        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        content = (extracted or "").strip()
        if not content:
            doc = Document(html)
            content_html = doc.summary()
            content = BeautifulSoup(content_html, 'lxml').get_text("\n", strip=True)

        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        summary = content[:180].replace("\n", " ") if content else ""

        return Article(
            title=title,
            url=url,
            summary=summary,
            content=content,
            publish_time=publish_time,
            source=self.source_name,
            source_name="TechCrunch(Artificial Intelligence)",
            author=author,
            image_url=image_url,
            tags=[],
            extra={},
        )
