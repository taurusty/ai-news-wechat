from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.images.cover import generate_cover
from app.images.downloader import download_image, guess_ext_from_url, safe_filename
from app.images.separator import generate_separator


def prepare_images(*, day_dir: Path, selected: List[Dict[str, Any]], draft_type: str, cover_cfg: Dict[str, Any], column_name: str = "") -> Tuple[Optional[str], Dict[str, str]]:
    """为当天输出准备图片文件

    返回：
    - cover_rel: 封面相对路径（相对 day_dir）
    - images_rel: article_url -> image相对路径（相对 day_dir）

    策略：
    - 图片命名格式：栏目名_序号_标题.jpg（清晰明了）
    - 所有图片统一放在 images/ 目录
    """

    day_dir.mkdir(parents=True, exist_ok=True)
    images_dir = day_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 不生成封面
    cover_rel = None

    # 下载文章图片，使用清晰的命名
    images_rel: Dict[str, str] = {}
    for idx, a in enumerate(selected, 1):
        url = a.get("url")
        img_url = a.get("image_url")
        title = a.get("title", "")
        if not url:
            continue

        rel = None
        if img_url:
            ext = guess_ext_from_url(img_url)
            # 清晰的命名：栏目名_序号_标题前20字符
            title_safe = safe_filename(title[:20]) if title else "untitled"
            fname = f"{column_name}_{idx:02d}_{title_safe}{ext}"
            out_path = images_dir / fname
            got = download_image(img_url, out_path)
            if got:
                rel = f"images/{fname}"
                print(f"[INFO] 下载图片: {fname}")

        if rel:
            images_rel[url] = rel

    return cover_rel, images_rel
