"""Jamendo API 로 무료 배경음악 (상업적 이용 가능한 CC 곡, 보컬 없는 곡만).

- 텔레그램 /bgm 으로 후보 곡을 들어보고 ⭐ 버튼으로 즐겨찾기 → 숏츠는 즐겨찾기 곡 중에서 사용.
- 즐겨찾기가 없으면 인기곡 중 자동 선택. 키가 없거나 실패하면 assets/bgm 의 저장된 곡.
"""
import random

import requests

from . import config

API = "https://api.jamendo.com/v3.0/tracks/"
MOODS = ["funk", "hiphop", "groove", "upbeat", "electronic", "lofi", "funky", "pop"]


def enabled():
    return bool(config.JAMENDO_CLIENT_ID) and not config.MOCK


def _query(**params):
    r = requests.get(API, timeout=20, params={
        "client_id": config.JAMENDO_CLIENT_ID, "format": "json", "audiodlformat": "mp32", "include": "licenses",
        **params})
    res = r.json()
    if res.get("headers", {}).get("status") != "success":
        raise RuntimeError(res.get("headers", {}).get("error_message"))
    return res.get("results", [])


def _ok(t):
    """영상 배경음악으로 안전한 곡: CC BY (출처 표기만 하면 상업적 이용·영상 결합 가능).
    NC(비상업), ND(변경 금지), SA(영상에도 같은 라이선스 요구), 라이선스 정보 없음은 제외."""
    lic = t.get("license_ccurl") or ""
    return bool(t.get("audiodownload_allowed", True) and "/licenses/by/" in lic
                and (t.get("audiodownload") or t.get("audio")))


def search(tag=None, n=3):
    """상업적 이용 가능한 후보 곡 n개 (텔레그램 미리듣기용)."""
    tags = [tag] if tag else random.sample(MOODS, len(MOODS))
    found = []
    for tg in tags:
        for offset in (0, 50, 100):
            try:
                found += [t for t in _query(tags=tg, limit=50, offset=offset, vocalinstrumental="instrumental",
                                            order="popularity_month", durationbetween="60_300") if _ok(t)]
            except Exception as e:
                print("[music] 검색 실패:", e)
            if len(found) >= n * 3:
                break
        if len(found) >= n * 3:
            break
    random.shuffle(found)
    return found[:n]


def download(t, out_dir):
    for url in (t.get("audiodownload"), t.get("audio")):
        if not url:
            continue
        a = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 (shorts-bot)"})
        print(f"[music] 받기 {t['name']}: HTTP {a.status_code}, {len(a.content) // 1024}KB, "
              f"{a.headers.get('content-type')}")
        if a.status_code == 200 and len(a.content) > 200_000:
            f = out_dir / f"bgm_{t['id']}.mp3"
            f.write_bytes(a.content)
            print(f"[music] {t['name']} - {t['artist_name']}")
            return f, f"Music: \"{t['name']}\" by {t['artist_name']} (Jamendo) License: {t.get('license_ccurl', '')}"
    return None, None


def favorites():
    from . import pipeline
    return pipeline.load_state().get("bgm_favs", [])


def pick(out_dir, tags=None):
    """(파일 경로, 출처 문구) 또는 (None, None). 즐겨찾기 곡 우선."""
    if not enabled():
        return None, None
    favs = favorites()
    random.shuffle(favs)
    for fav in favs[:3]:
        try:
            res = _query(id=fav["id"])
            print(f"[music] 즐겨찾기 '{fav['name']}' 조회: {len(res)}건")
            if res:
                f, credit = download(res[0], out_dir)
                if f:
                    return f, credit
        except Exception as e:
            print("[music] 즐겨찾기 곡 실패:", e)
    if favs:  # 즐겨찾기가 있으면 그 곡만 쓴다 (다른 곡으로 대체하지 않음)
        print("[music] 즐겨찾기 곡을 받지 못함 → 배경음악 없이 진행")
        return None, "NONE"
    for t in search(tags, n=3):
        try:
            f, credit = download(t, out_dir)
            if f:
                return f, credit
        except Exception as e:
            print("[music] 다운로드 실패:", type(e).__name__)
    return None, None


def by_name(name):
    """곡 이름(또는 '곡 - 아티스트')으로 찾기. (곡, 사유) — 못 쓰는 곡이면 (None, 사유)."""
    title, _, artist = name.partition(" - ")
    params = {"namesearch": title.strip(), "limit": 20}
    if artist.strip():
        params["artist_name"] = artist.strip()
    res = _query(**params)
    if not res:
        return None, f"'{name}' 곡을 Jamendo에서 찾지 못했어요."
    ok = [t for t in res if _ok(t)]
    if not ok:
        t = res[0]
        return None, (f"'{t['name']} - {t['artist_name']}' 은(는) 상업적 이용 금지(NC) 라이선스라 "
                      f"수익화 채널에 쓸 수 없어요.")
    exact = [t for t in ok if t["name"].lower() == title.strip().lower()]
    return (exact or ok)[0], ""


def calm_candidates(n=3):
    """가수 없는(연주곡) 잔잔한 곡 후보: 상업적 이용 가능 + musicinfo 로 연주곡·느린 템포 확인."""
    out = []
    seen = set()
    for tag in ["lofi", "chill", "piano", "acoustic", "ambient", "jazz", "relaxing"]:
        try:
            res = _query(tags=tag, limit=50, vocalinstrumental="instrumental", order="popularity_total",
                         durationbetween="90_300", include="licenses musicinfo")
        except Exception as e:
            print("[music]", e)
            continue
        for t in res:
            mi = t.get("musicinfo") or {}
            if t["id"] in seen:
                continue
            if _ok(t) and mi.get("vocalinstrumental") == "instrumental" and mi.get("speed") in ("verylow", "low", "medium"):
                seen.add(t["id"])
                out.append(t)
                print(f"[music] 후보 {t['id']} | {t['name']} - {t['artist_name']} | {tag} | speed={mi.get('speed')} "
                      f"| {t.get('license_ccurl')}")
            if len([x for x in out if x in res]) >= 2:
                break
        if len(out) >= n * 2:
            break
    return out
