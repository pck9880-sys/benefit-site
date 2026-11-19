"""지금 뜨는 주제 수집: 한국 인기 쇼츠(YouTube Data API, 키가 있을 때) + 구글 실시간 검색어(RSS, 키 불필요)."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from . import config

HT = "{https://trends.google.com/trending/rss}"


def google_trends():
    try:
        r = requests.get("https://trends.google.com/trending/rss?geo=KR", timeout=20)
        root = ET.fromstring(r.content)
    except Exception as e:
        print("[trends] 구글 트렌드 실패:", type(e).__name__)
        return []
    out = []
    for it in root.iter("item"):
        news = [n.findtext(f"{HT}news_item_title") or "" for n in it.findall(f"{HT}news_item")]
        out.append({"src": "구글 검색어", "title": it.findtext("title") or "",
                    "traffic": it.findtext(f"{HT}approx_traffic") or "", "news": [x for x in news if x][:2]})
    return out


def _yt(path, **params):
    r = requests.get(f"https://www.googleapis.com/youtube/v3/{path}",
                     params={"key": config.YOUTUBE_API_KEY, **params}, timeout=20)
    r.raise_for_status()
    return r.json()


def _secs(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def hot_shorts(limit=25):
    """최근 이틀 동안 한국에서 조회수 많은 쇼츠 (60초 이하)."""
    if not config.YOUTUBE_API_KEY:
        return []
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        s = _yt("search", part="id", type="video", videoDuration="short", order="viewCount", regionCode="KR",
                relevanceLanguage="ko", publishedAfter=since, maxResults=50, q="#shorts")
        ids = [x["id"]["videoId"] for x in s.get("items", [])]
        if not ids:
            return []
        v = _yt("videos", part="snippet,statistics,contentDetails", id=",".join(ids))
    except Exception as e:
        print("[trends] 유튜브 실패:", type(e).__name__, str(e)[:120])
        return []
    out = []
    for it in v.get("items", []):
        if _secs(it["contentDetails"].get("duration")) > 75:
            continue
        sn = it["snippet"]
        if not re.search(r"[가-힣]", sn.get("title", "")):
            continue
        out.append({"src": "인기 쇼츠", "title": sn["title"], "channel": sn.get("channelTitle"),
                    "views": int(it["statistics"].get("viewCount", 0)), "tags": (sn.get("tags") or [])[:5]})
    out.sort(key=lambda x: -x["views"])
    return out[:limit]


def collect():
    shorts, trends = hot_shorts(), google_trends()
    lines = []
    for x in shorts:
        lines.append(f"- [인기 쇼츠 · 조회수 {x['views']:,}] {x['title']} (채널: {x['channel']})")
    for x in trends[:20]:
        news = " / ".join(x["news"])
        lines.append(f"- [구글 검색어 · {x['traffic']}] {x['title']}" + (f" — 관련 기사: {news}" if news else ""))
    return "\n".join(lines)
