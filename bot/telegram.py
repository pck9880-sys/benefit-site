"""텔레그램 승인 봇 - 서버 없이 동작 (매시간 getUpdates로 버튼 클릭을 확인)."""
import requests

from . import config

last_error = ""


def enabled():
    return bool(config.TELEGRAM_BOT_TOKEN) and not config.MOCK


def _call(method, **payload):
    if not enabled():
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}", json=payload, timeout=30
        )
        data = r.json()
        if not data.get("ok"):
            global last_error
            last_error = f"{method}: {data.get('error_code')} {data.get('description')}"
            print("[telegram]", last_error)
            return None
        return data.get("result")
    except requests.RequestException as e:
        last_error = f"{method}: {type(e).__name__}"
        print("[telegram]", last_error)
        return None


def send(chat_id, text, buttons=None, html=False):
    payload = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
    if html:
        payload["parse_mode"] = "HTML"
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    res = _call("sendMessage", **payload)
    return res.get("message_id") if res else None


def edit(chat_id, message_id, text):
    _call("editMessageText", chat_id=chat_id, message_id=message_id, text=text[:4000],
          disable_web_page_preview=True)


def get_updates(offset):
    return _call("getUpdates", offset=offset, timeout=0, allowed_updates=["message", "callback_query"]) or []


def answer_callback(cb_id, text):
    _call("answerCallbackQuery", callback_query_id=cb_id, text=text)


def send_audio(chat_id, url, title, performer, buttons=None):
    """URL 의 음악을 텔레그램 미리듣기로 보냄 (텔레그램이 직접 받아감)."""
    payload = {"chat_id": chat_id, "audio": url, "title": title[:60], "performer": performer[:60]}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return _call("sendAudio", **payload)
