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
        posts.append(d)
    posts.sort(key=lambda d: d["published_at"], reverse=True)
    return posts


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
    fields = {}
    for d in posts:
        fields.setdefault(d["field_slug"], {"name": d["source"].get("field") or "기타", "posts": []})["posts"].append(d)
    cats = sorted(fields.items(), key=lambda kv: -len(kv[1]["posts"]))
    env.globals["categories"] = [(k, v["name"], len(v["posts"])) for k, v in cats]
    env.globals["recent"] = posts[:6]
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
                                                             related=related, faq_ld=faq_ld, canonical=f"{config.SITE_URL}/{d['url']}"))

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
        paginate(target_items[slug], f"target/{slug}/", name)
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
    write("calc/median/index.html", env.get_template("calc_median.html").render(canonical=f"{config.SITE_URL}/calc/median/"))
    for slug, aud, title, desc in GUIDES:
        items = [d for d in posts if set(aud) & set(d["audiences"]) and d["dl_state"] != "closed"]
        items.sort(key=lambda d: (not d["key"]["amount"], d["dl_state"] != "upcoming"))
        top = next((d for d in items if d["key"]["amount"] and "원" in d["key"]["amount"]), None)
        write(f"guide/{slug}/index.html", env.get_template("guide.html").render(
            g={"title": title, "desc": desc}, items=items, top=top, canonical=f"{config.SITE_URL}/guide/{slug}/"))

    for name in ("about", "privacy", "contact"):
        write(f"{name}.html", env.get_template(f"{name}.html").render(canonical=f"{config.SITE_URL}/{name}"))
    write("404.html", env.get_template("404.html").render(canonical=config.SITE_URL))

    # 검색용 인덱스
    write("search.json", json.dumps(
        [{"t": d["article"]["title"], "u": d["url"], "k": " ".join(d["article"]["tags"])} for d in posts],
        ensure_ascii=False))

    # SEO 파일
    urls = [f"{config.SITE_URL}/calc/median/"] + [f"{config.SITE_URL}/guide/{g[0]}/" for g in GUIDES]
    urls += [f"{config.SITE_URL}/", f"{config.SITE_URL}/latest/", f"{config.SITE_URL}/check/", f"{config.SITE_URL}/deadline/"]
    urls += [f"{config.SITE_URL}/c/{s}/" for s, _ in cats]
    urls += [f"{config.SITE_URL}/target/{s}/" for s, _, _ in targets] + [f"{config.SITE_URL}/region/{s}/" for s, _, _ in regions]
    urls += [f"{config.SITE_URL}/{d['url']}" for d in posts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(f"<url><loc>{escape(u)}</loc></url>" for u in urls) + "\n</urlset>\n")
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
