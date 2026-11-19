"""타입캐스트 음성 (키가 있을 때). 캐릭터 이름(예: 용식)으로 voice_id 를 자동으로 찾는다."""
import requests

from . import config

BASE = "https://api.typecast.ai"
_voice = {}


def enabled():
    return bool(config.TYPECAST_API_KEY) and not config.MOCK


def _h():
    return {"X-API-KEY": config.TYPECAST_API_KEY, "Content-Type": "application/json"}


def find_voices(name):
    r = requests.get(f"{BASE}/v3/voices", headers=_h(), timeout=30)
    r.raise_for_status()
    return [v for v in r.json() if name in ((v.get("voice_name") or {}).get("kor") or "")
            or name.lower() in ((v.get("voice_name") or {}).get("eng") or "").lower()]


def voice(name=None):
    """(voice_id, 모델) — 캐릭터 이름으로 검색 (기본 설정값)."""
    name = name or config.TYPECAST_VOICE_NAME
    if name in _voice:
        return _voice[name]
    vid = config.TYPECAST_VOICE_ID if name == config.TYPECAST_VOICE_NAME else ""
    model = "ssfm-v31"
    found = find_voices(name) if not vid else []
    if not vid:
        if not found:
            raise RuntimeError(f"타입캐스트에서 '{name}' 목소리를 찾지 못함")
        vid = found[0]["voice_id"]
        versions = [m["version"] for m in found[0].get("models", [])]
        model = next((v for v in ("ssfm-v31", "ssfm-v30", "ssfm-v21") if v in versions), versions[0] if versions else model)
    _voice[name] = (vid, model)
    return _voice[name]


def tts(text, out, prev="", nxt="", name=None):
    vid, model = voice(name)
    prompt = {"emotion_type": "smart", "previous_text": prev, "next_text": nxt} if model != "ssfm-v21" \
        else {"emotion_type": "preset", "emotion_preset": "normal"}
    r = requests.post(f"{BASE}/v1/text-to-speech", headers=_h(), timeout=60, json={
        "text": text, "voice_id": vid, "model": model, "language": "kor", "prompt": prompt,
        "output": {"audio_format": "mp3", "audio_tempo": config.TYPECAST_TEMPO, "target_lufs": -14,
                   "remove_silence_ms": 150}})
    if r.status_code != 200:
        raise RuntimeError(f"타입캐스트 HTTP {r.status_code}: {r.text[:200]}")
    out.write_bytes(r.content)
    return out


def check():
    """키·목소리 확인 결과 문장."""
    if not config.TYPECAST_API_KEY:
        return "타입캐스트 키(TYPECAST_API_KEY)가 아직 없어요."
    try:
        found = find_voices(config.TYPECAST_VOICE_NAME)
    except Exception as e:
        return f"타입캐스트 연결 실패: {e}"
    if not found:
        return f"타입캐스트 키는 정상인데 '{config.TYPECAST_VOICE_NAME}' 목소리는 API 목록에 없어요."
    lines = [f"- {(v.get('voice_name') or {}).get('kor')} ({v['voice_id']}) 모델 {[m['version'] for m in v.get('models', [])]}"
             for v in found[:5]]
    return f"✅ 타입캐스트 '{config.TYPECAST_VOICE_NAME}' 목소리 찾음\n" + "\n".join(lines)
