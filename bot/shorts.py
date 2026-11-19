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
    slowmo: bool = Field(default=False, description="하이라이트 장면 슬로모션")
    impact: bool = Field(default=False, description="강렬한 장면: 흰 플래시 + 큰 자막")
    sticker: str = Field(default="", description="예능 리액션 스티커 (예: 'ㅋㅋㅋ', '?!', '귀여움 주의')")
    orig_audio: bool = Field(default=False, description="이 장면은 더빙 없이 원본 영상 소리(게임 대사 등)를 쓰고 자막만")
    visual: str = Field(description="'photo' (실제 사진: 실존 인물·장소·물건·사건 현장) 또는 'ai' (재연 장면·주인공 연출 컷)")
    query: str = Field(description="실제 사진 검색어 (영어 2~4단어). 실존 대상은 정확한 고유명사+종류 (예: 'Samsung Lions baseball', 'Everland amusement park'), 일반 장면은 구체적으로 (예: 'baseball stadium crowd night'). ai 장면이어도 대체용으로 반드시 작성")
    ai_prompt: str = Field(description="AI 이미지 프롬프트 (영어). 주인공이 나오면 'the protagonist' 로 지칭. 사실적인 사진 느낌, 글자·로고 없음")
    overlay: str = Field(default="none", description="이미지 위에 올릴 카드: 'none' / 'headline'(실제 기사 제목) / 'comment'(실제 여론·댓글) "
                                                    "/ 'quote'(당사자·기관의 실제 발언)")
    overlay_text: str = Field(default="", description="카드 문구. headline 은 기사 제목 그대로, comment·quote 는 조사 자료에 실제로 "
                                                      "나온 반응·발언만 (지어내기·욕설·특정인 비방 금지). 강조할 부분은 **굵게**")
    overlay_source: str = Field(default="", description="headline 은 언론사명, comment 는 '온라인 커뮤니티' 같은 출처, quote 는 말한 사람·기관")


class Plan(BaseModel):
    topic: str = Field(description="고른 주제 한 줄")
    title_top: str = Field(description="상단 제목 첫 줄 (흰색), 13자 이내")
    title_bottom: str = Field(description="상단 제목 둘째 줄 (노란색, 궁금증 포인트), 13자 이내")
    character: str = Field(description="AI 장면에 계속 나올 주인공(가상 인물)의 생김새 영어 묘사 (나이·성별·옷·분위기). "
                                       "실존 인물을 닮게 만들지 않음 — 실존 인물은 'photo' 장면으로만 보여줌")
    photo_fallbacks: List[str] = Field(description="사진 검색이 안 될 때 쓸 넓은 영어 검색어 2~3개 (예: 'soccer stadium', 'football fans')")
    hook_video: str = Field(description="첫 장면 AI 영상 프롬프트 (영어, 5초, 역동적인 한 장면)")
    beats: List[Beat] = Field(description="내레이션 4~5문장 (전체 20초 이내). 첫 문장은 제목 내용을 다시 던지는 훅, 마지막은 반전·한마디 정리")
    question: str = Field(default="", description="마무리 직전 토론 유도 질문 1문장 (예: '근데 이거 실력임, 운빨임?'). "
                                                 "의견이 둘로 갈리게, 욕설·비하·혐오·정치 편가르기·특정인 공격 금지. 20자 이내")
    outro_impact: bool = Field(default=False, description="마무리 장면을 강렬하게 (플래시 + 큰 자막)")
    caption_style: str = Field(default="meme", description="'meme'(기본: 가운데 굵은 밈 자막, 줄마다 다른 색) / 'box' / 'epic'")
    outro_free: bool = Field(default=True, description="마무리 한마디를 그대로 사용")
    outro_custom: bool = Field(default=False, description="true 면 outro 를 그대로, false 면 기본 마무리('님들은 어떻게 생각해요잉?')")
    voice: str = Field(default="", description="비워두세요 (시스템이 정함)")
    outro: str = Field(default="", description="마무리 한마디: 시청자(대중) 입장에서 공감하는 반말 한 줄 "
                                     "(예: '솔직히 이 정도면 인정이지'). 시그니처 문구 없음. 20자 이내")
    yt_title: str = Field(description="유튜브 제목 40자 이내, 끝에 #shorts")
    description: str = Field(description="유튜브 설명 2~3줄")
    tags: List[str] = Field(description="해시태그용 키워드 5~8개 (# 없이)")
    sources: List[str] = Field(description="사실 확인에 쓴 출처 URL 1~3개")


PICK = """당신은 한국 유튜브 쇼츠 채널의 기획자입니다. 아래는 지금 한국에서 뜨는 쇼츠와 검색어입니다.

{trends}

최근에 이미 만든 주제 (겹치지 않게): {used}

1) 오늘의 핫이슈 후보 3개를 분야가 겹치지 않게 고르세요 (예: AI·IT 신제품/서비스, 스포츠(축구 등), 해외·세계 화제, 생활 트렌드).
   그중 '내레이션 + AI 이미지'로 15초 안에 가장 재미있게 풀 수 있는 1개를 최종 선택하세요.
   맨 앞에 "후보: 1) … 2) … 3) …  / 선택: N" 형식으로 한 줄 적으세요.
   좋은 주제: 신기한 사실, 해외 화제, 신기술·신제품, 게임·놀이기구·자동차처럼 장면으로 재연하기 좋은 것, 생활 속 의외의 이유.
   피할 주제: 정치·선거, 사망·사고·재난·범죄 피해, 연예인 사생활·루머, 특정인 비방, 건강·투자 조언, 미성년자.
2) 웹 검색으로 그 주제의 사실관계를 확인하세요. 검색으로 확인되지 않은 내용은 쓰지 않습니다.
3) 정리: 주제, 왜 뜨는지, 확인된 사실 5~8개(숫자·이름은 정확히), 출처 URL, 시청자가 '오?' 할 반전 포인트,
   실제 기사 제목 2~3개(언론사명 포함, 원문 그대로), 기사·커뮤니티에 인용된 실제 여론·반응 2~3개(원문 그대로, 욕설 제외)."""

WRITE = """당신은 조회수 높은 한국 유튜브 쇼츠 작가입니다. 아래 조사 내용으로 약 30초 쇼츠를 만드세요.
- 먼저 '이 영상이 말하려는 핵심 한 줄'을 정하고, 모든 문장이 그 한 줄을 향하게 짭니다.
  구성: ① 훅(무슨 일?) → ② 배경(왜 이슈?) → ③ 핵심 사실(숫자) → ④ 반전·쟁점(의견이 갈리는 지점) → ⑤ 정리 한 줄.
- 마무리는 시스템이 '님들은 어떻게 생각해요잉?'으로 고정해서 붙이므로 question 은 비워 두고, ⑤가 쟁점을 또렷하게 던지게 씁니다.
- 조사 내용에 있는 사실만 씁니다. 과장·낚시·지어낸 숫자 금지. 남의 쇼츠 대사를 베끼지 않습니다.
- 말투: 친구에게 썰 푸는 반말 쇼츠 내레이션 ("~라는데", "근데 여기서 반전", "~했다고 함", "~인 거"). 문장은 짧게.
  '~입니다', '~습니다', '~해요' 같은 존댓말 문장 끝은 절대 쓰지 않습니다.
- 요즘 이슈 쇼츠처럼 사이사이에 카드(overlay)를 넣습니다: 기사 제목 카드 1개(headline, 조사 자료의 실제 제목 그대로),
  실제 여론 카드 1~2개(comment, 조사 자료에 인용된 네티즌·시민 반응만 — 없으면 넣지 않음), 필요하면 실제 발언 카드(quote).
  카드 문구는 절대 지어내지 않습니다. 욕설·비방·사망/피해자 관련 조롱은 넣지 않습니다.
- 마무리 직전 question: 댓글 토론이 붙도록 의견이 갈리는 질문 1개 (A냐 B냐 형식). 자극적이어도 욕설·비하·혐오·정치 편가르기는 금지.
- 마무리(outro)는 시청자(대중) 입장 공감 한마디 (본문 beats 에는 넣지 않음): {outro_rule}
- 제목 2줄: 첫 줄은 상황, 둘째 줄(노란색)은 궁금증 ("~하는 이유", "~라고?", "결과는?").
- 화면은 요즘 인기 쇼츠처럼 문장마다 컷이 바뀝니다. 모든 문장은 내용에 딱 맞는 AI 이미지('ai')로 연출합니다
  (뉴스 화면·실제 사진은 쓰지 않음). ai_prompt 는 그 문장 내용이 한눈에 보이도록 구체적으로 (장소·사물·행동·분위기).
  · 실존 인물·장소·제품·사건은 'photo' (실제 사진 검색). 실존 인물을 AI로 그리지 않습니다.
  · 감정·상황 재연, '만약 내가 ~라면' 같은 장면은 'ai' — 매번 같은 가상 주인공(character)이 나오게 해서 이야기처럼 이어지게.
  · AI 프롬프트는 영어, 실제 사진처럼 (photorealistic, natural light, smartphone photo). 글자·로고·저작권 캐릭터 금지.

[조사 내용]
{notes}"""


PICKED = {}  # 오늘 후보·선택 한 줄 (텔레그램 알림용)


def now():
    return datetime.now(KST)


def pick_voice(st, ss):
    """기본은 태우. 텔레그램 '/shorts 창수' 로 요청하면 그 회차만 박창수."""
    req = st.get("shorts_voice_req")
    if req and req.get("at", "") > ss.get("voice_req_done", ""):
        ss["voice_req_done"] = req["at"]
        return req["voice"]
    return config.SHORTS_VOICE_CHAR


def outro_rule(voice):
    return "짧은 반말 공감 한 줄, 채널 시그니처('해요잉' 등) 금지 (예: '솔직히 이 정도면 인정이지')"


def plan_short(st, voice=None):
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
    PICKED["line"] = next((ln for ln in notes.splitlines() if "후보" in ln and "선택" in ln), "")
    res = contest._client().messages.parse(
        model=config.CLAUDE_MODEL, max_tokens=6000, output_config={"effort": "medium"}, output_format=Plan,
        messages=[{"role": "user", "content": WRITE.format(notes=notes, outro_rule=outro_rule(voice))}])
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
    if getattr(p, "caption_style", "") == "meme":  # 밈형 제목: 두 줄 모두 흰색, 아주 굵은 글씨
        return f"""<style>{meme_font_css()}{BASE_CSS}
.t{{position:absolute;top:90px;left:30px;right:30px;height:{MEDIA_Y - 110}px;display:flex;flex-direction:column;justify-content:center;
 align-items:center;font-family:BHS,Pretendard,sans-serif;line-height:1.12;color:#fff}}
.t div{{white-space:nowrap;font-size:150px;letter-spacing:-.02em}}</style>
<div class="t"><div>{e(p.title_top)}</div><div>{e(p.title_bottom)}</div></div>
<script>window.fit=function(){{const box=document.querySelector('.t');
 for(const d of box.children){{let s=150;while(d.scrollWidth>box.clientWidth&&s>50){{s-=2;d.style.fontSize=s+'px';}}}}}};</script>"""
    shade = (f'<div style="position:absolute;left:0;right:0;top:{MEDIA_Y + MEDIA - 420}px;height:420px;'
             f'background:linear-gradient(to bottom,rgba(0,0,0,0),rgba(0,0,0,.55))"></div>'
             if getattr(p, "caption_style", "box") == "epic" else "")  # 자막 뒤를 자연스럽게 어둡게
    return shade + f"""<style>{BASE_CSS}
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


_MEME_FONT = None


def meme_font_css():
    """Black Han Sans (OFL) 를 data URI 로 (브라우저가 로컬 파일을 못 읽어서)."""
    global _MEME_FONT
    if _MEME_FONT is None:
        import base64
        f = config.ROOT / "assets" / "fonts" / "BlackHanSans-Regular.ttf"
        _MEME_FONT = ("@font-face{font-family:'BHS';src:url(data:font/ttf;base64,"
                      + base64.b64encode(f.read_bytes()).decode() + ") format('truetype')}") if f.exists() else ""
    return _MEME_FONT


MEME_COLORS = ["#ffffff", "#ff3ef5", "#ffe600", "#3ef0ff"]
VARIETY = [("#FFE600", "#111"), ("#FF4D8D", "#fff"), ("#38D9FF", "#111"), ("#8CFF5A", "#111"), ("#FF9A2E", "#111")]


def caption_html(text, style="box", impact=False, idx=0, sticker=""):
    if style == "meme":  # 밈 자막: 영상 가운데, 굵은 기울임 글씨 + 두꺼운 검은 테두리, 줄마다 색이 다름
        col = MEME_COLORS[idx % len(MEME_COLORS)]
        hi = "#ffe600" if col == "#ffffff" else "#ffffff"
        body = re.sub(r"\*\*(.+?)\*\*", rf'<span style="color:{hi}">\1</span>', e(text))
        size = 104 if impact else 88
        return f"""<style>{meme_font_css()}{BASE_CSS}
.c{{position:absolute;top:{MEDIA_Y + int(MEDIA * 0.52)}px;left:30px;right:30px;text-align:center;font-family:BHS,Pretendard,sans-serif;
 font-size:{size}px;line-height:1.15;color:{col};-webkit-text-stroke:16px #000;paint-order:stroke fill;transform:skewX(-9deg);
 letter-spacing:-.01em;text-shadow:0 10px 18px rgba(0,0,0,.45)}}</style><div class="c">{body}</div>"""
    if style == "variety":  # 예능 자막: 색 박스 + 굵은 테두리 + 살짝 기울기, 리액션 스티커
        bg, fg = VARIETY[idx % len(VARIETY)]
        rot = (-2.5, 2, -1.5, 2.5, -2)[idx % 5]
        body = re.sub(r"\*\*(.+?)\*\*", r'<span class="k">\1</span>', e(text))
        stk = ""
        if sticker:
            stk = (f'<div class="s" style="transform:rotate({-rot * 3}deg)">{e(sticker)}</div>')
        return f"""<style>{BASE_CSS}
.c{{position:absolute;top:{CAP_Y - 20}px;left:0;right:0;text-align:center}}
.c span.box{{display:inline-block;max-width:960px;background:{bg};color:{fg};font-size:66px;font-weight:900;line-height:1.25;
 padding:16px 34px 20px;border-radius:26px;border:6px solid #111;box-shadow:8px 10px 0 #111;letter-spacing:-.03em;
 transform:rotate({rot}deg)}}
.k{{color:{'#e11d48' if fg == '#111' else '#FFE600'}}}
.s{{position:absolute;top:{MEDIA_Y + 70}px;right:60px;font-size:96px;font-weight:900;color:#fff;-webkit-text-stroke:10px #111;
 paint-order:stroke fill;text-shadow:6px 8px 0 #FF4D8D}}</style>{stk}<div class="c"><span class="box">{body}</span></div>"""
    if style == "epic":  # 영화 예고편 스타일: 박스 없이 굵은 흰 글씨 + 검은 테두리, **강조** 는 금색
        size = 100 if impact else 70
        top = MEDIA_Y + MEDIA // 2 - 80 if impact else CAP_Y
        badge = ""
        m = re.match(r"^\[(.+?)\]\s*", text)  # [현장 MC] 같은 말머리 → 작은 배지
        if m:
            badge, text = f'<div class="b">{e(m.group(1))}</div>', text[m.end():]
        body = re.sub(r"\*\*(.+?)\*\*", r'<span class="k">\1</span>', e(text))
        return f"""<style>{BASE_CSS}
.c{{position:absolute;top:{top}px;left:40px;right:40px;text-align:center;font-size:{size}px;font-weight:900;color:#fff;
 line-height:1.25;letter-spacing:-.03em;-webkit-text-stroke:{10 if impact else 7}px #000;paint-order:stroke fill;
 text-shadow:0 8px 24px rgba(0,0,0,.6)}}
.k{{color:#FFD54A}}
.b{{display:inline-block;margin-bottom:14px;background:#e11d48;color:#fff;font-size:34px;font-weight:900;padding:6px 18px;
 border-radius:8px;-webkit-text-stroke:0;text-shadow:none;letter-spacing:0}}</style><div class="c">{badge}<div>{body}</div></div>"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
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


def _rich(text):
    """**굵게** → 빨간 밑줄 강조"""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e(text))


def overlay_html(kind, text, source, bg_uri):
    """기사 제목·댓글·발언 카드 (실제 화면 캡처 대신 직접 그림 — 닉네임·얼굴은 흐리게 처리)."""
    bg = (f'<img src="{bg_uri}" style="position:absolute;inset:-40px;width:1160px;height:1160px;object-fit:cover;'
          f'filter:blur(16px) brightness(.6)">') if bg_uri else ""
    common = (f"<style>{FONT}*{{margin:0;box-sizing:border-box}}body{{width:{MEDIA}px;height:{MEDIA}px;background:#111;"
              f"font-family:Pretendard,sans-serif;word-break:keep-all;overflow:hidden;position:relative}}"
              f".wrap{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:70px}}"
              f"b{{text-decoration:underline;text-decoration-color:#ff3b30;text-decoration-thickness:6px;text-underline-offset:10px}}</style>")
    if kind == "headline":
        tag = ""
        m = re.match(r"^\s*\[(.+?)\]\s*", text)
        if m:
            tag, text = f'<span style="color:#e11d48">[{e(m.group(1))}]</span> ', text[m.end():]
        card = (f'<div style="background:#fff;border-radius:22px;padding:46px 50px;box-shadow:0 30px 80px rgba(0,0,0,.5);width:100%">'
                f'<div style="font-size:60px;font-weight:800;line-height:1.38;color:#111;letter-spacing:-.03em">{tag}{_rich(text)}</div>'
                f'<div style="margin-top:26px;font-size:32px;color:#6b7280;font-weight:600">{e(source)}</div></div>')
    elif kind == "comment":
        card = (f'<div style="background:#1f1f22;border-radius:26px;padding:40px 44px;width:100%;box-shadow:0 30px 80px rgba(0,0,0,.5)">'
                f'<div style="display:flex;align-items:center;gap:18px;margin-bottom:24px">'
                f'<span style="background:#2563eb;color:#fff;font-size:28px;font-weight:900;padding:6px 16px;border-radius:8px">BEST</span>'
                f'<span style="width:56px;height:56px;border-radius:50%;background:#f59e0b;filter:blur(7px)"></span>'
                f'<span style="font-size:32px;color:#d4d4d8;filter:blur(9px)">익명사용자1234</span>'
                f'<span style="font-size:28px;color:#71717a;margin-left:auto">{e(source)}</span></div>'
                f'<div style="font-size:54px;font-weight:700;color:#fff;line-height:1.42;letter-spacing:-.02em">{_rich(text)}</div></div>')
    elif kind == "score":  # 해외 평점 카드: "매체|점수|만점" 여러 개를 ; 로 (예: "Metacritic|78|100;IGN|8.5|10")
        rows = []
        for it in text.split(";"):
            name, sc, mx = (it.split("|") + ["", "", ""])[:3]
            try:
                ratio = float(sc) / float(mx)
            except ValueError:
                ratio = 0.7
            col = "#22c55e" if ratio >= .8 else "#eab308" if ratio >= .65 else "#ef4444"
            rows.append(f'<div style="display:flex;align-items:center;gap:26px;margin:16px 0">'
                        f'<div style="width:150px;height:150px;border-radius:24px;background:{col};color:#111;display:flex;'
                        f'align-items:center;justify-content:center;font-size:{68 if len(sc) < 4 else 56}px;font-weight:900">{e(sc)}</div>'
                        f'<div><div style="font-size:52px;font-weight:900;color:#fff">{e(name)}</div>'
                        f'<div style="font-size:30px;color:#a1a1aa">/ {e(mx)}점</div></div></div>')
        card = (f'<div style="background:rgba(17,17,20,.92);border-radius:30px;padding:40px 50px;width:100%;'
                f'box-shadow:0 30px 80px rgba(0,0,0,.6)"><div style="font-size:36px;color:#a1a1aa;font-weight:800;margin-bottom:10px">'
                f'{e(source or "해외 평점")}</div>{"".join(rows)}</div>')
    elif kind == "steam":  # 스팀 사용자 평가 카드: "이전평가|현재평가|리뷰 수"
        before, now_, cnt = (text.split("|") + ["", "", ""])[:3]
        def tag(t, c):
            return f'<span style="color:{c};font-weight:900">{e(t)}</span>'
        card = (f'<div style="background:linear-gradient(160deg,#1b2838,#2a475e);border-radius:28px;padding:44px 50px;width:100%;'
                f'box-shadow:0 30px 80px rgba(0,0,0,.6);color:#c7d5e0">'
                f'<div style="font-size:34px;font-weight:800;letter-spacing:.05em;color:#66c0f4">사용자 평가</div>'
                f'<div style="font-size:50px;margin-top:22px">{tag(before, "#b9a074")} '
                f'<span style="color:#fff;font-weight:900"> → </span> {tag(now_, "#66c0f4")}</div>'
                f'<div style="font-size:34px;margin-top:20px;color:#8f98a0">{e(cnt)}</div>'
                f'<div style="font-size:26px;margin-top:16px;color:#6b7a88">{e(source)}</div></div>')
    else:  # quote
        card = (f'<div style="background:#fff;border-radius:26px;padding:50px 54px;width:100%;box-shadow:0 30px 80px rgba(0,0,0,.5)">'
                f'<div style="font-size:54px;font-weight:600;color:#111;line-height:1.5;letter-spacing:-.02em">{_rich(text)}</div>'
                f'<div style="margin-top:26px;font-size:32px;color:#6b7280;font-weight:600">— {e(source)}</div></div>')
    return common + bg + f'<div class="wrap">{card}</div>'


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
CURRENT_VOICE = {}  # 이번 영상 목소리 (타입캐스트 캐릭터 이름)
LAST_BGM = None  # 이번 영상에 쓴 배경음악 파일 이름 (설명란 출처 표기용)
LAST_BGM_CREDIT = None  # Jamendo 곡이면 출처 문구


def music_credit():
    import json
    if LAST_BGM_CREDIT:
        return LAST_BGM_CREDIT
    f = config.ROOT / "assets" / "bgm" / "credits.json"
    if not LAST_BGM or not f.exists():
        return ""
    return json.loads(f.read_text("utf-8")).get(LAST_BGM, "")


def tts(text, out, prev="", nxt=""):
    """타입캐스트(키 있을 때) → 실패하면 무료 음성."""
    from . import typecast
    if typecast.enabled():
        try:
            f = typecast.tts(text, out, prev, nxt, name=CURRENT_VOICE.get("name"))
            ENGINES.append("typecast")
            return f
        except Exception as ex:
            if config.TYPECAST_ONLY:
                raise RuntimeError(f"타입캐스트({config.TYPECAST_VOICE_NAME}) 음성 실패 — 무료 음성으로 바꾸지 않고 중단: "
                                   f"{str(ex)[:200]}")
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
VOICES = {"용식": {}, "태우": {}, "박창수": {}}  # 사용 가능한 목소리 (마무리 시그니처 없음)


def voice_of(p):
    return p.voice if p.voice in VOICES else config.SHORTS_VOICE_CHAR


def signature(text, voice=None):
    """마무리 멘트 정리 (시그니처 문구 없이 그대로, '해요잉' 꼬리는 제거)."""
    t = re.sub(r"\s*(해요잉|요잉)[~!.]*$", "", (text or "").strip())
    return t or "솔직히 이건 인정이지"


def has_audio(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                        str(f)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def with_outro(p):
    """대본 끝에 토론 질문 + 마무리 한마디(대중 입장)를 붙인 복사본."""
    p = p.model_copy(deep=True)
    p.outro = config.SHORTS_OUTRO if (config.SHORTS_OUTRO and not p.outro_custom) else signature(p.outro)
    if p.question.strip():  # 토론 유도 질문 (마지막 장면 위에)
        p.beats.append(Beat(narration=p.question.strip(), card=p.question.strip(), twist=True, visual="ai", query="", ai_prompt=""))
    p.beats.append(Beat(narration=p.outro, card=p.outro, visual="ai", query="", ai_prompt="", impact=p.outro_impact))
    return p


def voices(p, work):
    """문장별 음성을 동시에 만든다 (타입캐스트 무료 플랜 동시 2개). p 는 with_outro 를 거친 대본."""
    from concurrent.futures import ThreadPoolExecutor
    n = [b.narration for b in p.beats]
    with ThreadPoolExecutor(max_workers=config.TTS_WORKERS) as ex:
        futs = [ex.submit(tts, t, work / f"a{i}.mp3", n[i - 1] if i else "", n[i + 1] if i + 1 < len(n) else "")
                for i, t in enumerate(n)]
        return [f.result() for f in futs]


def make_video(p, media, work, audios=None, voice_track=None, durations=None, keep_audio=False, bgm_spec=None,
               intro_voice=None):
    """media: 문장별 ("video"|"image", 경로) 또는 None(글자 카드). 마지막에 시그니처 마무리 멘트를 붙인다.
    audios 를 미리 만들어 넘기면 그대로 쓴다 (화면 소재와 동시에 만들어 시간 절약)."""
    from concurrent.futures import ThreadPoolExecutor
    global LAST_BGM, LAST_BGM_CREDIT
    CURRENT_VOICE["name"] = voice_of(p)
    p = with_outro(p)
    last = next((m for m in reversed(list(media)) if m), None)
    media = list(media) + [last] * max(0, len(p.beats) - len(media))  # 질문·마무리는 마지막 장면 그대로
    segs, jobs = [], []
    if voice_track or keep_audio:  # 통 녹음 / 원본 현장음: 장면은 durations 길이로 전환
        audios = [None] * len(p.beats)
    audios = audios or voices(p, work)
    voiced = len(p.beats) if (voice_track or keep_audio) else sum(1 for a in audios if a)
    events, t_beat = [], 0.0  # 효과음 (시각, 종류)
    with Renderer() as r:
        title = r.png(title_html(p), work / "title.png")
        for i, b in enumerate(p.beats):
            audio = audios[i]
            dur = durations[i] if durations else (duration(audio) + 0.05) if audio else max(2.2, len(b.narration) * 0.11)
            parts = [b.narration] if p.caption_style in ("epic", "variety", "meme") else chunks(b.narration)
            total_chars = sum(len(x) for x in parts) or 1
            caps, t = [], 0.0
            twist = getattr(b, "twist", False)
            for j, text in enumerate(parts):
                d = dur * len(text) / total_chars
                caps.append((r.png(caption_html(text, p.caption_style, b.impact, i, getattr(b, "sticker", "")),
                                   work / f"c{i}_{j}.png"), t, t + d))
                events.append((t_beat + t, "ding" if twist and not j else "pop"))  # 자막 뜰 때 '똑' (반전 자막은 '띵')
                t += d
            t_beat += dur
            mi = media[i] if i < len(media) and media[i] else (None, None)
            kind, src = mi[0], mi[1]
            start = mi[2] if len(mi) > 2 else 0.0  # CC 영상은 구간 시작점
            ov = getattr(b, "overlay", "none")
            if ov in ("headline", "comment", "quote", "score", "steam") and b.overlay_text:  # 기사 제목·여론·발언 카드
                bg_src = src if kind == "image" else next((m[1] for m in media if m and m[0] == "image"), None)
                if kind == "video":  # 영상 장면이면 그 장면의 한 프레임을 흐린 배경으로
                    fr = work / f"ovfr{i}.jpg"
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start + 1:.2f}", "-i", str(src),
                                    "-frames:v", "1", str(fr)])
                    bg_src = fr if fr.exists() else bg_src
                bg_uri = ""
                if bg_src:  # 브라우저가 로컬 파일을 못 읽으므로 작게 줄여 data URI 로
                    small = work / f"ovbg{i}.jpg"
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(bg_src), "-vf", "scale=540:-2",
                                    "-q:v", "5", str(small)], check=True)
                    import base64
                    bg_uri = "data:image/jpeg;base64," + base64.b64encode(small.read_bytes()).decode()
                card = r.png(overlay_html(ov, b.overlay_text, b.overlay_source, bg_uri),
                             work / f"ov{i}.png", MEDIA, MEDIA, transparent=False)
                kind, src = "card", card
            cmd = ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}"]
            frames = int(dur * 30) + 1
            if kind == "video":
                cmd += ["-ss", f"{start:.2f}", "-stream_loop", "-1", "-i", src]
                slow = "setpts=1.6*PTS," if b.slowmo else ""
                zoom = (f"scale={int(MEDIA * 1.12)}:{int(MEDIA * 1.12)}:force_original_aspect_ratio=increase,"
                        f"crop={MEDIA}:{MEDIA}," if b.impact else "")
                flash = "fade=t=in:st=0:d=0.35:color=white," if b.impact else ""
                media_f = (f"[1:v]{slow}scale={MEDIA}:{MEDIA}:force_original_aspect_ratio=increase,"
                           f"crop={MEDIA}:{MEDIA},{zoom}{flash}setsar=1,fps=30[m]")
            elif kind == "zzal":  # 짤(일러스트): 흰 바탕 가운데에 통째로, 살짝 통통 튀게
                flat = work / f"zz{i}.jpg"  # 투명 배경 PNG → 흰 바탕으로
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-f", "lavfi", "-i", "color=white:s=64x64",
                                "-filter_complex", "[1][0]scale2ref[b][z];[b][z]overlay=format=auto", "-frames:v", "1",
                                "-q:v", "2", str(flat)], check=True)
                cmd += ["-loop", "1", "-i", flat]
                zz = int(MEDIA * 0.78)
                media_f = (f"[1:v]scale={zz}:{zz}:force_original_aspect_ratio=decrease,"
                           f"pad={MEDIA}:{MEDIA}:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,"
                           f"zoompan=z='1+0.04*abs(sin(on/9))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                           f":d={frames}:s={MEDIA}x{MEDIA}:fps=30[m]")
            elif kind in ("image", "card"):  # 사진: 정사각으로 자르고 천천히 확대/축소 (카드는 글자가 안 잘리게 살짝만)
                cmd += ["-loop", "1", "-i", src]
                zmax, step = (1.04, 0.0006) if kind == "card" else (1.15, 0.0015)
                z = f"min(1.0+on*{step},{zmax})" if i % 2 == 0 else f"max({zmax}-on*{step},1.0)"
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
                cmd += (["-loop", "1", "-t", f"{dur:.3f}", "-i", c] if p.caption_style in ("epic", "variety", "meme") else ["-i", c])
            cmd += (["-i", audio] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            a_idx = 3 + len(caps)
            if keep_audio and kind == "video" and has_audio(src) and (keep_audio != "mixed" or b.orig_audio):  # 원본 소리
                a_idx = 1
                af = ("atempo=0.625," if b.slowmo else "")  # 슬로모션이면 소리도 느리고 낮게
                # 장면이 바뀔 때 소리가 툭 끊기지 않게 앞뒤를 짧게 페이드
                cmd += ["-filter:a", f"{af}afade=t=in:st=0:d=0.12,afade=t=out:st={max(0, dur - 0.2):.2f}:d=0.2"]
            fc = [media_f, f"[0:v][m]overlay=0:{MEDIA_Y}:shortest=1[v0]", "[v0][2:v]overlay=0:0[v1]"]
            last = "v1"
            for j, (_, t0, t1) in enumerate(caps):
                if p.caption_style in ("epic", "variety", "meme"):  # 자막이 부드럽게 나타났다 사라짐
                    fc.append(f"[{3 + j}:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.18:alpha=1,"
                              f"fade=t=out:st={max(t0, t1 - 0.12):.2f}:d=0.12:alpha=1[cf{j}]")
                    fc.append(f"[{last}][cf{j}]overlay=0:0:shortest=1[w{j}]")
                else:
                    fc.append(f"[{last}][{3 + j}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'[w{j}]")
                last = f"w{j}"
            fc.append(f"[{last}]format=yuv420p[vout]")
            seg = work / f"seg{i}.mp4"
            jobs.append([*cmd, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{a_idx}:a",
                         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30",
                         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", seg])
            segs.append(seg)
    # 장면 영상은 CPU 코어 수만큼 동시에 인코딩
    import os
    with ThreadPoolExecutor(max_workers=max(2, os.cpu_count() or 2)) as ex:
        list(ex.map(lambda a: ff(*a), jobs))
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs))
    joined = work / "joined.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    out = work / "shorts.mp4"
    # 오디오 믹스: 음성 + 배경음악(옅게) + 효과음
    inputs, chains, labels = ["-i", joined], [], ["[0:a]"]
    if keep_audio == "mixed" and voice_track:  # 게임 대사(원본) + 더빙(빈 구간) — 둘은 겹치지 않음
        inputs += ["-i", voice_track]
        chains.append("[0:a]loudnorm=I=-14:TP=-1.5,aresample=44100[orig]")
        chains.append("[1:a]loudnorm=I=-14:TP=-1.5,aresample=44100,aformat=channel_layouts=stereo[vo]")
        labels = ["[orig]", "[vo]"]
        voice_track = None
        keep_audio = True
        if bgm_spec:
            inputs += ["-stream_loop", "-1", "-ss", f"{bgm_spec.get('start', 0):.1f}", "-i", bgm_spec["file"]]
            chains.append(f"[2:a]loudnorm=I={bgm_spec.get('lufs', -30)}:TP=-6:LRA=11,aresample=44100,"
                          f"aformat=channel_layouts=stereo,afade=t=in:d=0.8[bg]")
            labels.append("[bg]")
            LAST_BGM, LAST_BGM_CREDIT = Path(bgm_spec["file"]).name, bgm_spec.get("credit")
            bgm_spec = None
        mixed_done = True
    else:
        mixed_done = False
    if keep_audio and not mixed_done:  # 현장음 크기 맞추기
        chains.append("[0:a]loudnorm=I=-14:TP=-1.5,aresample=44100,asplit=2[orig][key]")
        labels = ["[orig]"]
        if bgm_spec:  # 옅은 배경음악 + 현장음이 클 때 자동으로 더 줄이기(사이드체인 덕킹)
            inputs += ["-ss", f"{bgm_spec.get('start', 0):.1f}", "-i", bgm_spec["file"]]
            chains.append(f"[1:a]loudnorm=I={bgm_spec.get('lufs', -24)}:TP=-6:LRA=11,aresample=44100,"
                          f"aformat=channel_layouts=stereo,afade=t=in:d=0.8[bgraw]")
            chains.append("[bgraw][key]sidechaincompress=threshold=0.03:ratio=12:attack=30:release=500[bg]")
            labels.append("[bg]")
            LAST_BGM, LAST_BGM_CREDIT = Path(bgm_spec["file"]).name, bgm_spec.get("credit")
        else:
            chains[-1] = chains[-1].replace(",asplit=2[orig][key]", "[orig]")
        if intro_voice:  # 첫 장면에만 더빙: 목소리가 나오는 동안 현장음을 자동으로 줄임
            vi = len([a for a in inputs if a == "-i"])
            inputs += ["-i", str(intro_voice)]
            chains.append(f"[{vi}:a]loudnorm=I=-14:TP=-1.5,aresample=44100,aformat=channel_layouts=stereo,asplit=2[vo][vkey]")
            chains.append("[orig][vkey]sidechaincompress=threshold=0.02:ratio=10:attack=10:release=300[origd]")
            labels = ["[origd]", "[vo]"] + labels[1:]
    if voice_track and not mixed_done:  # 장면 음성(무음) 대신 통 녹음을 목소리로
        inputs += ["-i", voice_track]
        chains.append("[1:a]loudnorm=I=-14:TP=-1.5,aresample=44100,aformat=channel_layouts=stereo[vo]")
        labels = ["[vo]"]
    from . import music
    k = 2 if (voice_track or (keep_audio and bgm_spec)) else 1
    if keep_audio:
        bgm = None
    else:
        bgm, LAST_BGM_CREDIT = music.pick(work) if config.SHORTS_BGM else (None, "NONE")  # 배경음악 꺼져 있으면 없음
    if keep_audio:
        pass
    elif LAST_BGM_CREDIT == "NONE":  # 즐겨찾기만 쓰기로 했는데 못 받은 경우
        LAST_BGM_CREDIT = None
    elif not bgm:
        bgms = sorted(f for ext in ("*.mp3", "*.wav", "*.m4a") for f in (config.ROOT / "assets" / "bgm").glob(ext))
        bgm = random.choice(bgms) if bgms else None
    if bgm:
        LAST_BGM = bgm.name
        bl = duration(bgm)
        off = random.uniform(bl * 0.15, bl * 0.45) if bl > 60 else 0  # 긴 곡은 인트로를 건너뛰고 신나는 부분부터
        inputs += ["-stream_loop", "-1", "-ss", f"{off:.1f}", "-i", bgm]
        # 곡마다 음량이 달라서 먼저 일정한 크기(-30 LUFS)로 맞춘 뒤 목소리 아래로 옅게 깐다
        chains.append(f"[{k}:a]loudnorm=I={config.SHORTS_BGM_LUFS}:TP=-6:LRA=11,aresample=44100,afade=t=in:d=0.3[bg]")
        labels.append("[bg]")
        k += 1
    sfx_dir = config.ROOT / "assets" / "sfx"
    vol = {"pop": config.SHORTS_SFX_VOLUME, "whoosh": config.SHORTS_SFX_VOLUME * 0.8, "ding": config.SHORTS_SFX_VOLUME}
    for j, (at, kind) in enumerate(events if config.SHORTS_SFX else []):
        f = sfx_dir / f"{kind}.wav"
        if not f.exists():
            continue
        inputs += ["-i", f]
        ms = int(at * 1000)
        chains.append(f"[{k}:a]adelay={ms}|{ms},volume={vol[kind]}[s{j}]")
        labels.append(f"[s{j}]")
        k += 1
    if len(labels) > 1 or voice_track or keep_audio:
        chains.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0:normalize=0[a]"
                      if len(labels) > 1 else f"{labels[0]}anull[a]")
        ff(*inputs, "-filter_complex", ";".join(chains), "-map", "0:v", "-map", "[a]", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out)
    else:
        ff("-i", joined, "-c", "copy", "-movflags", "+faststart", out)
    return out, voiced


# ---------- 화면 소재 모으기 ----------
def gather_media(p, work):
    """문장별 화면: 첫 문장은 AI 영상(가능하면), 'ai' 는 AI 이미지, 'photo' 는 무료 실사 사진. 없으면 대체.
    (media 목록, 사진 출처 목록, 비용)"""
    from . import gpt_image, higgsfield, photos
    media, credits, used, cost = [None] * len(p.beats), [], set(), 0.0
    if gpt_image.enabled():  # 1순위: GPT 이미지
        ai_idx = list(range(len(p.beats)))  # 뉴스·실사 사진 없이 모든 장면을 GPT 이미지로
        prompts = [f"{p.beats[i].ai_prompt}. The protagonist: {p.character}. Photorealistic candid photo, natural light, "
                   f"shallow depth of field, Korean context if relevant. No readable text, no logos, no watermark"
                   for i in ai_idx]
        files, c = gpt_image.make_images(prompts, work)
        cost += c
        for i, f in zip(ai_idx, files):
            if f:
                media[i] = ("image", f)
        print(f"[shorts] GPT 이미지 {sum(1 for f in files if f)}/{len(files)}장, 약 ${c:.2f}")
    elif higgsfield.enabled():
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
    if gpt_image.enabled():  # 실패한 장면은 한 번 더 시도 → 그래도 없으면 옆 장면 이미지 재사용
        miss = [i for i in range(len(p.beats)) if not media[i]]
        if miss:
            files, c = gpt_image.make_images([f"{p.beats[i].ai_prompt}. Photorealistic candid photo, no text" for i in miss], work)
            cost += c
            for i, f in zip(miss, files):
                if f:
                    media[i] = ("image", f)
        for i in range(len(p.beats)):
            if not media[i]:
                media[i] = next((media[j] for j in (i - 1, i + 1, 0) if 0 <= j < len(media) and media[j]), None)
    for i, b in enumerate(p.beats):
        if media[i] or not config.SHORTS_PHOTOS:
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
             f"Characters casted: {config.TYPECAST_VOICE_NAME} https://typecast.ai") if config.TYPECAST_CREDIT else ""
    music = f"\n\n{music_credit()}" if music_credit() else ""
    return (f"{p.description}\n\n출처\n{src}{photo}\n\n※ 일부 장면은 AI로 만든 이미지예요.{voice}{music}\n\n{tags} #shorts")


def upload_youtube(video, p, credits=()):
    if not (config.UPLOAD_POST_API_KEY and config.UPLOAD_POST_USER):
        return None
    with open(video, "rb") as f:
        r = requests.post(
            "https://api.upload-post.com/api/upload",
            headers={"Authorization": f"Apikey {config.UPLOAD_POST_API_KEY}",
                     "Idempotency-Key": "shorts-" + __import__("hashlib").md5(p.yt_title.encode()).hexdigest()[:16]
                     + now().strftime("%Y%m%d")},
            data=[("user", config.UPLOAD_POST_USER), ("platform[]", "youtube"),
                  ("title", p.yt_title[:100]), ("youtube_title", p.yt_title[:100]),
                  ("youtube_description", full_description(p, credits)[:4900]),
                  *[("tags[]", t) for t in p.tags[:8]],
                  ("privacyStatus", config.SHORTS_PRIVACY), ("selfDeclaredMadeForKids", "false"),
                  ("containsSyntheticMedia", "true"), ("defaultLanguage", "ko"), ("defaultAudioLanguage", "ko"),
                  ("categoryId", "24"), ("async_upload", "true"),
                  *([("first_comment", f"{p.question.strip()} 👇 댓글로 의견 남겨줘요!")] if p.question.strip() else [])],
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


def has_image_source():
    from . import gpt_image, higgsfield
    return gpt_image.enabled() or higgsfield.enabled() or config.SHORTS_PHOTOS


def due(st):
    ss = load_ss()
    if st.get("paused") or config.SHORTS_PER_DAY <= 0:
        return False
    if not has_image_source():  # 이미지 만들 수단이 없으면 글자 카드 영상이 올라가므로 자동 제작 안 함
        print("[shorts] 이미지 생성 키(OPENAI_API_KEY/HIGGSFIELD_KEY)가 없어 자동 제작을 쉽니다")
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
        voice = pick_voice(st, ss)
        p, cost = plan_short(ss, voice)
        p.voice = voice
        print(f"[shorts] 주제: {p.topic} / 문장 {len(p.beats)} / AI컷 {sum(b.visual == 'ai' for b in p.beats)}")
        if PICKED.get("line"):
            pipeline.notify(st, "🎬 오늘의 숏츠 주제\n" + PICKED["line"][:600])
        import time
        from concurrent.futures import ThreadPoolExecutor
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=2) as ex:  # 화면 소재와 더빙을 동시에
            f_media = ex.submit(gather_media, p, work)
            f_voice = ex.submit(voices, with_outro(p), work)
            media, credits, cost2 = f_media.result()
            audios = f_voice.result()
        cost += cost2
        ss.setdefault("cost", {})[month] = round(ss.get("cost", {}).get(month, 0) + cost, 4)
        video, voiced = make_video(p, media, work, audios)
        print(f"[shorts] 완성 {duration(video):.1f}초, 음성 {voiced}/{len(p.beats) + 1}, 소재+더빙+렌더 {time.time() - t0:.0f}초")
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


def render_mixed(p, raw, d, media, work, voice):
    """원본 대사 장면 + 더빙 장면을 섞는다. 더빙은 원본 대사가 없는 장면에만 들어간다."""
    beats = with_outro(p).beats
    voiced_idx = [i for i, b in enumerate(beats) if not b.orig_audio]
    texts = [beats[i].narration for i in voiced_idx]
    if voice:  # 사용자가 녹음한 더빙 (더빙 문장만, 1.0배속) → 1.4배속
        fast = speed_up(voice, work)
    else:  # 임시 음성: 문장마다 만들어 0.35초 간격으로 이어붙임
        parts = [tts(t, work / f"mx{i}.mp3") for i, t in enumerate(texts)]
        lst = work / "mx.txt"
        gap = work / "gap.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.35", gap)
        lst.write_text("".join(f"file '{f}'\nfile '{gap}'\n" for f in parts if f))
        raw_all = work / "mx_all.wav"
        ff("-f", "concat", "-safe", "0", "-i", lst, "-ar", "44100", "-ac", "1", raw_all)
        fast = speed_up(raw_all, work)  # 실제 녹음과 같은 배속으로 맞춰 길이를 미리 확인
    vd = split_voice(fast, len(texts), work, texts)
    bounds = [0.0]
    for x_ in vd:
        bounds.append(bounds[-1] + x_)
    plan_d = list(raw.get("durations") or [0] * len(beats))
    durs, pieces, k = [], [], 0
    for i, b in enumerate(beats):
        if b.orig_audio:
            dur = float(plan_d[i])
            f = work / f"sil{i}.wav"
            ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{dur:.3f}", f)
        else:
            dur = vd[k]
            f = work / f"vp{i}.wav"
            ff("-i", fast, "-ss", f"{bounds[k]:.3f}", "-to", f"{bounds[k + 1]:.3f}", "-ar", "44100", "-ac", "1", f)
            k += 1
        durs.append(round(dur, 3))
        pieces.append(f)
    lst = work / "vtrack.txt"
    lst.write_text("".join(f"file '{f}'\n" for f in pieces))
    track = work / "vtrack.wav"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-ar", "44100", "-ac", "1", track)
    spec = raw.get("bgm")
    if spec:
        spec = {**spec, "file": str(d / spec["file"])}
    print(f"[mixed] 장면 길이 {durs} (합계 {sum(durs):.1f}초)")
    return make_video(p, media, work, durations=durs, keep_audio="mixed", voice_track=track, bgm_spec=spec)


def render_sample(folder):
    """assets/samples/<이름>/plan.json + img0.jpg… 로 영상만 만들어 텔레그램으로 보냄 (업로드 안 함)."""
    import json
    from . import pipeline
    d = config.ROOT / folder if not Path(folder).is_absolute() else Path(folder)
    raw = json.loads((d / "plan.json").read_text("utf-8"))
    p = Plan(**raw)
    if raw.get("media"):  # 장면별 소재 지정: {"video": "clip0.mp4", "start": 0} / {"image": "img3.jpg"}
        media = [("video", d / m["video"], float(m.get("start", 0))) if "video" in m
                 else ("zzal", d / m["zzal"]) if "zzal" in m else ("image", d / m["image"]) for m in raw["media"]]
    else:  # imgN.jpg (AI·사진) 또는 zN.png (짤: 이라스토야 등 일러스트)
        media = [("zzal", z) if (z := d / f"z{i}.png").exists() else ("image", f) if (f := d / f"img{i}.jpg").exists()
                 else None for i in range(len(p.beats))]
    work = Path(tempfile.mkdtemp(prefix="sample-"))
    audios = None
    voice = next((d / f"voice.{ext}" for ext in ("mp3", "wav", "m4a", "mp4") if (d / f"voice.{ext}").exists()), None)
    if raw.get("mixed_audio"):  # 게임 대사 장면(orig_audio)은 원본 소리, 나머지는 더빙
        video, voiced = render_mixed(p, raw, d, media, work, voice)
    elif raw.get("keep_audio"):  # 더빙 없이 원본 현장음 + 자막만 (장면 길이는 durations)
        spec = raw.get("bgm")
        if spec:
            spec = {**spec, "file": str(d / spec["file"])}
        durs = list(raw["durations"])
        intro = None
        if raw.get("intro_voice"):  # 첫 장면만 더빙: voice.mp3(첫 문장 녹음) → 없으면 임시 음성
            intro = voice or tts(p.beats[0].narration, work / "intro.mp3")
            if intro and voice:
                intro = speed_up(intro, work)
            if intro and not durs[0]:
                durs[0] = round(duration(intro) + 0.35, 2)
        video, voiced = make_video(p, media, work, durations=durs, keep_audio=True, bgm_spec=spec, intro_voice=intro)
    elif voice:  # 타입캐스트 웹에서 직접 만든 더빙 (반자동, 1.0배속으로 받아서 여기서 1.2배속)
        texts = [b.narration for b in with_outro(p).beats]
        fast = speed_up(voice, work)
        durs = split_voice(fast, len(texts), work, texts)
        video, voiced = make_video(p, media, work, voice_track=fast, durations=durs)
    elif True:
        video, voiced = make_video(p, media, work, audios)
    out = config.ROOT / "shorts_sample.mp4"
    shutil.copy(video, out)
    from . import typecast
    n_tc = ENGINES.count("typecast")
    voice = (f"타입캐스트 {config.TYPECAST_VOICE_NAME} {n_tc}/{len(p.beats) + 1}문장" if n_tc else "무료 음성") + \
        ("" if typecast.enabled() else " (타입캐스트 키 없음)")
    print(f"[sample] {duration(out):.1f}초, 음성 {voiced}/{len(p.beats) + 1} ({voice})")
    # 테스트 영상은 텔레그램으로 보내지 않음 (작업 채팅에서 먼저 확인)


def upload_file(video, plan_json, music_credit_text=""):
    """완성된 영상 파일을 그대로 유튜브에 올림 (Upload-Post). 업로드 결과 URL 을 기다렸다가 출력·알림."""
    import json
    import time
    from . import pipeline
    global LAST_BGM_CREDIT
    p = Plan(**json.loads(Path(plan_json).read_text("utf-8")))
    LAST_BGM_CREDIT = music_credit_text or None
    print(full_description(p))
    res = upload_youtube(Path(video), p)
    if res is None:
        raise RuntimeError("Upload-Post 키(UPLOAD_POST_API_KEY/UPLOAD_POST_USER)가 없어요")
    print("[upload] 응답:", json.dumps(res, ensure_ascii=False)[:500])
    url, rid = None, res.get("request_id")
    for _ in range(36):  # 최대 6분 기다림
        if not rid:
            break
        time.sleep(10)
        s = requests.get("https://api.upload-post.com/api/uploadposts/status", params={"request_id": rid},
                         headers={"Authorization": f"Apikey {config.UPLOAD_POST_API_KEY}"}, timeout=30).json()
        print("[upload] 상태:", s.get("status"))
        for r in s.get("results") or []:
            url = url or r.get("url") or r.get("post_url")
        if s.get("status") in ("completed", "failed"):
            print("[upload] 결과:", json.dumps(s, ensure_ascii=False)[:800])
            break
    st = pipeline.load_state()
    pipeline.notify(st, f"🎬 유튜브 업로드: {p.yt_title}\n{url or '처리 중 (유튜브 스튜디오에서 확인)'}")
    print("[upload] URL:", url)


def speed_up(voice, work, tempo=None):
    """목소리 높낮이는 그대로, 속도만 올림 (기본 1.2배)."""
    tempo = tempo or config.VOICE_FILE_TEMPO
    if duration(voice) / tempo > config.SHORTS_MAX_SECONDS:  # 최대 길이를 넘으면 더 빠르게
        tempo = round(duration(voice) / config.SHORTS_MAX_SECONDS, 3)
        print(f"[voice] {config.SHORTS_MAX_SECONDS}초 제한 → {tempo}배속으로 조정")
    out = work / "voice_fast.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-vn", "-af", f"atempo={tempo}",
                    "-ar", "44100", "-ac", "2", str(out)], check=True)
    print(f"[voice] {tempo}배속: {duration(voice):.1f}초 → {duration(out):.1f}초")
    return out


def split_voice(voice, n, work, texts=None):
    """타입캐스트 웹에서 받은 통 녹음을 문장 사이 쉼(무음) 기준으로 n 조각으로 자른다.
    문장 안에도 짧은 쉼이 있으므로, 글자 수 비율로 예상한 경계 위치에 가장 가까운(그리고 긴) 쉼을 고른다."""
    r = subprocess.run(["ffmpeg", "-i", str(voice), "-af", "silencedetect=noise=-38dB:d=0.15", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    total = duration(voice)
    gaps = [((s_ + e) / 2, e - s_) for s_, e in zip(starts, ends) if 0.3 < (s_ + e) / 2 < total - 0.3]
    lens = [len(re.sub(r"\s", "", t)) for t in texts] if texts and len(texts) == n else [1] * n
    head = ends[0] if starts and starts[0] < 0.05 else 0.0
    tail = starts[-1] if ends and ends[-1] > total - 0.05 else total
    speech = tail - head
    cuts, prev = [], 0.0
    for k in range(1, n):
        expect = head + speech * sum(lens[:k]) / sum(lens)
        cand = [(abs(m - expect) - 0.8 * g, m) for m, g in gaps if m > prev + 0.4]
        if not cand:
            break
        _, best = min(cand)
        cuts.append(best)
        prev = best
    if len(cuts) < n - 1:
        raise RuntimeError(f"문장 경계를 {len(cuts) + 1}개만 찾았어요 (필요 {n}개). 대본을 한 줄에 한 문장으로 넣어주세요.")
    bounds = [0.0] + cuts + [total]
    durs = [bounds[i + 1] - bounds[i] for i in range(n)]
    print(f"[voice] 통 녹음 {total:.1f}초 → 문장 {n}개 경계: {[round(c, 2) for c in cuts]}")
    return durs  # 녹음은 자르지 않음 (자르면 말끝이 끊김) — 화면·자막 전환 타이밍으로만 사용
