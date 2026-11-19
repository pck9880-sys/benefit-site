"""무료 실사 사진 검색: Pexels(키 있을 때) → Openverse(키 불필요, 상업적 이용 가능한 CC 사진).

출처 표기가 필요한 사진은 credit 문구를 돌려주고, 유튜브 설명에 붙인다.
"""
import requests

from . import config

UA = {"User-Agent": "shorts-bot/1.0 (automated content tool)"}


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


def find(query, used, out_path):
    """query 로 사진 1장을 받아 out_path 에 저장. (경로, 출처 문구) 또는 (None, None)."""
    for cand in pexels(query) + openverse(query):
        if cand["id"] in used:
            continue
        try:
            r = requests.get(cand["url"], headers=UA, timeout=30)
            if r.status_code != 200 or len(r.content) < 20_000 or not r.headers.get("content-type", "").startswith("image"):
                continue
            out_path.write_bytes(r.content)
            used.add(cand["id"])
            return out_path, cand["credit"]
        except requests.RequestException:
            continue
    return None, None
