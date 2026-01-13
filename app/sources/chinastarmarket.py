import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import trafilatura
from readability import Document

from app.sources.base import BaseSource, Article


def parse_view_count(text: str) -> Optional[int]:
    """解析阅读量文本，如："25,698" "2.3万" "阅读 2.1万" "2万+"。

    返回整数阅读量；解析失败返回 None。
    """
    if not text:
        return None
    t = text.strip()
    t = t.replace(",", "")
    t = re.sub(r"\s+", "", t)
    t = t.replace("阅读", "").replace("浏览", "").replace("次", "").replace("+", "")

    m = re.search(r"(\d+(?:\.\d+)?)(万)?", t)
    if not m:
        return None
    num = float(m.group(1))
    if m.group(2) == "万":
        num *= 10000
    try:
        return int(num)
    except Exception:
        return None


class ChinaStarMarketSource(BaseSource):
    """科创头条 - chinastarmarket.cn

    目标：
    - 从站点首页抓取“阅读量”候选
    - 严格取阅读量 Top10 作为候选池
    - 再抓取详情并返回 5-10 条（由上层 max_items 控制）

    说明：
    - chinastarmarket 首页 DOM 结构可能调整，因此这里用“链接 + 父容器文本”做宽松提取。
    - 如果阅读量解析不足 10 条，会退化为按已解析到的阅读量降序。
    """

    def __init__(self, weight: float = 1.0, enabled: bool = True):
        super().__init__(
            base_url="https://www.chinastarmarket.cn/",
            source_name="chinastarmarket",
            weight=weight,
            enabled=enabled,
        )

    async def fetch_articles(self, max_items: int = 10) -> List[Article]:
        """从首页抓取阅读量>1000的文章
        
        规则：
        - 降低阅读量阈值：从>10000降低到>1000（更容易凑够5条）
        - 从首页抓取所有符合条件的文章，按阅读量降序
        - 返回前 max_items 条
        
        注意：/telegraph 页面是动态加载的（Next.js），无法直接抓取
        """
        # 降低阈值：从>10000降到>1000
        articles = await self._fetch_from_homepage_lowered_threshold(max_items, min_view_count=1000)
        print(f"[INFO] 从首页抓取到 {len(articles)} 篇文章（阅读量>1000）")
        
        return articles[:max_items]

    async def _fetch_from_homepage_lowered_threshold(self, max_items: int = 10, min_view_count: int = 1000) -> List[Article]:
        """从首页抓取阅读量>min_view_count的文章
        
        Args:
            max_items: 最多返回的文章数
            min_view_count: 最低阅读量阈值（默认1000，原来是10000）
        """
        list_url = "https://www.chinastarmarket.cn/"
        html = await self.fetch(list_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html, "lxml")

        # candidates: url -> (title, view_count)
        candidates: Dict[str, Tuple[str, int]] = {}

        for a in soup.select('a[href]'):
            href = a.get('href')
            if not href:
                continue

            if href.startswith('/'):
                url = self.make_absolute_url(href)
            elif href.startswith('https://www.chinastarmarket.cn/'):
                url = href
            else:
                continue

            if not any(x in url for x in ["/detail/", "/news/", "/article/"]):
                continue

            title = (a.get_text() or "").strip()
            if len(title) < 6:
                continue

            # 在父容器文本中抓"阅读量"
            container_text = ""
            try:
                container = a
                for _ in range(5):
                    container = container.parent
                    if not container:
                        break
                    container_text = container.get_text(" ", strip=True)
                    if (
                        re.search(r"\b\d{1,3}(?:,\d{3})+\b", container_text)
                        or ("万" in container_text)
                        or ("阅读" in container_text)
                        or ("浏览" in container_text)
                    ):
                        break
            except Exception:
                container_text = ""

            vc = parse_view_count(container_text)
            if vc is None:
                continue
            # 降低阈值：从10000降到min_view_count
            if vc < min_view_count:
                continue

            if url not in candidates or vc > candidates[url][1]:
                candidates[url] = (title, vc)

            # 宽松限制：避免遍历太久（增加到150个）
            if len(candidates) >= 150:
                break

        # 按阅读量降序排序
        sorted_candidates = sorted(
            [(u, t, vc) for u, (t, vc) in candidates.items()],
            key=lambda x: x[2],
            reverse=True,
        )

        articles: List[Article] = []
        # 抓取前 max_items*2 个候选（多抓一些，避免详情页失败）
        for url, title, vc in sorted_candidates[:max_items * 2]:
            try:
                art = await self._fetch_detail(url, fallback_title=title)
                if art:
                    art.extra = art.extra or {}
                    art.extra["view_count"] = vc
                    articles.append(art)
                    print(f"[INFO] 科创头条成功抓取: [{vc:,}次] {title[:40]}")
            except Exception as e:
                print(f"[WARN] 抓取详情失败 {url}: {e}")
                continue

            if len(articles) >= max_items:
                break

        return articles

    # 注意：/telegraph 页面是动态加载的（Next.js），无法直接抓取
    # 已改为降低首页阅读量阈值（从>10000降到>1000）来确保有足够文章

    async def _fetch_detail(self, url: str, fallback_title: str = "") -> Optional[Article]:
        html = await self.fetch(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html, "lxml")

        # 尝试从__NEXT_DATA__提取（Next.js动态渲染）
        next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if next_data_script:
            try:
                import json
                data = json.loads(next_data_script.get_text())
                page_data = data.get('props', {}).get('pageProps', {}).get('data', {})
                
                if page_data:
                    title = page_data.get('title', fallback_title)
                    brief = page_data.get('brief', '')
                    content_html = page_data.get('content', '')
                    
                    # 从HTML内容提取纯文本
                    if content_html:
                        content_soup = BeautifulSoup(content_html, 'lxml')
                        content = content_soup.get_text("\n", strip=True)
                    else:
                        content = brief
                    
                    content = re.sub(r"\n{3,}", "\n\n", content).strip()
                    summary = brief[:220] if brief else content[:220].replace("\n", " ")
                    
                    # 提取图片
                    image_url = None
                    if content_html:
                        content_soup = BeautifulSoup(content_html, 'lxml')
                        img = content_soup.find('img')
                        if img:
                            src = img.get('src') or img.get('data-src')
                            if src:
                                if src.startswith('http'):
                                    image_url = src
                                elif src.startswith('/'):
                                    image_url = self.make_absolute_url(src)
                    
                    # 从og:image获取
                    if not image_url:
                        og_img = soup.find('meta', {"property": "og:image"})
                        if og_img and og_img.get('content'):
                            image_url = og_img['content'].strip()
                    
                    publish_time = datetime.now()
                    
                    return Article(
                        title=title,
                        url=url,
                        summary=summary,
                        content=content,
                        publish_time=publish_time,
                        source=self.source_name,
                        source_name="科创板日报",
                        author="",
                        image_url=image_url,
                        tags=[],
                        extra={},
                    )
            except Exception as e:
                print(f"[WARN] 解析__NEXT_DATA__失败: {e}")
        
        # 回退到传统方法（虽然可能抓不到内容）
        title = fallback_title
        h1 = soup.find('h1')
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
        
        # 尝试从title标签获取
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
        
        title = title.strip()
        if not title:
            return None

        publish_time = datetime.now()
        
        # 从 og:image 获取
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
        summary = content[:220].replace("\n", " ") if content else ""

        return Article(
            title=title,
            url=url,
            summary=summary,
            content=content,
            publish_time=publish_time,
            source=self.source_name,
            source_name="科创板日报",
            author="",
            image_url=image_url,
            tags=[],
            extra={},
        )
