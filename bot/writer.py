"""Claude로 공공데이터를 읽기 쉬운 안내글로 변환."""
from typing import List

from pydantic import BaseModel, Field

from . import config


class FAQ(BaseModel):
    q: str
    a: str


class Article(BaseModel):
    title: str = Field(description="검색에 잘 걸리는 제목, 45자 이내. 서비스명을 앞에 두고 뒤는 글마다 다르게: "
                                   "'자격 조건과 신청 방법', '얼마나 받을 수 있나', '신청 기간·필요 서류', '누가 대상인가' 등. "
                                   "'총정리', '완벽 정리', '꿀팁' 같은 상투어는 쓰지 않는다")
    description: str = Field(description="검색결과에 노출될 요약 1~2문장, 120자 이내")
    summary_points: List[str] = Field(description="핵심 요약 3~5개 (누가, 무엇을, 얼마나, 언제까지, 어떻게)")
    body_markdown: str = Field(description="본문 마크다운. ## 소제목 사용, 표/목록 활용")
    faq: List[FAQ] = Field(description="실제로 궁금해할 질문 3~5개와 답")
    tags: List[str] = Field(description="관련 키워드 3~6개")
    key_amount: str = Field(default="", description="받는 돈·혜택을 가장 크게 보여줄 숫자 한 개 (예: '최대 330만 원', '월 20만 원', '무료', '연 1.5%'). "
                                                  "소득 기준·보증금 한도 같은 '조건' 숫자는 넣지 않음. 데이터에 없으면 빈 문자열")
    key_amount_note: str = Field(default="", description="그 숫자가 무엇인지 25자 이내 (예: '맞벌이 가구 근로장려금')")
    key_target: str = Field(default="", description="누가 받나 30자 이내 한 줄")
    key_how: str = Field(default="", description="어떻게 신청하나 30자 이내 한 줄 (예: '복지로 온라인 또는 주민센터')")


SYSTEM = """당신은 정부 지원제도를 이웃에게 설명하듯 쉽게 풀어 쓰는 한국어 생활정보 에디터입니다.

사실 규칙 (가장 중요):
- 제공된 공식 데이터에 있는 사실만 씁니다. 금액, 날짜, 자격요건, 기관명, 전화번호를 추측하거나 지어내지 않습니다.
- 과장, 낚시성 표현("무조건", "누구나 100만원")을 쓰지 않습니다.

문체 규칙:
- 모든 문장을 친근한 해요체("~해요", "~예요", "~돼요")로 씁니다. "~합니다/~습니다"는 쓰지 않습니다.
- 첫 문단(제목 없이 2~3문장)은 이 제도가 필요한 사람의 상황으로 시작합니다. 질문형·상황형·숫자형 중 데이터에 어울리는 방식을 고르고, 매번 같은 문장으로 시작하지 않습니다.
- 데이터에 없는 정보가 있으면 글 전체에서 딱 한 번만 "자세한 기준은 ○○(문의처)에 물어보면 정확해요"처럼 알려 줍니다. "공식 안내에서 확인 필요"를 반복하지 않습니다.
- "해당없음", "기타 구비서류"처럼 공문서 표현을 그대로 옮기지 않고, 독자에게 의미 있는 말로 바꾸거나 생략합니다.
- 같은 금액·문장을 여러 섹션에서 되풀이하지 않습니다. 표에 나온 내용은 본문에서 설명을 덧붙일 때만 다시 씁니다.
- "결론적으로", "알아보겠습니다", "살펴보겠습니다" 같은 기계적인 연결어와 이모지를 쓰지 않습니다.

본문 구성 (섹션 제목은 자연스러운 말로 바꿔도 됩니다):
- 도입 문단 → ## 한눈에 보기(표) → ## 누가 받을 수 있나요 → ## 무엇을, 얼마나 받나요 → ## 신청 방법 → ## 신청 전에 알아두면 좋은 점 → ## 문의처
- "신청 전에 알아두면 좋은 점"에는 데이터에서 근거를 찾을 수 있는 실용 팁 2~3개를 씁니다. 예: 신청 기한·시기, 온라인/방문 중 더 편한 쪽, 전화 문의 시 미리 준비할 것, 함께 확인하면 좋은 비슷한 제도. 데이터에 없는 사실은 만들지 않습니다.
- 본문에 제목(# )은 넣지 않습니다. 출처 링크는 시스템이 자동으로 붙이므로 넣지 않습니다.
- FAQ 답변도 해요체로, 1~2문장으로 짧게 씁니다."""


def _fake_article(svc):
    name = svc.get("서비스명", "서비스")
    return Article(
        title=f"{name} 지원대상·신청방법 총정리",
        description=f"{name}의 지원 대상, 지원 내용, 신청 방법을 정리했습니다.",
        summary_points=["대상: " + svc.get("지원대상", "")[:40], "내용: " + svc.get("지원내용", "")[:40]],
        body_markdown="## 한눈에 보기\n\n| 항목 | 내용 |\n|---|---|\n| 기관 | "
        + svc.get("소관기관명", "")
        + " |\n\n## 누가 받을 수 있나요\n\n"
        + svc.get("지원대상", ""),
        faq=[FAQ(q="온라인 신청 되나요?", a="공식 안내에서 확인 필요합니다.")],
        tags=["정부지원금", name],
    ), 0.0


def write_article(svc, detail):
    """returns (Article, cost_usd)"""
    if config.MOCK or not config.ANTHROPIC_API_KEY:
        return _fake_article(svc)

    import anthropic

    keep = {k: v for k, v in {**svc, **detail}.items() if v and k not in ("조회수", "소관기관코드", "_q", "_demand")}
    data_text = "\n".join(f"- {k}: {v}" for k, v in keep.items())
    queries = svc.get("_q") or []
    seo = ("\n\n[사람들이 실제로 검색하는 표현]\n" + ", ".join(queries) +
           "\n제목은 이 중 가장 많이 쓰일 표현(예: '신청 방법', '조건', '지급일')을 자연스럽게 포함하고, "
           "자주 묻는 질문(FAQ)은 이 검색어들에 답하는 질문으로 만드세요. 공식 데이터에 없는 내용은 지어내지 마세요.") if queries else ""

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    res = client.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=8000,
        system=SYSTEM,
        output_config={"effort": "low"},
        output_format=Article,
        messages=[{"role": "user", "content": f"다음 공식 데이터로 안내글을 작성하세요.\n\n{data_text}{seo}"}],
    )
    if res.stop_reason == "refusal":
        raise RuntimeError("Claude가 작성을 거절함")
    if res.stop_reason == "max_tokens" or res.parsed_output is None:
        raise RuntimeError(f"글 생성 실패 (stop_reason={res.stop_reason})")

    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    cost = (res.usage.input_tokens * pin + res.usage.output_tokens * pout) / 1_000_000
    article = res.parsed_output
    try:
        article, c2, n = fact_check(client, article, data_text)
        cost += c2
        print(f"[fact-check] 수정 {n}건")
    except Exception as e:  # 검수가 실패해도 원래 글은 그대로 사용
        print(f"[fact-check] 건너뜀: {type(e).__name__}")
    return article, cost


class Fix(BaseModel):
    wrong: str = Field(description="글에 있는 틀린 표현 (글에 있는 그대로 정확히 복사)")
    right: str = Field(description="공식 데이터에 맞게 고친 표현")
    reason: str = Field(description="왜 틀렸는지 한 줄")


class Review(BaseModel):
    fixes: List[Fix] = Field(description="데이터와 다른 금액·날짜·기간·자격요건·기관명·연락처. 틀린 게 없으면 빈 목록")


REVIEW_SYSTEM = """당신은 정부 지원제도 안내글의 사실 검수자입니다. 안내글을 공식 데이터와 한 줄씩 대조합니다.
- 금액, 날짜, 기간, 나이, 소득 기준, 자격요건, 기관명, 전화번호, 신청 방법이 데이터와 다르면 고칩니다.
- 데이터에 없는 구체적 수치나 조건을 지어낸 문장은 '공식 안내에서 확인 필요'로 바꿉니다.
- 문체나 표현 취향은 고치지 않습니다. 사실 오류만 찾습니다."""


def fact_check(client, article, data_text):
    """공식 데이터와 대조해 사실 오류를 찾아 고친다. (고친 글, 비용, 수정 건수)"""
    body = "\n".join([article.title, article.description, *article.summary_points, article.body_markdown,
                      *[f"Q. {f.q} A. {f.a}" for f in article.faq]])
    res = client.messages.parse(
        model=config.CLAUDE_MODEL, max_tokens=4000, system=REVIEW_SYSTEM,
        output_config={"effort": "low"}, output_format=Review,
        messages=[{"role": "user", "content": f"[공식 데이터]\n{data_text}\n\n[안내글]\n{body}"}],
    )
    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    cost = (res.usage.input_tokens * pin + res.usage.output_tokens * pout) / 1_000_000
    review = res.parsed_output
    if not review or not review.fixes:
        return article, cost, 0
    a = article.model_dump()
    n = 0
    for fx in review.fixes:
        if not fx.wrong or fx.wrong == fx.right:
            continue
        for k in ("title", "description", "body_markdown"):
            if fx.wrong in a[k]:
                a[k] = a[k].replace(fx.wrong, fx.right)
                n += 1
        a["summary_points"] = [p.replace(fx.wrong, fx.right) for p in a["summary_points"]]
        a["faq"] = [{"q": f["q"], "a": f["a"].replace(fx.wrong, fx.right)} for f in a["faq"]]
    return Article(**a), cost, n
