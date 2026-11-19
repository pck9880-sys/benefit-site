"""무료 실사 사진 검색: Pexels(키 있을 때) → Openverse(키 불필요, 상업적 이용 가능한 CC 사진).

출처 표기가 필요한 사진은 credit 문구를 돌려주고, 유튜브 설명에 붙인다.
"""
import re

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
            from .ccvideo import license_ok
            if (ii.get("width") or 0) < 640 or not license_ok(lic):  # CC BY·CC0·PD·공공누리1 만 (SA·NC·ND 제외)
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
    cands = pexels(query) + wikimedia(query) + [c for c in openverse(query) if not re.search(r"\b(SA|NC|ND)\b", c["credit"])]
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


def get(query, out, mode="auto"):
    """실사 사진 1장 받기: Pexels(키) → Openverse(CC, 재시도) → 위키미디어. 사람 있으면 모자이크(bot.realimg).
    출처는 같은 폴더 credits.json 에 모아 설명란에 붙인다. 성공하면 출처 문구, 실패하면 None."""
    import json
    import time
    from pathlib import Path
    from . import realimg
    out = Path(out)
    cands = pexels(query)
    for _ in range(3):
        if cands:
            break
        cands = openverse(query)
        if not cands:
            time.sleep(2)
    cands = cands or wikimedia(query)
    cands = [c for c in cands if "SA" not in c.get("credit", "")]  # 동일조건변경허락(SA)은 영상에 못 씀
    for c in cands[:5]:
        try:
            r = requests.get(c["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"})
            r.raise_for_status()
            tmp = out.with_suffix(".src")
            tmp.write_bytes(r.content)
            realimg.process(tmp, out, mode)
            tmp.unlink(missing_ok=True)
            cf = out.parent / "credits.json"
            cr = json.loads(cf.read_text("utf-8")) if cf.exists() else {}
            cr[out.name] = c.get("credit", "")
            cf.write_text(json.dumps(cr, ensure_ascii=False, indent=1), "utf-8")
            print(f"[photos] {out.name} ← '{query}' {c.get('credit', '')[:80]}")
            return c.get("credit")
        except Exception as e:
            print("[photos] 받기 실패:", type(e).__name__)
    print(f"[photos] '{query}' 실사 사진 없음 → 다른 검색어로 다시 하거나 AI 이미지")
    return None


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "get":
        get(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "auto")
