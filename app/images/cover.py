from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Windows/Linux 通用：优先 DejaVu / 系统字体，失败则 fallback 默认字体
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_cover(*, out_path: str | Path, title: str, subtitle: str, date_str: str, width: int = 900, height: int = 500) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (width, height), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    # 简单渐变
    for y in range(height):
        r = int(15 + (y / height) * 20)
        g = int(23 + (y / height) * 35)
        b = int(42 + (y / height) * 55)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 文本
    title_font = _load_font(46)
    sub_font = _load_font(26)
    date_font = _load_font(22)

    pad = 48
    max_w = width - pad * 2

    def wrap(text: str, font: ImageFont.ImageFont, max_width: int):
        words = list(text)
        lines = []
        cur = ""
        for ch in words:
            test = cur + ch
            if draw.textlength(test, font=font) <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
        return lines

    title_lines = wrap(title.strip(), title_font, max_w)
    title_lines = title_lines[:2]

    y = 90
    for line in title_lines:
        draw.text((pad, y), line, font=title_font, fill=(255, 255, 255))
        y += 62

    draw.text((pad, y + 10), subtitle, font=sub_font, fill=(180, 205, 255))
    draw.text((pad, height - 70), date_str, font=date_font, fill=(200, 200, 200))

    img.save(out_path)
    return out_path
