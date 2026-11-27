"""data/posts/*.json → 정적 사이트(_site/) 생성."""
import json
import re
import shutil
from datetime import datetime
from html import escape
from urllib.parse import urlparse

import markdown
from jinja2 import Environment, FileSystemLoader

from . import config, taxonomy

PER_PAGE = 12
HOME_LATEST = 6
CALCS = [("calc/", "calc_index.html"), ("calc/median/", "calc_median.html"), ("calc/unemployment/", "calc_unemp.html"), ("calc/parental-leave/", "calc_parental.html"), ("calc/baby/", "calc_baby.html"),
         ("calc/severance/", "calc_severance.html"), ("calc/youth-savings/", "calc_youthsave.html")]
TOOL_RULES = [  # 글 제목·요약 키워드 → 관련 도구 (내부 링크)
    (("실업", "구직급여", "실직"), "calc/unemployment/", "실업급여 계산기", "하루 얼마, 며칠 받는지"),
    (("퇴직",), "calc/severance/", "퇴직금 계산기", "세후 실수령액까지"),
    (("육아휴직", "육아기"), "calc/parental-leave/", "육아휴직급여 계산기", "6+6 포함 월별 금액"),
    (("출산", "임신", "임산부", "아동수당", "부모급여", "첫만남", "영아", "산후"), "calc/baby/", "출산·육아 지원금 계산기", "우리 아이가 받는 총액"),
    (("적금", "도약계좌", "저축계좌", "미래적금"), "calc/youth-savings/", "청년미래적금 계산기", "만기 수령액·정부기여금"),
    (("중위소득", "기초생활", "생계급여", "주거급여", "의료급여", "교육급여", "차상위", "저소득"), "calc/median/", "기준 중위소득 계산기", "우리 집은 몇 %일까"),
    (("연말정산", "세액공제", "소득공제", "근로장려금", "자녀장려금"), "special/year-end-tax/", "연말정산 놓치는 공제 TOP 10", "13월의 월급 체크리스트"),
]


def tools_for(d):
    txt = " ".join(str(x) for x in (d["article"].get("title", ""), d["article"].get("description", ""), d.get("name", "")))
    out = [(u, t, s) for keys, u, t, s in TOOL_RULES if any(k in txt for k in keys)][:2]
    if len(out) < 2:
        out.append(("finder/", "30초 지원금 진단", "나는 1년에 얼마 받을까"))
    out.append(("fun/16/", "지원금 성향 16유형", "나의 젤리 캐릭터와 찰떡 지원금"))
    return out[:3]


CHANGES_2027 = [  # 2027 달라지는 것 (보건복지부 고시값으로 확인)
    {"name": "기준 중위소득 (1인 가구)", "a": 256.4, "b": 273.6, "u": "만 원", "fa": "256.4만 원", "fb": "273.6만 원", "diff": "+6.7%",
     "note": "월 2,564,238원 → 2,736,042원. 각종 복지 지원의 기준이 되는 금액이에요."},
    {"name": "기준 중위소득 (4인 가구)", "a": 649.5, "b": 693.0, "u": "만 원", "fa": "649.5만 원", "fb": "693.0만 원", "diff": "+6.7%",
     "note": "월 6,494,738원 → 6,929,885원. 제도 도입 이후 가장 큰 인상이에요."},
    {"name": "생계급여 기준 (4인 가구)", "a": 207.8, "b": 221.8, "u": "만 원", "fa": "207.8만 원", "fb": "221.8만 원", "diff": "+14만 원",
     "note": "중위소득 32%. 소득인정액이 이보다 적으면 차액을 생계급여로 받아요."},
    {"name": "아동수당 받는 나이", "a": 9, "b": 10, "u": "세 미만", "fa": "만 9세 미만", "fb": "10세 미만", "diff": "+1세",
     "note": "매년 1세씩 늘어 2030년에는 만 13세 미만까지 받아요."},
]
LIFE = [  # 내 인생 지원금 타임라인 (만 원, 확인된 2026 기준값으로 만든 예시)
    {"age": "0세", "emoji": "👶", "title": "태어나면", "items": [("첫만남이용권 (첫째)", 200, "바우처"), ("부모급여 0세 (월 100만 × 12)", 1200, "현금")], "link": "calc/baby/"},
    {"age": "1세", "emoji": "🧸", "title": "돌이 지나면", "items": [("부모급여 1세 (월 50만 × 12)", 600, "현금")], "link": "calc/baby/"},
    {"age": "0~8세", "emoji": "🎒", "title": "어린이 시절 내내", "items": [("아동수당 (월 10만 × 108개월)", 1080, "현금")], "link": "guide/baby/"},
    {"age": "20대", "emoji": "🏠", "title": "독립해서 월세 살 때", "items": [("청년월세 지원 (월 최대 20만 × 24개월)", 480, "조건부")], "link": "guide/youth/"},
    {"age": "20~30대", "emoji": "💰", "title": "목돈 모을 때", "items": [("청년미래적금 정부기여금 (우대형 3년)", 216, "조건부")], "link": "calc/youth-savings/"},
    {"age": "30대", "emoji": "💼", "title": "회사를 그만두게 되면", "items": [("실업급여 (월급 300만 · 150일 예시)", 991, "조건부")], "link": "calc/unemployment/"},
    {"age": "30대", "emoji": "🍼", "title": "아이를 키우며 휴직하면", "items": [("육아휴직급여 12개월 (최대)", 2310, "조건부")], "link": "calc/parental-leave/"},
    {"age": "40~50대", "emoji": "🧾", "title": "소득이 적은 해에는", "items": [("근로장려금 (맞벌이 최대, 1년)", 330, "조건부")], "link": "search/?q=근로장려금"},
    {"age": "65세~", "emoji": "🌿", "title": "어르신이 되면", "items": [("기초연금 (월 최대 34.97만 × 20년 예시)", 8393, "조건부")], "link": "guide/senior/"},
]
GUIDES = [  # 생애주기 모음: (주소, 대상 태그, 제목, 한 줄 설명)
    ("youth", ["youth"], "청년이 받을 수 있는 지원금", "만 19~39세 청년 대상 지원제도만 모았어요."),
    ("baby", ["pregnancy", "child"], "임신·출산·육아 지원금", "임신부터 아이 키우는 가정까지 받을 수 있는 혜택이에요."),
    ("senior", ["senior"], "어르신이 받을 수 있는 혜택", "65세 이상 어르신 대상 지원제도를 모았어요."),
]  # 홈에는 최신 6개만, 나머지는 /latest/


def slugify(s):
    return re.sub(r"[^\w가-힣]+", "-", s).strip("-") or "etc"


FIELD_FIX = [(r"장려금", "생활안정")]


def load_posts():
    posts = []
    for p in config.POSTS_DIR.glob("*.json"):
        d = json.loads(p.read_text("utf-8"))
        d["url"] = f"posts/{d['id']}"  # 확장자 없는 깔끔한 주소 (파일은 .html 로 저장)
        for pat, fld in FIELD_FIX:  # 공공데이터 분류가 어색한 제도 바로잡기 (예: 근로장려금이 '주거·자립')
            if re.search(pat, d["article"].get("title", "")):
                d["source"]["field"] = fld
        d["field_slug"] = slugify(d["source"].get("field") or "기타")
        d["date"] = d["published_at"][:10]
        d["region"] = taxonomy.region_of(d["source"].get("org"))
        d["audiences"] = taxonomy.audiences_of(d)
        d["dl_state"], d["dl_date"] = taxonomy.deadline_info(d["source"].get("deadline"))
        d["key"] = taxonomy.key_facts(d)
        up = str(d["source"].get("updated") or "")
        d["data_date"] = f"{up[:4]}.{up[4:6]}.{up[6:8]}" if len(up) >= 8 else d["published_at"][:10].replace("-", ".")
        d["modified_at"] = (d.get("revisions") or [{}])[-1].get("date") or d["published_at"]
        posts.append(d)
    posts.sort(key=lambda d: d["published_at"], reverse=True)
    return posts



def news_items(limit=8):
    """오늘의 지원금 뉴스 헤드라인. 실패하면 마지막 캐시 사용."""
    import json as _j
    cache = config.DATA_DIR / "news_cache.json"
    items = []
    if not config.MOCK:
        try:
            from .news import headlines
            for t, l in headlines()[:40]:
                title, _, src = t.rpartition(" - ")
                items.append([title or t, src or "뉴스", l])
        except Exception:
            items = []
    if items:
        items = items[:limit]
        cache.write_text(_j.dumps(items, ensure_ascii=False), encoding="utf-8")
    elif cache.exists():
        items = _j.loads(cache.read_text(encoding="utf-8"))
    return items


def build():
    base_path = urlparse(config.SITE_URL).path.rstrip("/")  # GitHub Pages 하위경로 대응
    env = Environment(loader=FileSystemLoader(config.ROOT / "templates"), autoescape=True)

    def dl_clean(t, n=40):  # 신청기한 문구 정리: '○ 정기신청 : 5.1.~5.31.○ 반기…' → '정기신청 5.1.~5.31. · 반기…'
        t = re.sub(r"\s*[○●◦▪■□·]\s*", " · ", t or "").strip(" ·")
        t = re.sub(r"\s*:\s*", " ", re.sub(r"\s+", " ", t))
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
    env.filters["dl"] = dl_clean
    env.globals.update(
        site_name=config.SITE_NAME, site_url=config.SITE_URL, site_desc=config.SITE_DESCRIPTION,
        base=base_path, adsense=config.ADSENSE_CLIENT, year=datetime.now().year,
        mail_user=config.CONTACT_EMAIL.split("@")[0], mail_host=config.CONTACT_EMAIL.split("@")[-1],
        google_verify=config.GOOGLE_SITE_VERIFICATION, naver_verify=config.NAVER_SITE_VERIFICATION,
    )
    out = config.OUT_DIR
    if out.exists():
        shutil.rmtree(out)
    (out / "posts").mkdir(parents=True)
    (out / "c").mkdir()
    shutil.copytree(config.ROOT / "static", out / "static")

    posts = load_posts()
    try:  # 글마다 요약 카드 이미지
        from . import cards
        for d in posts:
            cards.make(d, out / "static" / "cards" / f"{d['id']}.webp")
            d["card"] = f"static/cards/{d['id']}.webp"
    except Exception as e:
        print(f"[cards] 건너뜀: {e}")
    fields = {}
    for d in posts:
        fields.setdefault(d["field_slug"], {"name": d["source"].get("field") or "기타", "posts": []})["posts"].append(d)
    cats = sorted(fields.items(), key=lambda kv: -len(kv[1]["posts"]))
    env.globals["categories"] = [(k, v["name"], len(v["posts"])) for k, v in cats]
    env.globals["recent"] = posts[:6]
    env.globals["news"] = news_items()
    # 대상별·지역별·마감 분류 (모든 페이지 사이드바에서 쓰므로 먼저 계산)
    from datetime import date
    today = date.today()
    target_items = {slug: [d for d in posts if slug in d["audiences"]] for slug, _, _, _ in taxonomy.AUDIENCES}
    region_items = {slug: [d for d in posts if d["region"] == slug] for slug in taxonomy.REGION_NAMES}
    targets = [(slug, name, len(target_items[slug])) for slug, name, _, _ in taxonomy.AUDIENCES if target_items[slug]]
    regions = [(slug, name, len(region_items[slug])) for slug, name in taxonomy.REGION_NAMES.items() if region_items[slug]]
    upcoming = sorted([d for d in posts if d["dl_state"] == "upcoming"], key=lambda d: d["dl_date"])
    for d in upcoming:
        d["d_day"] = (d["dl_date"] - today).days
    always = [d for d in posts if d["dl_state"] == "always"]
    others = [d for d in posts if d["dl_state"] == "unknown"]
    env.globals.update(targets=targets, regions=regions, soon=[d for d in upcoming if d["d_day"] <= 30][:5],
                       aud_names=taxonomy.AUDIENCE_NAMES, region_names=taxonomy.REGION_NAMES)

    def write(rel, html):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(html, "utf-8")

    from markdown.extensions.toc import TocExtension
    md = markdown.Markdown(extensions=["tables", "sane_lists",
                                       TocExtension(slugify=lambda v, sep: "s-" + re.sub(r"\s+", "-", v.strip()))])
    for d in posts:
        md.reset()
        body_html = md.convert(d["article"]["body_markdown"].replace("<", "&lt;"))  # 원시 HTML 차단
        toc = [{"id": t["id"], "name": t["name"]} for t in md.toc_tokens]
        # 본문 중간 광고를 넣기 위해 가운데 소제목 앞에서 둘로 나눔
        cuts = [m.start() for m in re.finditer(r"<h2", body_html)]
        mid = cuts[len(cuts) // 2] if len(cuts) >= 3 else len(body_html)
        body_top, body_bottom = body_html[:mid], body_html[mid:]
        read_min = max(1, round(len(re.sub(r"<[^>]+>", "", body_html)) / 500))
        faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in d["article"]["faq"]]}, ensure_ascii=False).replace("</", "<\\/") if d["article"]["faq"] else ""
        related = [x for x in fields[d["field_slug"]]["posts"] if x["id"] != d["id"]][:4]
        if len(related) < 4:
            related += [x for x in posts if x["id"] != d["id"] and x not in related][:4 - len(related)]
        write(d["url"] + ".html", env.get_template("post.html").render(post=d, a=d["article"], body_top=body_top, body_bottom=body_bottom, toc=toc, read_min=read_min,
                                                             related=related, tools=tools_for(d), faq_ld=faq_ld, canonical=f"{config.SITE_URL}/{d['url']}"))

    # 목록 페이지 (페이지네이션)
    def paginate(items, prefix, title, tmpl_name="list.html"):
        pages = max(1, -(-len(items) // PER_PAGE))
        for i in range(pages):
            rel = f"{prefix}index.html" if i == 0 else f"{prefix}page/{i + 1}.html"
            url = f"{config.SITE_URL}/{prefix}" + ("" if i == 0 else f"page/{i + 1}")
            write(rel, env.get_template(tmpl_name).render(
                posts=items[i * PER_PAGE:(i + 1) * PER_PAGE], title=title, page=i + 1, pages=pages, total=len(items),
                prefix=prefix, canonical=url))

    write("index.html", env.get_template("list.html").render(  # 홈: 최신 6개만
        posts=posts[:HOME_LATEST], title=None, page=1, pages=1, total=len(posts), prefix="", canonical=f"{config.SITE_URL}/",
        more=len(posts) > HOME_LATEST))
    paginate(posts, "latest/", "전체 지원제도")
    for slug, v in cats:
        paginate(v["posts"], f"c/{slug}/", v["name"])
    for slug, name, _ in targets:
        paginate(target_items[slug], f"target/{slug}/", f"{name} 대상")
    for slug, name, _ in regions:
        paginate(region_items[slug], f"region/{slug}/", name)

    write("deadline/index.html", env.get_template("deadline.html").render(
        upcoming=upcoming, always=always, others=others, today=today.isoformat(),
        canonical=f"{config.SITE_URL}/deadline/"))

    # 자격 진단
    write("check/index.html", env.get_template("check.html").render(canonical=f"{config.SITE_URL}/check/",
          audience_list=[(s_, n_) for s_, n_, _, _ in taxonomy.AUDIENCES], region_list=list(taxonomy.REGION_NAMES.items())))
    write("check.json", json.dumps([{
        "t": d["article"]["title"], "u": d["url"], "f": d["source"].get("field"), "o": d["source"].get("org"),
        "r": d["region"], "a": d["audiences"],
        "amin": (d["source"].get("cond") or {}).get("age_min"), "amax": (d["source"].get("cond") or {}).get("age_max"),
        "d": d["article"]["description"]} for d in posts], ensure_ascii=False))

    # 도구 · 생애주기 모음
    for rel, tmpl in CALCS:
        from .calcseo import CALC_SEO
        write(f"{rel}index.html", env.get_template(tmpl).render(canonical=f"{config.SITE_URL}/{rel}", seo=CALC_SEO.get(rel)))
    for slug, aud, title, desc in GUIDES:
        items = [d for d in posts if set(aud) & set(d["audiences"]) and d["dl_state"] != "closed"]
        items.sort(key=lambda d: (not d["key"]["amount"], d["dl_state"] != "upcoming"))
        top = next((d for d in items if d["key"]["amount"] and "원" in d["key"]["amount"]), None)
        write(f"guide/{slug}/index.html", env.get_template("guide.html").render(
            g={"title": title, "desc": desc}, items=items, top=top, canonical=f"{config.SITE_URL}/guide/{slug}/"))

    write("special/life/index.html", env.get_template("life.html").render(life=LIFE, total=sum(v for st in LIFE for _, v, _ in st["items"]),
          canonical=f"{config.SITE_URL}/special/life/"))
    write("special/2027-calendar/index.html", env.get_template("calendar2027.html").render(canonical=f"{config.SITE_URL}/special/2027-calendar/"))
    FUN = [("hub", "fun/", "혜택 놀이터 · 지원금 성향 16유형 · 유형 테스트 · 놓친 돈 영수증 · 빙고", "지원금 유형 테스트, 놓친 돈 영수증, 지원금 빙고. 30초면 끝나는 지원금 놀이."),
           ("type", "fun/type/", "지원금 유형 테스트 · 나의 지원금 캐릭터는?", "8문항으로 알아보는 나의 지원금 캐릭터. 결과에 맞는 혜택도 추천해요."),
           ("missed", "fun/missed/", "내가 놓친 돈 영수증 · 아직 안 받은 지원금", "받을 수 있는데 아직 신청하지 않은 지원금을 영수증으로 뽑아드려요."),
           ("p16", "fun/16/", "지원금 성향 16유형 테스트 · MBTI로 보는 나의 젤리 캐릭터", "12문항으로 알아보는 지원금 성향 16유형. 유형별 젤리 캐릭터와 찰떡 지원금 TOP 3를 알려드려요."),
           ("bingo", "fun/bingo/", "지원금 빙고 · 받아본 혜택 체크하고 친구와 대결", "받아본 정부 지원금을 체크해 빙고를 완성하고 친구와 비교해요.")]
    import re as _re
    for k, nm, q in _re.findall(r"\n (\w{4}):\['([^']+)','([^']+)',", (config.ROOT / "templates" / "fun.html").read_text(encoding="utf-8")):
        write(f"fun/16/{k}/index.html", env.get_template("fun.html").render(
            f={"mode": "p16", "preset": k, "og": f"/static/types/og/{k}.png", "title": f"{k} {nm} · 지원금 성향 16유형",
               "desc": f"{k} 유형은 '{nm}'! \"{q}\" 나의 지원금 젤리 캐릭터와 찰떡 지원금 TOP 3를 확인해 보세요."},
            canonical=f"{config.SITE_URL}/fun/16/{k}/"))
    for mode, rel, title, desc in FUN:
        write(rel + "index.html", env.get_template("fun.html").render(f={"mode": mode, "title": title, "desc": desc}, canonical=f"{config.SITE_URL}/{rel}"))
    YE_SCHED = [("1월 15일", "간소화 서비스 오픈", "홈택스에서 공제 자료 조회·내려받기"),
                ("1월 20일", "추가·수정 자료 반영", "병원·카드사가 늦게 낸 자료까지 확정"),
                ("1~2월", "회사에 서류 제출", "회사마다 마감일이 달라요"),
                ("2~3월", "환급금 입금", "보통 2월 또는 3월 월급과 함께"),
                ("5월", "놓친 공제 추가 신청", "종합소득세 신고 또는 5년 안에 경정청구")]
    YE_ITEMS = [
        {"t": "월세 세액공제", "who": "무주택 세대주 · 총급여 8천만 원 이하", "amt": "월세 15~17%",
         "how": "1년 월세(연 1,000만 원 한도)의 15%, 총급여 5,500만 원 이하면 17%를 세금에서 빼줘요. 연 월세 600만 원이면 최대 약 100만 원이에요. 전입신고가 된 주소여야 하고 임대차계약서와 이체 내역이 필요해요.",
         "miss": "간소화 자료에 나오지 않아서 직접 서류를 내야 해요. 집주인 동의는 필요 없어요."},
        {"t": "부양가족 인적공제", "who": "소득 적은 부모님·형제·자녀가 있다면", "amt": "1인당 150만 원 공제",
         "how": "연 소득 100만 원 이하(근로소득만 있으면 총급여 500만 원 이하)인 가족 1명당 150만 원을 소득에서 빼줘요. 따로 사는 부모님도 실제로 부양하면 넣을 수 있어요(만 60세 이상).",
         "miss": "형제끼리 중복으로 넣으면 안 돼서, 서로 미루다 아무도 안 넣는 경우가 많아요."},
        {"t": "의료비 세액공제", "who": "병원비가 총급여 3%를 넘었다면", "amt": "초과분 15~30%",
         "how": "총급여의 3%를 넘게 쓴 의료비의 15%(난임 시술 30%, 미숙아·선천성 이상아 20%)를 공제해요. 부양가족이 아니어도 내가 낸 가족 의료비는 넣을 수 있어요.",
         "miss": "안경·콘택트렌즈(1인 50만 원 한도)는 간소화에 안 나와서 안경점 영수증을 따로 받아야 해요. 실손보험으로 돌려받은 금액은 빼야 해요."},
        {"t": "청년 중소기업 취업자 감면", "who": "만 15~34세에 중소기업 취업", "amt": "소득세 90% 감면",
         "how": "취업일부터 5년 동안 소득세의 90%를 감면받아요(연 200만 원 한도). 군 복무 기간만큼 나이 기준이 늘어나요.",
         "miss": "회사에 감면 신청서를 내야 적용돼요. 지난 5년 치도 경정청구로 돌려받을 수 있어요."},
        {"t": "신용·체크카드 소득공제", "who": "카드 사용액이 총급여 25%를 넘었다면", "amt": "15~40% 공제",
         "how": "총급여 25%를 넘게 쓴 금액에서 신용카드 15%, 체크카드·현금영수증 30%, 전통시장·대중교통 40%를 공제해요. 총급여 7천만 원 이하면 도서·공연·영화 등 문화비도 30%예요.",
         "miss": "가족 카드 사용액도 부양가족 요건을 채우면 합칠 수 있는데 빠뜨리기 쉬워요."},
        {"t": "연금저축·IRP 세액공제", "who": "노후 대비 계좌에 넣었다면", "amt": "최대 148.5만 원",
         "how": "연금저축과 IRP를 합쳐 연 900만 원까지 넣은 금액의 16.5%(총급여 5,500만 원 초과는 13.2%)를 돌려받아요.",
         "miss": "12월 31일까지 넣은 금액만 올해 공제돼요. 연말에 한 번 더 확인하세요."},
        {"t": "주택청약 소득공제", "who": "무주택 세대주 · 총급여 7천만 원 이하", "amt": "납입액 40%",
         "how": "주택청약종합저축에 넣은 돈(연 300만 원 한도)의 40%를 소득에서 빼줘요. 연 300만 원이면 120만 원 공제예요.",
         "miss": "은행에 '무주택 확인서'를 내야 공제 자료가 나와요. 안 냈다면 지금 은행 앱에서 신청하세요."},
        {"t": "교육비 세액공제", "who": "본인·자녀 학비, 학원비(취학 전)", "amt": "15%",
         "how": "본인 대학원·직업훈련비는 한도 없이, 자녀는 초중고 1인 300만 원·대학생 900만 원까지 15%를 공제해요. 취학 전 아이 학원비·체육시설비도 들어가요.",
         "miss": "교복(50만 원)·체험학습비(30만 원)·취학 전 학원비는 간소화에 빠질 때가 많아요."},
        {"t": "기부금·고향사랑기부", "who": "기부나 고향사랑기부를 했다면", "amt": "10만 원까지 전액",
         "how": "고향사랑기부는 10만 원까지 낸 돈을 전액 세금에서 돌려받고 답례품도 받아요. 일반 기부금은 15%(1천만 원 초과분 30%)예요.",
         "miss": "종교단체·소규모 단체 기부금은 간소화에 안 나올 수 있어서 영수증을 따로 받아야 해요."},
        {"t": "중도 입사·퇴사자 합산", "who": "올해 회사를 옮겼다면", "amt": "놓치면 환급 0원",
         "how": "이전 회사의 근로소득 원천징수영수증을 지금 회사에 내야 1년 소득이 합쳐져 제대로 정산돼요. 연말에 회사를 안 다니고 있다면 5월 종합소득세 신고로 직접 환급받아요.",
         "miss": "이전 회사 소득을 안 합치면 공제가 적게 들어가거나 나중에 추가 세금이 나올 수 있어요."},
    ]
    YE_FAQ = [
        ("연말정산 간소화 서비스는 언제 열리나요?", "보통 1월 15일에 홈택스·손택스에서 열려요. 병원·카드사의 추가 자료는 1월 20일쯤 확정돼요."),
        ("놓친 공제는 나중에 받을 수 없나요?", "5월 종합소득세 신고 기간에 추가로 신청하거나, 5년 안에 경정청구를 하면 돌려받을 수 있어요."),
        ("환급금은 언제 들어오나요?", "회사마다 다르지만 보통 2월이나 3월 월급과 함께 들어와요."),
        ("월세 세액공제는 집주인 동의가 필요한가요?", "필요 없어요. 임대차계약서, 주민등록등본, 월세 이체 내역만 있으면 돼요."),
        ("맞벌이 부부는 누가 공제받는 게 유리한가요?", "의료비처럼 총급여 기준을 넘어야 하는 공제는 급여가 적은 쪽, 신용카드는 보통 급여가 많은 쪽이 유리해요. 부양가족은 두 사람 중 한 명만 넣을 수 있어요."),
    ]
    write("special/year-end-tax/index.html", env.get_template("yearend.html").render(sched=YE_SCHED, items=YE_ITEMS, faq=YE_FAQ, canonical=f"{config.SITE_URL}/special/year-end-tax/"))
    _log = []
    for d in posts:
        t = d["article"]["title"]
        _log.append((d["published_at"][:10], "새 지원금", "", t, d["url"]))
        if d.get("updated_at"):
            _log.append((d["updated_at"][:10], "정보 변경", "chg", t, d["url"]))
        if d.get("rewritten_at"):
            _log.append((d["rewritten_at"][:10], "내용 보강", "", t, d["url"]))
    _log.sort(key=lambda e: e[0], reverse=True)
    write("updates/index.html", env.get_template("updates.html").render(
        log=[{"d": e[0][5:].replace("-", "."), "kind": e[1], "cls": e[2], "title": e[3], "url": e[4]} for e in _log[:60]],
        today=datetime.now().strftime("%Y.%m.%d") if "datetime" in globals() else "", canonical=f"{config.SITE_URL}/updates/"))
    write("wallet/index.html", env.get_template("wallet.html").render(canonical=f"{config.SITE_URL}/wallet/"))
    write("finder/index.html", env.get_template("finder.html").render(canonical=f"{config.SITE_URL}/finder/"))
    write("special/2027-changes/index.html", env.get_template("changes.html").render(items=CHANGES_2027, canonical=f"{config.SITE_URL}/special/2027-changes/"))
    from . import specials
    for sp in specials.SPECIALS:  # 특집 (카드뉴스 + 체크리스트)
        write(f"special/{sp['slug']}/index.html", env.get_template("special.html").render(sp=sp, canonical=f"{config.SITE_URL}/special/{sp['slug']}/"))

    for name in ("about", "privacy", "contact", "principles"):
        write(f"{name}.html", env.get_template(f"{name}.html").render(canonical=f"{config.SITE_URL}/{name}"))
    write("search/index.html", env.get_template("search.html").render(canonical=f"{config.SITE_URL}/search/",
          audience_list=[(s_, n_) for s_, n_, _, _ in taxonomy.AUDIENCES], region_list=list(taxonomy.REGION_NAMES.items())))
    write("404.html", env.get_template("404.html").render(canonical=config.SITE_URL))

    # 검색용 인덱스
    write("search.json", json.dumps(
        [{"t": d["article"]["title"], "u": d["url"], "n": d["source"].get("name", ""), "f": d["source"].get("field", ""),
          "m": d["key"]["amount"] or "", "k": " ".join(d["article"]["tags"] + [d["article"].get("description", "")]),
          "r": d["region"], "a": d["audiences"], "x": d["dl_state"], "dd": d["dl_date"].isoformat() if d["dl_state"] == "upcoming" and d.get("dl_date") else "",
          "amin": (d["source"].get("cond") or {}).get("age_min"), "amax": (d["source"].get("cond") or {}).get("age_max")} for d in posts],
        ensure_ascii=False))

    # SEO 파일
    from . import specials
    urls = [f"{config.SITE_URL}/{rel}" for rel, _ in CALCS] + [f"{config.SITE_URL}/special/{sp['slug']}/" for sp in specials.SPECIALS] + [f"{config.SITE_URL}/special/2027-changes/", f"{config.SITE_URL}/finder/", f"{config.SITE_URL}/special/life/", f"{config.SITE_URL}/special/2027-calendar/", f"{config.SITE_URL}/fun/", f"{config.SITE_URL}/fun/type/", f"{config.SITE_URL}/fun/missed/", f"{config.SITE_URL}/fun/bingo/", f"{config.SITE_URL}/fun/16/", f"{config.SITE_URL}/special/year-end-tax/", f"{config.SITE_URL}/updates/"] + [f"{config.SITE_URL}/fun/16/{k}/" for k in ("ENTJ","INTJ","INTP","ENTP","INFJ","INFP","ENFP","ENFJ","ISTJ","ISFJ","ESTJ","ESFJ","ISTP","ISFP","ESTP","ESFP")] + [f"{config.SITE_URL}/guide/{g[0]}/" for g in GUIDES]
    urls += [f"{config.SITE_URL}/", f"{config.SITE_URL}/latest/", f"{config.SITE_URL}/check/", f"{config.SITE_URL}/deadline/"]
    urls += [f"{config.SITE_URL}/c/{s}/" for s, v in cats if len(v["posts"]) >= 3]
    urls += [f"{config.SITE_URL}/target/{s}/" for s, _, _ in targets if len(target_items[s]) >= 3] + [f"{config.SITE_URL}/region/{s}/" for s, _, _ in regions if len(region_items[s]) >= 3]
    urls += [f"{config.SITE_URL}/{d['url']}" for d in posts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(f"<url><loc>{escape(u)}</loc></url>" for u in urls) + "\n</urlset>\n")
    from email.utils import format_datetime
    from datetime import datetime as _dt, timezone as _tz
    def _rfc(t):
        try: return format_datetime(_dt.fromisoformat(t.replace("Z", "+00:00")).astimezone(_tz.utc))
        except Exception: return ""
    items = "".join(f"<item><title>{escape(d['article']['title'])}</title><link>{escape(config.SITE_URL + '/' + d['url'])}</link>"
                    f"<guid>{escape(config.SITE_URL + '/' + d['url'])}</guid><description>{escape(d['article'].get('description', ''))}</description>"
                    f"<pubDate>{_rfc(d['published_at'])}</pubDate></item>" for d in posts[:30])
    write("feed.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
          f"<title>{escape(config.SITE_NAME)}</title><link>{config.SITE_URL}/</link><description>{escape(config.SITE_DESCRIPTION)}</description><language>ko</language>"
          + items + "</channel></rss>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {config.SITE_URL}/sitemap.xml\n")
    if config.ADSENSE_CLIENT:
        pub = config.ADSENSE_CLIENT.replace("ca-", "")
        write("ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    (out / ".nojekyll").write_text("")
    key_file = config.ROOT / "static" / "indexnow-key.txt"
    if key_file.exists():  # IndexNow 키는 사이트 최상위에 있어야 전체 주소에 적용됨
        key = key_file.read_text().strip()
        (out / f"{key}.txt").write_text(key)
    print(f"built {len(posts)} posts → {out}")


def build_redirect(new_url, out_dir):
    """Cloudflare 로 옮긴 뒤 옛 GitHub Pages 주소로 들어온 사람을 새 주소의 같은 페이지로 보낸다."""
    import pathlib
    out = pathlib.Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<link rel="canonical" href="{new_url}/"><title>주소가 바뀌었어요</title>
<script>var p=location.pathname.replace(/^\\/[^/]+/,'');location.replace("{new_url}"+p+location.search+location.hash);</script>
</head><body>주소가 <a href="{new_url}/">{new_url}</a> 로 바뀌었어요.</body></html>"""
    for name in ("index.html", "404.html"):
        (out / name).write_text(page, "utf-8")
    (out / ".nojekyll").write_text("")
