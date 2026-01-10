from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional


def export_xiumi_package(*, day_dir: Path, draft: Dict[str, Any], selected: List[Dict[str, Any]], cover_rel: Optional[str], images_rel: Dict[str, str]) -> None:
    """导出秀米友好包：

    - xiumi.html：正文用【封面图】【配图N】占位符
    - xiumi_images/：00_cover + 01-10 配图
    - xiumi_manifest.json/txt：编号到新闻的映射（含标题/来源/链接/文件名）
    """

    from app.render.xiumi_html import render_xiumi_html

    day_dir = Path(day_dir)
    xdir = day_dir / "xiumi"
    img_dir = xdir / "xiumi_images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # 1) 写 xiumi.html
    xhtml = render_xiumi_html(draft=draft, items=selected)
    (xdir / "xiumi.html").write_text(xhtml, encoding="utf-8")

    # 2) 复制封面
    manifest: List[Dict[str, Any]] = []
    if cover_rel:
        src = day_dir / cover_rel
        if src.exists():
            dst = img_dir / "00_cover.png"
            shutil.copyfile(src, dst)
            manifest.append({
                "slot": "cover",
                "placeholder": "【封面图】",
                "file": str(Path("xiumi_images") / dst.name),
            })

    # 3) 复制配图（按 selected 顺序）
    for idx, a in enumerate(selected, 1):
        url = a.get("url", "")
        img_rel = images_rel.get(url)
        if not img_rel:
            continue
        src = day_dir / img_rel
        if not src.exists():
            continue

        ext = src.suffix.lower() or ".jpg"
        dst_name = f"{idx:02d}{ext}"
        dst = img_dir / dst_name
        try:
            shutil.copyfile(src, dst)
        except Exception:
            continue

        manifest.append({
            "slot": idx,
            "placeholder": f"【配图{idx}】",
            "file": str(Path("xiumi_images") / dst.name),
            "title": a.get("title", ""),
            "source": a.get("source_name", a.get("source", "")),
            "url": url,
        })

    (xdir / "xiumi_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 可读版 txt
    lines: List[str] = []
    for m in manifest:
        if m.get("slot") == "cover":
            lines.append(f"{m['placeholder']} -> {m['file']}")
        else:
            lines.append(f"{m['placeholder']} -> {m['file']} | {m.get('title','')} | {m.get('source','')} | {m.get('url','')}")
    (xdir / "xiumi_manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
