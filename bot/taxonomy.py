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
