"""지원금 글마다 요약 카드 이미지(1200x630) 생성: 금액·대상·신청 방법. 글 상단 이미지와 공유 미리보기(og:image)로 사용."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config

W, H = 1200, 630
FB = config.ROOT / "assets" / "fonts" / "Pretendard-ExtraBold.otf"
FM = config.ROOT / "assets" / "fonts" / "Pretendard-Bold.otf"
FS = config.ROOT / "assets" / "fonts" / "Pretendard-SemiBold.otf"
_bg = None


def _font(p, s):
    return ImageFont.truetype(str(p), s)


def _background():
    global _bg
    if _bg is None:
        im = Image.new("RGB", (W, H), (8, 5, 28))
        g = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(g)
        d.ellipse((-200, -260, 560, 420), fill=(74, 43, 216))
        d.ellipse((820, -220, 1420, 300), fill=(150, 40, 110))
        d.ellipse((700, 420, 1300, 900), fill=(40, 60, 150))
        _bg = Image.blend(im, g.filter(ImageFilter.GaussianBlur(140)), 0.75)
    return _bg.copy()


def _wrap(d, text, font, width, lines):
    out, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) > width:
            out.append(cur)
            cur = ch.lstrip()
            if len(out) == lines:
                break
        else:
            cur += ch
    if len(out) < lines and cur:
        out.append(cur)
    if len(out) == lines and "".join(out) != text.replace("\n", ""):
        out[-1] = out[-1][:-1].rstrip() + "…"
    return out


def make(d, path):
    a, k, src = d["article"], d["key"], d["source"]
    im = _background()
    dr = ImageDraw.Draw(im)
    # 머리: 분야 칩 + 기관
    chip = (src.get("field") or "지원제도")[:10]
    f = _font(FM, 26)
    w = dr.textlength(chip, font=f)
    dr.rounded_rectangle((64, 56, 64 + w + 40, 100), 22, fill=(107, 76, 245))
    dr.text((84, 62), chip, font=f, fill="white")
    dr.text((64 + w + 60, 64), (src.get("org") or "")[:24], font=_font(FS, 24), fill=(201, 192, 245))
    # 제목
    ft = _font(FB, 50)
    y = 130
    for line in _wrap(dr, a["title"], ft, W - 128, 2):
        dr.text((64, y), line, font=ft, fill="white")
        y += 64
    # 금액
    y += 18
    amt = k.get("amount") or "혜택 내용은 본문 확인"
    fa = _font(FB, 78 if len(amt) <= 12 else 58)
    gl = Image.new("L", (W, H), 0)
    ImageDraw.Draw(gl).text((64, y), amt, font=fa, fill=255)
    grad = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(grad)
    for x in range(W):
        t = x / W
        c = (int(191 + (255 - 191) * t), int(230 - 52 * t), int(255 - 28 * t))
        gd.line([(x, 0), (x, H)], fill=c)
    im.paste(grad, (0, 0), gl)
    if k.get("amount_note"):
        dr.text((64, y + (92 if len(amt) <= 12 else 72)), k["amount_note"][:34], font=_font(FS, 26), fill=(255, 179, 217))
    # 하단 두 칸: 대상 / 신청
    by = 470
    for i, (lab, val) in enumerate((("누가", k.get("target") or "본문 참고"), ("신청", k.get("how") or src.get("contact") or "본문 참고"))):
        x0 = 64 + i * 544
        dr.rounded_rectangle((x0, by, x0 + 528, by + 112), 22, fill=(24, 15, 66), outline=(80, 62, 160), width=2)
        dr.text((x0 + 24, by + 16), lab, font=_font(FM, 22), fill=(143, 211, 255))
        fv = _font(FM, 26)
        for j, line in enumerate(_wrap(dr, val, fv, 480, 2)):
            dr.text((x0 + 24, by + 46 + j * 32), line, font=fv, fill="white")
    dr.text((W - 64, 70), "benefy.kr", font=_font(FB, 26), fill=(201, 192, 245), anchor="ra")
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=82)
