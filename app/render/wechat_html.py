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
    """渲染段落，统一使用有序列表（数字编号）
    
    注意：不渲染 # 和 ## 标题，只保留栏目标题（每日资讯、科创头条、学术动态）
    """
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

        # 跳过 markdown 中的标题（# 和 ##），只保留栏目标题
        if line.startswith("# ") or line.startswith("## "):
            # 不渲染，直接跳过
            continue
        if line.startswith("> "):
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


def render_wechat_html(
    *,
    columns_data: List[Dict[str, Any]],
    source_urls: List[str],
    run_date: date,
) -> str:
    """渲染最终公众号 HTML（单页三栏目）。

    columns_data: [{draft, items, cover_rel, images_rel}, ...]
    - 每个栏目渲染：栏目标题 + Markdown正文
    - 不包含图片（图片单独保存，用户手动上传到微信）
    - 文末按栏目顺序输出文献来源（标题+超链接）
    """

    out: List[str] = []

    # 不再包含封面图片

    out.append(
        f"<p style=\"margin:6px 0 14px;font-size:13px;line-height:1.6;color:#666;\">日期：{_esc(run_date.isoformat())}</p>"
    )

    for idx, col in enumerate(columns_data, 1):
        draft: Dict[str, Any] = col.get("draft") or {}
        items: List[Dict[str, Any]] = col.get("items") or []

        col_name = draft.get("name") or f"栏目{idx}"
        md = draft.get("markdown") or ""

        out.append("<hr style=\"border:none;border-top:1px solid #eee;margin:18px 0;\"/>")
        out.append(
            f"<h2 style=\"font-size:20px;line-height:1.5;margin:14px 0 10px;\">{_esc(col_name)}</h2>"
        )

        # 不再包含图片

        out.extend(_render_paragraphs(md.splitlines()))

    # 信息来源：按栏目顺序，显示标题+超链接
    out.append("<hr style=\"border:none;border-top:1px solid #eee;margin:18px 0;\"/>")
    out.append(
        "<h2 style=\"font-size:18px;line-height:1.5;margin:16px 0 10px;\">信息来源</h2>"
    )
    
    # 按栏目顺序输出文献来源
    for col in columns_data:
        col_name = col.get("draft", {}).get("name") or ""
        items = col.get("items") or []
        
        if not items:
            continue
        
        # 栏目小标题
        out.append(
            f"<h3 style=\"font-size:16px;line-height:1.5;margin:14px 0 8px;font-weight:bold;\">{_esc(col_name)}</h3>"
        )
        out.append("<ol style=\"padding-left:22px;margin:10px 0;\">")
        
        for item in items:
            title = item.get("title", "无标题")
            url = item.get("url", "")
            if url:
                # 超链接格式：标题是可点击的链接
                out.append(
                    f"<li style=\"margin:6px 0;font-size:13px;line-height:1.6;color:#333;\">"
                    f"<a href=\"{_esc(url)}\" target=\"_blank\" style=\"color:#0066cc;text-decoration:none;\">{_esc(title)}</a>"
                    f"</li>"
                )
        
        out.append("</ol>")

    body = "\n".join(out)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"></head>"
        "<body style=\"font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,PingFang SC,Hiragino Sans GB,Microsoft YaHei,sans-serif;\">"
        f"{body}"
        "</body></html>"
    )
