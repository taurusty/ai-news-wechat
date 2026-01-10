from __future__ import annotations

from typing import Dict, Any

from app.render.wechat_html import render_wechat_html


def render_final_html(draft: Dict[str, Any], *, cover_rel: str | None = None, items: list[dict] | None = None, images_rel: dict[str, str] | None = None) -> str:
    """渲染最终公众号HTML。

    为了保持主流程稳定，simple_html 作为对外入口，内部转向更完整的 wechat_html 渲染。
    """
    return render_wechat_html(
        draft=draft,
        cover_rel=cover_rel,
        items=items or [],
        images_rel=images_rel or {},
    )
