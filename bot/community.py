"""커뮤니티 인기 유머글 가져오기 (로컬 Chromium, Claude 토큰 안 씀).

  python -m bot.community hot [n]            → 인기글 목록 (루리웹 유머 베스트, 개드립 인기) 댓글 수 순
  python -m bot.community grab <URL> <폴더>  → 본문 글·이미지(p1.jpg…)·베스트 댓글을 폴더에 저장 + post.json

웃긴 인기글은 대부분 본문이 '이미지'(캡처·짤·만화)라서, 그 이미지를 장면으로 그대로 쓰고 내레이션으로 풀어 준다.
이미지 속 사람 얼굴은 bot.realimg auto 로 모자이크. 출처(사이트명)는 설명란에 표기.
"""
import asyncio
import io
import json
import re
import sys
from pathlib import Path

import requests
from PIL import Image

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124 Safari/537.36")
SITES = {
    "루리웹": {"list": "https://bbs.ruliweb.com/best/humor", "a": "a.subject_link, td.subject a.deco",
             "body": ".view_content", "best": ".comment_table .best .text_wrapper", "cmt": ".comment_table .text_wrapper"},
    "개드립": {"list": "https://www.dogdrip.net/dogdrip?sort_index=popular", "a": "a.ed.title-link, .title-link",
             "body": "div.ed.article-wrapper div.rhymix_content", "best": "", "cmt": "div[class*=comment_].rhymix_content"},
}


def _site(url):
    return "루리웹" if "ruliweb" in url else "개드립" if "dogdrip" in url else None


async def _hot(n):
    from playwright.async_api import async_playwright
    out = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(user_agent=UA)
        for name, s in SITES.items():
            try:
                await pg.goto(s["list"], timeout=25000)
                await pg.wait_for_timeout(1500)
                rows = await pg.eval_on_selector_all(s["a"], "as=>as.map(a=>[a.innerText.trim(),a.href])")
            except Exception as ex:
                print(f"[community] {name} 목록 실패: {ex}")
                continue
            for t, href in rows:
                t = re.sub(r"\s+", " ", t)
                m = re.search(r"\((\d+)\)\s*$", t)  # 루리웹: 제목 (댓글수)
                title = re.sub(r"^\d+\s+|\s*\(\d+\)\s*$", "", t).strip()
                if len(title) < 4 or "핫딜" in title:
                    continue
                out.append({"site": name, "title": title, "url": href, "comments": int(m.group(1)) if m else None})
        await b.close()
    seen, res = set(), []
    for x in out:
        if x["url"] not in seen:
            seen.add(x["url"])
            res.append(x)
    res.sort(key=lambda x: -(x["comments"] or 0))  # 댓글 많은 순 (반응 큰 글)
    return res[:n * 2]


async def _grab(url, folder):
    from playwright.async_api import async_playwright
    s = SITES[_site(url)]
    d = Path(folder)
    d.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(user_agent=UA)
        await pg.goto(url, timeout=30000)
        await pg.wait_for_timeout(2000)
        title = re.sub(r"\s*[-|:].{0,20}$", "", await pg.title()).strip()
        body = await pg.query_selector(s["body"])
        text = (await body.inner_text()).strip() if body else ""
        imgs = await body.eval_on_selector_all("img", "is=>is.map(i=>i.currentSrc||i.src)") if body else []
        best = []
        if s["best"]:
            best = [re.sub(r"^BEST\s*", "", (await e.inner_text()).strip()) for e in await pg.query_selector_all(s["best"])]
        if len(best) < 3:
            best += [(await e.inner_text()).strip() for e in (await pg.query_selector_all(s["cmt"]))[:8]]
        await b.close()
    best = [re.sub(r"\s+", " ", c)[:80] for c in dict.fromkeys(best) if c and len(c) > 1][:6]
    saved = []
    for i, src in enumerate([x for x in imgs if x.startswith("http")][:8], 1):
        try:
            r = requests.get(src, timeout=30, headers={"User-Agent": UA, "Referer": url})
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            if min(im.size) < 120:  # 아이콘·이모티콘 제외
                continue
            f = d / f"p{len(saved) + 1}.jpg"
            im.save(f, quality=92)
            saved.append({"file": f.name, "w": im.size[0], "h": im.size[1]})
        except Exception as ex:
            print(f"[community] 이미지 실패 {src[:60]}: {ex}")
    post = {"site": _site(url), "url": url, "title": title, "text": text[:3000], "images": saved, "best_comments": best}
    (d / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=1), "utf-8")
    print(f"[community] {post['site']} '{title}' — 글 {len(text)}자, 이미지 {len(saved)}장, 댓글 {len(best)}개 → {d / 'post.json'}")
    return post


def hot(n=15):
    return asyncio.run(_hot(n))


def grab(url, folder):
    return asyncio.run(_grab(url, folder))


if __name__ == "__main__":
    if sys.argv[1] == "hot":
        for x in hot(int(sys.argv[2]) if len(sys.argv) > 2 else 15):
            print(f"{x['site']}\t{x['comments'] or ''}\t{x['title']}\t{x['url']}")
    elif sys.argv[1] == "grab":
        grab(sys.argv[2], sys.argv[3])
