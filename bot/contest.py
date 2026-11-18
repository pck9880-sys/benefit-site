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
    "030210001": "네이밍·슬로건",  # 문구와 짧은 설명만으로 제출이 끝나는 분야만
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
WEB_SEARCH_USD = 0.01  # 웹 검색 1회 비용 (1,000회당 $10)


class Candidate(BaseModel):
    text: str = Field(description="출품작 본문 (슬로건/네이밍 등). 공고의 글자 수 제한 준수")
    angle: str = Field(description="방향: 감성/직관/언어유희/지역·역사성/미래지향 중 하나 또는 그 외")
    explanation: str = Field(description="제출용 작품 설명. 공고의 설명 분량 제한 안에서, 주제 키워드와 연결해 논리적으로")
    fit: int = Field(description="주제적합도·대표성 1~5")
    originality: int = Field(description="창의성·독창성 1~5")
    symbolism: int = Field(description="상징성·함축성 1~5")
    memorability: int = Field(description="대중성·전달성 1~5")
    usability: int = Field(description="활용성 1~5")
    why: str = Field(description="어떤 심사 기준을 노렸는지 한 줄")


class Package(BaseModel):
    keywords: List[str] = Field(description="공고에서 뽑은 핵심 키워드 3~6개")
    format_rules: str = Field(description="제출물 형식·글자 수·설명 분량 제한 요약 (공고 기준)")
    per_person_limit: str = Field(description="1인 접수 가능 개수 (없으면 '명시 없음')")
    ai_policy: str = Field(description="AI 사용 관련 규정 (없으면 '언급 없음')")
    submit_method: str = Field(description="접수 방법: 온라인 폼/이메일/홈페이지 게시판/우편 등과 접수처(URL·이메일 주소)")
    required_docs: List[str] = Field(description="제출해야 하는 서류·파일 목록 (신청서, 개인정보 동의서 등)")
    personal_fields: List[str] = Field(description="응모자가 직접 입력해야 할 개인정보 항목")
    email_template: str = Field(description="이메일 접수일 때 제목과 본문 틀 (개인정보는 [이름] 같은 자리표시자). 이메일 접수가 아니면 빈 문자열")
    announce: str = Field(description="발표일·발표 방법 (없으면 '명시 없음')")
    text_only: bool = Field(description="출품작 문구와 짧은 작품설명만으로 제출이 끝나면 true. 제안서·기획서·이미지·영상·별도 파일 작성이 필요하면 false")
    candidates: List[Candidate] = Field(description="서로 다른 방향의 후보 12개 (자체 채점 포함)")
    caution: str = Field(description="제출 전에 사람이 꼭 확인할 점 한 줄")


SYSTEM = """당신은 공모전 수상 경험이 많은 카피라이터입니다. 한국어 공모전 공고와 사전 조사 자료를 읽고 출품안과 제출 패키지를 만듭니다.

심사에서 흔히 보는 기준에 맞춰 만듭니다:
- 주제적합도·대표성: 공고가 말한 정체성·비전·특성을 정확히 담는다 (공고의 핵심 키워드를 먼저 뽑는다)
- 창의성·독창성: 흔한 단어 조합("함께하는", "더 나은", "행복한 ○○")을 피하고 새 표현을 찾는다
- 상징성·함축성: 짧지만 여러 의미가 겹쳐 읽히게 한다 (지명·행사명·핵심 가치를 엮는 언어유희 등)
- 대중성·전달성: 한 번 들으면 기억나고 소리 내어 읽기 쉽다 (리듬, 대구, 운율)
- 활용성: 현수막·로고·홍보물에 바로 쓸 수 있게 짧고 단단하게

결격 사유는 반드시 피합니다:
- 조사 자료에 나온 기존 슬로건·이전 수상작·광고 문구·상표와 같거나 비슷한 표현
- 실존 브랜드명, 정치적·종교적 편향, 특정 집단 비하
- 공고의 글자 수·형식 제한 위반 (직접 세어서 확인)

후보 12개는 서로 다른 방향으로 만들고, 각 항목을 엄격하게 채점합니다 (뻔한 표현은 독창성 2 이하).
조사 자료의 사실(역사, 지역 특색, 기관 비전)을 활용하되, 자료와 공고에 없는 사실은 지어내지 않습니다."""


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)


def _cost(usage):
    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    c = (usage.input_tokens * pin + usage.output_tokens * pout) / 1_000_000
    stu = getattr(usage, "server_tool_use", None)
    if stu is not None:
        c += (getattr(stu, "web_search_requests", 0) or 0) * WEB_SEARCH_USD
    return c


def _search_call(prompt, max_uses):
    """웹 검색을 쓰는 호출. (텍스트, 비용)"""
    client = _client()
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}]
    messages = [{"role": "user", "content": prompt}]
    cost, res = 0.0, None
    for _ in range(4):  # pause_turn 이어받기
        res = client.messages.create(model=config.CLAUDE_MODEL, max_tokens=6000, tools=tools,
                                     output_config={"effort": "medium"}, messages=messages)
        cost += _cost(res.usage)
        if res.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": res.content}]
    text = "\n".join(b.text for b in res.content if getattr(b, "type", "") == "text").strip()
    return text, cost


def research(d):
    prompt = f"""다음 공모전의 출품작을 만들기 전에 웹 검색으로 사전 조사를 해주세요.

공모전: {d['title']} / 주최: {d['organizer']}
공고 요약: {d['detail'][:1500]}

조사할 것:
1. 주최 기관·행사·지역의 배경 (역사, 특색, 비전, 최근 이슈) - 출품작에 녹일 수 있는 구체적 사실
2. 이 기관·행사가 예전에 썼던 슬로건이나 이전 회차 수상작 (겹치면 안 되므로)
3. 비슷한 공모전의 최근 수상작 경향

결과는 한국어로 간결하게:
[배경 사실] 5~8줄
[기존 슬로건·이전 수상작] 찾은 것 그대로 나열 (없으면 '찾지 못함')
[수상작 경향] 2~3줄
[출처] 참고한 URL 3~5개"""
    return _search_call(prompt, 5)


def generate(d, notes):
    client = _client()
    info = (f"공모전: {d['title']}\n주최: {d['organizer']}\n분야: {d['category']}\n시상: {d['prize']}\n"
            f"접수기간: {d['period']}\n접수방법(사이트 표기): {d['method']}\n\n[세부요강]\n{d['detail']}\n\n[사전 조사]\n{notes}")
    res = client.messages.parse(model=config.CLAUDE_MODEL, max_tokens=16000, system=SYSTEM,
                                output_config={"effort": "high"}, output_format=Package,
                                messages=[{"role": "user", "content": info}])
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"출품안 생성 실패 (stop_reason={res.stop_reason})")
    return res.parsed_output, _cost(res.usage)


def dup_check(cands):
    """상위 후보가 이미 쓰이는 문구인지 웹 검색. {번호: (결과, 근거)}"""
    listing = "\n".join(f"{i}. {c.text}" for i, c in enumerate(cands, 1))
    prompt = f"""아래 문구들이 이미 다른 곳에서 슬로건·광고 문구·상호·상표·공모전 수상작으로 쓰이고 있는지 웹 검색으로 확인해주세요.
똑같거나 거의 같은 문구가 있으면 '유사', 없으면 'OK'.

{listing}

답변은 문구마다 한 줄씩, 정확히 이 형식으로만:
번호|OK 또는 유사|근거(유사면 URL, OK면 -)"""
    text, cost = _search_call(prompt, max(3, len(cands)))
    result = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*\|\s*(OK|유사)\s*\|\s*(.*)", line)
        if m:
            result[int(m.group(1))] = (m.group(2), m.group(3).strip())
    return result, cost


def make_package(d):
    """조사 → 생성(12개, 자체 채점) → 상위 7개 중복 검사 → 최종 5개. (결과 dict, 비용)"""
    if config.MOCK or not config.ANTHROPIC_API_KEY:
        cands = [Candidate(text=f"테스트 출품안 {i}", angle="직관", explanation="설명", fit=4, originality=4,
                           symbolism=3, memorability=4, usability=4, why="포인트") for i in range(1, 6)]
        pkg = Package(keywords=["테스트"], format_rules="(테스트)", per_person_limit="1개", ai_policy="언급 없음",
                      submit_method="온라인 폼", required_docs=["신청서"], personal_fields=["이름", "연락처"],
                      email_template="", announce="명시 없음", text_only=True, candidates=cands, caution="공고 확인")
        return {"pkg": pkg, "top": cands, "dups": {}, "notes": "(테스트 조사)"}, 0.0
    notes, c1 = research(d)
    pkg, c2 = generate(d, notes)
    ranked = sorted(pkg.candidates, key=lambda c: c.fit + c.originality + c.symbolism + c.memorability + c.usability,
                    reverse=True)[:7]
    dups, c3 = dup_check(ranked)
    top = [c for i, c in enumerate(ranked, 1) if dups.get(i, ("OK", ""))[0] != "유사"][:5]
    return {"pkg": pkg, "top": top, "dups": {ranked[i - 1].text: v for i, v in dups.items() if i <= len(ranked)},
            "notes": notes}, c1 + c2 + c3


def _len_ko(s):
    return len(re.sub(r"[\s\.,!?~'\"“”‘’·…\-]", "", s))


def format_messages(d, r, cost):
    """휴대폰용 텔레그램 메시지 2개: ①추천 1순위 요약 ②탭해서 복사 + 접수 링크 (HTML)"""
    from html import escape as e
    pkg, top = r["pkg"], r["top"]
    best = top[0]
    score = lambda c: c.fit + c.originality + c.symbolism + c.memorability + c.usability
    notes = "\n".join(l for l in r["notes"].splitlines() if l.strip())[:600]
    m1 = [f"🏆 {d['title']}", f"마감 {d['deadline']} · {d['prize'][:60]}", "",
          f"⭐ 추천 1순위 ({score(best)}/25점)", best.text, f"노린 점: {best.why}", ""]
    if len(top) > 1:
        m1.append("다른 후보: " + " / ".join(c.text for c in top[1:]))
    dropped = [t for t, (v, _) in r["dups"].items() if v == "유사"]
    if dropped:
        m1.append("🚫 기존 문구와 비슷해 뺀 후보: " + " / ".join(dropped))
    m1 += ["", f"형식: {pkg.format_rules}", f"1인 접수: {pkg.per_person_limit} · AI 규정: {pkg.ai_policy}",
           f"발표: {pkg.announce}", "", "🔎 조사 요약", notes, f"(비용 ${cost:.3f})"]
    link = d["home"] or d["url"]
    m2 = ["📮 <b>제출하기</b> (회색 글자를 탭하면 복사돼요)", "",
          "① 출품작", f"<code>{e(best.text)}</code>", f"({_len_ko(best.text)}자, 공백·부호 제외)", "",
          "② 작품설명", f"<code>{e(best.explanation)}</code>", "",
          f"③ 접수 링크: {e(link)}", f"   접수 방법: {e(pkg.submit_method)}",
          f"④ 직접 입력: {e(', '.join(pkg.personal_fields) or '-')}",
          f"⑤ 제출 서류: {e(', '.join(pkg.required_docs) or '없음')}", "",
          "✅ 제출 전: 1인 접수 개수 · 글자 수 · 출품작 인터넷 검색"]
    if pkg.email_template:
        m2 += ["", "✉️ 이메일 접수 틀 (탭하면 복사)", f"<code>{e(pkg.email_template)}</code>"]
    return [("\n".join(m1), False), ("\n".join(m2), True)]


def needs_document(d):
    """제안서·기획서 같은 문서를 요구하는 공모전인지 (출품안만으로 제출 불가)."""
    return bool(re.search(r"제안서|기획서|계획서|PPT|ppt|발표자료|보고서", d["detail"])) and not re.search(
        r"네이밍|슬로건|표어|명칭|이름", d["title"])


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
            if ok and needs_document(d):
                ok, why = False, "제안서 등 문서 필요"
            print(f"[contest] {sid} {d['title'][:30]} → {why}")
            if ok:
                candidates.append(d)
    candidates = st.pop("contest_retry", []) + candidates
    st["contest_last_date"] = now().strftime("%Y-%m-%d")
    st["contest_seen"] = st["contest_seen"][-1000:]
    candidates.sort(key=prize_value, reverse=True)
    sent = 0
    limit = st.pop("contest_limit_once", None) or config.CONTESTS_PER_DAY
    tried = 0
    for d in candidates:
        if sent >= limit or tried >= limit + 2:  # 문서형으로 판정돼 건너뛰는 경우 대비 최대 2개 더 시도
            break
        tried += 1
        try:
            r, cost = make_package(d)
        except Exception as e:
            print(f"[contest] 생성 실패 {d['id']}: {e}")
            st["contest_last_error"] = f"{type(e).__name__}: {str(e)[:400]}"
            continue
        st.setdefault("cost", {})[month] = round(st["cost"].get(month, 0) + cost, 5)
        st.pop("contest_last_error", None)
        if not r["pkg"].text_only or not r["top"]:
            print(f"[contest] {d['id']} 문서·파일 필요 또는 후보 없음 → 건너뜀")
            continue
        try:
            msgs = format_messages(d, r, cost)
        except Exception as e:
            st["contest_last_error"] = f"format {type(e).__name__}: {str(e)[:300]}"
            print("[contest]", st["contest_last_error"])
            continue
        for msg, html in msgs:
            if config.MOCK:
                print(msg)
            elif notify(st, msg[:3900], html=html) is None:
                st["contest_last_error"] = "telegram " + telegram.last_error
        sent += 1
    print(f"[contest] 후보 {len(candidates)}개 중 {sent}개 전송")
    if not config.MOCK:
        if candidates and sent == 0:
            st["contest_retry"] = candidates[:config.CONTESTS_PER_DAY]  # 다음 실행 때 다시 시도
            notify(st, "⚠️ 공모전 출품안 생성 중 오류가 나서 다음 실행 때 다시 시도합니다.\n" + st.get("contest_last_error", ""))
        elif not candidates:
            notify(st, "🏆 오늘은 조건에 맞는 새 공모전이 없어요.")
