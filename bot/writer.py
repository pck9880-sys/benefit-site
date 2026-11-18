"""Claude로 공공데이터를 읽기 쉬운 안내글로 변환."""
from typing import List

from pydantic import BaseModel, Field

from . import config


class FAQ(BaseModel):
    q: str
    a: str


class Article(BaseModel):
    title: str = Field(description="검색에 잘 걸리는 제목. 서비스명 + '지원대상·신청방법' 같은 핵심어. 45자 이내")
    description: str = Field(description="검색결과에 노출될 요약 1~2문장, 120자 이내")
    summary_points: List[str] = Field(description="핵심 요약 3~5개 (누가, 무엇을, 얼마나, 언제까지, 어떻게)")
    body_markdown: str = Field(description="본문 마크다운. ## 소제목 사용, 표/목록 활용")
    faq: List[FAQ] = Field(description="실제로 궁금해할 질문 3~5개와 답")
    tags: List[str] = Field(description="관련 키워드 3~6개")


SYSTEM = """당신은 정부 지원제도를 일반인이 이해하기 쉽게 풀어 쓰는 한국어 정보 작가입니다.

반드시 지킬 규칙:
- 제공된 공식 데이터에 있는 사실만 씁니다. 금액, 날짜, 자격요건, 기관명을 추측하거나 지어내지 않습니다.
- 데이터에 없는 정보는 "공식 안내에서 확인 필요"라고 씁니다.
- 어려운 행정용어는 쉬운 말로 풀되 의미를 바꾸지 않습니다.
- 과장, 낚시성 표현("무조건", "누구나 100만원")을 쓰지 않습니다.
- 본문 구성: ## 한눈에 보기(표) / ## 누가 받을 수 있나요 / ## 무엇을 지원하나요 / ## 신청 방법 / ## 필요 서류 / ## 문의처
- 본문에 제목(# )은 넣지 않습니다. 출처 링크는 시스템이 자동으로 붙이므로 넣지 않습니다."""


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

    keep = {k: v for k, v in {**svc, **detail}.items() if v and k not in ("조회수", "소관기관코드")}
    data_text = "\n".join(f"- {k}: {v}" for k, v in keep.items())

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    res = client.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=8000,
        system=SYSTEM,
        output_config={"effort": "low"},
        output_format=Article,
        messages=[{"role": "user", "content": f"다음 공식 데이터로 안내글을 작성하세요.\n\n{data_text}"}],
    )
    if res.stop_reason == "refusal":
        raise RuntimeError("Claude가 작성을 거절함")
    if res.stop_reason == "max_tokens" or res.parsed_output is None:
        raise RuntimeError(f"글 생성 실패 (stop_reason={res.stop_reason})")

    pin, pout = config.PRICES.get(config.CLAUDE_MODEL, (4.0, 20.0))
    cost = (res.usage.input_tokens * pin + res.usage.output_tokens * pout) / 1_000_000
    return res.parsed_output, cost
