"""글을 지역·대상·마감일로 분류 (모음 페이지, 자격 진단, 마감 캘린더용)."""
import re
from datetime import date

REGIONS = [  # (slug, 이름, 기관명에서 찾을 말)
    ("seoul", "서울", ["서울"]), ("busan", "부산", ["부산"]), ("daegu", "대구", ["대구"]),
    ("incheon", "인천", ["인천"]), ("gwangju", "광주", ["광주광역시", "광주 "]), ("daejeon", "대전", ["대전"]),
    ("ulsan", "울산", ["울산"]), ("sejong", "세종", ["세종"]), ("gyeonggi", "경기", ["경기"]),
    ("gangwon", "강원", ["강원"]), ("chungbuk", "충북", ["충청북도", "충북"]), ("chungnam", "충남", ["충청남도", "충남"]),
    ("jeonbuk", "전북", ["전라북도", "전북"]), ("jeonnam", "전남", ["전라남도", "전남"]),
    ("gyeongbuk", "경북", ["경상북도", "경북"]), ("gyeongnam", "경남", ["경상남도", "경남"]), ("jeju", "제주", ["제주"]),
]
REGION_NAMES = {s: n for s, n, _ in REGIONS} | {"national": "전국"}

# (slug, 이름, 자격조건 코드, 키워드)
AUDIENCES = [
    ("youth", "청년", [], r"청년"),
    ("senior", "어르신", [], r"노인|어르신|고령"),
    ("pregnancy", "임신·출산", ["JA0301", "JA0302", "JA0303"], r"임신|출산|임산부|난임|산모"),
    ("child", "아이 키우는 가정", [], r"아동|영유아|자녀|양육|보육|육아"),
    ("student", "학생", ["JA0317", "JA0318", "JA0319", "JA0320"], r"학생|장학|대학생"),
    ("disabled", "장애인", ["JA0328"], r"장애"),
    ("veteran", "국가보훈", ["JA0329"], r"보훈|국가유공"),
    ("lowincome", "저소득층", [], r"기초생활|차상위|저소득|생계급여"),
    ("singleparent", "한부모·조손", ["JA0403"], r"한부모|조손"),
    ("multicultural", "다문화·북한이탈", ["JA0401", "JA0402"], r"다문화|북한이탈|새터민"),
    ("oneperson", "1인 가구", ["JA0404"], r"1인\s*가구"),
    ("multichild", "다자녀", ["JA0411"], r"다자녀"),
    ("homeless", "무주택·세입자", ["JA0412"], r"무주택|전세|월세|임차"),
    ("jobseeker", "구직자", ["JA0327"], r"구직|실업|취업"),
    ("worker", "직장인", ["JA0326"], r"근로자|직장인"),
    ("farmer", "농어업인", ["JA0313", "JA0314", "JA0315", "JA0316"], r"농업인|어업인|농가|어가|축산"),
    ("business", "소상공인·창업", ["JA1101", "JA1102", "JA1103"], r"소상공인|자영업|창업"),
]
AUDIENCE_NAMES = {s: n for s, n, _, _ in AUDIENCES}


def region_of(org):
    org = org or ""
    for slug, _, keys in REGIONS:
        if any(org.startswith(k) or f" {k}" in org for k in keys):
            return slug
    return "national"


def audiences_of(post):
    src, a = post.get("source", {}), post.get("article", {})
    cond = src.get("cond") or {}
    codes = set(cond.get("codes") or [])
    text = " ".join([a.get("title", ""), src.get("name") or "", " ".join(a.get("summary_points", []))])
    code_hits = [slug for slug, _, cs, _ in AUDIENCES if codes & set(cs)]
    if len(code_hits) > 4:  # 대상 코드가 거의 다 찍힌 제도 = '대상 제한 없음' → 코드 무시하고 본문 키워드로만
        code_hits = []
    out = []
    for slug, _, cs, kw in AUDIENCES:
        if slug in code_hits or re.search(kw, text):
            out.append(slug)
    amin, amax = cond.get("age_min"), cond.get("age_max")
    if amax and amax <= 39 and (amin or 0) >= 15 and "youth" not in out:
        out.append("youth")
    if amin and amin >= 60 and "senior" not in out:
        out.append("senior")
    inc = {c for c in codes if c.startswith("JA020")}
    if inc and inc <= {"JA0201", "JA0202"} and "lowincome" not in out:
        out.append("lowincome")
    if "소상공인" in (src.get("user_type") or "") and "business" not in out:
        out.append("business")
    return out


def deadline_info(text, today=None):
    """신청기한 문구 해석 → ('always'|'upcoming'|'closed'|'unknown', 마감일 date 또는 None)"""
    today = today or date.today()
    text = text or ""
    if re.search(r"상시|수시|연중", text):
        return "always", None
    dates = []
    for y, m, d in re.findall(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})", text):
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    if not dates:
        return "unknown", None
    end = max(dates)
    return ("upcoming" if end >= today else "closed"), end


# ---------- 글 상단 '한눈에' 정보 (금액 크게 · 대상 · 신청) ----------
_MONEY = re.compile(r"(월|연|1인당|가구당|1회|1명당)?\s*(최대\s*)?([\d][\d,]*(?:\.\d+)?)\s*(억|천만|백만|만|천)?\s*원")
_UNIT = {"억": 1e8, "천만": 1e7, "백만": 1e6, "만": 1e4, "천": 1e3, None: 1, "": 1}


def _won(m):
    try:
        return float(m.group(3).replace(",", "")) * _UNIT[m.group(4)]
    except ValueError:
        return 0


def _pretty(v):
    if v >= 1e8:
        return f"{v / 1e8:g}억 원"
    if v >= 1e4:
        return f"{v / 1e4:,.0f}만 원" if v % 1e4 == 0 else f"{v / 1e4:,.1f}만 원"
    return f"{v:,.0f}원"


def _strip_label(p):
    return re.sub(r"^\s*(대상|누가|지원 ?내용|내용|지원|금액|한도|무엇을|신청 ?방법|신청 ?기간|신청 ?기한|신청|언제까지|방법)\s*[:：]\s*", "", p).strip()


def key_facts(post):
    """{'amount': '최대 330만 원' 또는 None, 'amount_note': 그 문장, 'target': 대상 한 줄, 'how': 신청 한 줄}
    글에 key_* 필드가 있으면(새 글) 그대로, 없으면 요약 문장에서 뽑는다."""
    a = post.get("article", {})
    if a.get("key_amount") or a.get("key_target"):
        return {"amount": a.get("key_amount") or None, "amount_note": a.get("key_amount_note", ""),
                "target": a.get("key_target", ""), "how": a.get("key_how", "")}
    pts = a.get("summary_points", [])
    best, note = None, ""
    for p in pts:
        if re.search(r"^\s*(대상|누가)", p) or re.search(r"소득\s*기준|^\s*소득", p):
            continue  # 대상·소득 기준 문장의 금액은 '받는 돈'이 아님
        for m in _MONEY.finditer(p):
            if re.search(r"소득|저축액|원금|보증금\s*$", p[max(0, m.start() - 14):m.start()]):
                continue
            v = _won(m)
            if v >= 1000 and (best is None or v > best[0]):
                pre = (m.group(1) or "").strip()
                best = (v, ("최대 " if m.group(2) or "최대" in p[:m.start()] else "") + (pre + " " if pre else "") + _pretty(v))
                note = _strip_label(p)
    amount = best[1].strip() if best else None
    if not amount:
        pct = next((re.search(r"(\d+(?:\.\d+)?)\s*%", p) for p in pts if "%" in p and not re.match(r"^\s*대상", p)), None)
        free = next((p for p in pts if "무료" in p), None)
        if pct:
            amount, note = f"{pct.group(1)}%", _strip_label(next(p for p in pts if pct.group(0) in p))
        elif free:
            amount, note = "무료", _strip_label(free)
    target = next((_strip_label(p) for p in pts if re.match(r"^\s*(대상|누가)", p)), "")
    how = next((_strip_label(p) for p in pts if re.match(r"^\s*(신청 ?방법|방법)", p)), "") or \
        next((_strip_label(p) for p in pts if re.search(r"신청|홈페이지|방문|온라인|홈택스|복지로|정부24", p) and p is not None
              and not re.match(r"^\s*(대상|누가)", p)), "")
    return {"amount": amount, "amount_note": note, "target": target, "how": how}
