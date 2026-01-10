from __future__ import annotations

import html
import re
from typing import Any, Dict, List


def _esc(s: str) -> str:
    return html.escape(s or "")


def _inline(s: str) -> str:
    s = _esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code style=\"background:#f5f5f5;padding:2px 4px;border-radius:3px;\">\1</code>", s)
    return s


def _split_daily_items(md: str) -> tuple[list[str], list[str], list[str]]:
    """把Markdown拆成 pre / items / post。

    items：连续的 "- " 列表项内容（去掉前缀）
    """
    lines = (md or "").splitlines()
    pre: list[str] = []
    items: list[str] = []
    post: list[str] = []

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

    return pre, items, post


def render_xiumi_html(*, draft: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """生成更适合秀米的HTML：

    - 不输出<img>，改用占位符：
      - 【封面图】
      - 【配图1】...【配图10】
    - 文末“今日资讯来源”仅文本引用

    说明：
    - 正文要点顺序与 items 顺序对应。
    """

    md = draft.get("markdown", "")
    out: List[str] = []

    # 封面占位符
    out.append("<p><strong>【封面图】</strong></p>")

    draft_type = draft.get("type")
    if draft_type == "daily_summary":
        pre, md_items, post = _split_daily_items(md)

        def render_lines(lines: list[str]):
            for raw in lines:
                line = raw.rstrip()
                if not line.strip():
                    continue
                if line.startswith("# "):
                    out.append(f"<h1>{_inline(line[2:])}</h1>")
                elif line.startswith("## "):
                    out.append(f"<h2>{_inline(line[3:])}</h2>")
                elif line.startswith("> "):
                    out.append(f"<blockquote>{_inline(line[2:])}</blockquote>")
                else:
                    # 避免残留 "- " 被渲染成黑点
                    if line.lstrip().startswith("- "):
                        line = line.lstrip()[2:]
                    out.append(f"<p>{_inline(line)}</p>")

        render_lines(pre)

        # 今日要点：编号 + 配图占位符
        out.append("<p><strong>今日要点</strong></p>")

        if not md_items:
            # 兜底：模型没按 '- ' 输出列表时，避免出现只有 1 条编号
            md_items = []

        for idx, text in enumerate(md_items, 1):
            out.append(f"<p><strong>{idx}.</strong> {_inline(text)}</p>")
            out.append(f"<p><strong>【配图{idx}】</strong></p>")

        # post 里如果还有以“- ”开头的行，按续号继续编号
        next_idx = len(md_items) + 1
        for raw in post:
            line = raw.rstrip()
            if not line.strip():
                continue
            if line.lstrip().startswith("- "):
                text = line.lstrip()[2:].strip()
                out.append(f"<p><strong>{next_idx}.</strong> {_inline(text)}</p>")
                out.append(f"<p><strong>【配图{next_idx}】</strong></p>")
                next_idx += 1
            else:
                out.append(f"<p>{_inline(line)}</p>")

    else:
        # 深度解读：不做结构假设，只把段落输出，封面后你可自行插图
        for raw in md.splitlines():
            line = raw.rstrip()
            if not line.strip():
                continue
            if line.startswith("# "):
                out.append(f"<h1>{_inline(line[2:])}</h1>")
            elif line.startswith("## "):
                out.append(f"<h2>{_inline(line[3:])}</h2>")
            elif line.startswith("> "):
                out.append(f"<blockquote>{_inline(line[2:])}</blockquote>")
            else:
                if line.lstrip().startswith("- "):
                    line = line.lstrip()[2:]
                out.append(f"<p>{_inline(line)}</p>")

    # 参考文献
    if items:
        out.append("<hr/>")
        out.append("<h2>今日资讯来源</h2>")
        out.append("<ol>")
        for a in items:
            title = a.get("title", "")
            out.append(f"<li>{_esc(title)}</li>")
        out.append("</ol>")

    body = "\n".join(out)
    return f"<!doctype html><html><head><meta charset=\"utf-8\"></head><body>{body}</body></html>"
