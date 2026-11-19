"""무료 실사 사진 검색: Pexels(키 있을 때) → Openverse(키 불필요, 상업적 이용 가능한 CC 사진).

출처 표기가 필요한 사진은 credit 문구를 돌려주고, 유튜브 설명에 붙인다.
"""
import requests

from . import config

UA = {"User-Agent": "jiwon-shorts-bot/1.0 (https://github.com/pck9880-sys/benefit-site; automated video tool) python-requests"}


def pexels(query, n=8):
    if not config.PEXELS_API_KEY:
        return []
    try:
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": config.PEXELS_API_KEY},
                         params={"query": query, "per_page": n, "orientation": "square"}, timeout=20)
        r.raise_for_status()
        return [{"url": p["src"]["large2x"], "credit": f"Photo: {p['photographer']} / Pexels", "id": f"px{p['id']}"}
                for p in r.json().get("photos", [])]
    except Exception as e:
        print("[photos] pexels 실패:", type(e).__name__)
        return []


def wikimedia(query, n=8):
    """위키미디어 공용 (실존 인물·장소에 강함, 자유 라이선스)."""
    import re
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=20, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": n, "prop": "imageinfo",
            "iiprop": "url|extmetadata|size", "iiurlwidth": 1200})
        r.raise_for_status()
        out = []
        for pg in sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
            ii = (pg.get("imageinfo") or [{}])[0]
            m = ii.get("extmetadata") or {}
            lic = (m.get("LicenseShortName") or {}).get("value", "")
            if (ii.get("width") or 0) < 640 or not re.search(r"CC|Public domain|PD", lic, re.I) or "NC" in lic:
                continue
            artist = re.sub(r"<[^>]+>", "", (m.get("Artist") or {}).get("value", "unknown"))[:60]
            out.append({"url": ii.get("thumburl") or ii["url"], "id": f"wm{pg['pageid']}",
                        "credit": f"Photo: {artist} ({lic}) {ii.get('descriptionurl', '')}"})
        return out
    except Exception as e:
        print("[photos] wikimedia 실패:", type(e).__name__)
        return []


def openverse(query, n=10):
    try:
        r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=20,
                         params={"q": query, "license_type": "commercial,modification", "page_size": n,
                                 "mature": "false"})
        r.raise_for_status()
        out = []
        for x in r.json().get("results", []):
            if (x.get("width") or 0) < 640 or (x.get("height") or 0) < 480:
                continue
            lic = f"CC {x['license'].upper()} {x.get('license_version') or ''}".strip()
            out.append({"url": x["url"], "id": f"ov{x['id']}",
                        "credit": f"Photo: {x.get('creator') or 'unknown'} ({lic}) {x.get('foreign_landing_url') or ''}"})
        return out
    except Exception as e:
        print("[photos] openverse 실패:", type(e).__name__)
        return []


def find(query, used, out_path, fallbacks=()):
    """query 로 사진 1장을 받아 out_path 에 저장. 안 되면 더 짧은 검색어로 재시도. (경로, 출처) 또는 (None, None)."""
    words = query.split()
    tries = [query] + ([" ".join(words[:-1])] if len(words) > 2 else []) + list(fallbacks)
    for q in dict.fromkeys(t for t in tries if t):
        f, credit = _find_one(q, used, out_path)
        if f:
            return f, credit
    return None, None


def _find_one(query, used, out_path):
    fails = []
    cands = pexels(query) + wikimedia(query) + openverse(query)
    for cand in cands:
        if cand["id"] in used:
            continue
        try:
            r = requests.get(cand["url"], headers=UA, timeout=30)
            if r.status_code != 200 or len(r.content) < 20_000 or not r.headers.get("content-type", "").startswith("image"):
                fails.append(str(r.status_code))
                continue
            out_path.write_bytes(r.content)
            used.add(cand["id"])
            return out_path, cand["credit"]
        except requests.RequestException as e:
            fails.append(type(e).__name__)
            continue
    print(f"[photos] '{query}': 후보 {len(cands)}개, 실패 {fails[:6]}")
    return None, None
