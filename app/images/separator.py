from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int):
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


def generate_separator(*, out_path: str | Path, text: str, width: int = 900, height: int = 160) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (width, height), (250, 250, 250))
    draw = ImageDraw.Draw(img)

    # 线条
    y = height // 2
    draw.line([(60, y), (width - 60, y)], fill=(210, 210, 210), width=2)

    # 文本块
    font = _load_font(28)
    padding = 18
    text_w = draw.textlength(text, font=font)
    box_w = int(text_w + padding * 2)
    box_h = 54
    x0 = (width - box_w) // 2
    y0 = y - box_h // 2

    draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=14, fill=(255, 255, 255), outline=(220, 220, 220), width=2)
    draw.text((x0 + padding, y0 + 12), text, font=font, fill=(40, 40, 40))

    img.save(out_path)
    return out_path
