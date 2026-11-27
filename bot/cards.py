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
    """검은 공간 + 오른쪽에서 새어 나오는 빛줄기 하나 (파랑→주황)."""
    global _bg
    if _bg is None:
        im = Image.new("RGB", (W, H), (6, 6, 8))
        # 바닥에 번지는 빛
        floor = Image.new("RGB", (W, H), (0, 0, 0))
        fd = ImageDraw.Draw(floor)
        fd.polygon([(1010, 300), (1060, 300), (1200, 630), (760, 630)], fill=(40, 62, 110))
        im = Image.blend(im, floor.filter(ImageFilter.GaussianBlur(60)), 0.55)
        # 빛줄기 (세로 그라데이션)
        beam = Image.new("RGB", (W, H), (0, 0, 0))
        bd = ImageDraw.Draw(beam)
        for y in range(40, 330):
            t = (y - 40) / 290
            c = (int(90 + 165 * t), int(150 - 60 * t), int(255 - 200 * t))
            bd.line([(1026, y), (1038, y)], fill=c)
        glow = Image.blend(beam.filter(ImageFilter.GaussianBlur(14)), beam.filter(ImageFilter.GaussianBlur(70)), 0.5)
        glow = Image.eval(glow, lambda v: min(255, v * 3))
        im = Image.composite(beam, im, beam.convert("L").point(lambda v: 255 if v > 10 else 0))
        im = Image.blend(im, Image.eval(Image.merge("RGB", [ImageChops.add(a, b) for a, b in zip(im.split(), glow.split())]), lambda v: v), 0.6)
        _bg = im
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
    gray, dim = (150, 150, 158), (96, 96, 104)
    dr.text((64, 60), ((src.get("field") or "지원제도") + "  ·  " + (src.get("org") or ""))[:34], font=_font(FS, 24), fill=gray)
    ft = _font(FB, 48)
    y = 112
    for line in _wrap(dr, a["title"], ft, 860, 2):
        dr.text((64, y), line, font=ft, fill=(236, 236, 240))
        y += 62
    y += 26
    amt = k.get("amount") or "혜택 내용은 본문 확인"
    dr.text((64, y), amt, font=_font(FB, 84 if len(amt) <= 11 else 60), fill="white")
    if k.get("amount_note"):
        dr.text((66, y + (100 if len(amt) <= 11 else 76)), k["amount_note"][:34], font=_font(FS, 25), fill=gray)
    by = 486
    dr.line([(64, by - 18), (880, by - 18)], fill=(40, 40, 46), width=2)
    for i, (lab, val) in enumerate((("누가", k.get("target") or "본문 참고"), ("신청", k.get("how") or src.get("contact") or "본문 참고"))):
        x0 = 64 + i * 420
        dr.text((x0, by), lab, font=_font(FM, 21), fill=dim)
        for j, line in enumerate(_wrap(dr, val, _font(FM, 24), 380, 2)):
            dr.text((x0, by + 32 + j * 31), line, font=_font(FM, 24), fill=(214, 214, 220))
    dr.text((64, 22), "", font=_font(FS, 10))
    dr.text((W - 64, H - 46), "benefy.kr", font=_font(FB, 22), fill=dim, anchor="ra")
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=84)
