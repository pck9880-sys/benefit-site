"""KPI 리포트 - 본인 텔레그램으로만 전송 (사이트나 공개 저장소에는 표시하지 않음)."""
import json
from datetime import datetime, timedelta, timezone

from . import config

KST = timezone(timedelta(hours=9))
REPORT_HOUR_KST = 21  # 매일 저녁 9시 리포트


def now():
    return datetime.now(KST)


def bump(st, key, n=1):
    """오늘 날짜 기준 카운터 증가 (예: 공모전 전송 수)."""
    day = now().strftime("%Y-%m-%d")
    k = st.setdefault("kpi", {}).setdefault(key, {})
    k[day] = k.get(day, 0) + n
    for old in sorted(k)[:-60]:  # 최근 60일만 보관
        k.pop(old)


def _sum(st, key, days):
    k = st.get("kpi", {}).get(key, {})
    since = (now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    return sum(v for d, v in k.items() if d >= since)


def report(st):
    posts = [json.loads(p.read_text("utf-8")) for p in config.POSTS_DIR.glob("*.json")]
    today = now().strftime("%Y-%m-%d")
    week_ago = (now() - timedelta(days=6)).strftime("%Y-%m-%d")
    p_today = sum(1 for p in posts if p.get("published_at", "")[:10] == today)
    p_week = sum(1 for p in posts if p.get("published_at", "")[:10] >= week_ago)
    blog_total = sum(1 for p in posts if p.get("blog_sent"))
    blog_week = sum(1 for p in posts if (p.get("blog_sent") or "") >= week_ago)
    drafts = len(list(config.DRAFTS_DIR.glob("*.json")))
    month = now().strftime("%Y-%m")
    cost = st.get("cost", {}).get(month, 0)
    fields = {}
    for p in posts:
        f = p.get("source", {}).get("field") or "기타"
        fields[f] = fields.get(f, 0) + 1
    top = ", ".join(f"{k} {v}" for k, v in sorted(fields.items(), key=lambda x: -x[1])[:4])
    lines = [
        f"📊 KPI 리포트 ({now().strftime('%m/%d %H:%M')})", "",
        "■ 지원금 사이트",
        f"  게시글 총 {len(posts)}개 (오늘 +{p_today}, 7일 +{p_week})",
        f"  승인 대기 초안 {drafts}개",
        f"  분야: {top or '-'}",
        f"  애드센스 신청 목표: 글 30개 → {'달성 ✅' if len(posts) >= 30 else f'{30 - len(posts)}개 남음'}",
        "",
        "■ 네이버 블로그",
        f"  블로그용 글 받은 수: 총 {blog_total}개 (7일 {blog_week}개)",
        "",
        "■ 공모전",
        f"  출품안 받은 공모전: 오늘 {_sum(st, 'contests_sent', 1)}개 · 7일 {_sum(st, 'contests_sent', 7)}개 · 30일 {_sum(st, 'contests_sent', 30)}개",
        f"  확인한 공고 누적 {len(st.get('contest_seen', []))}건",
        "",
        "■ 비용 (Claude API)",
        f"  이번 달 ${cost:.2f} / 상한 ${config.MAX_MONTHLY_USD:g} ({cost / config.MAX_MONTHLY_USD * 100:.0f}%)",
        "",
        "■ 방문자 수",
        "  Cloudflare 대시보드 → Workers & Pages → jiwon-hyetaek → Metrics(Web Analytics)",
        "",
        "명령어: /kpi 지금 보기",
    ]
    return "\n".join(lines)


def run(st, notify):
    """매일 저녁 9시에 한 번 자동 전송."""
    t = now()
    if t.hour >= REPORT_HOUR_KST and st.get("kpi_last_date") != t.strftime("%Y-%m-%d") and st.get("owner_chat_id"):
        notify(st, report(st))
        st["kpi_last_date"] = t.strftime("%Y-%m-%d")
