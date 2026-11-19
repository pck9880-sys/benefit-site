"""いらすとや(irasutoya.com) 짤 검색·저장.

이용 규약: 상업 이용 가능, 한 작품에 20점까지(그 이상은 유료). 비방·공서양속 위반 용도 금지, 출처 표기는 선택.
→ 숏츠 1편에 1~3장만 쓴다. 검색은 일본어가 정확함 (예: カンニング, 試験, AI, ロボット).
"""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (shorts-bot)"}
FEED = "https://www.irasutoya.com/feeds/posts/summary"


def search(q, n=8):
    """[(제목, 큰 이미지 URL, 글 주소)]"""
    r = requests.get(FEED, headers=UA, timeout=20, params={"q": q, "alt": "json", "max-results": n})
    r.raise_for_status()
    out = []
    for e in r.json()["feed"].get("entry", []):
        thumb = (e.get("media$thumbnail") or {}).get("url")
        if not thumb:
            continue
        big = re.sub(r"/s\d+(-c)?/", "/s800/", thumb)
        page = next((l["href"] for l in e["link"] if l["rel"] == "alternate"), "")
        out.append((e["title"]["$t"], big, page))
    return out


def save(url, path):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


if __name__ == "__main__":
    import sys
    for t, u, pg in search(" ".join(sys.argv[1:]) or "カンニング"):
        print(t, u, pg, sep=" | ")
