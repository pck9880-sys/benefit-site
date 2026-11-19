"""사이트 글 → 유튜브 숏츠(세로 1080x1920, 30~45초) 자동 제작.

흐름: 글 고르기 → Claude 대본(장면 5개) → 장면 이미지(HTML→PNG) → 무료 음성(edge-tts) → ffmpeg 합성
→ 업로드: UPLOAD_POST_API_KEY 가 있으면 유튜브에 자동 업로드, 없으면 텔레그램으로 영상+제목·설명 전송.
영상 파일은 저장소에 남기지 않는다 (용량). 이 모듈은 별도 워크플로(shorts.yml)에서만 돈다.
"""
import asyncio
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from html import escape as e
from pathlib import Path
from typing import List

import requests
from pydantic import BaseModel, Field

from . import config, telegram

KST = timezone(timedelta(hours=9))
W, H = 1080, 1920
VOICE = config.SHORTS_VOICE


class Scene(BaseModel):
    screen: str = Field(description="화면에 크게 띄울 문구. 2줄 이내, 줄마다 14자 이내, 줄바꿈은 \\n")
    narration: str = Field(description="이 장면에서 읽을 내레이션 1~2문장 (해요체, 40자 이내)")


class Script(BaseModel):
    hook: Scene = Field(description="첫 장면: 시청자가 '내 얘기네' 하고 멈추게 하는 한 줄. 대상+혜택 중심. 과장 금지")
    points: List[Scene] = Field(description="핵심 3개: 누가 / 얼마나·무엇을 / 언제·어떻게 신청")
    title: str = Field(description="유튜브 제목 40자 이내, 끝에 #shorts. 검색어(제도명) 포함")
    description: str = Field(description="유튜브 설명 3~4줄. 핵심 요약 + '자세한 신청 방법은 아래 링크' 문장")
    tags: List[str] = Field(description="해시태그용 키워드 5~8개 (# 없이)")


SYSTEM = """당신은 정부 지원금 정보를 30초 유튜브 숏츠로 만드는 작가입니다.
- 받은 자료에 있는 사실만 씁니다. 금액·날짜·나이·자격을 지어내지 않습니다. 자료에 없으면 그 내용은 빼세요.
- 과장·낚시 금지("무조건", "누구나 100만원", "안 받으면 바보").
- 화면 문구는 짧고 굵게. 내레이션은 화면 문구를 자연스럽게 풀어 읽는 말투(해요체).
- 마지막 안내 장면은 시스템이 붙이므로 쓰지 않습니다."""


def now():
    return datetime.now(KST)


def thumb_key(name):
    n = name or ""
    for keys, k in ((("주거",), "housing"), (("고용", "창업", "일자리"), "work"), (("임신", "출산"), "birth"),
                    (("보육", "교육"), "edu"), (("보건", "의료", "건강"), "health"), (("보호", "돌봄"), "care"),
                    (("생활", "안정", "금융"), "living"), (("문화", "환경"), "culture"), (("농", "어업"), "farm")):
        if any(x in n for x in keys):
            return k
    return "etc"


def pick_post():
    from . import taxonomy
    posts = []
    for p in config.POSTS_DIR.glob("*.json"):
        d = json.loads(p.read_text("utf-8"))
        if d.get("shorts_sent"):
            continue
        state, _ = taxonomy.deadline_info(d["source"].get("deadline"))
        if state == "closed":
            continue
        d["_path"] = p
        d["_rank"] = (0 if state == "upcoming" else 1, d.get("published_at", ""))
        posts.append(d)
    if not posts:
        return None
    posts.sort(key=lambda d: (d["_rank"][0], -datetime.fromisoformat(d["_rank"][1]).timestamp() if d["_rank"][1] else 0))
    return posts[0]


def write_script(post):
    a, src = post["article"], post["source"]
    if config.MOCK or not config.ANTHROPIC_API_KEY:
        name = src.get("name", "지원금")
        return Script(hook=Scene(screen=f"{name[:14]}\n아직 모르세요?", narration=f"{name}, 아직 모르시나요?"),
                      points=[Scene(screen="누가 받나요?\n" + (src.get("user_type") or "")[:14], narration="대상부터 볼게요."),
                              Scene(screen="무엇을 주나요?\n현금 지원", narration="지원 내용은 이래요."),
                              Scene(screen="신청은\n온라인으로", narration="신청은 이렇게 해요.")],
                      title=f"{name} 한 번에 정리 #shorts", description="테스트 설명", tags=["정부지원금", name]), 0.0
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    content = (f"[제도명] {src.get('name')}\n[기관] {src.get('org')}\n[신청기한] {src.get('deadline')}\n"
               f"[요약]\n" + "\n".join(a["summary_points"]) + f"\n\n[본문]\n{a['body_markdown'][:5000]}")
    res = client.messages.parse(model=config.CLAUDE_MODEL, max_tokens=3000, system=SYSTEM,
                                output_config={"effort": "low"}, output_format=Script,
                                messages=[{"role": "user", "content": content}])
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"숏츠 대본 생성 실패 (stop_reason={res.stop_reason})")
    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    s = res.parsed_output
    s.points = s.points[:3]
    return s, (res.usage.input_tokens * pin + res.usage.output_tokens * pout) / 1_000_000


# ---------- 장면 이미지 ----------
CSS = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
*{margin:0;box-sizing:border-box}
body{width:1080px;height:1920px;font-family:Pretendard,sans-serif;color:#fff;overflow:hidden;word-break:keep-all;
 background:radial-gradient(120% 80% at 80% 0%,#1f3a6b 0%,#14213d 55%,#0b1426 100%)}
.top{position:absolute;top:150px;left:80px;right:80px;display:flex;align-items:center;gap:20px;font-size:40px;font-weight:700;opacity:.92}
.top svg{width:62px;height:62px}
.top em{font-style:normal;color:#5eead4}
.cat{position:absolute;top:300px;left:80px;background:rgba(94,234,212,.15);border:2px solid rgba(94,234,212,.5);
 color:#5eead4;font-size:38px;font-weight:700;padding:12px 30px;border-radius:999px}
.img{position:absolute;right:80px;bottom:330px;width:560px;height:560px;object-fit:cover;border-radius:64px;opacity:.95;
 box-shadow:0 40px 120px rgba(0,0,0,.45)}
.main{position:absolute;top:470px;left:80px;right:80px}
.num{font-size:44px;font-weight:800;color:#0b1426;background:#5eead4;display:inline-block;padding:8px 26px;border-radius:16px;margin-bottom:36px}
h1{font-size:112px;line-height:1.18;font-weight:900;letter-spacing:-.03em;text-shadow:0 6px 30px rgba(0,0,0,.35)}
h1 b{color:#fcd34d}
.sub{margin-top:40px;font-size:46px;line-height:1.45;font-weight:600;color:#cbd5e1;max-width:880px}
.bar{position:absolute;left:80px;right:80px;bottom:200px;height:12px;border-radius:6px;background:rgba(255,255,255,.15)}
.bar i{display:block;height:100%;border-radius:6px;background:#5eead4}
.foot{position:absolute;left:80px;right:80px;bottom:110px;font-size:34px;color:#94a3b8}
.cta h1{font-size:96px}
.cap{position:absolute;left:80px;right:80px;bottom:330px;font-size:52px;line-height:1.5;font-weight:700;color:#e2e8f0;
 background:rgba(255,255,255,.07);border-left:10px solid #5eead4;border-radius:20px;padding:44px 48px}
.url{margin-top:50px;display:inline-block;font-size:48px;font-weight:800;background:#fff;color:#14213d;padding:22px 40px;border-radius:24px}
"""

SHIELD = ('<svg viewBox="0 0 64 64"><path d="M32 4 8 13v17c0 15 10 26 24 30 14-4 24-15 24-30V13z" fill="#0f766e"/>'
          '<path d="m21 32 8 8 15-16" stroke="#fff" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _lines(text):
    return "<br>".join(e(x.strip()) for x in text.replace("\\n", "\n").split("\n") if x.strip())


def scene_html(kind, scene, idx, total, post, img_uri):
    head = f'<div class="top">{SHIELD}<span>정부<em>혜택</em> 한눈에</span></div>'
    bar = f'<div class="bar"><i style="width:{round((idx + 1) / total * 100)}%"></i></div>'
    field = e(post["source"].get("field") or "정부지원")
    if kind == "cta":
        site = config.SITE_URL.replace("https://", "")
        body = (f'<div class="main cta"><h1>신청 방법·서류는<br><b>더보기 링크</b>에서<br>확인하세요</h1>'
                f'<div class="url">{e(site)}</div><p class="sub">신청 전 정부24 공식 안내도 꼭 확인하세요</p></div>')
    else:
        num = f'<div class="num">{idx}/3</div>' if kind == "point" else ""
        body = f'<div class="main">{num}<h1>{_lines(scene.screen)}</h1></div>'
        if kind == "point":  # 소리 없이 보는 사람을 위한 자막
            body += f'<div class="cap">{e(scene.narration)}</div>'
    img = f'<img class="img" src="{img_uri}">' if kind == "hook" else ""
    foot = f'<div class="foot">출처: 행정안전부 공공서비스 정보 · {e(post["source"].get("org") or "")}</div>'
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>'
            f'{head}<div class="cat">{field}</div>{img}{body}{bar}{foot}</body></html>')


def render_images(script, post, work):
    from playwright.sync_api import sync_playwright
    img = (config.ROOT / "static" / "img" / "cat" / f"{thumb_key(post['source'].get('field'))}.webp").resolve().as_uri()
    scenes = [("hook", script.hook)] + [("point", p) for p in script.points] + [("cta", None)]
    files = []
    with sync_playwright() as p:
        import os
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        page = b.new_page(viewport={"width": W, "height": H})
        for i, (kind, sc) in enumerate(scenes):
            f = work / f"s{i}.html"
            f.write_text(scene_html(kind, sc, i, len(scenes), post, img), "utf-8")
            page.goto(f.as_uri())
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(300)
            out = work / f"s{i}.png"
            page.screenshot(path=str(out))
            files.append(out)
        b.close()
    narr = [script.hook.narration] + [p.narration for p in script.points] + \
           ["자세한 신청 방법은 더보기 링크에서 확인하세요."]
    return files, narr


# ---------- 음성 ----------
def tts(text, out):
    """무료 음성 합성. 실패하면 None (자막만 있는 영상으로 계속)."""
    try:
        import edge_tts

        async def go():
            await edge_tts.Communicate(text, VOICE, rate="+12%").save(str(out))
        asyncio.run(go())
        return out if out.exists() and out.stat().st_size > 1000 else None
    except Exception as ex:
        print(f"[shorts] 음성 실패: {type(ex).__name__}: {ex}")
        return None


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def make_video(images, narr, work):
    segs, voiced = [], 0
    for i, (img, text) in enumerate(zip(images, narr)):
        audio = tts(text, work / f"a{i}.mp3")
        dur = (duration(audio) + 0.45) if audio else 3.2
        voiced += bool(audio)
        frames = int(dur * 30)
        seg = work / f"seg{i}.mp4"
        vf = (f"scale=1188:-2,zoompan=z='min(zoom+0.0007,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps=30,fade=t=in:st=0:d=0.2,format=yuv420p")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(img)]
        cmd += ["-i", str(audio)] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        cmd += ["-vf", vf, "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-shortest" if audio else "-t", ]
        if not audio:
            cmd += [f"{dur:.2f}"]
        cmd += [str(seg)]
        subprocess.run(cmd, check=True)
        segs.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    out = work / "shorts.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    return out, voiced


# ---------- 업로드 ----------
def full_description(script, post):
    link = f"{config.SITE_URL}/{post['url'] if 'url' in post else 'posts/' + post['id']}"
    tags = " ".join("#" + t.replace(" ", "") for t in script.tags[:8])
    return (f"{script.description}\n\n👉 자세한 신청 방법: {link}\n\n"
            f"※ 행정안전부 공공서비스 정보를 바탕으로 정리했어요. 신청 전 정부24 공식 안내를 꼭 확인하세요.\n\n{tags} #shorts")


def upload_youtube(video, script, post):
    """Upload-Post API 로 유튜브 업로드. 성공하면 결과 dict, 키가 없으면 None."""
    if not (config.UPLOAD_POST_API_KEY and config.UPLOAD_POST_USER):
        return None
    with open(video, "rb") as f:
        r = requests.post(
            "https://api.upload-post.com/api/upload",
            headers={"Authorization": f"Apikey {config.UPLOAD_POST_API_KEY}",
                     "Idempotency-Key": f"shorts-{post['id']}"},
            data=[("user", config.UPLOAD_POST_USER), ("platform[]", "youtube"),
                  ("title", script.title[:100]),
                  ("youtube_title", script.title[:100]),
                  ("youtube_description", full_description(script, post)[:4900]),
                  *[("tags[]", t) for t in script.tags[:8]],
                  ("privacyStatus", config.SHORTS_PRIVACY), ("selfDeclaredMadeForKids", "false"),
                  ("containsSyntheticMedia", "true"), ("defaultLanguage", "ko"), ("defaultAudioLanguage", "ko"), ("categoryId", "27"), ("async_upload", "true")],
            files={"video": ("shorts.mp4", f, "video/mp4")}, timeout=300)
    if r.status_code >= 300:
        raise RuntimeError(f"유튜브 업로드 실패 HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def send_telegram(st, video, script, post, uploaded):
    chat = st.get("owner_chat_id") or config.TELEGRAM_CHAT_ID
    if not chat or not telegram.enabled():
        return
    if uploaded is not None:
        cap = f"🎬 숏츠 유튜브 업로드 완료 ({config.SHORTS_PRIVACY})\n<b>{e(script.title)}</b>"
    else:
        cap = "🎬 오늘의 숏츠\n영상 길게 눌러 저장 → 유튜브 앱 + → 업로드\n제목·설명은 다음 메시지를 탭해서 복사"
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video, "rb") as f:
            r = requests.post(url, data={"chat_id": chat, "caption": cap, "parse_mode": "HTML",
                                         "supports_streaming": "true", "width": W, "height": H},
                              files={"video": ("shorts.mp4", f, "video/mp4")}, timeout=300)
        if not r.json().get("ok"):
            print("[shorts] 텔레그램 영상 전송 실패:", r.text[:200])
    except requests.RequestException as ex:
        print("[shorts] 텔레그램 영상 전송 실패:", type(ex).__name__)
    if uploaded is None:
        telegram.send(chat, f"제목\n<code>{e(script.title)}</code>", html=True)
        telegram.send(chat, f"설명\n<code>{e(full_description(script, post))}</code>", html=True)


# ---------- 실행 ----------
def due(st):
    if st.get("paused") or config.SHORTS_PER_DAY <= 0:
        return False
    tried = st.get("shorts_tried")
    if tried and now() - datetime.fromisoformat(tried) < timedelta(minutes=50):
        return False  # 방금 시도함 (실패해도 15분마다 반복하지 않게)
    if st.get("shorts_request"):
        return True
    today = now().strftime("%Y-%m-%d")
    done = st.get("kpi", {}).get("shorts_made", {}).get(today, 0)
    return now().hour >= config.SHORTS_HOUR_KST and done < config.SHORTS_PER_DAY


def run(force=False):
    from . import kpi, pipeline
    st = pipeline.load_state()
    if not force and not due(st):
        print("[shorts] 오늘 할 일 없음")
        return
    if st.get("cost", {}).get(now().strftime("%Y-%m"), 0) >= config.MAX_MONTHLY_USD:
        print("[shorts] 월 비용 상한 도달")
        return
    post = pick_post()
    if not post:
        print("[shorts] 만들 글 없음")
        st.pop("shorts_request", None)
        pipeline.save_json(config.STATE_FILE, st)
        return
    work = Path(tempfile.mkdtemp(prefix="shorts-"))
    st["shorts_tried"] = now().isoformat(timespec="minutes")
    try:
        script, cost = write_script(post)
        month = now().strftime("%Y-%m")
        st.setdefault("cost", {})[month] = round(st.get("cost", {}).get(month, 0) + cost, 4)
        images, narr = render_images(script, post, work)
        video, voiced = make_video(images, narr, work)
        print(f"[shorts] {post['source'].get('name')} → {duration(video):.1f}초, 음성 {voiced}/{len(narr)}")
        uploaded = None
        try:
            uploaded = upload_youtube(video, script, post)
        except Exception as ex:
            pipeline.notify(st, f"⚠️ 유튜브 자동 업로드 실패 → 영상을 텔레그램으로 보낼게요\n{str(ex)[:300]}")
        send_telegram(st, video, script, post, uploaded)
        if config.SHORTS_KEEP:
            shutil.copy(video, config.ROOT / "shorts_preview.mp4")
        path = post.pop("_path")
        post.pop("_rank", None)
        post["shorts_sent"] = now().isoformat(timespec="minutes")
        path.write_text(json.dumps(post, ensure_ascii=False, indent=1), "utf-8")
        kpi.bump(st, "shorts_made")
        st.pop("shorts_request", None)
    except Exception as ex:
        pipeline.notify(st, f"⚠️ 숏츠 제작 실패: {type(ex).__name__}: {str(ex)[:300]}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        pipeline.save_json(config.STATE_FILE, st)
