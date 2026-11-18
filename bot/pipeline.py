"""매시간 실행: 텔레그램 승인 처리 → (하루 1회) 새 글 생성 → 자동 승인 → 상태 저장."""
import json
import traceback
from datetime import datetime, timedelta, timezone

from . import config, gov24, telegram, writer

KST = timezone(timedelta(hours=9))

HELP = (
    "🤖 자동 게시 봇\n\n"
    "매일 새 글 초안이 오면 ✅ 승인 / ❌ 거절 버튼만 눌러주세요.\n"
    f"응답이 없으면 {config.AUTO_APPROVE_HOURS:g}시간 후 자동 게시됩니다 (0이면 자동 게시 안 함).\n"
    "버튼은 최대 1시간 이내에 반영됩니다.\n\n"
    "명령어\n/status 현황\n/pause 일시정지\n/resume 재개\n/now 다음 실행 때 바로 글 생성\n/approveall 대기 초안 전부 승인\n"
    "/contest 다음 실행 때 공모전 출품안 받기\n/contestoff 공모전 알림 끄기 · /conteston 켜기"
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


def notify(st, text, buttons=None):
    if st.get("owner_chat_id"):
        return telegram.send(st["owner_chat_id"], text, buttons)
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
                      f"✅ 게시됨 ({how})\n{d['article']['title']}\n{config.SITE_URL}/posts/{d['id']}.html")


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
        elif text == "/now":
            st["force_generate"] = True
            notify(st, "다음 실행(1시간 이내) 때 새 글을 생성합니다.")
        elif text == "/approveall":
            n = len(drafts())
            for p in drafts():
                publish(st, p, "일괄 승인")
            notify(st, f"✅ {n}개 승인했습니다.")
        elif text == "/contest":
            st["contest_force"] = True
            notify(st, "🏆 다음 실행(1시간 이내) 때 공모전 출품안을 보내드릴게요.")
        elif text == "/contestoff":
            st["contest_off"] = True
            notify(st, "🏆 공모전 알림을 껐습니다. /conteston 으로 다시 켜기")
        elif text == "/conteston":
            st["contest_off"] = False
            notify(st, "🏆 공모전 알림을 켰습니다.")
        elif text == "/status":
            notify(st, status_text(st))
        else:
            notify(st, HELP)


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
    return t.hour >= config.GENERATE_HOUR_KST and st["last_generate_date"] != t.strftime("%Y-%m-%d")


def generate(st):
    month = now().strftime("%Y-%m")
    st["force_generate"] = False
    if st["cost"].get(month, 0) >= config.MAX_MONTHLY_USD:
        st["last_generate_date"] = now().strftime("%Y-%m-%d")
        notify(st, f"⚠️ 이번 달 비용 상한(${config.MAX_MONTHLY_USD:g})에 도달해 생성을 건너뜁니다.")
        return

    used = set(st["used_ids"])
    services = [s for s in gov24.list_services() if s.get("서비스ID") and s["서비스ID"] not in used
                and s.get("지원내용") and s.get("지원대상")]
    services.sort(key=lambda s: int(s.get("조회수") or 0), reverse=True)  # 많이 찾는 것부터
    st["last_generate_date"] = now().strftime("%Y-%m-%d")  # 목록 조회 성공 후에만 '오늘 완료' 처리

    made = 0
    for svc in services:
        if made >= config.POSTS_PER_DAY:
            break
        sid = svc["서비스ID"]
        st["used_ids"].append(sid)
        try:
            detail = gov24.service_detail(sid)
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
            },
            "article": article.model_dump(),
            "cost_usd": round(cost, 5),
        }
        path = config.DRAFTS_DIR / f"{sid}.json"
        save_json(path, d)
        made += 1
        if telegram.enabled() and st.get("owner_chat_id"):
            a = d["article"]
            preview = (
                f"📝 새 초안 ({made}/{config.POSTS_PER_DAY})\n\n{a['title']}\n\n"
                + "\n".join(f"• {p}" for p in a["summary_points"])
                + f"\n\n출처: {d['source']['url'] or '-'}\n비용: ${cost:.4f}"
            )
            d["message_id"] = notify(st, preview, [[{"text": "✅ 승인", "callback_data": f"ok:{sid}"},
                                                    {"text": "❌ 거절", "callback_data": f"no:{sid}"}]])
            save_json(path, d)
    print(f"generated {made} drafts")


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


def tick():
    from . import contest
    st = load_state()
    try:
        handle_updates(st)  # 텔레그램 주인 등록·명령어는 항상 처리
        if benefit_ready():
            if should_generate(st):
                generate(st)
            auto_approve(st)
        else:
            print("지원금 사이트: API 키가 없어 글 생성은 건너뜁니다.")
        contest.run(st, notify)
    except Exception:
        err = traceback.format_exc()
        print(err)
        notify(st, "⚠️ 오류 발생\n" + err[-1500:])
        raise
    finally:
        save_json(config.STATE_FILE, st)
