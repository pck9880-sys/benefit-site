"""지원금 글마다 요약 카드 이미지(1200x630) 생성: 금액·대상·신청 방법. 글 상단 이미지와 공유 미리보기(og:image)로 사용."""
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from . import config

W, H = 1200, 630
FB = config.ROOT / "assets" / "fonts" / "Pretendard-ExtraBold.otf"
FM = config.ROOT / "assets" / "fonts" / "Pretendard-Bold.otf"
FS = config.ROOT / "assets" / "fonts" / "Pretendard-SemiBold.otf"
_bg = None


def _font(p, s):
    return ImageFont.truetype(str(p), s)


def _background():
    """레퍼런스 톤: 어두운 방, 오른쪽 문틈에서 새어 나오는 빛과 바닥에 번지는 빛."""
    global _bg
    if _bg is None:
        import numpy as np
        yy, xx = np.mgrid[0:H, 0:W].astype("float32")
        base = np.zeros((H, W, 3), "float32")
        base += 5
        # 벽 반사광 (문틈 주변이 아주 은은하게)
        d = np.sqrt(((xx - 1000) / 420) ** 2 + ((yy - 250) / 360) ** 2)
        base += (np.clip(1 - d, 0, 1) ** 2)[..., None] * np.array([22, 30, 52], "float32")
        # 바닥 빛 (문틈 아래에서 왼쪽 아래로 퍼지는 사다리꼴)
        top, bot = 470, H
        t = np.clip((yy - top) / (bot - top), 0, 1)
        left = 980 - t * 620
        right = 1010 + t * 120
        inside = (yy >= top) & (xx >= left) & (xx <= right)
        spread = np.clip(1 - (1010 - xx) / np.maximum(1, 1010 - left), 0, 1)
        floor = inside * (spread ** 1.6) * (1 - t * 0.55)
        fl = Image.fromarray((np.clip(floor, 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(10))
        base += (np.asarray(fl, "float32") / 255)[..., None] * np.array([62, 84, 140], "float32")
        # 문틈 빛줄기: 위 파랑 → 아래 주황
        k = np.clip((yy - 60) / 410, 0, 1)
        col = np.stack([90 + 165 * k, 160 - 70 * k, 255 - 205 * k], -1)
        core = np.exp(-((xx - 1003) / 5.5) ** 2) * ((yy > 60) & (yy < 470))
        halo = np.exp(-((xx - 1003) / 46) ** 2) * np.exp(-(np.clip(np.abs(yy - 265) - 205, 0, None) / 30) ** 2)
        base += core[..., None] * col * 1.0 + halo[..., None] * col * 0.35
        img = Image.fromarray(np.clip(base, 0, 255).astype("uint8"))
        _bg = img.filter(ImageFilter.GaussianBlur(0.6))
    return _bg.copy()


def _wrap(d, text, font, width, lines):
    words, out, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1].rstrip() + "…"
    return out


def make(d, path):
    a, k, src = d["article"], d["key"], d["source"]
    im = _background()
    dr = ImageDraw.Draw(im)
    gray, dim = (138, 140, 150), (88, 90, 100)
    dr.text((72, 66), ((src.get("field") or "지원제도") + "   " + (src.get("org") or ""))[:30], font=_font(FS, 22), fill=dim)
    ft = _font(FB, 44)
    y = 112
    for line in _wrap(dr, a["title"], ft, 780, 2):
        dr.text((72, y), line, font=ft, fill=(232, 232, 236))
        y += 58
    y += 30
    amt = k.get("amount") or "혜택 내용은 본문 확인"
    fa = _font(FB, 96 if len(amt) <= 10 else 66)
    import re as _re
    x = 68
    for part in _re.split(r"([0-9][0-9,.]*)", amt):  # 숫자는 흰색, '최대·월·만 원' 같은 말은 옅게
        if not part:
            continue
        num = bool(_re.match(r"[0-9]", part))
        dr.text((x, y), part, font=fa, fill=(255, 255, 255) if num else (120, 122, 132))
        x += dr.textlength(part, font=fa)
    if k.get("amount_note"):
        dr.text((72, y + (114 if len(amt) <= 10 else 84)), k["amount_note"][:30], font=_font(FS, 24), fill=gray)
    by = 500
    for i, (lab, val) in enumerate((("누가 받나요", k.get("target") or "본문 참고"), ("어떻게 신청하나요", k.get("how") or src.get("contact") or "본문 참고"))):
        x0 = 72 + i * 380
        dr.text((x0, by), lab, font=_font(FM, 19), fill=dim)
        for j, line in enumerate(_wrap(dr, val, _font(FM, 22), 340, 2)):
            dr.text((x0, by + 28 + j * 29), line, font=_font(FM, 22), fill=(205, 206, 214))
    dr.text((72, H - 600), "", font=_font(FS, 10))
    dr.text((W - 72, 66), "BENEFY", font=_font(FB, 20), fill=dim, anchor="ra")
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=86)
