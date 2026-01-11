from __future__ import annotations

import html
import re
from datetime import date
from typing import Any, Dict, List, Optional


def _esc(s: str) -> str:
    return html.escape(s or "")


import re

def _strip_conclusion_prefix(s: str) -> str:
    # 移除“**结论/影响：**”或“**结论/影响:**”等前缀
    return re.sub(r"\*\*结论/影响[:：]\*\*\s*", "", s)

def _inline(s: str) -> str:
    s = _strip_conclusion_prefix(_esc(s))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code style=\"background:#f5f5f5;padding:2px 4px;border-radius:3px;\">\1</code>", s)
    return s


def _render_paragraphs(lines: List[str]) -> List[str]:
    """渲染段落，统一使用有序列表（数字编号）"""
    out: List[str] = []
    in_ol = False  # 有序列表状态
    
    for raw in lines:
        line = raw.rstrip()
        # 空行：如果当前在有序列表中，则忽略空行继续列表；否则跳过
        if not line.strip():
            if in_ol:
                # 在列表中，保持 <ol> 打开，直接跳过空行
                continue
            continue

        if line.startswith("# "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(
                f"<h1 style=\"font-size:24px;line-height:1.4;margin:18px 0 10px;\">{_inline(line[2:])}</h1>"
            )
        elif line.startswith("## "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(
                f"<h2 style=\"font-size:18px;line-height:1.5;margin:16px 0 10px;\">{_inline(line[3:])}</h2>"
            )
        elif line.startswith("> "):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(
                f"<blockquote style=\"margin:12px 0;padding:10px 12px;border-left:4px solid #ddd;background:#fafafa;color:#444;\">{_inline(line[2:])}</blockquote>"
            )
        elif re.match(r"^\d+\.\s+", line):  # 列表编号行
            # 处理数字编号（1. 2. 3. ...）- 优先匹配
            if not in_ol:
                out.append("<ol style=\"padding-left:22px;margin:10px 0;\">")
                in_ol = True
            # 移除数字编号，保留内容（浏览器会自动编号）
            content = re.sub(r"^\d+\.\s+", "", line)
            out.append(
                f"<li style=\"margin:6px 0;font-size:15px;line-height:1.75;color:#222;\">{_inline(content)}</li>"
            )
        elif line.startswith("- "):
            # 兼容旧格式：- 开头也转为有序列表
            if not in_ol:
                out.append("<ol style=\"padding-left:22px;margin:10px 0;\">")
                in_ol = True
            out.append(
                f"<li style=\"margin:6px 0;font-size:15px;line-height:1.75;color:#222;\">{_inline(line[2:])}</li>"
            )
        else:
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(
                f"<p style=\"margin:10px 0;font-size:15px;line-height:1.75;color:#222;\">{_inline(line)}</p>"
            )

    if in_ol:
        out.append("</ol>")
    return out


def _pick_column_images(items: List[Dict[str, Any]], images_rel: Dict[str, str], max_images: int = 2) -> List[str]:
    picked: List[str] = []
    for a in items:
        if len(picked) >= max_images:
            break
        url = a.get("url")
        if not url:
            continue
        img = images_rel.get(url)
        if img and img not in picked:
            picked.append(img)
    return picked


def render_wechat_html(
    *,
    columns_data: List[Dict[str, Any]],
    source_urls: List[str],
    run_date: date,
) -> str:
    """渲染最终公众号 HTML（单页三栏目）。

    columns_data: [{draft, items, cover_rel, images_rel}, ...]
    - 每个栏目渲染：栏目标题 +（可选）1-2张栏目配图 + Markdown正文
    - 文末输出所有来源 URL
    """

    out: List[str] = []

    # 顶部封面：取第一个栏目生成的封面（如果有）
    top_cover = None
    for c in columns_data:
        cover_rel = c.get("cover_rel")
        if cover_rel:
            top_cover = cover_rel
            break

    if top_cover:
        out.append(
            f"<p style=\"margin:0 0 14px;\"><img src=\"{_esc(top_cover)}\" style=\"width:100%;border-radius:10px;\"/></p>"
        )

    out.append(
        f"<p style=\"margin:6px 0 14px;font-size:13px;line-height:1.6;color:#666;\">日期：{_esc(run_date.isoformat())}</p>"
    )

    for idx, col in enumerate(columns_data, 1):
        draft: Dict[str, Any] = col.get("draft") or {}
        items: List[Dict[str, Any]] = col.get("items") or []
        images_rel: Dict[str, str] = col.get("images_rel") or {}

        col_name = draft.get("name") or f"栏目{idx}"
        md = draft.get("markdown") or ""

        out.append("<hr style=\"border:none;border-top:1px solid #eee;margin:18px 0;\"/>")
        out.append(
            f"<h2 style=\"font-size:20px;line-height:1.5;margin:14px 0 10px;\">{_esc(col_name)}</h2>"
        )

        # 每栏 1-2 张图
        picked_imgs = _pick_column_images(items, images_rel, max_images=2)
        for img_rel in picked_imgs:
            out.append(
                f"<p style=\"margin:8px 0 14px;\"><img src=\"{_esc(img_rel)}\" style=\"width:100%;border-radius:8px;\"/></p>"
            )

        out.extend(_render_paragraphs(md.splitlines()))

    # 信息来源：列出 URL
    if source_urls:
        out.append("<hr style=\"border:none;border-top:1px solid #eee;margin:18px 0;\"/>")
        out.append(
            "<h2 style=\"font-size:18px;line-height:1.5;margin:16px 0 10px;\">信息来源</h2>"
        )
        out.append("<ol style=\"padding-left:22px;margin:10px 0;\">")
        for u in sorted(set(source_urls)):
            out.append(
                f"<li style=\"margin:6px 0;font-size:13px;line-height:1.6;color:#333;\">{_esc(u)}</li>"
            )
        out.append("</ol>")

    body = "\n".join(out)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"></head>"
        "<body style=\"font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,PingFang SC,Hiragino Sans GB,Microsoft YaHei,sans-serif;\">"
        f"{body}"
        "</body></html>"
    )
