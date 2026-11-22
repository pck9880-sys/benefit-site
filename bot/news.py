"""새 지원금 발표 감지: 구글 뉴스 RSS에서 하루 동안 기사가 몰린 지원금 이름을 찾아 텔레그램으로 알리고, 정부24에 있으면 바로 글 대기열 맨 앞에 넣는다."""
import collections
import hashlib
import re
import urllib.parse
import urllib.request
from html import unescape

QUERIES = ["지원금 신청 시작", "신청 접수 시작 지원", "바우처 신청", "수당 지급 시작", "장려금 신청", "장학금 신청 시작", "지원금 지급일"]
TERM = re.compile(r"([가-힣]{2,14}(?:지원금|장려금|수당|바우처|급여|장학금|이용권|연금|쿠폰|감면|환급금))")
SKIP = re.compile(r"캐나다|미국|일본|중국|호주|베트남|사설|칼럼|주식|코인|증시")


def headlines():
    items = []
    for q in QUERIES:
        url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:1d") + "&hl=ko&gl=KR&ceid=KR:ko"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            xml = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "ignore")
        except Exception:
            continue
        for t, link in re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>", xml):
            t = unescape(t)
            if not SKIP.search(t):
                items.append((t, link))
    seen, out = set(), []
    for t, l in items:
        if t not in seen:
            seen.add(t)
            out.append((t, l))
    return out


def hot_terms(items, top=6):
    c, ex = collections.Counter(), {}
    for t, l in items:
        for term in set(TERM.findall(t.replace(" ", ""))):
            if len(term) < 4:
                continue
            c[term] += 1
            ex.setdefault(term, (t, l))
    return [(term, n, ex[term]) for term, n in c.most_common(top) if n >= 2]


def run(st, notify, gov24, used):
    """하루 1번: 뜨는 지원금 TOP을 알리고, 정부24에 있는 서비스는 대기열 앞에 최대 2개 끼워 넣는다."""
    from . import config
    if config.MOCK:
        return
    hot = hot_terms(headlines())
    if not hot:
        return
    sent = set(st.setdefault("news_sent", []))
    lines, pushed = [], 0
    queue = st.setdefault("queue", [])
    for term, n, (title, link) in hot:
        h = hashlib.md5(term.encode()).hexdigest()[:10]
        tag = ""
        if pushed < 2:
            try:
                found = []
                base = re.sub(r"(지원금|장려금|수당|바우처|급여|장학금|이용권|연금|쿠폰|감면|환급금)$", "", term)
                for kw in dict.fromkeys([term[:8], base[:6], base[:4]]):
                    if len(kw) >= 2 and not found:
                        found = [s for s in gov24.search(kw) if s.get("서비스ID") and s["서비스ID"] not in used]
            except Exception:
                found = []
            if found:
                s = found[0]
                if s["서비스ID"] not in {q.get("서비스ID") for q in queue}:
                    queue.insert(0, {k: s.get(k) for k in ("서비스ID", "서비스명", "서비스분야", "소관기관명", "조회수", "지원대상",
                                                         "지원내용", "신청방법", "신청기한", "상세조회URL", "사용자구분", "전화문의", "수정일시") if s.get(k)} | {"_demand": 99, "_news": 1})
                    pushed += 1
                    tag = " → ✅ 다음 글로 자동 작성"
        if h in sent and not tag:
            continue
        sent.add(h)
        lines.append(f"• {term} (기사 {n}건){tag}\n  {title}\n  {link}")
    st["news_sent"] = list(sent)[-300:]
    if lines:
        notify(st, "📰 오늘 뜨는 지원금 뉴스\n정부24에 있는 건 자동으로 글을 쓰고, 없는 건 /post 키워드 로 요청할 수 있어요.\n\n" + "\n\n".join(lines))
