"""카드뉴스 이미지 생성 (Benefy 톤: 다크 + 바이올렛, 큰 숫자 하나, 카드당 메시지 하나).

cards = [{"kind": "cover"|"item"|"end", ...}] → out_dir/1.webp, 2.webp ... (1080x1350, 4:5)
"""
import html
import os
from pathlib import Path

from . import config

FONTS = config.ROOT / "assets" / "fonts"
MARK = (config.ROOT / "assets" / "mark_glow.svg").read_text() if (config.ROOT / "assets" / "mark_glow.svg").exists() else ""
e = html.escape


def _css():
    f = lambda n: (FONTS / n).as_uri()
    return f"""
@font-face{{font-family:P;src:url({f('Pretendard-Medium.otf')});font-weight:500}}
@font-face{{font-family:P;src:url({f('Pretendard-SemiBold.otf')});font-weight:600}}
@font-face{{font-family:P;src:url({f('Pretendard-Bold.otf')});font-weight:700}}
@font-face{{font-family:P;src:url({f('Pretendard-ExtraBold.otf')});font-weight:800}}
@font-face{{font-family:Q;src:url({f('quicksand-700.woff2')})}}
*{{margin:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:#06070b;color:#fff;font-family:P;letter-spacing:-.03em;position:relative;overflow:hidden}}
.glow{{position:absolute;width:760px;height:760px;right:-260px;top:-260px;background:radial-gradient(circle,#5b4cf0 0,rgba(91,76,240,.35) 35%,transparent 68%);opacity:.55}}
.glow.b{{right:auto;top:auto;left:-300px;bottom:-320px;background:radial-gradient(circle,#3b5bff 0,rgba(59,91,255,.25) 35%,transparent 68%);opacity:.45}}
.wrap{{position:absolute;inset:96px 96px 150px}}
.chip{{display:inline-block;font-weight:700;font-size:30px;color:#c9c2ff;border:2px solid rgba(201,194,255,.35);border-radius:999px;padding:8px 24px}}
.num{{font-family:Q;font-size:200px;line-height:.9;color:transparent;-webkit-text-stroke:3px rgba(201,194,255,.55);margin:40px 0 0}}
h1{{font-weight:800;font-size:96px;line-height:1.18;margin-top:56px}}
h1 b{{color:#b8b0ff}}
h2{{font-weight:800;font-size:68px;line-height:1.25;margin-top:30px}}
.sub{{font-weight:500;font-size:36px;color:#a9abc8;margin-top:34px;line-height:1.5}}
.amt{{margin-top:56px}}.amt small{{display:block;font-weight:600;font-size:30px;color:#a9abc8}}
.amt strong{{display:block;font-weight:800;font-size:150px;line-height:1.05;letter-spacing:-.04em;margin-top:6px}}
.amt strong em{{font-style:normal;font-size:64px;color:#b8b0ff;margin-left:8px}}
ul{{list-style:none;margin-top:56px;border-top:2px solid rgba(255,255,255,.12)}}
li{{display:flex;gap:28px;padding:26px 0;border-bottom:2px solid rgba(255,255,255,.12);font-size:34px;line-height:1.45}}
li b{{flex:none;width:150px;color:#a9abc8;font-weight:600}}
li span{{font-weight:600}}
.cta{{margin-top:64px;display:inline-block;background:#fff;color:#06070b;font-weight:800;font-size:40px;border-radius:24px;padding:28px 44px}}
.foot{{position:absolute;left:96px;right:96px;bottom:70px;display:flex;align-items:center;justify-content:space-between;font-size:28px;color:#8a8cab}}
.brand{{display:flex;align-items:center;gap:16px}}.brand svg{{width:54px;height:54px}}
.brand b{{font-family:Q;font-size:40px;color:#fff;letter-spacing:-.01em}}.brand small{{font-size:24px;margin-left:6px}}
.pg{{font-family:Q;font-size:30px}}.swipe{{color:#c9c2ff;font-weight:700}}
.hero-mark{{position:absolute;right:-30px;bottom:-40px;width:440px;height:440px}}.hero-mark svg{{width:100%;height:100%}}
.ico{{position:absolute;right:96px;top:150px;width:220px;height:220px;color:#8b7dff;opacity:.35}}.ico svg{{width:100%;height:100%}}
"""


ICONS = {
    "flame": '<path d="M12 22c4 0 7-3 7-7 0-4-3-6-4-9-1 2-2 3-3 3 0-2-1-4-3-6 0 4-4 6-4 11 0 5 3 8 7 8z"/>',
    "card": '<rect x="2" y="5" width="20" height="14" rx="2.5"/><path d="M2 10h20M6 15h4"/>',
    "bolt": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M9 20v-5h6v5"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
}


def _ico(name):
    return (f'<div class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" '
            f'stroke-linejoin="round">{ICONS[name]}</svg></div>') if name in ICONS else ""


def _html(c, i, n):
    foot = (f'<div class="foot"><div class="brand"><div style="width:54px;height:54px;background:#06070b;border-radius:14px">{MARK}</div>'
            f'<b>Benefy</b><small>정부혜택을 한눈에</small></div>'
            f'<span class="pg">{"<span class=swipe>넘겨보기 →</span>&nbsp;&nbsp;" if i == 1 else ""}{i} / {n}</span></div>')
    if c["kind"] == "cover":
        body = (f'<span class="chip">{e(c["chip"])}</span><h1>{c["title"]}</h1><p class="sub">{e(c["sub"])}</p>'
                f'<div class="hero-mark">{MARK}</div>')
    elif c["kind"] == "item":
        rows = "".join(f"<li><b>{e(k)}</b><span>{e(v)}</span></li>" for k, v in c["rows"])
        amt = (f'<div class="amt"><small>{e(c["amt_label"])}</small><strong>{e(c["amt"])}<em>{e(c.get("unit", ""))}</em></strong></div>'
               if c.get("amt") else "")
        body = f'<span class="chip">{e(c["chip"])}</span><div class="num">{i - 1:02d}</div><h2>{e(c["title"])}</h2>{amt}<ul>{rows}</ul>'
    else:
        body = f'<span class="chip">{e(c["chip"])}</span><h1>{c["title"]}</h1><p class="sub">{e(c["sub"])}</p><span class="cta">{e(c["cta"])}</span>'
    return f'<html><head><meta charset="utf-8"><style>{_css()}</style></head><body><div class="glow"></div><div class="glow b"></div>{_ico(c.get("icon", "check" if c["kind"] == "end" else ""))}<div class="wrap">{body}</div>{foot}</body></html>'


def render(cards, out_dir):
    from playwright.sync_api import sync_playwright
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp.html"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None, args=["--disable-dev-shm-usage"])
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, c in enumerate(cards, 1):
            tmp.write_text(_html(c, i, len(cards)), "utf-8")
            pg.goto(tmp.as_uri())
            pg.wait_for_timeout(300)
            png = out / f"{i}.png"
            pg.screenshot(path=str(png))
            from PIL import Image
            Image.open(png).convert("RGB").save(out / f"{i}.webp", "WEBP", quality=86)
            png.unlink()
        b.close()
    tmp.unlink()
    return [out / f"{i}.webp" for i in range(1, len(cards) + 1)]
