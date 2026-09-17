import os
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parents[2]
FONT_PATH = BASE_DIR / "assets" / "fonts" / "HiraginoSansGB.ttc"
POSTER_DIR = BASE_DIR / "static" / "uploads" / "posters"
POSTER_DIR.mkdir(parents=True, exist_ok=True)

POSTER_W, POSTER_H = 750, 1000

# 设计系统色板
C_PRIMARY = (196, 116, 92)      # #C4745C
C_SECONDARY = (212, 165, 116)   # #D4A574
C_BG_WARM = (250, 246, 241)     # #FAF6F1
C_TEXT_DARK = (45, 32, 22)      # #2D2016
C_TEXT_SUB = (181, 169, 155)    # #B5A99B
C_ACCENT_SOFT = (219, 186, 176) # #DBBAB0
C_WHITE = (255, 255, 255)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except Exception:
        for fallback in [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]:
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:
                continue
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _resize_photo(photo: Image.Image, target_w: int, target_h: int) -> Image.Image:
    ratio_w = target_w / photo.width
    ratio_h = target_h / photo.height
    ratio = max(ratio_w, ratio_h)
    resized = photo.resize((int(photo.width * ratio), int(photo.height * ratio)), Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _vertical_gradient(draw: ImageDraw.ImageDraw, rect: tuple, color_top: tuple, color_bottom: tuple):
    x0, y0, x1, y1 = rect
    for y in range(y0, y1):
        ratio = (y - y0) / max(1, y1 - y0 - 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        draw.line([(x0, y), (x1, y)], fill=(r, g, b))


def _save_poster(img: Image.Image) -> str:
    filename = f"{uuid.uuid4().hex}.jpg"
    path = POSTER_DIR / filename
    img.convert("RGB").save(str(path), "JPEG", quality=90)
    return f"/static/uploads/posters/{filename}"


def generate_warm_letter(photo_path: str, caption: str, date_str: str, sender_name: str) -> str:
    """温暖信笺 — 米色信纸底，照片居中带边框，文字在下"""
    img = Image.new("RGB", (POSTER_W, POSTER_H), C_BG_WARM)
    draw = ImageDraw.Draw(img)

    # 信纸纹理：细横线
    for y in range(0, POSTER_H, 40):
        draw.line([(40, y), (POSTER_W - 40, y)], fill=(*C_ACCENT_SOFT, 60), width=1)

    # 顶部装饰线
    draw.rectangle([(60, 50), (POSTER_W - 60, 54)], fill=C_PRIMARY)

    # 照片区域
    photo = Image.open(photo_path)
    photo_w, photo_h = 630, 440
    photo_resized = _resize_photo(photo, photo_w, photo_h)
    photo_x = (POSTER_W - photo_w) // 2
    photo_y = 90

    # 照片边框
    border = 6
    draw.rectangle(
        [(photo_x - border, photo_y - border),
         (photo_x + photo_w + border, photo_y + photo_h + border)],
        fill=C_WHITE,
    )
    img.paste(photo_resized, (photo_x, photo_y))

    # 文字区域
    font_main = _load_font(30)
    font_small = _load_font(22)
    text_y = photo_y + photo_h + 50
    text_max_w = POSTER_W - 140

    lines = _wrap_text(draw, caption, font_main, text_max_w)
    for line in lines[:5]:
        draw.text((70, text_y), line, fill=C_TEXT_DARK, font=font_main)
        text_y += 48

    # 底部签名区
    sign_y = POSTER_H - 120
    draw.line([(POSTER_W - 300, sign_y), (POSTER_W - 70, sign_y)], fill=C_ACCENT_SOFT, width=1)
    draw.text((POSTER_W - 280, sign_y + 16), f"—— {sender_name}", fill=C_TEXT_SUB, font=font_small)
    draw.text((POSTER_W - 280, sign_y + 48), date_str, fill=C_TEXT_SUB, font=font_small)

    # 底部装饰线
    draw.rectangle([(60, POSTER_H - 50), (POSTER_W - 60, POSTER_H - 46)], fill=C_PRIMARY)

    return _save_poster(img)


def generate_sunset_glow(photo_path: str, caption: str, date_str: str, sender_name: str) -> str:
    """暮光温情 — 暖色渐变头部，照片圆角，底部半透明文字条"""
    img = Image.new("RGB", (POSTER_W, POSTER_H), C_BG_WARM)
    draw = ImageDraw.Draw(img)

    # 顶部暖色渐变
    _vertical_gradient(draw, (0, 0, POSTER_W, 200), C_PRIMARY, C_SECONDARY)

    # 顶部标题
    font_title = _load_font(28)
    draw.text((60, 40), "一份来自远方的牵挂", fill=C_WHITE, font=font_title)
    font_small = _load_font(20)
    draw.text((60, 80), date_str, fill=(*C_BG_WARM, 200), font=font_small)

    # 照片（带圆角效果）
    photo = Image.open(photo_path)
    photo_w, photo_h = 650, 480
    photo_resized = _resize_photo(photo, photo_w, photo_h)
    photo_x = (POSTER_W - photo_w) // 2
    photo_y = 160

    # 圆角蒙版
    mask = Image.new("L", (photo_w, photo_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (photo_w, photo_h)], radius=24, fill=255)

    # 白色底板
    bg_plate = Image.new("RGB", (photo_w + 12, photo_h + 12), C_WHITE)
    img.paste(bg_plate, (photo_x - 6, photo_y - 6))

    photo_rounded = Image.new("RGB", (photo_w, photo_h), C_BG_WARM)
    photo_rounded.paste(photo_resized, (0, 0))
    img.paste(photo_rounded, (photo_x, photo_y), mask)

    # 底部半透明文字条
    text_bar_y = photo_y + photo_h + 40
    overlay = Image.new("RGBA", (POSTER_W, 200), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [(40, 0), (POSTER_W - 40, 180)], radius=20,
        fill=(45, 32, 22, 30),
    )
    img.paste(Image.alpha_composite(
        Image.new("RGBA", (POSTER_W, 200), (*C_BG_WARM, 255)),
        overlay,
    ).convert("RGB"), (0, text_bar_y))

    # 文字
    font_main = _load_font(28)
    text_max_w = POSTER_W - 140
    lines = _wrap_text(draw, caption, font_main, text_max_w)
    ty = text_bar_y + 24
    for line in lines[:4]:
        draw.text((70, ty), line, fill=C_TEXT_DARK, font=font_main)
        ty += 44

    # 署名
    font_sign = _load_font(22)
    draw.text((POSTER_W - 260, POSTER_H - 80), f"—— {sender_name}", fill=C_TEXT_SUB, font=font_sign)

    return _save_poster(img)


def generate_garden_frame(photo_path: str, caption: str, date_str: str, sender_name: str) -> str:
    """花园相框 — 暖底+角落装饰圆点，白色内框，照片+胶囊文字"""
    img = Image.new("RGB", (POSTER_W, POSTER_H), C_BG_WARM)
    draw = ImageDraw.Draw(img)

    # 四角装饰圆点
    dot_r = 18
    dots = [
        (50, 50), (POSTER_W - 50, 50),
        (50, POSTER_H - 50), (POSTER_W - 50, POSTER_H - 50),
        (110, 50), (50, 110), (POSTER_W - 110, 50), (POSTER_W - 50, 110),
        (50, POSTER_H - 110), (110, POSTER_H - 50),
        (POSTER_W - 50, POSTER_H - 110), (POSTER_W - 110, POSTER_H - 50),
    ]
    for cx, cy in dots:
        draw.ellipse([(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)], fill=C_ACCENT_SOFT)

    # 白色内框
    inner_margin = 36
    draw.rounded_rectangle(
        [(inner_margin, inner_margin),
         (POSTER_W - inner_margin, POSTER_H - inner_margin)],
        radius=20, fill=C_WHITE,
    )

    # 照片
    photo = Image.open(photo_path)
    photo_w, photo_h = 580, 460
    photo_resized = _resize_photo(photo, photo_w, photo_h)
    photo_x = (POSTER_W - photo_w) // 2
    photo_y = 100

    # 照片圆角蒙版
    mask = Image.new("L", (photo_w, photo_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (photo_w, photo_h)], radius=16, fill=255)
    photo_rounded = Image.new("RGB", (photo_w, photo_h), C_WHITE)
    photo_rounded.paste(photo_resized, (0, 0))
    img.paste(photo_rounded, (photo_x, photo_y), mask)

    # 胶囊形文字区
    capsule_y = photo_y + photo_h + 40
    capsule_h = 200
    draw.rounded_rectangle(
        [(70, capsule_y), (POSTER_W - 70, capsule_y + capsule_h)],
        radius=capsule_h // 2, fill=C_BG_WARM,
    )

    # 文字
    font_main = _load_font(26)
    text_max_w = POSTER_W - 200
    lines = _wrap_text(draw, caption, font_main, text_max_w)
    ty = capsule_y + 30
    for line in lines[:4]:
        bbox = draw.textbbox((0, 0), line, font=font_main)
        tw = bbox[2] - bbox[0]
        draw.text(((POSTER_W - tw) // 2, ty), line, fill=C_TEXT_DARK, font=font_main)
        ty += 40

    # 底部信息
    font_small = _load_font(20)
    info_text = f"{sender_name} · {date_str}"
    bbox = draw.textbbox((0, 0), info_text, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((POSTER_W - tw) // 2, POSTER_H - 90), info_text, fill=C_TEXT_SUB, font=font_small)

    return _save_poster(img)


def generate_simple_elegant(photo_path: str, caption: str, date_str: str, sender_name: str) -> str:
    """素雅留白 — 纯白底大留白，左侧竖线装饰，文字左对齐"""
    img = Image.new("RGB", (POSTER_W, POSTER_H), C_WHITE)
    draw = ImageDraw.Draw(img)

    # 左侧装饰竖线
    draw.rectangle([(50, 60), (54, POSTER_H - 60)], fill=C_PRIMARY)

    # 照片
    photo = Image.open(photo_path)
    photo_w, photo_h = 600, 440
    photo_resized = _resize_photo(photo, photo_w, photo_h)
    photo_x = 80
    photo_y = 80
    img.paste(photo_resized, (photo_x, photo_y))

    # 细分隔线
    sep_y = photo_y + photo_h + 30
    draw.line([(80, sep_y), (300, sep_y)], fill=C_ACCENT_SOFT, width=2)

    # 文字
    font_main = _load_font(28)
    font_small = _load_font(20)
    text_max_w = POSTER_W - 160
    lines = _wrap_text(draw, caption, font_main, text_max_w)
    ty = sep_y + 30
    for line in lines[:5]:
        draw.text((80, ty), line, fill=C_TEXT_DARK, font=font_main)
        ty += 46

    # 签名
    draw.text((80, POSTER_H - 110), sender_name, fill=C_PRIMARY, font=font_main)
    draw.text((80, POSTER_H - 70), date_str, fill=C_TEXT_SUB, font=font_small)

    return _save_poster(img)


TEMPLATE_REGISTRY = {
    "warm_letter": {"fn": generate_warm_letter, "label": "温暖信笺", "desc": "米色信纸风格，适合文字较多、情感深的内容"},
    "sunset_glow": {"fn": generate_sunset_glow, "label": "暮光温情", "desc": "暖色渐变，适合风景、户外照片"},
    "garden_frame": {"fn": generate_garden_frame, "label": "花园相框", "desc": "温暖花园风格，适合食物、小物件"},
    "simple_elegant": {"fn": generate_simple_elegant, "label": "素雅留白", "desc": "纯白极简风格，适合人物照片"},
}


def generate_all_posters(photo_path: str, caption: str, date_str: str, sender_name: str) -> list[dict]:
    results = []
    for key, tmpl in TEMPLATE_REGISTRY.items():
        poster_url = tmpl["fn"](photo_path, caption, date_str, sender_name)
        results.append({
            "template_name": key,
            "poster_url": poster_url,
            "label": tmpl["label"],
            "desc": tmpl["desc"],
        })
    return results


def generate_single_poster(template_name: str, photo_path: str, caption: str, date_str: str, sender_name: str) -> str:
    tmpl = TEMPLATE_REGISTRY.get(template_name)
    if not tmpl:
        raise ValueError(f"未知模板: {template_name}")
    return tmpl["fn"](photo_path, caption, date_str, sender_name)
