"""주간 방문 리포트: Cloudflare Web Analytics(실제 브라우저 방문) → 텔레그램.
실행: python -m bot.report  (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, TELEGRAM_* 필요)"""
import datetime as dt
import json
import os
import urllib.request

from . import config

API = "https://api.cloudflare.com/client/v4/graphql"


def gql(query, variables):
    req = urllib.request.Request(API, data=json.dumps({"query": query, "variables": variables}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


Q = """query($a:String!,$s:Time!,$e:Time!){viewer{accounts(filter:{accountTag:$a}){
 total:rumPageloadEventsAdaptiveGroups(limit:1,filter:{datetime_geq:$s,datetime_lt:$e}){count sum{visits}}
 daily:rumPageloadEventsAdaptiveGroups(limit:10,filter:{datetime_geq:$s,datetime_lt:$e},orderBy:[date_ASC]){count sum{visits} dimensions{date}}
 pages:rumPageloadEventsAdaptiveGroups(limit:8,filter:{datetime_geq:$s,datetime_lt:$e},orderBy:[count_DESC]){count dimensions{requestPath}}
 refs:rumPageloadEventsAdaptiveGroups(limit:6,filter:{datetime_geq:$s,datetime_lt:$e},orderBy:[count_DESC]){count dimensions{refererHost}}
 dev:rumPageloadEventsAdaptiveGroups(limit:4,filter:{datetime_geq:$s,datetime_lt:$e},orderBy:[count_DESC]){count dimensions{deviceType}}
}}}"""


def fetch(days=7, end=None):
    end = end or dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start = end - dt.timedelta(days=days)
    r = gql(Q, {"a": os.environ["CLOUDFLARE_ACCOUNT_ID"], "s": start.isoformat() + "Z", "e": end.isoformat() + "Z"})
    if r.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "") for e in r["errors"]))
    return r["data"]["viewer"]["accounts"][0], start, end


def build():
    cur, s, e = fetch()
    prev, _, _ = fetch(end=s)
    pv = cur["total"][0]["count"] if cur["total"] else 0
    vi = cur["total"][0]["sum"]["visits"] if cur["total"] else 0
    ppv = prev["total"][0]["count"] if prev["total"] else 0
    diff = f"{(pv - ppv) / ppv * 100:+.0f}%" if ppv else "첫 주"
    kst = lambda t: (t + dt.timedelta(hours=9)).strftime("%m/%d")
    L = [f"📊 Benefy 주간 리포트 ({kst(s)}~{kst(e - dt.timedelta(seconds=1))})", "",
         f"방문 {vi:,}회 · 페이지뷰 {pv:,}회 (지난주 대비 {diff})", ""]
    if cur["daily"]:
        L.append("📅 일별 페이지뷰")
        mx = max(d["count"] for d in cur["daily"]) or 1
        for d in cur["daily"]:
            L.append(f"{d['dimensions']['date'][5:]} {'▇' * max(1, round(d['count'] / mx * 10))} {d['count']}")
        L.append("")
    if cur["pages"]:
        L.append("🔥 많이 본 페이지")
        L += [f"{i}. {p['dimensions']['requestPath']} — {p['count']}" for i, p in enumerate(cur["pages"], 1)]
        L.append("")
    if cur["refs"]:
        L.append("🔗 유입 경로")
        L += [f"· {r['dimensions']['refererHost'] or '직접 입력·북마크'} — {r['count']}" for r in cur["refs"]]
        L.append("")
    if cur["dev"]:
        L.append("📱 기기: " + " · ".join(f"{d['dimensions']['deviceType']} {d['count']}" for d in cur["dev"]))
    L += ["", "※ 실제 브라우저 방문만 집계 (봇 제외). 본인 확인 방문도 포함돼요."]
    return "\n".join(L)


def send(text):
    from . import telegram
    chat = config.TELEGRAM_CHAT_ID
    if not chat:
        try:
            chat = json.load(open(config.DATA_DIR / "state.json")).get("owner_chat_id")
        except Exception:
            chat = None
    if chat:
        telegram.send(chat, text)


if __name__ == "__main__":
    try:
        msg = build()
    except Exception as ex:  # 권한 부족 등은 원인을 그대로 알려줌
        msg = f"⚠️ 주간 리포트 생성 실패\n{ex}\n\nCloudflare API 토큰에 'Account Analytics: Read' 권한이 필요할 수 있어요."
    print(msg)
    send(msg)
