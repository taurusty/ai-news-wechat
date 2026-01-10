from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

import httpx
from lxml import etree

from app.sources.exceptions import SourceError


@dataclass
class Article:
    """统一文章数据结构"""
    title: str
    url: str
    summary: str
    content: str
    publish_time: datetime
    source: str
    source_name: str
    author: str = ""
    image_url: Optional[str] = None
    tags: List[str] = None
    extra: Dict[str, Any] = None

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "content": self.content,
            "publish_time": self.publish_time.isoformat(),
            "source": self.source,
            "source_name": self.source_name,
            "author": self.author,
            "image_url": self.image_url,
            "tags": self.tags or [],
            "extra": self.extra or {}
        }


class BaseSource(ABC):
    """所有抓取源的基类"""
    
    def __init__(self, base_url: str, source_name: str, weight: float = 1.0, enabled: bool = True):
        self.base_url = base_url
        self.source_name = source_name
        self.weight = weight
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
    async def close(self):
        await self.client.aclose()
        
    async def fetch(self, url: str, method: str = "GET", **kwargs) -> str:
        """发送HTTP请求并返回文本（带简单重试，处理429/5xx）"""
        import asyncio
        last_err = None
        for attempt in range(3):
            try:
                resp = await self.client.request(method, url, **kwargs)
                # 429/5xx 做退避重试
                if resp.status_code == 429 or 500 <= resp.status_code <= 599:
                    last_err = SourceError(f"HTTP {resp.status_code} for {url}")
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                last_err = e
                await asyncio.sleep(1.0 * (attempt + 1))
        raise SourceError(f"Failed to fetch {url}: {str(last_err)}")
    
    async def fetch_html(self, url: str, **kwargs) -> etree._Element:
        """获取并解析HTML"""
        html = await self.fetch(url, **kwargs)
        return etree.HTML(html)
    
    def make_absolute_url(self, url: str) -> str:
        """将相对URL转换为绝对URL"""
        if url.startswith('http'):
            return url
        return urljoin(self.base_url, url)
    
    @abstractmethod
    async def fetch_articles(self, max_items: int = 10) -> List[Article]:
        """抓取文章列表，子类必须实现此方法"""
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self.source_name}>"