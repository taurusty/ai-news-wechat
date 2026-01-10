from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional


def _esc(s: str) -> str:
    return html.escape(s or "")


def _inline(s: str) -> str:
    s = _esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code style=\"background:#f5f5f5;padding:2px 4px;border-radius:3px;\">\1</code>", s)
    return s


def _split_daily_sections(md: str) -> List[Dict[str, Any]]:
    """把“干货总结”Markdown粗分成：开篇 / 要闻(列表) / 结语。

    目标：给“要闻每条”插图提供锚点。

    规则：
    - 开篇：从开始到第一个列表项（- 开头）之前的段落
    - 要闻：连续的 `- ` 列表项（每条视为一条新闻）
    - 结语：列表结束后的段落

    注意：这不是严格Markdown解析，只做稳定的工程化近似。
    """

    lines = (md or "").splitlines()
    pre: List[str] = []
    items: List[str] = []
    post: List[str] = []

    state = "pre"
    for raw in lines:
        line = raw.rstrip()
        if state == "pre":
            if line.lstrip().startswith("- "):
                state = "items"
                items.append(line.lstrip()[2:].strip())
            else:
                pre.append(line)
        elif state == "items":
            if line.lstrip().startswith("- "):
                items.append(line.lstrip()[2:].strip())
            else:
                state = "post"
                post.append(line)
        else:
            post.append(line)

    return [
        {"type": "pre", "lines": pre},
        {"type": "items", "items": items},
        {"type": "post", "lines": post},
    ]


def _render_paragraphs(lines: List[str]) -> List[str]:
    out: List[str] = []
    in_ul = False
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            continue

        if line.startswith("# "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h1 style=\"font-size:24px;line-height:1.4;margin:18px 0 10px;\">{_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<h2 style=\"font-size:18px;line-height:1.5;margin:16px 0 10px;\">{_inline(line[3:])}</h2>")
        elif line.startswith("> "):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(
                f"<blockquote style=\"margin:12px 0;padding:10px 12px;border-left:4px solid #ddd;background:#fafafa;color:#444;\">{_inline(line[2:])}</blockquote>"
            )
        elif line.startswith("- "):
            if not in_ul:
                out.append("<ul style=\"padding-left:22px;margin:10px 0;\">")
                in_ul = True
            out.append(f"<li style=\"margin:6px 0;font-size:15px;line-height:1.75;color:#222;\">{_inline(line[2:])}</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(f"<p style=\"margin:10px 0;font-size:15px;line-height:1.75;color:#222;\">{_inline(line)}</p>")

    if in_ul:
        out.append("</ul>")
    return out


def render_wechat_html(*, draft: Dict[str, Any], cover_rel: Optional[str], items: List[Dict[str, Any]], images_rel: Dict[str, str]) -> str:
    """公众号友好 HTML 渲染

    新需求：
    - “今日资讯来源”仅作为参考文献：不配图，只列出处
    - 正文部分：干货总结中“每条要闻”后插入配图（优先原图，否则占位图）

    注意：深度解读目前不强制逐段插图（可以后续再加）；但仍会生成封面。
    """

    md = draft.get("markdown", "")
    out: List[str] = []

    # 封面
    if cover_rel:
        out.append(
            f"<p style=\"margin:0 0 14px;\"><img src=\"{_esc(cover_rel)}\" style=\"width:100%;border-radius:10px;\"/></p>"
        )

    draft_type = draft.get("type")
    if draft_type == "daily_summary":
        sections = _split_daily_sections(md)
        for sec in sections:
            if sec["type"] == "pre":
                out.extend(_render_paragraphs(sec["lines"]))
            elif sec["type"] == "items":
                # 用“每条要闻后跟图”的形式渲染（不使用<ul>，避免出现黑点）
                items_text: List[str] = sec.get("items", [])
                out.append("<div style=\"margin:10px 0;\">")
                for idx, text in enumerate(items_text, 1):
                    out.append(
                        f"<p style=\"margin:10px 0 6px;font-size:15px;line-height:1.75;color:#222;\"><strong>{idx}.</strong> {_inline(text)}</p>"
                    )
                    # 为第 idx 条选入新闻插图（与 selected 顺序对齐）
                    if idx <= len(items):
                        url = items[idx - 1].get("url")
                        img_rel = images_rel.get(url)
                        if img_rel:
                            out.append(
                                f"<p style=\"margin:8px 0 14px;\"><img src=\"{_esc(img_rel)}\" style=\"width:100%;border-radius:8px;\"/></p>"
                            )
                out.append("</div>")
            else:
                # post 部分不要让“- ”再变成<ul>，统一当成普通段落
                post_lines = []
                for ln in sec.get("lines", []):
                    if isinstance(ln, str) and ln.lstrip().startswith("- "):
                        post_lines.append(ln.lstrip()[2:])
                    else:
                        post_lines.append(ln)
                out.extend(_render_paragraphs(post_lines))
    else:
        # 深度解读：保持现有Markdown渲染（不逐条插图），避免错误插入
        out.extend(_render_paragraphs(md.splitlines()))

    # 参考文献区：不配图
    if items:
        out.append("<hr style=\"border:none;border-top:1px solid #eee;margin:18px 0;\"/>")
        out.append("<h2 style=\"font-size:18px;line-height:1.5;margin:16px 0 10px;\">今日资讯来源</h2>")
        out.append("<ol style=\"padding-left:22px;margin:10px 0;\">")
        for a in items:
            title = a.get("title", "")
            out.append(
                f"<li style=\"margin:6px 0;font-size:13px;line-height:1.6;color:#333;\">{_esc(title)}</li>"
            )
        out.append("</ol>")

    body = "\n".join(out)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"></head>"
        "<body style=\"font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,PingFang SC,Hiragino Sans GB,Microsoft YaHei,sans-serif;\">"
        f"{body}"
        "</body></html>"
    )
