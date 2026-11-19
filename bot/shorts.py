"""지금 뜨는 이슈 → 유튜브 숏츠(세로 1080x1920, 30~45초) 자동 제작.

형식: 상단 2줄 제목(흰색+노란색) / 가운데 정사각 영상 / 영상 하단 자막 / 검은 배경.
흐름: 인기 쇼츠·검색어 수집 → Claude가 주제 선정·웹 조사·대본 → 힉스필드 AI 영상(키 없으면 글자 카드)
→ 무료 음성(edge-tts) → 자막·배경음악 합성(ffmpeg) → 유튜브 자동 업로드(Upload-Post) 또는 텔레그램 전송.
남의 영상은 쓰지 않는다 (주제만 참고, 대본·영상은 새로 만듦). 영상 파일은 저장소에 남기지 않는다.
"""
import asyncio
import random
import re
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
MEDIA_Y, MEDIA = 440, 1080  # 가운데 정사각 영상 위치·크기
CAP_Y = 1330  # 자막 위치 (영상 아래쪽에 겹침)


class Beat(BaseModel):
    narration: str = Field(description="읽을 문장 1개. 24자 이내, 반말 썰 말투 ('~라는데', '~거든', '~했다고 함', '~인 거'). '~입니다/~습니다/~해요' 금지")
    card: str = Field(description="AI 영상이 없을 때 화면 가운데 카드에 띄울 짧은 문구 (20자 이내)")
    twist: bool = Field(default=False, description="반전·핵심 숫자가 나오는 문장이면 true ('띵' 효과음)")
    visual: str = Field(description="'photo' (실제 사진: 실존 인물·장소·물건·사건 현장) 또는 'ai' (재연 장면·주인공 연출 컷)")
    query: str = Field(description="실제 사진 검색어 (영어 2~4단어). 실존 대상은 정확한 고유명사+종류 (예: 'Samsung Lions baseball', 'Everland amusement park'), 일반 장면은 구체적으로 (예: 'baseball stadium crowd night'). ai 장면이어도 대체용으로 반드시 작성")
    ai_prompt: str = Field(description="AI 이미지 프롬프트 (영어). 주인공이 나오면 'the protagonist' 로 지칭. 사실적인 사진 느낌, 글자·로고 없음")


class Plan(BaseModel):
    topic: str = Field(description="고른 주제 한 줄")
    title_top: str = Field(description="상단 제목 첫 줄 (흰색), 13자 이내")
    title_bottom: str = Field(description="상단 제목 둘째 줄 (노란색, 궁금증 포인트), 13자 이내")
    character: str = Field(description="AI 장면에 계속 나올 주인공(가상 인물)의 생김새 영어 묘사 (나이·성별·옷·분위기). "
                                       "실존 인물을 닮게 만들지 않음 — 실존 인물은 'photo' 장면으로만 보여줌")
    photo_fallbacks: List[str] = Field(description="사진 검색이 안 될 때 쓸 넓은 영어 검색어 2~3개 (예: 'soccer stadium', 'football fans')")
    hook_video: str = Field(description="첫 장면 AI 영상 프롬프트 (영어, 5초, 역동적인 한 장면)")
    beats: List[Beat] = Field(description="내레이션 4~5문장 (전체 20초 이내). 첫 문장은 제목 내용을 다시 던지는 훅, 마지막은 반전·한마디 정리")
    yt_title: str = Field(description="유튜브 제목 40자 이내, 끝에 #shorts")
    description: str = Field(description="유튜브 설명 2~3줄")
    tags: List[str] = Field(description="해시태그용 키워드 5~8개 (# 없이)")
    sources: List[str] = Field(description="사실 확인에 쓴 출처 URL 1~3개")


PICK = """당신은 한국 유튜브 쇼츠 채널의 기획자입니다. 아래는 지금 한국에서 뜨는 쇼츠와 검색어입니다.

{trends}

최근에 이미 만든 주제 (겹치지 않게): {used}

1) 인기 쇼츠 제목들에서 어떤 소재·훅이 먹히는지 파악하고, 그중 우리가 '새로 만든 AI 영상 + 내레이션'으로 재미있게 풀 수 있는 주제 1개를 고르세요.
   좋은 주제: 신기한 사실, 해외 화제, 신기술·신제품, 게임·놀이기구·자동차처럼 장면으로 재연하기 좋은 것, 생활 속 의외의 이유.
   피할 주제: 정치·선거, 사망·사고·재난·범죄 피해, 연예인 사생활·루머, 특정인 비방, 건강·투자 조언, 미성년자.
2) 웹 검색으로 그 주제의 사실관계를 확인하세요. 검색으로 확인되지 않은 내용은 쓰지 않습니다.
3) 정리: 주제, 왜 뜨는지, 확인된 사실 5~8개(숫자·이름은 정확히), 출처 URL, 시청자가 '오?' 할 반전 포인트."""

WRITE = """당신은 조회수 높은 한국 유튜브 쇼츠 작가입니다. 아래 조사 내용으로 30~40초 쇼츠를 만드세요.
- 조사 내용에 있는 사실만 씁니다. 과장·낚시·지어낸 숫자 금지. 남의 쇼츠 대사를 베끼지 않습니다.
- 말투: 친구에게 썰 푸는 반말 쇼츠 내레이션 ("~라는데", "근데 여기서 반전", "~했다고 함", "~인 거"). 문장은 짧게.
  '~입니다', '~습니다', '~해요' 같은 존댓말 문장 끝은 절대 쓰지 않습니다.
- 제목 2줄: 첫 줄은 상황, 둘째 줄(노란색)은 궁금증 ("~하는 이유", "~라고?", "결과는?").
- 화면은 요즘 인기 쇼츠처럼 문장마다 컷이 바뀝니다. 문장마다 실제 사진('photo')과 AI 연출 컷('ai')을 섞으세요 (대략 반반).
  · 실존 인물·장소·제품·사건은 'photo' (실제 사진 검색). 실존 인물을 AI로 그리지 않습니다.
  · 감정·상황 재연, '만약 내가 ~라면' 같은 장면은 'ai' — 매번 같은 가상 주인공(character)이 나오게 해서 이야기처럼 이어지게.
  · AI 프롬프트는 영어, 실제 사진처럼 (photorealistic, natural light, smartphone photo). 글자·로고·저작권 캐릭터 금지.

[조사 내용]
{notes}"""


def now():
    return datetime.now(KST)


def plan_short(st):
    """(Plan, 비용)"""
    if config.MOCK or not config.ANTHROPIC_API_KEY:
        return Plan(topic="테스트 주제", title_top="미국 놀이공원에서", title_bottom="난리 난 기구의 정체",
                    character="a Korean man in his 20s wearing a hoodie", photo_fallbacks=["amusement park"], hook_video="a roller coaster drops at sunset",
                    beats=[Beat(narration="미국 놀이공원에 새로 생긴 기구가 난리라는데", card="미국 놀이공원 신상 기구",
                                visual="photo", query="roller coaster", ai_prompt=""),
                           Beat(narration="높이가 무려 백 미터가 넘는다고 함", card="높이 100m 이상",
                                visual="ai", query="drop tower ride", ai_prompt="the protagonist screaming on a drop tower"),
                           Beat(narration="근데 여기서 반전이 있음", card="근데 반전", visual="photo", query="amusement park", ai_prompt="")],
                    yt_title="미국 놀이공원 신상 기구 #shorts", description="테스트", tags=["놀이기구"],
                    sources=["https://example.com"]), 0.0
    from . import contest, trends
    used = ", ".join(st.get("shorts_topics", [])[-30:]) or "없음"
    collected = trends.collect() or "(수집 실패 — 웹 검색으로 오늘 한국 화제를 직접 찾으세요)"
    notes, cost = contest._search_call(PICK.format(trends=collected, used=used), max_uses=6)
    res = contest._client().messages.parse(
        model=config.CLAUDE_MODEL, max_tokens=6000, output_config={"effort": "medium"}, output_format=Plan,
        messages=[{"role": "user", "content": WRITE.format(notes=notes)}])
    cost += contest._cost(res.usage)
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"숏츠 대본 생성 실패 (stop_reason={res.stop_reason})")
    p = res.parsed_output
    return p, cost


# ---------- 그래픽 (HTML → 투명 PNG) ----------
FONT = "@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');"
BASE_CSS = FONT + ("*{margin:0;box-sizing:border-box}body{width:1080px;height:1920px;background:transparent;"
                   "font-family:Pretendard,sans-serif;word-break:keep-all;overflow:hidden}")


def title_html(p):
    return f"""<style>{BASE_CSS}
.t{{position:absolute;top:110px;left:40px;right:40px;height:{MEDIA_Y - 140}px;display:flex;flex-direction:column;
 justify-content:center;align-items:center;font-weight:900;line-height:1.2;letter-spacing:-.035em}}
.t div{{white-space:nowrap;font-size:98px}}
.a{{color:#fff}}.b{{color:#FFE400}}
.ch{{position:absolute;top:70px;left:0;right:0;text-align:center;font-size:30px;font-weight:700;color:#9ca3af}}</style>
<div class="ch">{e(config.SHORTS_CHANNEL)}</div>
<div class="t"><div class="a">{e(p.title_top)}</div><div class="b">{e(p.title_bottom)}</div></div>
<script>window.fit=function(){{  // 제목이 검은 띠(레터박스) 밖으로 넘치지 않게 글자 크기를 줄임
 const box=document.querySelector('.t');
 for(const d of box.children){{let s=98;while(d.scrollWidth>box.clientWidth&&s>40){{s-=2;d.style.fontSize=s+'px';}}}}
 let s2=parseInt(getComputedStyle(box.children[0]).fontSize);
 while(box.scrollHeight>box.clientHeight&&s2>40){{s2-=2;for(const d of box.children)d.style.fontSize=Math.min(s2,parseInt(d.style.fontSize||98))+'px';}}
}};</script>"""


def caption_html(text):
    return f"""<style>{BASE_CSS}
.c{{position:absolute;top:{CAP_Y}px;left:0;right:0;text-align:center}}
.c span{{display:inline-block;max-width:960px;background:rgba(0,0,0,.82);color:#fff;font-size:62px;font-weight:800;
 line-height:1.3;padding:14px 30px;border-radius:14px;letter-spacing:-.02em}}</style>
<div class="c"><span>{e(text)}</span></div>"""


def card_html(text):
    return f"""<style>{FONT}*{{margin:0;box-sizing:border-box}}
body{{width:{MEDIA}px;height:{MEDIA}px;background:#fff;display:flex;align-items:center;justify-content:center;
 font-family:Pretendard,sans-serif;word-break:keep-all}}
p{{font-size:84px;font-weight:600;color:#222;text-align:center;line-height:1.35;padding:0 90px;letter-spacing:-.03em}}</style><p>{e(text)}</p>"""


class Renderer:
    def __enter__(self):
        import os
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        return self

    def png(self, html, out, w=W, h=H, transparent=True):
        page = self._b.new_page(viewport={"width": w, "height": h})
        page.set_content("<!doctype html><html><head><meta charset='utf-8'></head><body>" + html + "</body></html>")
        page.evaluate("document.fonts.ready")
        page.evaluate("window.fit && window.fit()")
        page.wait_for_timeout(150)
        page.screenshot(path=str(out), omit_background=transparent)
        page.close()
        return out

    def __exit__(self, *a):
        self._b.close()
        self._pw.stop()


# ---------- 음성 ----------
ENGINES = []  # 문장별로 실제 쓴 음성 엔진 기록


def tts(text, out, prev="", nxt=""):
    """타입캐스트(키 있을 때) → 실패하면 무료 음성."""
    from . import typecast
    if typecast.enabled():
        try:
            f = typecast.tts(text, out, prev, nxt)
            ENGINES.append("typecast")
            return f
        except Exception as ex:
            print(f"[shorts] 타입캐스트 실패 → 무료 음성: {str(ex)[:150]}")
    try:
        import edge_tts

        async def go():
            await edge_tts.Communicate(text, config.SHORTS_VOICE, rate="+25%").save(str(out))
        asyncio.run(go())
        ENGINES.append("edge")
        return out if out.exists() and out.stat().st_size > 1000 else None
    except Exception as ex:
        print(f"[shorts] 음성 실패: {type(ex).__name__}")
        return None


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def chunks(text, n=15):
    """자막을 한 줄(약 15자)씩 나눔."""
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out or [text]


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


# ---------- 합성 ----------
def make_video(p, media, work):
    """media: 문장별 ("video"|"image", 경로) 또는 None(글자 카드)"""
    segs = []
    # 음성은 브라우저(Playwright)를 열기 전에 미리 만든다 (같은 스레드에서 asyncio 충돌 방지)
    n = [b.narration for b in p.beats]
    audios = [tts(t, work / f"a{i}.mp3", n[i - 1] if i else "", n[i + 1] if i + 1 < len(n) else "")
              for i, t in enumerate(n)]
    voiced = sum(1 for a in audios if a)
    events, t_beat = [], 0.0  # 효과음 (시각, 종류)
    with Renderer() as r:
        title = r.png(title_html(p), work / "title.png")
        for i, b in enumerate(p.beats):
            audio = audios[i]
            dur = (duration(audio) + 0.05) if audio else max(2.2, len(b.narration) * 0.11)
            parts = chunks(b.narration)
            total_chars = sum(len(x) for x in parts)
            caps, t = [], 0.0
            if i:
                events.append((t_beat, "whoosh"))  # 장면 전환 '휙'
            if getattr(b, "twist", False):
                events.append((t_beat + 0.05, "ding"))  # 반전 '띵'
            for j, text in enumerate(parts):
                d = dur * len(text) / total_chars
                caps.append((r.png(caption_html(text), work / f"c{i}_{j}.png"), t, t + d))
                events.append((t_beat + t, "pop"))  # 자막 뜰 때 '뽁'
                t += d
            t_beat += dur
            kind, src = media[i] if i < len(media) and media[i] else (None, None)
            cmd = ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}"]
            frames = int(dur * 30) + 1
            if kind == "video":
                cmd += ["-stream_loop", "-1", "-i", src]
                media_f = (f"[1:v]scale={MEDIA}:{MEDIA}:force_original_aspect_ratio=increase,"
                           f"crop={MEDIA}:{MEDIA},setsar=1,fps=30[m]")
            elif kind == "image":  # 사진: 정사각으로 자르고 천천히 확대/축소 (번갈아)
                cmd += ["-loop", "1", "-i", src]
                z = "min(1.0+on*0.0015,1.15)" if i % 2 == 0 else "max(1.15-on*0.0015,1.0)"
                media_f = (f"[1:v]scale={MEDIA * 2}:{MEDIA * 2}:force_original_aspect_ratio=increase,"
                           f"crop={MEDIA * 2}:{MEDIA * 2},setsar=1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)'"
                           f":y='ih/2-(ih/zoom/2)':d={frames}:s={MEDIA}x{MEDIA}:fps=30[m]")
            else:
                card = r.png(card_html(b.card), work / f"k{i}.png", MEDIA, MEDIA, transparent=False)
                cmd += ["-loop", "1", "-i", card]
                media_f = (f"[1:v]scale={int(MEDIA * 1.1)}:-2,zoompan=z='min(zoom+0.0008,1.06)':x='iw/2-(iw/zoom/2)'"
                         f":y='ih/2-(ih/zoom/2)':d={frames}:s={MEDIA}x{MEDIA}:fps=30[m]")
            cmd += ["-i", title]
            for c, _, _ in caps:
                cmd += ["-i", c]
            cmd += (["-i", audio] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            a_idx = 3 + len(caps)
            fc = [media_f, f"[0:v][m]overlay=0:{MEDIA_Y}:shortest=1[v0]", "[v0][2:v]overlay=0:0[v1]"]
            last = "v1"
            for j, (_, t0, t1) in enumerate(caps):
                fc.append(f"[{last}][{3 + j}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'[w{j}]")
                last = f"w{j}"
            fc.append(f"[{last}]format=yuv420p[vout]")
            seg = work / f"seg{i}.mp4"
            ff(*cmd, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{a_idx}:a",
               "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30",
               "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", seg)
            segs.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    joined = work / "joined.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    out = work / "shorts.mp4"
    # 오디오 믹스: 음성 + 배경음악(옅게) + 효과음
    inputs, chains, labels = ["-i", joined], [], ["[0:a]"]
    bgms = sorted((config.ROOT / "assets" / "bgm").glob("*.mp3"))
    k = 1
    if bgms:
        inputs += ["-stream_loop", "-1", "-i", random.choice(bgms)]
        chains.append(f"[{k}:a]volume={config.SHORTS_BGM_VOLUME}[bg]")
        labels.append("[bg]")
        k += 1
    sfx_dir = config.ROOT / "assets" / "sfx"
    vol = {"pop": config.SHORTS_SFX_VOLUME, "whoosh": config.SHORTS_SFX_VOLUME * 0.8, "ding": config.SHORTS_SFX_VOLUME}
    for j, (at, kind) in enumerate(events):
        f = sfx_dir / f"{kind}.wav"
        if not f.exists():
            continue
        inputs += ["-i", f]
        ms = int(at * 1000)
        chains.append(f"[{k}:a]adelay={ms}|{ms},volume={vol[kind]}[s{j}]")
        labels.append(f"[s{j}]")
        k += 1
    if len(labels) > 1:
        chains.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[a]")
        ff(*inputs, "-filter_complex", ";".join(chains), "-map", "0:v", "-map", "[a]", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out)
    else:
        ff("-i", joined, "-c", "copy", "-movflags", "+faststart", out)
    return out, voiced


# ---------- 화면 소재 모으기 ----------
def gather_media(p, work):
    """문장별 화면: 첫 문장은 AI 영상(가능하면), 'ai' 는 AI 이미지, 'photo' 는 무료 실사 사진. 없으면 대체.
    (media 목록, 사진 출처 목록, 비용)"""
    from . import higgsfield, photos
    media, credits, used, cost = [None] * len(p.beats), [], set(), 0.0
    if higgsfield.enabled():
        ai_idx = [i for i, b in enumerate(p.beats) if b.visual == "ai"]
        prompts = [f"{p.beats[i].ai_prompt}. The protagonist: {p.character}. Photorealistic, natural light, "
                   f"candid smartphone photo, no text, no logos" for i in ai_idx]
        files, c = higgsfield.make_images(prompts, work)
        cost += c
        for i, f in zip(ai_idx, files):
            if f:
                media[i] = ("image", f)
        if config.HIGGSFIELD_CLIPS > 0:
            clips, c = higgsfield.make_clips([f"{p.hook_video}. Photorealistic, cinematic, no text"], work,
                                             config.HIGGSFIELD_SECONDS)
            cost += c
            if clips and clips[0]:
                media[0] = ("video", clips[0])
        print(f"[shorts] 힉스필드: 이미지 {sum(1 for f in files if f)}/{len(files)}, 예상 ${cost:.2f}")
    for i, b in enumerate(p.beats):
        if media[i]:
            continue
        f, credit = photos.find(b.query, used, work / f"p{i}.jpg", fallbacks=p.photo_fallbacks)
        if f:
            media[i] = ("image", f)
            credits.append(credit)
    print(f"[shorts] 화면: 영상 {sum(1 for m in media if m and m[0] == 'video')}, "
          f"사진·이미지 {sum(1 for m in media if m and m[0] == 'image')}, 글자카드 {sum(1 for m in media if not m)}")
    return media, credits, cost


# ---------- 업로드 ----------
def full_description(p, credits=()):
    from . import typecast
    tags = " ".join("#" + t.replace(" ", "") for t in p.tags[:8])
    src = "\n".join(f"- {u}" for u in p.sources[:3])
    photo = ("\n\n사진 출처\n" + "\n".join(f"- {c}" for c in dict.fromkeys(credits))) if credits else ""
    voice = (f"\n\nThis content was produced with Typecast, an AI virtual actor service. "
             f"Characters casted: {config.TYPECAST_VOICE_NAME} https://typecast.ai") if typecast.enabled() else ""
    return (f"{p.description}\n\n출처\n{src}{photo}\n\n※ 일부 장면은 AI로 만든 이미지예요.{voice}\n\n{tags} #shorts")


def upload_youtube(video, p, credits=()):
    if not (config.UPLOAD_POST_API_KEY and config.UPLOAD_POST_USER):
        return None
    with open(video, "rb") as f:
        r = requests.post(
            "https://api.upload-post.com/api/upload",
            headers={"Authorization": f"Apikey {config.UPLOAD_POST_API_KEY}",
                     "Idempotency-Key": "shorts-" + re.sub(r"\W", "", p.topic)[:40] + now().strftime("%Y%m%d")},
            data=[("user", config.UPLOAD_POST_USER), ("platform[]", "youtube"),
                  ("title", p.yt_title[:100]), ("youtube_title", p.yt_title[:100]),
                  ("youtube_description", full_description(p, credits)[:4900]),
                  *[("tags[]", t) for t in p.tags[:8]],
                  ("privacyStatus", config.SHORTS_PRIVACY), ("selfDeclaredMadeForKids", "false"),
                  ("containsSyntheticMedia", "true"), ("defaultLanguage", "ko"), ("defaultAudioLanguage", "ko"),
                  ("categoryId", "24"), ("async_upload", "true")],
            files={"video": ("shorts.mp4", f, "video/mp4")}, timeout=300)
    if r.status_code >= 300:
        raise RuntimeError(f"유튜브 업로드 실패 HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def send_telegram(st, video, p, uploaded, credits):
    chat = st.get("owner_chat_id") or config.TELEGRAM_CHAT_ID
    if not chat or not telegram.enabled():
        return
    cap = f"🎬 숏츠: {e(p.topic)}\n" + (f"유튜브 업로드 완료 ({config.SHORTS_PRIVACY})" if uploaded is not None else
                                        "영상 길게 눌러 저장 → 유튜브 앱 + → 업로드\n제목·설명은 다음 메시지 탭해서 복사")
    try:
        with open(video, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendVideo",
                              data={"chat_id": chat, "caption": cap, "parse_mode": "HTML", "supports_streaming": "true",
                                    "width": W, "height": H},
                              files={"video": ("shorts.mp4", f, "video/mp4")}, timeout=300)
        if not r.json().get("ok"):
            print("[shorts] 텔레그램 영상 전송 실패:", r.text[:200])
    except requests.RequestException as ex:
        print("[shorts] 텔레그램 영상 전송 실패:", type(ex).__name__)
    if uploaded is None:
        telegram.send(chat, f"제목\n<code>{e(p.yt_title)}</code>", html=True)
        telegram.send(chat, f"설명\n<code>{e(full_description(p, credits))}</code>", html=True)


# ---------- 실행 ----------
STATE = config.DATA_DIR / "shorts_state.json"  # 숏츠 기록은 따로 저장 (메인 작업과 파일 충돌 방지)


def load_ss():
    import json
    return json.loads(STATE.read_text("utf-8")) if STATE.exists() else {}


def requested(st, ss):
    req = st.get("shorts_request")
    if not req:
        return False
    done = ss.get("request_done", "")
    if req is True:  # 예전 형식
        return not done
    return str(req) > done


def due(st):
    ss = load_ss()
    if st.get("paused") or config.SHORTS_PER_DAY <= 0:
        return False
    tried = ss.get("shorts_tried")
    if tried and now() - datetime.fromisoformat(tried) < timedelta(minutes=50):
        return False  # 방금 시도함 (실패해도 15분마다 반복하지 않게)
    if requested(st, ss):
        return True
    done = ss.get("kpi", {}).get("shorts_made", {}).get(now().strftime("%Y-%m-%d"), 0)
    return now().hour >= config.SHORTS_HOUR_KST and done < config.SHORTS_PER_DAY


def run(force=False):
    from . import higgsfield, kpi, pipeline
    st = pipeline.load_state()
    if not force and not due(st):
        print("[shorts] 오늘 할 일 없음")
        return
    ss = load_ss()
    month = now().strftime("%Y-%m")
    if st.get("cost", {}).get(month, 0) + ss.get("cost", {}).get(month, 0) >= config.MAX_MONTHLY_USD:
        print("[shorts] 월 비용 상한 도달")
        return
    work = Path(tempfile.mkdtemp(prefix="shorts-"))
    ss["shorts_tried"] = now().isoformat(timespec="minutes")
    was_requested = requested(st, ss)
    try:
        p, cost = plan_short(ss)
        print(f"[shorts] 주제: {p.topic} / 문장 {len(p.beats)} / AI컷 {sum(b.visual == 'ai' for b in p.beats)}")
        media, credits, cost2 = gather_media(p, work)
        cost += cost2
        ss.setdefault("cost", {})[month] = round(ss.get("cost", {}).get(month, 0) + cost, 4)
        video, voiced = make_video(p, media, work)
        print(f"[shorts] 완성 {duration(video):.1f}초, 음성 {voiced}/{len(p.beats)}")
        uploaded = None
        try:
            uploaded = upload_youtube(video, p, credits)
        except Exception as ex:
            pipeline.notify(st, f"⚠️ 유튜브 자동 업로드 실패 → 영상을 텔레그램으로 보낼게요\n{str(ex)[:300]}")
        send_telegram(st, video, p, uploaded, credits)
        if config.SHORTS_KEEP:
            shutil.copy(video, config.ROOT / "shorts_preview.mp4")
        ss["shorts_topics"] = (ss.get("shorts_topics", []) + [p.topic])[-60:]
        kpi.bump(ss, "shorts_made")
        if was_requested:
            ss["request_done"] = now().isoformat(timespec="seconds")
    except Exception as ex:
        pipeline.notify(st, f"⚠️ 숏츠 제작 실패: {type(ex).__name__}: {str(ex)[:300]}")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        pipeline.save_json(STATE, ss)


def render_sample(folder):
    """assets/samples/<이름>/plan.json + img0.jpg… 로 영상만 만들어 텔레그램으로 보냄 (업로드 안 함)."""
    import json
    from . import pipeline
    d = config.ROOT / folder if not Path(folder).is_absolute() else Path(folder)
    p = Plan(**json.loads((d / "plan.json").read_text("utf-8")))
    media = [("image", f) if (f := d / f"img{i}.jpg").exists() else None for i in range(len(p.beats))]
    work = Path(tempfile.mkdtemp(prefix="sample-"))
    video, voiced = make_video(p, media, work)
    out = config.ROOT / "shorts_sample.mp4"
    shutil.copy(video, out)
    from . import typecast
    n_tc = ENGINES.count("typecast")
    voice = (f"타입캐스트 {config.TYPECAST_VOICE_NAME} {n_tc}/{len(p.beats)}문장" if n_tc else "무료 음성") + \
        ("" if typecast.enabled() else " (타입캐스트 키 없음)")
    print(f"[sample] {duration(out):.1f}초, 음성 {voiced}/{len(p.beats)} ({voice})")
    st = pipeline.load_state()
    send_telegram(st, out, p, uploaded=None, credits=())
    pipeline.notify(st, f"🧪 틀 테스트 영상: {duration(out):.1f}초 · 목소리 {voice}")
