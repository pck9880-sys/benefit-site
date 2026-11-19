"""사이트에 게시된 글을 네이버 블로그용으로 다시 써서 텔레그램으로 보낸다.

- 네이버는 같은 글이 다른 곳에 있으면 유사문서로 보고 노출을 줄이므로, 문체·구성을 바꾼 별도 글을 만든다.
- 블로그 자동 업로드는 하지 않는다 (네이버 정책상 블로그 정지 위험). 휴대폰에서 탭-복사 → 붙여넣기.
- 하루 BLOG_PER_DAY 개까지만 (한꺼번에 많이 올리면 저품질 위험).
"""
import json
from datetime import datetime, timedelta, timezone
from html import escape as e
from typing import List

from pydantic import BaseModel, Field

from . import config

KST = timezone(timedelta(hours=9))


class BlogPost(BaseModel):
    title: str = Field(description="네이버 검색에 잘 걸리는 블로그 제목. 사이트 글 제목과 다른 표현으로, 32자 이내")
    body: str = Field(description="블로그 본문 (일반 텍스트, 마크다운 기호 금지). 1,500~2,500자")
    tags: List[str] = Field(description="네이버 블로그 태그 8~10개 (# 없이)")


SYSTEM = """당신은 생활 정보 네이버 블로그를 운영하는 작가입니다. 정부 지원제도 정리 글을 받아, 네이버 블로그에 올릴 새 글로 다시 씁니다.

규칙:
- 원문 문장을 그대로 옮기지 말고, 구성과 문장을 완전히 새로 씁니다 (같은 글로 보이면 안 됨).
- 말투는 친근한 해요체. 첫 문단은 "이런 분이라면 꼭 보세요" 식으로 독자 상황에서 시작합니다.
- 휴대폰 블로그 편집기에 그대로 붙여넣을 수 있게 일반 텍스트만 씁니다. #, *, |, 표 문법을 쓰지 않습니다.
- 소제목은 "■ 소제목" 형식, 목록은 "✔ " 또는 "1. " 으로 시작합니다. 문단 사이는 빈 줄 하나.
- 금액·날짜·자격요건은 받은 자료에 있는 것만 씁니다. 지어내지 않습니다.
- 마지막 문단에 "신청 전 정부24 공식 안내에서 최신 내용을 꼭 확인하세요"를 넣습니다.
- 과장·낚시 표현("무조건", "누구나 다 받는") 금지."""


def now():
    return datetime.now(KST)


def write(post):
    a, src = post["article"], post["source"]
    if config.MOCK or not config.ANTHROPIC_API_KEY:
        return BlogPost(title=f"[블로그] {src.get('name')}", body="테스트 본문\n\n■ 소제목\n✔ 항목", tags=["정부지원금"]), 0.0
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    content = (f"[원문 제목] {a['title']}\n[핵심 요약]\n" + "\n".join(a["summary_points"]) +
               f"\n\n[본문]\n{a['body_markdown']}\n\n[자주 묻는 질문]\n" +
               "\n".join(f"Q. {f['q']} A. {f['a']}" for f in a["faq"]) +
               f"\n\n[기관] {src.get('org')} [신청기한] {src.get('deadline')} [문의] {src.get('contact')}")
    res = client.messages.parse(model=config.CLAUDE_MODEL, max_tokens=8000, system=SYSTEM,
                                output_config={"effort": "low"}, output_format=BlogPost,
                                messages=[{"role": "user", "content": content}])
    if res.stop_reason == "refusal" or res.parsed_output is None:
        raise RuntimeError(f"블로그 글 생성 실패 (stop_reason={res.stop_reason})")
    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    return res.parsed_output, (res.usage.input_tokens * pin + res.usage.output_tokens * pout) / 1_000_000


def _chunks(text, size=3500):
    parts, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) + 2 > size and cur:
            parts.append(cur)
            cur = ""
        cur += (para + "\n\n")
    if cur.strip():
        parts.append(cur)
    return parts


def messages(post, bp):
    src = post["source"]
    link = f"{config.SITE_URL}/posts/{post['id']}"
    parts = _chunks(bp.body)
    head = ["📝 <b>네이버 블로그용 글</b> (회색 글자를 탭하면 복사돼요)", "",
            "① 제목", f"<code>{e(bp.title)}</code>", "",
            "③ 태그 (한 번에 복사)", f"<code>{e(' '.join('#' + t.replace(' ', '') for t in bp.tags))}</code>", "",
            f"② 본문은 다음 메시지 {len(parts)}개를 순서대로 복사해 붙여넣으세요.", "",
            "④ 맨 아래에 출처 링크도 붙여주세요", f"<code>{e(src.get('url') or link)}</code>",
            "", "올리는 순서: 네이버 블로그 앱 → 글쓰기 → 제목 붙여넣기 → 본문 붙여넣기 → 태그 → 발행"]
    out = ["\n".join(head)]
    for i, p in enumerate(parts, 1):
        out.append(f"② 본문 {i}/{len(parts)}\n<code>{e(p.strip())}</code>")
    return out


def run(st, notify):
    """오늘 아직 블로그 글을 안 보낸 게시글 중 BLOG_PER_DAY 개까지 블로그용 글을 만들어 전송."""
    if not config.BLOG_PER_DAY or not (config.MOCK or (config.ANTHROPIC_API_KEY and st.get("owner_chat_id"))):
        return
    today = now().strftime("%Y-%m-%d")
    if st.get("blog_date") != today:
        st["blog_date"], st["blog_count"] = today, 0
    month = now().strftime("%Y-%m")
    for path in sorted(config.POSTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime):
        if st["blog_count"] >= config.BLOG_PER_DAY or st.get("cost", {}).get(month, 0) >= config.MAX_MONTHLY_USD:
            break
        post = json.loads(path.read_text("utf-8"))
        if post.get("blog_sent"):
            continue
        try:
            bp, cost = write(post)
        except Exception as ex:
            print(f"[blog] 실패 {post['id']}: {ex}")
            st["blog_last_error"] = f"{type(ex).__name__}: {str(ex)[:300]}"
            break
        st.setdefault("cost", {})[month] = round(st["cost"].get(month, 0) + cost, 5)
        for msg in messages(post, bp):
            if config.MOCK:
                print(msg)
            else:
                notify(st, msg[:4000], html=True)
        post["blog_sent"] = today
        path.write_text(json.dumps(post, ensure_ascii=False, indent=1), "utf-8")
        st["blog_count"] += 1
