"""검색 수요 측정: 네이버·구글 자동완성으로 '사람들이 실제로 검색하는 말'을 모아 글 주제 우선순위를 정한다."""
import json
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; benefy-bot)"}
_cache = {}


def _get(url, timeout=8):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def suggest(term):
    """네이버+구글 자동완성 목록 (중복 제거). 실패하면 빈 목록."""
    term = term.strip()
    if not term:
        return []
    if term in _cache:
        return _cache[term]
    q = urllib.parse.quote(term)
    out = []
    try:
        d = json.loads(_get(f"https://ac.search.naver.com/nx/ac?q={q}&st=100&r_format=json&frm=nv"))
        out += [x[0] for x in (d.get("items") or [[]])[0]]
    except Exception:
        pass
    try:
        d = json.loads(_get(f"https://suggestqueries.google.com/complete/search?client=firefox&hl=ko&q={q}"))
        out += d[1]
    except Exception:
        pass
    seen, res = set(), []
    for s in out:
        k = s.replace(" ", "")
        if k not in seen:
            seen.add(k)
            res.append(s)
    _cache[term] = res
    time.sleep(0.15)
    return res


_GENERIC = r"(지원\s*사업|지원사업|사업|서비스|제공|운영|지원)$"


def core_terms(name):
    """서비스명 → 검색어 후보 (긴 것부터)."""
    n = re.sub(r"\(.*?\)|\[.*?\]", " ", name or "")
    n = re.sub(r"\s+", " ", n).strip()
    cands = [n]
    short = re.sub(_GENERIC, "", n).strip()
    if short and short != n:
        cands.append(short)
    words = n.split()
    if len(words) > 2:
        cands.append(" ".join(words[:2]))
    return [c for i, c in enumerate(cands) if c and len(c) >= 2 and c not in cands[:i]]


def score(name):
    """(수요 점수, 실제 검색어 목록). 자동완성이 많이 붙을수록 많이 찾는 주제."""
    for t in core_terms(name):
        s = suggest(t)
        key = t.replace(" ", "")
        hits = [x for x in s if key[:4] in x.replace(" ", "")]
        if hits:
            return len(hits), hits[:8]
    return 0, []


def rank(services, limit=150):
    """조회수 상위 limit개만 수요를 재고, 수요 점수 → 조회수 순으로 정렬. 각 항목에 '_q'(실제 검색어) 추가."""
    from . import config
    if config.MOCK:
        return services
    head, tail = services[:limit], services[limit:]
    for s in head:
        try:
            s["_demand"], s["_q"] = score(s.get("서비스명", ""))
        except Exception:
            s["_demand"], s["_q"] = 0, []
    head.sort(key=lambda s: (s.get("_demand", 0), int(s.get("조회수") or 0)), reverse=True)
    return head + tail
