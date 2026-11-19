"""IndexNow: 새로 생긴 페이지를 네이버·Bing 등에 바로 알림 (로그인 불필요한 공개 표준)."""
import json
import re
from urllib.parse import quote

import requests

from . import config

KEY_FILE = config.ROOT / "static" / "indexnow-key.txt"
SENT_FILE = config.DATA_DIR / "indexnow_sent.json"
ENDPOINTS = ["https://searchadvisor.naver.com/indexnow", "https://api.indexnow.org/indexnow"]


def run():
    if "localhost" in config.SITE_URL or "github.io" in config.SITE_URL:
        return
    key = KEY_FILE.read_text().strip()
    sitemap = (config.OUT_DIR / "sitemap.xml").read_text("utf-8")
    urls = [quote(u, safe=":/?=&%#") for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)]  # 한글 주소 인코딩
    sent = set(json.loads(SENT_FILE.read_text("utf-8"))) if SENT_FILE.exists() else set()
    new = [u for u in urls if u not in sent][:1000]
    if not new:
        print("[indexnow] 새 주소 없음")
        return
    host = re.sub(r"^https?://", "", config.SITE_URL).split("/")[0]
    body = {"host": host, "key": key, "keyLocation": f"{config.SITE_URL}/{key}.txt", "urlList": new}
    ok = False
    for ep in ENDPOINTS:
        try:
            r = requests.post(ep, json=body, timeout=30)
            print(f"[indexnow] {ep} → {r.status_code}")
            ok = ok or r.status_code in (200, 202)
        except requests.RequestException as e:
            print(f"[indexnow] {ep} 실패: {type(e).__name__}")
    if ok:
        SENT_FILE.write_text(json.dumps(sorted(sent | set(new)), ensure_ascii=False), "utf-8")
