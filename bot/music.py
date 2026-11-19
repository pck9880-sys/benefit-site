"""Jamendo API 로 무료 배경음악 받기 (상업적 이용 가능한 CC 곡만, 보컬 없는 곡만).

키(JAMENDO_CLIENT_ID)가 없거나 실패하면 None → assets/bgm 의 저장된 곡을 쓴다.
"""
import random

import requests

from . import config

API = "https://api.jamendo.com/v3.0/tracks/"
MOODS = ["funk", "hiphop", "groove", "upbeat", "electronic", "lofi", "funky"]


def enabled():
    return bool(config.JAMENDO_CLIENT_ID) and not config.MOCK


def pick(out_dir, tags=None):
    """(파일 경로, 출처 문구) 또는 (None, None)."""
    if not enabled():
        return None, None
    tag = tags or random.choice(MOODS)
    try:
        r = requests.get(API, timeout=20, params={
            "client_id": config.JAMENDO_CLIENT_ID, "format": "json", "limit": 30, "tags": tag,
            "vocalinstrumental": "instrumental", "order": "popularity_month", "audiodlformat": "mp32",
            "include": "licenses", "durationbetween": "60_300"})
        res = r.json()
        if res.get("headers", {}).get("status") != "success":
            print("[music] jamendo 오류:", res.get("headers", {}).get("error_message"))
            return None, None
        ok = [t for t in res.get("results", [])
              if t.get("audiodownload_allowed", True) and "-nc" not in (t.get("license_ccurl") or "") 
              and (t.get("audiodownload") or t.get("audio"))]
        random.shuffle(ok)
        for t in ok[:5]:
            url = t.get("audiodownload") or t.get("audio")
            a = requests.get(url, timeout=60)
            if a.status_code == 200 and len(a.content) > 200_000:
                f = out_dir / f"bgm_{t['id']}.mp3"
                f.write_bytes(a.content)
                credit = (f"Music: \"{t['name']}\" by {t['artist_name']} (Jamendo) "
                          f"License: {t.get('license_ccurl', '')}")
                print(f"[music] {t['name']} - {t['artist_name']} ({tag})")
                return f, credit
        print(f"[music] '{tag}' 상업적 이용 가능한 곡 없음 ({len(res.get('results', []))}곡 중)")
    except Exception as e:
        print("[music] jamendo 실패:", type(e).__name__)
    return None, None
