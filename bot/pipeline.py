"""매시간 실행: 텔레그램 승인 처리 → (하루 1회) 새 글 생성 → 자동 승인 → 상태 저장."""
import json
import traceback
from datetime import datetime, timedelta, timezone

from . import config, gov24, telegram, writer

KST = timezone(timedelta(hours=9))

HELP = (
    "🤖 자동 게시 봇\n\n"
    "지원금 글은 4시간마다 2개씩(글 150개 이후엔 1개씩) 자동 게시되고, 결과는 저녁 9시 KPI 리포트로 알려드려요.\n"
    f"응답이 없으면 {round(config.AUTO_APPROVE_HOURS * 60)}분 뒤 다음 확인 때 자동 게시됩니다.\n"
    "버튼은 15분 안에 반영되고, 반영되면 메시지가 「✅ 게시됨」으로 바뀝니다.\n\n"
    "명령어\n/status 현황\n/pause 일시정지\n/resume 재개\n/now 다음 실행 때 바로 글 생성\n/approveall 대기 초안 전부 승인\n"
    "/post 지금 글 1개 올리기 · /post 3 (3개) · /post 청년 월세 (주제 지정)\n/kpi 성과 리포트 보기 (매일 저녁 9시 자동 전송)\n/contest 다음 실행 때 공모전 출품안 받기\n/contestoff 공모전 알림 끄기 · /conteston 켜기\n/shorts 지금 이슈 숏츠 1개 만들기 (기본 목소리 태우 · /shorts 창수 → 박창수)\n/bgm 배경음악 후보 듣고 고르기 (/bgm funk 처럼 장르 지정 · /bgmadd 곡이름 으로 직접 추가 · /bgmlist 목록 · /bgmclear 자동 선택)"
)


def now():
    return datetime.now(KST)


def load_json(path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), "utf-8")


def load_state():
    st = load_json(config.STATE_FILE, {})
    st.setdefault("owner_chat_id", config.TELEGRAM_CHAT_ID or None)
    st.setdefault("tg_offset", 0)
    st.setdefault("last_generate_date", "")
    st.setdefault("paused", False)
    st.setdefault("force_generate", False)
    st.setdefault("cost", {})
    st.setdefault("used_ids", [])
    return st


def drafts():
    return sorted(config.DRAFTS_DIR.glob("*.json"))


def notify(st, text, buttons=None, html=False):
    if st.get("owner_chat_id"):
        return telegram.send(st["owner_chat_id"], text, buttons, html=html)
    return None


# ---------- 게시 / 거절 ----------
def publish(st, path, how):
    d = load_json(path, None)
    if not d:
        return
    d["published_at"] = now().isoformat()
    save_json(config.POSTS_DIR / path.name, d)
    path.unlink()
    if d.get("message_id") and st.get("owner_chat_id"):
        telegram.edit(st["owner_chat_id"], d["message_id"],
                      f"✅ 게시됨 ({how})\n{d['article']['title']}\n{config.SITE_URL}/posts/{d['id']}")


def reject(st, path):
    d = load_json(path, None)
    if not d:
        return
    path.unlink()
    if d.get("message_id") and st.get("owner_chat_id"):
        telegram.edit(st["owner_chat_id"], d["message_id"], f"❌ 거절됨\n{d['article']['title']}")


# ---------- 텔레그램 입력 처리 ----------
def handle_updates(st):
    if not telegram.enabled():
        return
    for u in telegram.get_updates(st["tg_offset"] + 1):
        st["tg_offset"] = max(st["tg_offset"], u["update_id"])
        msg = u.get("message")
        cb = u.get("callback_query")
        chat_id = (msg or {}).get("chat", {}).get("id") or (cb or {}).get("message", {}).get("chat", {}).get("id")
        if not chat_id:
            continue
        if not st["owner_chat_id"] and msg and msg.get("chat", {}).get("type") == "private":
            st["owner_chat_id"] = chat_id  # 첫 메시지를 보낸 사람이 주인
            telegram.send(chat_id, "✅ 주인으로 등록되었습니다.\n\n" + HELP)
            continue
        if str(chat_id) != str(st["owner_chat_id"]):
            continue  # 다른 사람 무시

        if cb:
            action, _, sid = (cb.get("data") or "").partition(":")
            if action in ("bgm", "bgmdel"):
                handle_bgm_button(st, cb, action, sid)
                continue
            path = config.DRAFTS_DIR / f"{sid}.json"
            telegram.answer_callback(cb["id"], "처리했습니다")
            if path.exists():
                publish(st, path, "승인") if action == "ok" else reject(st, path)
            continue

        text = (msg.get("text") or "").strip().split("@")[0]
        if text == "/pause":
            st["paused"] = True
            notify(st, "⏸ 일시정지했습니다. /resume 으로 재개")
        elif text == "/resume":
            st["paused"] = False
            notify(st, "▶️ 재개했습니다.")
        elif text.startswith("/post") or text.startswith("/글"):
            arg = text.split(maxsplit=1)[1].strip() if " " in text else ""
            if not arg:
                req = {"count": 1}
            elif arg.isdigit():
                req = {"count": max(1, min(int(arg), 10))}
            else:
                req = {"keyword": arg[:30], "count": 1}
            st.setdefault("post_requests", []).append(req)
            what = f"'{req['keyword']}' 관련 글 1개" if req.get("keyword") else f"글 {req['count']}개"
            notify(st, f"📝 요청 받았어요. {what}를 지금 만들고 있어요 (1~3분 뒤 링크를 보내드려요)")
        elif text == "/now":
            st["force_generate"] = True
            notify(st, "다음 실행(15분 이내) 때 새 글을 생성합니다.")
        elif text == "/approveall":
            n = len(drafts())
            for p in drafts():
                publish(st, p, "일괄 승인")
            notify(st, f"✅ {n}개 승인했습니다.")
        elif text == "/contest":
            st["contest_force"] = True
            notify(st, "🏆 다음 실행(15분 이내) 때 공모전 출품안을 보내드릴게요.")
        elif text == "/contestoff":
            st["contest_off"] = True
            notify(st, "🏆 공모전 알림을 껐습니다. /conteston 으로 다시 켜기")
        elif text == "/conteston":
            st["contest_off"] = False
            notify(st, "🏆 공모전 알림을 켰습니다.")
        elif text.startswith("/shorts"):
            st["shorts_request"] = now().isoformat(timespec="seconds")
            if "창수" in text or "박창수" in text:
                st["shorts_voice_req"] = {"voice": "박창수", "at": st["shorts_request"]}
            notify(st, "🎬 숏츠를 만들기 시작할게요 (영상 완성까지 약 5~10분)")
        elif text.startswith("/bgm"):
            handle_bgm_command(st, text)
        elif text == "/kpi":
            from . import kpi
            notify(st, kpi.report(st))
        elif text == "/status":
            notify(st, status_text(st))
        else:
            notify(st, HELP)


def handle_bgm_command(st, text):
    """/bgm [장르] 후보 3곡 미리듣기 · /bgmlist 즐겨찾기 · /bgmclear 즐겨찾기 비우기(자동 선택)"""
    from . import music
    if not music.enabled():
        notify(st, "🎵 Jamendo 키(JAMENDO_CLIENT_ID)가 없어서 곡을 고를 수 없어요.")
        return
    favs = st.setdefault("bgm_favs", [])
    if text.startswith("/bgmclear"):
        st["bgm_favs"] = []
        notify(st, "🎵 즐겨찾기를 비웠어요. 이제 인기곡 중에서 자동으로 골라요.")
        return
    if text.startswith("/bgmadd"):
        name = text.split(maxsplit=1)[1].strip() if " " in text else ""
        if not name:
            notify(st, "🎵 곡 이름을 같이 보내주세요. 예: /bgmadd Soul Fashion Lounge  (아티스트까지: /bgmadd 곡 - 아티스트)")
            return
        try:
            t, why = music.by_name(name)
        except Exception as e:
            t, why = None, f"검색 실패: {e}"
        if not t:
            notify(st, "🎵 " + why)
            return
        info = {"id": str(t["id"]), "name": t["name"], "artist": t["artist_name"]}
        if all(f["id"] != info["id"] for f in favs):
            favs.append(info)
            st["bgm_favs"] = favs[-20:]
        telegram.send_audio(st.get("owner_chat_id") or config.TELEGRAM_CHAT_ID, t.get("audio") or t.get("audiodownload"),
                            t["name"], t["artist_name"])
        notify(st, f"⭐ '{t['name']} - {t['artist_name']}' 즐겨찾기에 추가했어요. (즐겨찾기 {len(st['bgm_favs'])}곡)")
        return
    if text.startswith("/bgmlist"):
        if not favs:
            notify(st, "🎵 즐겨찾기 곡이 없어요. /bgm 으로 후보를 들어보고 ⭐ 를 눌러주세요.")
            return
        notify(st, "🎵 숏츠에 쓰는 즐겨찾기 곡 (누르면 삭제)",
               buttons=[[{"text": f"🗑 {f['name']} - {f['artist']}"[:60], "callback_data": f"bgmdel:{f['id']}"}] for f in favs])
        return
    tag = text.split(maxsplit=1)[1].strip().lower() if " " in text else None
    tracks = music.search(tag, n=3)
    if not tracks:
        notify(st, f"🎵 '{tag}' 장르에서 상업적으로 쓸 수 있는 곡을 못 찾았어요. 예: /bgm funk, /bgm hiphop, /bgm lofi")
        return
    notify(st, f"🎵 후보 {len(tracks)}곡이에요{f' ({tag})' if tag else ''}. 들어보고 마음에 들면 ⭐ 를 눌러주세요.\n"
               "다른 후보: /bgm 다시 · 장르 지정: /bgm funk · 목록: /bgmlist")
    chat = st.get("owner_chat_id") or config.TELEGRAM_CHAT_ID
    for t in tracks:
        telegram.send_audio(chat, t.get("audio") or t.get("audiodownload"), t["name"], t["artist_name"],
                            buttons=[[{"text": "⭐ 이 곡 쓰기", "callback_data": f"bgm:{t['id']}"}]])
    st["bgm_last"] = {str(t["id"]): {"id": str(t["id"]), "name": t["name"], "artist": t["artist_name"]} for t in tracks}


def handle_bgm_button(st, cb, action, tid):
    favs = st.setdefault("bgm_favs", [])
    if action == "bgm":
        info = (st.get("bgm_last") or {}).get(tid, {"id": tid, "name": f"곡 {tid}", "artist": ""})
        if all(f["id"] != tid for f in favs):
            favs.append(info)
            st["bgm_favs"] = favs[-20:]
        telegram.answer_callback(cb["id"], "⭐ 즐겨찾기에 추가했어요")
        notify(st, f"⭐ '{info['name']}' 추가! 이제 숏츠는 즐겨찾기 {len(st['bgm_favs'])}곡 중에서 골라요. (/bgmlist)")
    else:
        st["bgm_favs"] = [f for f in favs if f["id"] != tid]
        telegram.answer_callback(cb["id"], "삭제했어요")
        notify(st, f"🗑 삭제했어요. 남은 즐겨찾기 {len(st['bgm_favs'])}곡")


def status_text(st):
    month = now().strftime("%Y-%m")
    n_posts = len(list(config.POSTS_DIR.glob("*.json")))
    return (
        f"📊 현황\n게시글: {n_posts}개\n승인 대기: {len(drafts())}개\n"
        f"이번 달 API 비용: ${st['cost'].get(month, 0):.3f} (상한 ${config.MAX_MONTHLY_USD:g})\n"
        f"상태: {'⏸ 일시정지' if st['paused'] else '▶️ 동작 중'}\n사이트: {config.SITE_URL}\n"
        f"공모전: {'꺼짐' if st.get('contest_off') else '켜짐'} · 지금까지 {len(st.get('contest_seen', []))}건 확인"
    )


# ---------- 새 글 생성 ----------
def should_generate(st):
    if st["paused"]:
        return False
    if st["force_generate"]:
        return True
    t = now()
    if config.SCHEDULE == "hourly":
        every = max(1, config.GENERATE_EVERY_HOURS)
        return t.hour % every == 0 and st.get("last_generate_hour") != t.strftime("%Y-%m-%d %H")
    return t.hour >= config.GENERATE_HOUR_KST and st["last_generate_date"] != t.strftime("%Y-%m-%d")


def generate(st, picks=None, want=None, announce=False):
    """picks/want 를 주면 요청받은 글만 바로 만든다 (텔레그램 /post 명령)."""
    month = now().strftime("%Y-%m")
    if picks is None:
        st["force_generate"] = False
    if st["cost"].get(month, 0) >= config.MAX_MONTHLY_USD:
        st["last_generate_date"] = now().strftime("%Y-%m-%d")
        notify(st, f"⚠️ 이번 달 비용 상한(${config.MAX_MONTHLY_USD:g})에 도달해 생성을 건너뜁니다.")
        return

    used = set(st["used_ids"])
    queue = [q for q in st.get("queue", []) if q.get("서비스ID") not in used]
    if picks is None and len(queue) < 5:  # 대기열이 비면 정부24 목록을 다시 받아 많이 찾는 순으로 채움
        gov24_all = gov24.list_services()
        services = [s for s in gov24_all if s.get("서비스ID") and s["서비스ID"] not in used
                    and s.get("지원내용") and s.get("지원대상")]
        services.sort(key=lambda s: int(s.get("조회수") or 0), reverse=True)
        try:  # 실제 검색 수요(자동완성) 순으로 다시 정렬
            from . import demand
            services = demand.rank(services)
        except Exception as e:
            print(f"[demand] 건너뜀: {e}")
        keep = ["서비스ID", "서비스명", "서비스분야", "소관기관명", "조회수", "지원대상", "지원내용", "신청방법",
                "신청기한", "상세조회URL", "사용자구분", "전화문의", "수정일시", "선정기준", "서비스목적요약", "지원유형", "_q", "_demand"]
        # 이미 게시한 글 중 정부 데이터가 수정된 것은 다시 쓰기 대기열에 넣음
        latest = {x["서비스ID"]: x for x in gov24_all if x.get("서비스ID")}
        for p in config.POSTS_DIR.glob("*.json"):
            d0 = load_json(p, {})
            new = latest.get(d0.get("id"))
            if new and new.get("수정일시") and new.get("수정일시") != d0.get("source", {}).get("updated") \
                    and d0.get("id") not in st.setdefault("refresh", []):
                st["refresh"].append(d0["id"])
        from . import taxonomy
        local = [x for x in services if taxonomy.region_of(x.get("소관기관명")) != "national"]
        national = [x for x in services if taxonomy.region_of(x.get("소관기관명")) == "national"]
        mixed = []  # 전국 2개 : 지역 1개 비율로 섞어 지역별 모음 페이지도 채움
        while (national or local) and len(mixed) < 60:
            mixed += national[:2] + local[:1]
            national, local = national[2:], local[1:]
        queue = [{k: s.get(k) for k in keep if s.get(k)} for s in mixed[:60]]
    if picks is None and queue and not any("_demand" in q for q in queue):  # 예전 대기열도 검색 수요 순으로 재정렬
        try:
            from . import demand
            queue = demand.rank(queue)
        except Exception as e:
            print(f"[demand] 건너뜀: {e}")
    if picks is not None:  # 요청 글: 대기열·정기 일정은 건드리지 않음
        services, limit = [x for x in picks if x.get("서비스ID") not in used], want
    else:
        services = queue
        st["last_generate_date"] = now().strftime("%Y-%m-%d")  # 목록 조회 성공 후에만 '오늘 완료' 처리
        st["last_generate_hour"] = now().strftime("%Y-%m-%d %H")
        limit = config.POSTS_PER_HOUR if config.SCHEDULE == "hourly" else config.POSTS_PER_DAY
        if config.SCHEDULE == "hourly" and len(list(config.POSTS_DIR.glob("*.json"))) >= config.SLOWDOWN_AFTER_POSTS:
            limit = 1  # 글이 충분히 쌓이면 속도를 줄여 대량 생성으로 보이지 않게
        refresh_one(st, month)
    published = []
    made = 0
    for svc in services:
        if made >= limit:
            break
        sid = svc["서비스ID"]
        st["used_ids"].append(sid)
        try:
            detail = gov24.service_detail(sid)
            try:
                cond = gov24.support_conditions(sid)
            except Exception:
                cond = None
            article, cost = writer.write_article(svc, detail)
        except Exception as e:  # 한 건 실패해도 계속
            print(f"[skip] {sid}: {e}")
            continue
        st["cost"][month] = round(st["cost"].get(month, 0) + cost, 5)
        d = {
            "id": sid,
            "created_at": now().isoformat(),
            "source": {
                "name": svc.get("서비스명"),
                "org": svc.get("소관기관명") or detail.get("소관기관명"),
                "field": svc.get("서비스분야") or "기타",
                "user_type": svc.get("사용자구분"),
                "deadline": svc.get("신청기한") or detail.get("신청기한"),
                "url": svc.get("상세조회URL"),
                "apply_url": detail.get("온라인신청사이트URL"),
                "contact": detail.get("문의처") or svc.get("전화문의"),
                "updated": svc.get("수정일시"),
                "cond": cond,
            },
            "article": article.model_dump(),
            "cost_usd": round(cost, 5),
        }
        path = config.DRAFTS_DIR / f"{sid}.json"
        save_json(path, d)
        made += 1
        if not config.REQUIRE_APPROVAL or announce:
            publish(st, path, "요청" if announce else "자동")  # 승인 없이 바로 게시
            published.append(d)
            continue
        if telegram.enabled() and st.get("owner_chat_id"):
            a = d["article"]
            preview = (
                f"📝 새 초안 ({made}/{limit})\n\n{a['title']}\n\n"
                + "\n".join(f"• {p}" for p in a["summary_points"])
                + f"\n\n출처: {d['source']['url'] or '-'}\n비용: ${cost:.4f}"
            )
            d["message_id"] = notify(st, preview, [[{"text": "✅ 승인", "callback_data": f"ok:{sid}"},
                                                    {"text": "❌ 거절", "callback_data": f"no:{sid}"}]])
            save_json(path, d)
    done = set(st["used_ids"])
    st["queue"] = [q for q in queue if q.get("서비스ID") not in done]
    print(f"generated {made} posts")
    if announce:
        if published:
            notify(st, "✅ 요청하신 글을 올렸어요 (사이트 반영까지 약 2분)\n\n" + "\n\n".join(
                f"• {x['article']['title']}\n{config.SITE_URL}/posts/{x['id']}" for x in published))
        else:
            notify(st, "⚠️ 요청하신 글을 만들지 못했어요. 이미 올린 주제이거나 정부 데이터에서 찾지 못했어요.")


def handle_requests(st):
    """텔레그램으로 받은 글 요청 처리: {'count': n} 또는 {'keyword': '...'}"""
    reqs = st.pop("post_requests", [])
    for r in reqs:
        used = set(st["used_ids"])
        if r.get("keyword"):
            try:
                kw = r["keyword"]
                found = gov24.search(kw)
                if not found and " " in kw:  # "청년 월세" → "청년"으로 찾고 모든 단어가 들어간 것만
                    words = kw.split()
                    found = [x for x in gov24.search(words[0])
                             if all(w in (x.get("서비스명") or "").replace(" ", "") for w in words)]
            except Exception as e:
                notify(st, f"⚠️ 검색 실패: {e}")
                continue
            found = [x for x in found if x.get("서비스ID") not in used and x.get("지원내용")]
            found.sort(key=lambda x: int(x.get("조회수") or 0), reverse=True)
            if not found:
                notify(st, f"🔎 '{r['keyword']}' 관련 지원제도 중 아직 안 올린 것을 찾지 못했어요.")
                continue
            generate(st, picks=found, want=r.get("count", 1), announce=True)
        else:
            queue = [q for q in st.get("queue", []) if q.get("서비스ID") not in used]
            if len(queue) < r["count"]:
                generate(st, picks=None)  # 대기열 채우기 겸 정기 생성
                queue = [q for q in st.get("queue", []) if q.get("서비스ID") not in set(st["used_ids"])]
            generate(st, picks=queue, want=r["count"], announce=True)


# ---------- 자동 승인 ----------
def auto_approve(st):
    # 텔레그램이 없으면 승인 절차 없이 바로 게시
    no_approval = not telegram.enabled() or not st.get("owner_chat_id")
    for p in drafts():
        d = load_json(p, {})
        age_h = (now() - datetime.fromisoformat(d["created_at"])).total_seconds() / 3600
        if no_approval or (config.AUTO_APPROVE_HOURS > 0 and age_h >= config.AUTO_APPROVE_HOURS):
            publish(st, p, "자동")


def benefit_ready():
    return config.MOCK or bool(config.DATA_GO_KR_KEY and config.ANTHROPIC_API_KEY)


def refresh_one(st, month):
    """정부 데이터가 바뀐 기존 글 1개를 최신 내용으로 다시 쓴다 (주소·게시일은 유지)."""
    queue = st.get("refresh") or []
    while queue:
        sid = queue.pop(0)
        path = config.POSTS_DIR / f"{sid}.json"
        if not path.exists():
            continue
        d = load_json(path, {})
        try:
            items = [x for x in gov24.list_services_by_id(sid)] if hasattr(gov24, "list_services_by_id") else []
            svc = items[0] if items else {"서비스ID": sid, "서비스명": d["source"].get("name")}
            detail = gov24.service_detail(sid)
            svc = {**svc, **{k: v for k, v in detail.items() if v}}
            article, cost = writer.write_article(svc, detail)
        except Exception as e:
            print(f"[refresh] {sid} 실패: {e}")
            return
        st["cost"][month] = round(st["cost"].get(month, 0) + cost, 5)
        d["article"] = article.model_dump()
        d["source"]["updated"] = svc.get("수정일시") or d["source"].get("updated")
        d["updated_at"] = now().isoformat()
        save_json(path, d)
        print(f"[refresh] {sid} 최신 내용으로 갱신")
        return


def backfill_conditions(limit=15):
    """자격 조건이 없는 기존 글에 정부 데이터의 자격 조건을 채운다 (실행당 최대 limit 개)."""
    n = 0
    for p in config.POSTS_DIR.glob("*.json"):
        if n >= limit:
            break
        d = load_json(p, {})
        if d.get("source", {}).get("cond") is not None:
            continue
        try:
            d["source"]["cond"] = gov24.support_conditions(d["id"])
        except Exception as e:
            print(f"[cond] {d['id']} 실패: {e}")
            d["source"]["cond"] = {"codes": [], "age_min": None, "age_max": None}
        save_json(p, d)
        n += 1


def tick():
    from . import contest
    st = load_state()
    st["check"] = {"telegram_token_loaded": telegram.enabled(),  # 값은 기록하지 않고 읽혔는지만
                   "anthropic_key_loaded": bool(config.ANTHROPIC_API_KEY),
                   "submit_info_loaded": {k: bool(v) for k, v in __import__("bot.submit", fromlist=["me"]).me().items()},
                   "at": now().isoformat(timespec="minutes")}
    try:
        handle_updates(st)  # 텔레그램 주인 등록·명령어는 항상 처리
        if benefit_ready():
            if st.get("post_requests"):
                handle_requests(st)
            t = now()
            if t.hour >= config.NEWS_HOUR_KST and st.get("news_date") != t.strftime("%Y-%m-%d"):
                st["news_date"] = t.strftime("%Y-%m-%d")
                try:  # 오늘 뜨는 지원금 뉴스 → 알림 + 정부24에 있으면 대기열 맨 앞
                    from . import news
                    news.run(st, notify, gov24, set(st["used_ids"]))
                except Exception as e:
                    print(f"[news] 건너뜀: {e}")
            if should_generate(st):
                generate(st)
            auto_approve(st)
            backfill_conditions()
            from . import blog
            blog.run(st, notify)
        else:
            print("지원금 사이트: API 키가 없어 글 생성은 건너뜁니다.")
        if config.CONTESTS_ON:  # 공모전 중단 중
            contest.run(st, notify)
        from . import kpi
        kpi.run(st, notify)
    except Exception:
        err = traceback.format_exc()
        print(err)
        notify(st, "⚠️ 오류 발생\n" + err[-1500:])
        raise
    finally:
        save_json(config.STATE_FILE, st)
