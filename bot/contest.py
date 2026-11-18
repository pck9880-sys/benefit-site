"""공모전 출품안 자동 생성.

콘테스트코리아(robots.txt 허용)의 네이밍·슬로건 / 아이디어 공모전을 하루 1번 확인해서
- 접수 중 · 무료 · 온라인 접수 · 일반인 참가 가능한 것만 고르고
- AI 사용 금지 문구가 있는 공모전은 건너뛰고
- Claude가 출품안 후보를 만들어 텔레그램으로 보냅니다.
제출은 사용자가 직접 합니다 (공모전 사이트 자동 제출은 하지 않음).
"""
import html
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List

import requests
from pydantic import BaseModel, Field

from . import config, telegram

KST = timezone(timedelta(hours=9))
BASE = "https://www.contestkorea.com/sub"
UA = {"User-Agent": "Mozilla/5.0 (compatible; contest-helper/1.0)"}
CATEGORIES = {
    "030210001": "네이밍·슬로건",
    "031410001": "아이디어·창업",
}
# 개인 경험을 지어내야 하거나, AI로 만들기 부적절한 유형은 제외
EXCLUDE_WORDS = ["해커톤", "솔버톤", "수기", "체험담", "사연", "사진", "영상", "UCC", "웹툰", "그림", "포스터", "디자인", "캐릭터",
                 "논문", "시나리오", "소설", "시 공모", "작곡", "노래", "건축", "콩쿠르", "오디션", "유료"]
AI_BAN = re.compile(r"(AI|인공지능|생성형|챗GPT|ChatGPT|GPT)[^.\n]{0,40}(금지|불가|제한|실격|허용하지|사용할 수 없|취소)")


def now():
    return datetime.now(KST)


def _get(url):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    time.sleep(1.5)  # 사이트에 부담 주지 않도록 천천히
    return r.text


def _text(fragment):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"[ \t ]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def list_ids(code):
    page = _get(f"{BASE}/list.php?int_gbn=1&Txt_bcode={code}")
    return list(dict.fromkeys(re.findall(rf"view\.php\?int_gbn=1&Txt_bcode={code}&str_no=(\d+)", page)))


def _field(text, label, stop_labels):
    m = re.search(rf"{label}\s*\n(.*?)\n(?:{'|'.join(stop_labels)})", text, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def fetch_detail(code, sid):
    url = f"{BASE}/view.php?int_gbn=1&Txt_bcode={code}&str_no={sid}"
    raw = _get(url)
    text = _text(raw)
    labels = ["대표분야", "참가대상", "접수기간", "심사기간", "대회지역", "시상내역", "홈페이지", "접수방법", "참가비용", "콘코 SNS"]
    title_m = re.search(r'<meta property="og:title" content="([^"]+)"', raw)
    detail_m = (re.search(r"\n\s*공모명\s*\n(.*?)\n\s*본 게시물은", text, re.S)
                or re.search(r"\n\s*세부요강\s*\n(.*?)\n\s*본 게시물은", text, re.S))
    home_m = re.search(r'href="(https?://[^"]+)"[^>]*class="homepage_go"', raw)
    d = {
        "id": sid, "code": code, "category": CATEGORIES.get(code, ""), "url": url,
        "title": html.unescape(title_m.group(1)).strip() if title_m else _field(text, "전체", ["//-->"]),
        "organizer": _field(text, r"주최 \. 주관", labels),
        "target": _field(text, "참가대상", labels),
        "period": _field(text, "접수기간", labels),
        "prize": _field(text, "시상내역", labels),
        "method": _field(text, "접수방법", labels),
        "fee": _field(text, "참가비용", labels),
        "home": html.unescape(home_m.group(1)) if home_m else "",
        "detail": (detail_m.group(1).strip() if detail_m else "")[:3500],
    }
    m = re.search(r"(\d{4})\.(\d{2})\.(\d{2})\s*~\s*(\d{4})\.(\d{2})\.(\d{2})", d["period"])
    d["deadline"] = f"{m.group(4)}-{m.group(5)}-{m.group(6)}" if m else ""
    return d


def eligible(d):
    """자동 출품안을 만들어도 되는 공모전인지 판단. (통과 여부, 이유)"""
    title = d["title"]
    if not d["detail"]:
        return False, "세부요강 없음"
    if any(w in title for w in ["수기", "체험담", "사연", "유료"]):
        return False, "개인 경험이 필요한 유형"
    wordish = any(w in title for w in ["네이밍", "슬로건", "표어", "명칭", "이름", "캐치프레이즈", "아이디어", "제안", "글귀", "문구"])
    if not wordish and any(w in title for w in EXCLUDE_WORDS):
        return False, "제외 유형"
    if "무료" not in d["fee"]:
        return False, "유료 접수"
    if d["target"] and not any(w in d["target"] for w in ["누구나", "일반인", "제한없음", "국민"]):
        return False, "일반인 참가 불가"
    if "온라인" not in d["method"] and "이메일" not in d["method"] and "e-mail" not in d["method"].lower():
        return False, "온라인 접수 아님"
    if not d["deadline"]:
        return False, "마감일 불명"
    days = (datetime.fromisoformat(d["deadline"]).date() - now().date()).days
    if days < 2:
        return False, "마감 임박"
    if AI_BAN.search(d["detail"]):
        return False, "AI 사용 금지"
    return True, f"D-{days}"


def prize_value(d):
    """정렬용: 시상내역에서 가장 큰 금액(만원)."""
    nums = [int(x.replace(",", "")) for x in re.findall(r"([\d,]+)\s*만\s*원", d["prize"] + d["detail"])]
    return max(nums) if nums else 0


# ---------- Claude ----------
class Entry(BaseModel):
    text: str = Field(description="출품작 본문 (슬로건/네이밍/아이디어 제목 등)")
    explanation: str = Field(description="작품 설명. 공고에 설명 분량 제한이 있으면 그 안으로")
    why: str = Field(description="심사위원에게 어필할 포인트 한 줄")


class Ideas(BaseModel):
    format_rules: str = Field(description="공고에서 찾은 제출 형식·글자수·개수 제한 요약. 없으면 '명시 없음'")
    ai_policy: str = Field(description="공고의 AI 사용 관련 규정 요약. 언급이 없으면 '언급 없음'")
    entries: List[Entry] = Field(description="서로 다른 방향의 출품안 5개")
    tip: str = Field(description="제출 전에 사람이 꼭 확인할 점 한 줄")


SYSTEM = """당신은 공모전 수상 경험이 많은 카피라이터입니다. 한국어 공모전 공고를 읽고 출품안 후보를 만듭니다.

규칙:
- 공고의 주제, 글자 수, 형식 제한을 반드시 지킵니다. 글자 수 제한이 있으면 직접 세어서 확인합니다.
- 기존 유명 슬로건·상표·다른 수상작을 베끼지 않습니다. 실존 브랜드명을 쓰지 않습니다.
- 다섯 개 후보는 서로 다른 방향(감성/직관/언어유희/지역성/미래지향 등)으로 만듭니다.
- 사실을 지어내지 않습니다. 공고에 없는 정보는 추측하지 않습니다."""


def make_ideas(d):
    if config.MOCK or not config.ANTHROPIC_API_KEY:
        return Ideas(format_rules="(테스트)", ai_policy="언급 없음",
                     entries=[Entry(text=f"테스트 출품안 {i}", explanation="설명", why="포인트") for i in range(1, 6)],
                     tip="공고 확인"), 0.0
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    info = f"공모전: {d['title']}\n주최: {d['organizer']}\n분야: {d['category']}\n시상: {d['prize']}\n\n[세부요강]\n{d['detail']}"
    res = client.messages.parse(
        model=config.CLAUDE_MODEL, max_tokens=8000, system=SYSTEM,
        output_config={"effort": "medium"}, output_format=Ideas,
        messages=[{"role": "user", "content": info}],
    )
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"출품안 생성 실패 (stop_reason={res.stop_reason})")
    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    return res.parsed_output, (res.usage.input_tokens * pin + res.usage.output_tokens * pout) / 1_000_000


def _len_ko(s):
    return len(re.sub(r"[\s\.,!?~'\"“”‘’·…\-]", "", s))


def format_message(d, ideas, cost):
    lines = [f"🏆 {d['title']}", f"주최: {d['organizer']} · 참가대상: {d['target'][:40]}", f"마감: {d['deadline']} · 시상: {d['prize'][:60]}",
             f"형식: {ideas.format_rules}", f"AI 규정: {ideas.ai_policy}", ""]
    for i, e in enumerate(ideas.entries, 1):
        lines.append(f"{i}) {e.text}  ({_len_ko(e.text)}자, 공백·부호 제외)")
        lines.append(f"   └ {e.why}")
    lines += ["", f"📝 1번 작품설명 예시: {ideas.entries[0].explanation}" if ideas.entries else "",
              "", f"⚠️ {ideas.tip}", "제출 전 공고의 AI 사용 규정과 1인 접수 개수를 꼭 확인하세요.",
              f"공고: {d['url']}"]
    if d["home"]:
        lines.append(f"주최사 공고: {d['home']}")
    lines.append(f"(생성 비용 ${cost:.3f})")
    return "\n".join(lines)


def should_run(st):
    if st.get("contest_off") or st.get("paused"):
        return False
    if st.get("contest_force") or st.get("contest_retry"):
        return True
    t = now()
    return t.hour >= config.CONTEST_HOUR_KST and st.get("contest_last_date") != t.strftime("%Y-%m-%d")


def run(st, notify):
    st.setdefault("contest_seen", [])
    if config.MOCK and not os.environ.get("CONTEST_TEST"):
        return  # 일반 테스트에서는 외부 사이트에 접속하지 않음
    if not (config.MOCK or config.ANTHROPIC_API_KEY) or not should_run(st):
        return
    if not (config.MOCK or st.get("owner_chat_id")):
        return  # 받을 사람이 없으면 생성하지 않음
    month = now().strftime("%Y-%m")
    if st.get("cost", {}).get(month, 0) >= config.MAX_MONTHLY_USD:
        return
    st["contest_force"] = False
    seen = set(st["contest_seen"])
    candidates = []
    for code in CATEGORIES:
        try:
            ids = list_ids(code)
        except requests.RequestException as e:
            print(f"[contest] 목록 실패 {code}: {e}")
            continue
        for sid in ids:
            if sid in seen:
                continue
            seen.add(sid)
            st["contest_seen"].append(sid)
            try:
                d = fetch_detail(code, sid)
            except requests.RequestException as e:
                print(f"[contest] 상세 실패 {sid}: {e}")
                continue
            ok, why = eligible(d)
            print(f"[contest] {sid} {d['title'][:30]} → {why}")
            if ok:
                candidates.append(d)
    candidates = st.pop("contest_retry", []) + candidates
    st["contest_last_date"] = now().strftime("%Y-%m-%d")
    st["contest_seen"] = st["contest_seen"][-1000:]
    candidates.sort(key=prize_value, reverse=True)
    sent = 0
    for d in candidates[:config.CONTESTS_PER_DAY]:
        try:
            ideas, cost = make_ideas(d)
        except Exception as e:
            print(f"[contest] 생성 실패 {d['id']}: {e}")
            st["contest_last_error"] = f"{type(e).__name__}: {str(e)[:400]}"
            continue
        st.setdefault("cost", {})[month] = round(st["cost"].get(month, 0) + cost, 5)
        msg = format_message(d, ideas, cost)
        if config.MOCK:
            print(msg)
        else:
            notify(st, msg)
        sent += 1
    print(f"[contest] 후보 {len(candidates)}개 중 {sent}개 전송")
    if not config.MOCK:
        if candidates and sent == 0:
            st["contest_retry"] = candidates[:config.CONTESTS_PER_DAY]  # 다음 실행 때 다시 시도
            notify(st, "⚠️ 공모전 출품안 생성 중 오류가 나서 다음 실행 때 다시 시도합니다.\n" + st.get("contest_last_error", ""))
        elif not candidates:
            notify(st, "🏆 오늘은 조건에 맞는 새 공모전이 없어요.")
