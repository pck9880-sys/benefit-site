"""분위기별 인기곡 배경음악 (Mac 로컬 음원 폴더에서 고름).

- 음원 폴더: ~/쇼츠작업/음원/<분위기>/*.mp3  (SHORTS_SONG_DIR 로 변경 가능)
  분위기 = 감동 / 웃긴글 / 기본. 저작권 곡이라 저장소(git)에는 올리지 않는다.
- 곡별 설정(선택): ~/쇼츠작업/음원/songs.json
  {"꿈꾸던 어른이 되었나요.mp3": {"start": 42, "credit": "곡명 - 가수"}}
  start = 하이라이트 시작 초. 없으면 곡 길이의 30% 지점부터.
- plan.json 에 "mood": "감동" 을 쓰면 그 분위기, 없으면 주제로 추정 (기본값 '기본').
  특정 곡을 지정하려면 "song": "파일이름.mp3" (분위기 폴더 안 또는 음원 폴더 기준 경로).
- 주의: 상업 음원은 유튜브 Content ID 로 수익이 원곡자에게 가거나 일부 국가에서 차단될 수 있다.
"""
import json
import os
import random
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("SHORTS_SONG_DIR", str(Path.home() / "쇼츠작업" / "음원")))
MOODS = ("감동", "웃긴글", "기본")
KEYWORDS = {
    "감동": ("감동", "위로", "눈물", "응원", "어른", "꿈", "가족", "엄마", "아빠", "고마", "추억"),
    "웃긴글": ("웃긴", "유머", "ㅋㅋ", "레전드", "웃음", "황당", "개그", "썰"),
}
EXT = ("*.mp3", "*.m4a", "*.wav")
LUFS_UNDER_VOICE = float(os.environ.get("SHORTS_SONG_LUFS", "-26"))  # 더빙 아래 깔 때
LUFS_MAIN = float(os.environ.get("SHORTS_SONG_LUFS_MAIN", "-16"))  # 더빙 없이 음악이 주인공일 때


def mood_of(raw):
    m = (raw.get("mood") or "").strip()
    if m in MOODS:
        return m
    text = " ".join(str(raw.get(k, "")) for k in ("topic", "title_top", "title_bottom", "yt_title"))
    for mood, words in KEYWORDS.items():
        if any(w in text for w in words):
            return mood
    return "기본"


def _length(f):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                             capture_output=True, text=True, timeout=20).stdout
        return float(out.strip())
    except Exception:
        return 0.0


def _meta():
    f = ROOT / "songs.json"
    try:
        return json.loads(f.read_text("utf-8")) if f.exists() else {}
    except Exception as ex:
        print("[songs] songs.json 읽기 실패:", ex)
        return {}


def pick(raw, main=False):
    """bgm 설정 dict {file, start, lufs, credit} 또는 None (음원 없음).
    기본은 꺼짐 (2026-11-20: 음악은 미리 깔지 않고 유튜브 '저장됨' 사운드 사용). SHORTS_SONG_PREMIX=1 일 때만."""
    if os.environ.get("SHORTS_SONG_PREMIX") != "1":
        return None
    fixed = os.environ.get("SHORTS_SONG_FILE")  # 순서대로 정해진 곡 파일 (shorts_chrome_prep.sh)
    if fixed and Path(fixed).exists():
        f = Path(fixed)
        m = _meta().get(f.name, {})
        start = m.get("start")
        if start is None:
            bl = _length(f)
            start = round(bl * 0.3, 1) if bl > 60 else 0
        print(f"[songs] 지정 곡 {f.name} ({start}초부터)")
        return {"file": str(f), "start": float(start), "lufs": LUFS_MAIN if main else LUFS_UNDER_VOICE,
                "credit": m.get("credit") or f"Music: {f.stem}", "mood": mood_of(raw)}
    mood = mood_of(raw)
    want = raw.get("song")
    f = None
    if want:
        for c in (ROOT / mood / want, ROOT / want, Path(want).expanduser()):
            if c.exists():
                f = c
                break
        if not f:
            print(f"[songs] 지정 곡 없음: {want}")
    if not f:
        files = [x for pat in EXT for x in (ROOT / mood).glob(pat)]
        if not files and mood != "기본":
            files = [x for pat in EXT for x in (ROOT / "기본").glob(pat)]
        if not files:
            print(f"[songs] {ROOT / mood} 에 음원 없음 → 기존 배경음악 사용")
            return None
        f = random.choice(sorted(files))
    m = _meta().get(f.name, {})
    start = m.get("start")
    if start is None:
        bl = _length(f)
        start = round(bl * 0.3, 1) if bl > 60 else 0
    print(f"[songs] 분위기 {mood} → {f.name} ({start}초부터)")
    return {"file": str(f), "start": float(start), "lufs": LUFS_MAIN if main else LUFS_UNDER_VOICE,
            "credit": m.get("credit") or f"Music: {f.stem}", "mood": mood}


def ensure_dirs():
    for m in MOODS:
        (ROOT / m).mkdir(parents=True, exist_ok=True)
    return ROOT
