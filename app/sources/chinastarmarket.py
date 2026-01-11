import re
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
        """从首页抓取，不足5条时从 /telegraph 补充
        
        规则：
        - 先从首页抓取阅读量>10000的文章（Top10候选）
        - 如果不足5条，从 /telegraph 页面补充到至少5条
        - 最终返回不超过 max_items 条
        """
        min_required = 5
        
        # 第一步：从首页抓取
        articles = await self._fetch_from_homepage(max_items)
        print(f"[INFO] 从首页抓取到 {len(articles)} 篇文章")
        
        # 如果不足5条，从 /telegraph 补充
        if len(articles) < min_required:
            need_more = min_required - len(articles)
            print(f"[INFO] 不足{min_required}条，需要从 /telegraph 补充 {need_more} 篇")
            telegraph_articles = await self._fetch_from_telegraph(need_more)
            
            # 去重：避免重复URL
            existing_urls = {a.url for a in articles}
            added_count = 0
            for art in telegraph_articles:
                if art.url not in existing_urls:
                    articles.append(art)
                    added_count += 1
                    if len(articles) >= max_items:
                        break
            
            print(f"[INFO] 从 /telegraph 补充了 {added_count} 篇，当前共 {len(articles)} 篇")
        
        return articles[:max_items]

    async def _fetch_from_homepage(self, max_items: int = 10) -> List[Article]:
        """从首页抓取阅读量>10000的文章"""
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
            # 阅读量必须大于10000
            if vc < 10000:
                continue

            if url not in candidates or vc > candidates[url][1]:
                candidates[url] = (title, vc)

            # 宽松限制：避免遍历太久
            if len(candidates) >= 80:
                break

        # 按阅读量降序取Top10候选
        sorted_candidates = sorted(
            [(u, t, vc) for u, (t, vc) in candidates.items()],
            key=lambda x: x[2],
            reverse=True,
        )
        top10 = sorted_candidates[:10]

        articles: List[Article] = []
        for url, title, vc in top10:
            try:
                art = await self._fetch_detail(url, fallback_title=title)
                if art:
                    art.extra = art.extra or {}
                    art.extra["view_count"] = vc
                    articles.append(art)
            except Exception:
                continue

            if len(articles) >= max_items:
                break

        return articles

    async def _fetch_from_telegraph(self, need_count: int) -> List[Article]:
        """从 /telegraph 页面抓取文章补充
        
        根据实际页面结构：
        <a class="... list-link" href="/detail/2254121" ...>
            <strong>标题</strong>
        </a>
        """
        telegraph_url = "https://www.chinastarmarket.cn/telegraph"
        articles: List[Article] = []
        
        try:
            html = await self.fetch(telegraph_url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(html, "lxml")
            
            links = []
            seen_urls = set()
            
            # 优先使用 list-link 类选择器（根据实际页面结构）
            for a in soup.select('a.list-link, a[class*="list-link"]'):
                href = a.get('href')
                if not href:
                    continue
                    
                if href.startswith('/'):
                    url = self.make_absolute_url(href)
                elif href.startswith('https://www.chinastarmarket.cn/'):
                    url = href
                else:
                    continue
                    
                # 只抓取 /detail/ 开头的文章
                if '/detail/' not in url:
                    continue
                    
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 标题可能在 <strong> 标签内，或者直接在 a 标签的文本中
                title = ""
                strong = a.find('strong')
                if strong:
                    title = strong.get_text(strip=True)
                else:
                    title = a.get_text(strip=True)
                
                # 如果还是太短，尝试获取整个链接的文本
                if len(title) < 6:
                    title = a.get_text(" ", strip=True)
                
                # 清理标题：移除可能的【】标记
                title = re.sub(r'^【.*?】', '', title).strip()
                
                if len(title) < 6:
                    continue
                    
                links.append((url, title))
                    
                # 多抓一些候选，因为可能有些抓取失败
                if len(links) >= need_count * 4:
                    break
            
            # 如果 list-link 选择器没找到足够的，回退到通用选择器
            if len(links) < need_count:
                for a in soup.select('a[href*="/detail/"]'):
                    href = a.get('href')
                    if not href:
                        continue
                        
                    if href.startswith('/'):
                        url = self.make_absolute_url(href)
                    elif href.startswith('https://www.chinastarmarket.cn/'):
                        url = href
                    else:
                        continue
                        
                    if '/detail/' not in url:
                        continue
                        
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    title = a.get_text(strip=True)
                    # 清理标题
                    title = re.sub(r'^【.*?】', '', title).strip()
                    
                    if len(title) >= 6:
                        links.append((url, title))
                        
                    if len(links) >= need_count * 4:
                        break
            
            print(f"[INFO] 从 /telegraph 找到 {len(links)} 个候选链接")
            
            # 抓取详情
            for url, title in links:
                if len(articles) >= need_count:
                    break
                try:
                    art = await self._fetch_detail(url, fallback_title=title)
                    if art:
                        # telegraph 页面可能没有阅读量，设为0
                        art.extra = art.extra or {}
                        if "view_count" not in art.extra:
                            art.extra["view_count"] = 0
                        articles.append(art)
                        print(f"[INFO] 从 /telegraph 成功抓取: {art.title[:50]}")
                except Exception as e:
                    print(f"[WARN] 抓取 /telegraph 文章失败 {url}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[WARN] 从 /telegraph 补充抓取失败: {e}")
            import traceback
            traceback.print_exc()
            
        print(f"[INFO] 从 /telegraph 最终补充了 {len(articles)} 篇文章")
        return articles

    async def _fetch_detail(self, url: str, fallback_title: str = "") -> Optional[Article]:
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

        # 优先从 og:image 获取
        image_url = None
        og_img = soup.find('meta', {"property": "og:image"})
        if og_img and og_img.get('content'):
            image_url = og_img['content'].strip()
        
        # 如果 og:image 没有，从文章正文中提取第一张图片
        if not image_url:
            # 尝试从正文中找 img 标签
            img_tags = soup.select('article img, .content img, .article-content img, .post-content img, [class*="content"] img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src:
                    if src.startswith('http'):
                        image_url = src
                    elif src.startswith('/'):
                        image_url = self.make_absolute_url(src)
                    else:
                        image_url = self.make_absolute_url(src)
                    break

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
