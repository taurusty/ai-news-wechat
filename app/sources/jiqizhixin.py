import re
import json
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
        # 使用机器之心的API接口
        api_url = "https://www.jiqizhixin.com/api/v1/articles"
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Referer": "https://www.jiqizhixin.com/"
            }
            json_text = await self.fetch(api_url, headers=headers)
            articles_data = json.loads(json_text)
            
            articles: List[Article] = []
            for item in articles_data:
                try:
                    # 从API数据构建文章
                    title = item.get('title', '').strip()
                    if not title or 'title-' in title:  # 跳过无效标题
                        continue
                    
                    # 构建文章URL（猜测格式）
                    # 注意：API没有返回URL，可能需要进一步调整
                    description = item.get('description', '').strip()
                    cover_image = item.get('cover_image')
                    author_info = item.get('author', {})
                    author = author_info.get('author_name', '') if author_info else ''
                    
                    if not description or len(description) < 20:
                        continue
                    
                    # 由于API没有返回详细URL，我们暂时无法获取完整内容
                    # 仅使用description作为summary和content
                    article = Article(
                        title=title,
                        url=self.base_url,  # 暂时使用首页URL
                        summary=description[:180],
                        content=description,
                        publish_time=datetime.utcnow(),
                        source=self.source_name,
                        source_name="机器之心",
                        author=author,
                        image_url=cover_image,
                        tags=[],
                        extra={},
                    )
                    articles.append(article)
                    
                    if len(articles) >= max_items:
                        break
                except Exception:
                    continue
            
            return articles
        except Exception as e:
            raise SourceError(f"jiqizhixin API fetch failed: {e}")

    async def _parse_list(self, html: str, max_items: int) -> List[Article]:
        # 保留旧方法以备用
        return []

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
