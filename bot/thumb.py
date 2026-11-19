"""숏츠 썸네일 (기본값) — 클릭을 부르되 유튜브 심의(성적 콘텐츠·오해 소지 썸네일 정책)를 넘지 않는 선.

- 감동: 영상 장면 중 가장 강한 컷 + 제목 2줄.
- 웃긴글·기본: AI 성인 여성 이미지(예쁘고 핏 좋은 옷으로 몸매 라인이 드러나는 정도) + 주제에 맞는 표정·리액션 + 제목 2줄.
  넘지 않는 선(코드로 고정): 25세 이상 성인, 옷 다 갖춰 입음, 속옷·수영복·노출·가슴/엉덩이 클로즈업·선정적 자세 금지,
  실존 인물 닮은꼴 금지, 영상 내용과 연결된 리액션(낚시성 무관 썸네일 금지).
- 사용법:
  1) prompt(raw) 문구로 Figma generate_image (정사각 1024x1024) → assets/samples/<slug>/thumb_src.jpg
  2) python -m bot.thumb assets/samples/<slug>  → thumb.jpg (1080x1920, 제목 합성)
  plan.json "thumb": false 면 만들지 않음.
"""
import json
import sys
from html import escape as e
from pathlib import Path

from . import config, songs

SAFE = ("adult woman in her late 20s, fully clothed, no lingerie, no swimwear, no cleavage focus, "
        "no suggestive pose, not resembling any real person, no text, no logo, no watermark")

REACTION = {
    "웃긴글": "laughing hard with hand over mouth, eyes squinted, playful and bright energy",
    "기본": "surprised expression with wide eyes and slightly open mouth, pointing at the viewer",
}


def prompt(raw):
    mood = songs.mood_of(raw)
    if mood == "감동":
        return None  # 감동은 영상 장면 컷 사용
    topic = raw.get("topic", "")
    return ("Square 1:1 photorealistic photo for a YouTube Shorts thumbnail. A beautiful Korean "
            f"{SAFE.split(',')[0]} with a slim, well-proportioned figure, wearing a stylish form-fitting outfit "
            "(fitted knit top or slim cardigan with high-waist jeans) that shows her body silhouette tastefully, "
            f"{REACTION[mood]}. Reaction relates to this topic: {topic}. Waist-up framing, face in the upper third, "
            "bright clean studio light, soft pastel background, high contrast, sharp focus, Instagram-model look. "
            + ", ".join(SAFE.split(", ")[1:]) + ".")


def compose(folder):
    from .shorts import Renderer, BASE_CSS, MEDIA_Y, MEDIA
    d = Path(folder) if Path(folder).is_absolute() else config.ROOT / folder
    raw = json.loads((d / "plan.json").read_text("utf-8"))
    if raw.get("thumb") is False:
        print("[thumb] 썸네일 안 만듦 (plan thumb=false)")
        return None
    src = next((d / n for n in ("thumb_src.jpg", "thumb_src.png") if (d / n).exists()), None)
    if not src:  # 감동형·이미지 없음 → 첫 장면 이미지
        m = raw.get("media") or []
        names = [x.get("image") for x in m if x.get("image")] + ["img0.jpg"]
        src = next((d / n for n in names if n and (d / n).exists()), None)
    if not src:
        print("[thumb] 원본 이미지 없음")
        return None
    import base64
    uri = "data:image/jpeg;base64," + base64.b64encode(src.read_bytes()).decode()
    # 채널 기존 썸네일 느낌: 검은 바탕 + 위 흰/노랑 두 줄 제목 + 가운데 정사각 장면 + 아래쪽 어두운 자막 상자
    import re
    cap = raw.get("thumb_caption") or next((b.get("narration", "") for b in raw.get("beats", [])), "")
    cap = re.sub(r"\*\*", "", cap)
    if len(cap) > 16:  # 어절 단위로 자르기 (단어 중간 끊김 금지)
        cut = cap[:16].rsplit(" ", 1)[0]
        cap = (cut if len(cut) >= 6 else cap[:15]).rstrip(" ,") + "…"
    html = f"""<style>{BASE_CSS}
body{{background:#000}}
.t{{position:absolute;top:110px;left:40px;right:40px;height:{MEDIA_Y - 140}px;display:flex;flex-direction:column;
 justify-content:center;align-items:center;font-weight:900;line-height:1.2;letter-spacing:-.035em}}
.t div{{white-space:nowrap;font-size:98px}}.a{{color:#fff}}.b{{color:#FFE400}}
.m{{position:absolute;left:0;top:{MEDIA_Y}px;width:1080px;height:{MEDIA}px;background:url({uri}) center 30%/cover}}
.c{{position:absolute;left:0;right:0;top:{MEDIA_Y + MEDIA - 190}px;text-align:center}}
.c span{{display:inline-block;background:rgba(20,20,20,.82);color:#fff;font-size:62px;font-weight:800;
 padding:14px 34px 18px;border-radius:18px;letter-spacing:-.03em;white-space:nowrap}}</style>
<div class="t"><div class="a">{e(raw.get('title_top', ''))}</div><div class="b">{e(raw.get('title_bottom', ''))}</div></div>
<div class="m"></div>{f'<div class="c"><span>{e(cap)}</span></div>' if cap else ''}
<script>window.fit=function(){{const box=document.querySelector('.t');
 for(const x of box.children){{let s=98;while(x.scrollWidth>box.clientWidth&&s>40){{s-=2;x.style.fontSize=s+'px';}}}}}};</script>"""
    out = d / "thumb.jpg"
    png = d / "_thumb.png"
    with Renderer() as r:
        r.png(html, png, 1080, 1920, transparent=False)
    from .shorts import ff
    ff("-i", png, "-q:v", "2", out)
    png.unlink(missing_ok=True)
    print("[thumb]", out)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "prompt":
        print(prompt(json.loads((Path(sys.argv[2]) / "plan.json").read_text("utf-8"))) or "감동형: 장면 컷 사용")
    else:
        compose(sys.argv[1])
