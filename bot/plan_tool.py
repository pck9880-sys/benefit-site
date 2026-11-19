"""숏츠 카테고리 템플릿 도구 — 대본 쓰는 Claude 가 형식을 덜 고민하게 해서 빠르고 일정하게.

  python -m bot.plan_tool new <slug> <웃긴글|감동|이슈>   → 폴더 + 뼈대 plan.json (템플릿 값 채움, 빈칸만 채우면 됨)
  python -m bot.plan_tool check <slug>                   → 자동 보정(장면 배치·썸네일 문구·고지문·태그) + 규칙 검사
                                                           문제가 있으면 목록 출력 후 종료코드 1 → 고치고 다시 실행
템플릿: templates/shorts/<종류>.json
"""
import json
import re
import sys
from pathlib import Path

from . import config

TPL_DIR = config.ROOT / "templates" / "shorts"
SAMPLES = config.ROOT / "assets" / "samples"
KINDS = {"웃긴글": "웃긴글", "유머": "웃긴글", "감동": "감동", "이슈": "이슈", "핫이슈": "이슈"}
BAD_END = re.compile(r"(요|니다|해요잉|어요|아요|세요|죠)[.!?~ㅋㅎ\s]*$")


def tpl(kind):
    return json.loads((TPL_DIR / f"{KINDS[kind]}.json").read_text("utf-8"))


def kind_of(p):
    return "이슈" if p.get("kind") == "이슈" else ("감동" if p.get("mood") == "감동" else "웃긴글")


def _beat():
    return {"narration": "", "card": "", "twist": False, "visual": "ai", "query": "", "ai_prompt": "",
            "overlay": "none", "overlay_text": "", "overlay_source": ""}


def new(slug, kind):
    t = tpl(kind)
    d = SAMPLES / slug
    d.mkdir(parents=True, exist_ok=True)
    n_ai = t["ai_images"]
    p = {"topic": "", "title_top": "", "title_bottom": "", **t["plan"],
         "intro_post": {"emoji": t["intro"]["emoji"], "board": t["intro"]["board"]},
         "beats": [_beat() for _ in range(t["beats"][1])],
         "outro": "", "media": [],
         "gpt_images": [{"file": f"img{i}.jpg", "prompt": ""} for i in range(n_ai)],
         "thumb_caption": "", "end_comments": [], "yt_title": "", "description": "", "tags": list(t["tags"]),
         "sources": [], "pin_comment": ""}
    (d / "plan.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), "utf-8")
    print(f"[plan] {d / 'plan.json'} 만듦 ({t['label']}: 문장 {t['beats'][0]}~{t['beats'][1]}개, AI 이미지 {n_ai}장, "
          f"짤 {t['zzal']['min']}~{t['zzal']['max']}장({t['zzal']['source'] or '없음'}), 실제 사진 {t['real_photos']['min']}~{t['real_photos']['max']}장)")
    print("  빈칸: topic, title_top/bottom(줄당 9자 이내), beats[].narration(음슴체), gpt_images[].prompt, "
          "end_comments(실제 댓글 3~5), yt_title, description, pin_comment, sources")


def prep_post_images(d):
    """커뮤니티 원글 이미지(p*.jpg) → 장면용 정사각(sN.jpg). 얼굴 모자이크(auto), 긴 캡처는 위에서부터 나눠 여러 장면으로,
    가로·세로 비율이 안 맞으면 흐린 배경 위에 통째로 (글자가 잘리지 않게). 이미 만든 건 건너뜀."""
    from PIL import Image, ImageFilter
    from . import realimg
    out = []
    srcs = sorted(d.glob("p[0-9]*.jpg"), key=lambda x: int(re.sub(r"\D", "", x.stem) or 0))
    if srcs and not (d / "s1.jpg").exists():
        k = 0
        for f in srcs:
            realimg.process(f, f, "auto")  # 사람 얼굴 모자이크
            im = Image.open(f).convert("RGB")
            w, h = im.size
            parts = [im]
            if h > w * 1.35:  # 긴 캡처: 가로폭 x (가로폭*1.1) 조각으로
                step = int(w * 1.1)
                parts = [im.crop((0, y, w, min(h, y + step))) for y in range(0, h, step) if min(h, y + step) - y > w * 0.25]
            for part in parts:
                k += 1
                S = 1080
                bg = part.resize((S, S)).filter(ImageFilter.GaussianBlur(40))
                pw, ph = part.size
                sc = min(S / pw, S / ph)
                fg = part.resize((max(1, int(pw * sc)), max(1, int(ph * sc))))
                bg.paste(fg, ((S - fg.size[0]) // 2, (S - fg.size[1]) // 2))
                bg.save(d / f"s{k}.jpg", quality=92)
    return sorted((x.name for x in d.glob("s[0-9]*.jpg")), key=lambda n: int(re.sub(r"\D", "", n)))


def _layout(p, d, t):
    """템플릿 순서대로 AI·짤·실제 사진을 장면에 배치 (같은 종류가 모자라면 다른 종류로)."""
    pools = {
        "ai": [g["file"] for g in p.get("gpt_images", []) if not g["file"].startswith("thumb")],
        "zzal": sorted(x.name for x in d.glob("z*.png")),
        "real": sorted(x.name for x in d.glob("r[0-9]*.jpg")),
        "post": prep_post_images(d),
    }
    used = {k: 0 for k in pools}
    media = []
    n = len(p["beats"])
    for i in range(n):
        want = t["media_pattern"][i % len(t["media_pattern"])]
        order = [want, "post", "ai", "real", "zzal"]
        if t["zzal"]["max"] == 0:
            order = [x for x in order if x != "zzal"]
        for k in order:
            lim = t["zzal"]["max"] if k == "zzal" else (t["real_photos"]["max"] if k == "real" else 99)
            if pools[k] and used[k] < max(lim, 0) and (k == "ai" or used[k] < len(pools[k])):  # 원글·짤·사진은 한 번씩
                f = pools[k][used[k] % len(pools[k])]
                used[k] += 1
                media.append({"zzal": f} if k == "zzal" else {"image": f})
                break
        else:
            media.append({"image": pools["ai"][i % len(pools["ai"])]} if pools["ai"] else media[-1])
    # 규칙(2026-11-20): AI 이미지 2장마다 실사(실제 사진·원글 이미지) 1장 — AI 가 3장 연속이면 남은 실사로 바꿈
    ai_set = set(pools["ai"])
    real_left = [x for x in pools["real"] + pools["post"] if not any(x in m.values() for m in media)]
    streak = 0
    for i, m in enumerate(media):
        if m.get("image") in ai_set:
            streak += 1
            if streak > 2 and real_left:
                media[i] = {"image": real_left.pop(0)}
                streak = 0
        else:
            streak = 0
    return media


def check(slug):
    d = SAMPLES / slug
    p = json.loads((d / "plan.json").read_text("utf-8"))
    kind = kind_of(p)
    t = tpl(kind)
    for k, v in t["plan"].items():  # 템플릿 고정값
        if k in ("mood", "kind", "caption_style") or not p.get(k):
            p[k] = v
    errs, notes = [], []

    # 제목·문장
    for k in ("title_top", "title_bottom"):
        s = p.get(k, "")
        if not s:
            errs.append(f"{k} 비어 있음")
        elif len(s.replace(" ", "")) > 9:
            errs.append(f"{k} '{s}' 너무 김 (공백 빼고 9자 이내)")
    beats = [b for b in p.get("beats", []) if b.get("narration", "").strip()]
    p["beats"] = beats
    lo, hi = t["beats"]
    if not lo <= len(beats) <= hi:
        errs.append(f"문장 {len(beats)}개 (필요 {lo}~{hi})")
    for i, b in enumerate(beats):
        s = re.sub(r"\*\*", "", b["narration"]).strip()
        if len(s) > 30:
            errs.append(f"문장{i + 1} 30자 넘음: {s}")
        if BAD_END.search(s):
            errs.append(f"문장{i + 1} 존댓말/해요체 끝: {s} → 음슴체(~함/~했음/~임)로")
        b.setdefault("card", s)
    ends = [re.sub(r"[^가-힣]", "", re.sub(r"\*\*", "", b["narration"]))[-2:] for b in beats]
    for i in range(2, len(ends)):
        if ends[i] and ends[i] == ends[i - 1] == ends[i - 2]:
            errs.append(f"문장{i - 1}~{i + 1} 끝맺음 '{ends[i]}' 3번 연속 → 이어 주는 말(~했는데/~하더니/~해서)·명사 끝 등으로 섞기")
            break
    import unicodedata
    def _jong_m(ch):  # 받침이 ㅁ 인 글자(했음·함·임·됨·옴…) = 음슴체 명사형 끝
        if not ("가" <= ch <= "힣"):
            return False
        return (ord(ch) - 0xAC00) % 28 == 16
    eum = sum(1 for e in ends if e and _jong_m(e[-1]))
    if beats and eum > len(beats) * 0.55:
        errs.append(f"'~음/~함' 끝이 {eum}/{len(beats)}문장 → 절반 이하로. '~했는데/~하더니/~해서/~니까', 명사 끝, 'ㅋㅋ' 로 이어 쓰기")
    for k in ("yt_title", "pin_comment", "description"):
        if "해요잉" in p.get(k, ""):
            errs.append(f"{k} 에 '해요잉' 금지")
    if p.get("outro") and not p.get("outro_custom"):
        p["outro"] = ""

    # 이미지 문구: 스타일 꼬리 + 썸네일
    gi = [g for g in p.get("gpt_images", []) if not g["file"].startswith("thumb")]
    for g in gi:
        if not g.get("prompt", "").strip():
            errs.append(f"gpt_images {g['file']} 프롬프트 비어 있음")
        elif "no text" not in g["prompt"].lower():
            g["prompt"] = g["prompt"].rstrip(". ") + ". " + t["image_style"]
    if t["thumb_ai"]:
        from . import thumb
        gi.append({"file": "thumb_src.jpg", "prompt": thumb.prompt(p)})
        if not p.get("thumb_caption"):
            errs.append("thumb_caption 비어 있음 (15자 이내 훅)")
    p["gpt_images"] = gi

    # 짤·실제 사진 수
    nz = len(list(d.glob("z*.png")))
    if not t["zzal"]["min"] <= nz <= max(t["zzal"]["max"], t["zzal"]["min"]):
        errs.append(f"짤 {nz}장 (필요 {t['zzal']['min']}~{t['zzal']['max']}, {t['zzal']['source'] or '사용 안 함'})")
    nr = len(list(d.glob("r[0-9]*.jpg")))
    npost = len(list(d.glob("p[0-9]*.jpg")))
    if t.get("post_min") and npost < t["post_min"]:
        errs.append(f"원글 이미지 {npost}장 (최소 {t['post_min']}: python -m bot.community grab <URL> assets/samples/<slug>)")
    if nr < t["real_photos"]["min"] and not npost:
        errs.append(f"실제 사진 {nr}장 (최소 {t['real_photos']['min']}, bot.realimg 로 모자이크 처리해서 rN.jpg)")

    # 장면 배치: 비었거나 없는 파일을 가리키면 템플릿 순서로 다시
    pending = {g["file"] for g in gi}
    ok = p.get("media") and len(p["media"]) >= len(beats) and all(
        (d / (m.get("image") or m.get("zzal") or m.get("video", ""))).exists()
        or (m.get("image") in pending) for m in p["media"])
    if not ok:
        p["media"] = _layout(p, d, t)
        notes.append("장면 배치를 템플릿 순서로 채움")
    # 문장에 딱 맞는 '과장된 실사' — beat 에 real_query 가 있으면 그 문장 장면에 실사를 자동으로 받아 넣음
    from . import photos
    for i, b in enumerate(beats):
        q = (b.get("real_query") or "").strip()
        if not q:
            continue
        f = d / f"r{100 + i}.jpg"
        if not f.exists():
            photos.get(q, f, b.get("real_mode", "auto"))
        if f.exists() and i < len(p["media"]):
            p["media"][i] = {"image": f.name}
        elif not f.exists():
            errs.append(f"문장{i + 1} 실사 '{q}' 못 찾음 → real_query 를 다른 영어 검색어로")
    ai_names = {g["file"] for g in gi if not g["file"].startswith("thumb")}
    n_ai = sum(1 for m in p["media"] if m.get("image") in ai_names)
    n_real = sum(1 for m in p["media"] if re.match(r"^[rs]\d+\.jpg$", m.get("image", "")))
    need = (n_ai + 1) // 2
    if n_real < need:
        errs.append(f"AI 장면 {n_ai}개에 실사 {n_real}개 → AI 2장당 실사 1장 필수: 실사 {need - n_real}장 더 "
                    f"(python -m bot.photos get \"<영어 검색어>\" assets/samples/<slug>/rN.jpg auto)")
    if kind == "감동" and any("zzal" in m for m in p["media"]):
        p["media"] = [m for m in p["media"] if "zzal" not in m] or p["media"]
        p["media"] = _layout(p, d, t)

    # 첫·끝 장면, 설명·태그
    ip = p.get("intro_post") if isinstance(p.get("intro_post"), dict) else {}
    ip.setdefault("emoji", t["intro"]["emoji"])
    ip.setdefault("board", t["intro"]["board"])
    p["intro_post"] = ip
    ec = p.get("end_comments") or []
    if not 3 <= len(ec) <= 5:
        errs.append(f"end_comments {len(ec)}개 (원글 실제 댓글 3~5개)")
    desc = p.get("description", "")
    for line in t["disclaimers"]:
        if kind == "이슈" and "모자이크" in line and nr == 0:
            continue
        if line not in desc:
            desc = desc.rstrip() + "\n\n" + line
    cf = d / "credits.json"
    if cf.exists():
        for c in json.loads(cf.read_text("utf-8")).values():
            if c and c not in desc:
                desc = desc.rstrip() + "\n" + c
    pj = d / "post.json"
    if pj.exists():
        site = json.loads(pj.read_text("utf-8")).get("site", "")
        if site and site not in desc:
            desc = desc.rstrip() + f"\n※ 출처: {site} 인기글"
    p["description"] = desc.strip()
    p["tags"] = list(dict.fromkeys((p.get("tags") or []) + t["tags"]))[:12]
    if p.get("yt_title") and "#shorts" not in p["yt_title"]:
        p["yt_title"] = p["yt_title"].rstrip() + " #shorts"
    if not p.get("yt_title"):
        errs.append("yt_title 비어 있음")

    (d / "plan.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), "utf-8")
    for x in notes:
        print("[plan] 보정:", x)
    if errs:
        print("[plan] 고칠 것:")
        for x in errs:
            print("  -", x)
        return 1
    print(f"[plan] OK ({t['label']}, 문장 {len(beats)}, 장면 {len(p['media'])}, 이미지 요청 {len(gi)}장, 짤 {nz}, 실제 사진 {nr})")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "new":
        new(sys.argv[2], sys.argv[3])
    elif cmd == "check":
        sys.exit(check(sys.argv[2]))
