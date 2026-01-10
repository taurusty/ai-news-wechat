from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.images.cover import generate_cover
from app.images.downloader import download_image, guess_ext_from_url, safe_filename
from app.images.separator import generate_separator


def prepare_images(*, day_dir: Path, selected: List[Dict[str, Any]], draft_type: str, cover_cfg: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, str]]:
    """为当天输出准备图片文件

    返回：
    - cover_rel: 封面相对路径（相对 day_dir）
    - images_rel: article_url -> image相对路径（相对 day_dir）

    策略：
    - 生成封面 cover.png
    - 每条新闻：优先下载其 image_url；若没有/下载失败，生成一个 separator 图片充当“配图占位”
    """

    day_dir.mkdir(parents=True, exist_ok=True)
    images_dir = day_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 1) cover
    cover_rel = None
    try:
        title = "AI热点" if draft_type == "daily_summary" else "深度解读"
        subtitle = "每日资讯播报 + 结论" if draft_type == "daily_summary" else "产业分析 · 产品评测"
        date_str = day_dir.name
        cover_path = day_dir / "cover.png"
        generate_cover(
            out_path=cover_path,
            title=title,
            subtitle=subtitle,
            date_str=date_str,
            width=int(cover_cfg.get("width", 900)),
            height=int(cover_cfg.get("height", 500)),
        )
        cover_rel = "cover.png"
    except Exception:
        cover_rel = None

    # 2) per-article images
    images_rel: Dict[str, str] = {}
    for idx, a in enumerate(selected, 1):
        url = a.get("url")
        img_url = a.get("image_url")
        if not url:
            continue

        rel = None
        if img_url:
            ext = guess_ext_from_url(img_url)
            fname = f"{idx:02d}_{safe_filename(a.get('source','src'))}{ext}"
            out_path = images_dir / fname
            got = download_image(img_url, out_path)
            if got:
                rel = f"images/{fname}"

        if not rel:
            # 生成分隔图当做占位
            fname = f"{idx:02d}_sep.png"
            out_path = images_dir / fname
            try:
                generate_separator(out_path=out_path, text="AI 快讯")
                rel = f"images/{fname}"
            except Exception:
                rel = None

        if rel:
            images_rel[url] = rel

    return cover_rel, images_rel
