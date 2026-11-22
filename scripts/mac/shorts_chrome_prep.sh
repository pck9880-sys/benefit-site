#!/bin/zsh
# 숏츠 1편: 로컬 작업 폴더 정리 → 크롬 Claude 로 타입캐스트 더빙 → 더빙 렌더 → iCloud Drive/쇼츠업로드 에 전달(사용자가 앱으로 업로드).
# 사용: scripts/mac/shorts_chrome_prep.sh <slug>
#   SHORTS_DUB_ONLY=1  더빙만 하고 끝 (이미지 생성과 동시에 돌릴 때)
#   SHORTS_PUBLISH=0   테스트(비공개)
#   SHORTS_CHROME_MODEL 크롬 단계 모델 (기본 sonnet: 버튼 조작이라 가볍게, 사용량 절약)
# 음악: 지정 곡 파일이 ~/쇼츠작업/음원/ 에 있으면 영상에 직접 깔고 공개. 없으면 PC 스튜디오에선 저장한 사운드를
#       넣을 수 없으므로(2026-11-20 확인) 비공개로 올리고 결과.txt 에 '음악: 앱에서 추가 필요'.
# 결과: ~/쇼츠작업/<날짜>_<slug>/{더빙용}/영상.mp4, thumb.jpg, 업로드정보.json, 결과.txt / 기록: ~/쇼츠작업/usage.tsv
set -u
export SHORTS_BGM=0
export VOICE_FILE_TEMPO=1.2 SHORTS_MAX_SECONDS=60  # 더빙 1.2배 고정
SLUG="$1"
REPO="$HOME/benefit-site"
SRC="$REPO/assets/samples/$SLUG"
WORK="$HOME/쇼츠작업"
DIR="$WORK/$(date +%Y%m%d)_$SLUG"
PORT=$((18000 + RANDOM % 1000))
MODEL="${SHORTS_CHROME_MODEL:-sonnet}"
cd "$REPO" || exit 1
[ -f "$SRC/plan.json" ] || { echo "plan.json 없음: $SRC"; exit 1; }
mkdir -p "$DIR/더빙용"
touch "$DIR/결과.txt"

# 단계별 시간·사용량 기록 (claude -p --output-format json)
run_claude() {  # run_claude <단계이름> <프롬프트파일>
  local step=$1 t0=$(date +%s) out
  out=$(caffeinate -u claude -p --chrome --model "$MODEL" "$(fill "$2")" --output-format json \
          --permission-mode acceptEdits --allowedTools "Bash,Read,Write,Glob,Grep,mcp__claude-in-chrome" 2>>"$DIR/chrome.log")
  print -r -- "$out" | python3 "$REPO/scripts/mac/usage_log.py" "$SLUG" "$step" "$(( $(date +%s) - t0 ))" >> "$DIR/chrome.log"
}

# 1) 업로드 정보 + 더빙 대본 + 곡 정하기
python3 - "$SRC" "$DIR" <<'EOF'
import json, os, re, sys
from pathlib import Path
src, d = Path(sys.argv[1]), Path(sys.argv[2])
p = json.loads((src / "plan.json").read_text("utf-8"))
from bot import config, shorts
# 저장한 사운드 곡 순서 (사용자 지정 2026-11-20). 종류마다 돌아가며, 순번은 ~/쇼츠작업/song_rotation.json
SONGS = {"웃긴글": [("Forever Has Always Been (영원은 그렇듯) - Redoor", ("forever", "영원")),
                  ("Machi No Dorufin - Kingo Hamada", ("machi", "dorufin")),
                  ("Helios - Jicmus", ("helios",))],
         "감동": [("Lily of The Valley (은방울) - Kim Daniel", ("lily", "은방울")),
                ("꿈꾸던 어른이 되었나요? - 머무르 MEOMURU", ("꿈꾸던",))]}
kind = "감동" if p.get("mood") == "감동" else "웃긴글"  # 핫이슈도 유머 곡 목록
info_f = d / "업로드정보.json"
old = json.loads(info_f.read_text("utf-8")) if info_f.exists() else {}
if old.get("song") and any(old["song"] == s for s, _ in SONGS[kind]):  # 같은 편 재실행: 곡 순번 유지
    song = old["song"]
else:
    f = Path(os.path.expanduser("~/쇼츠작업/song_rotation.json"))
    rot = json.loads(f.read_text()) if f.exists() else {}
    n = rot.get(kind, 0)
    rot[kind] = n + 1
    f.write_text(json.dumps(rot, ensure_ascii=False))
    song = SONGS[kind][n % len(SONGS[kind])][0]
keys = next(k for s, k in SONGS[kind] if s == song)
lib = Path(os.path.expanduser("~/쇼츠작업/음원"))
files = [x for x in lib.rglob("*") if x.suffix.lower() in (".mp3", ".m4a", ".wav") and any(k in x.name.lower() for k in keys)]
song_file = str(files[0]) if files else ""
info = {"title": p.get("yt_title"), "description": shorts.full_description(shorts.Plan(**p)),
        "tags": p.get("tags"), "pin_comment": p.get("pin_comment"), "thumb": "thumb.jpg",
        "song": song, "song_file": song_file, "music": "영상에 포함" if song_file else "앱에서 추가 필요",
        "music_concept": p.get("music_concept", "")}
info_f.write_text(json.dumps(info, ensure_ascii=False, indent=1), "utf-8")
outro = p.get("outro") if p.get("outro_custom") else config.SHORTS_OUTRO
body = [re.sub(r"\*\*", "", b["narration"]) for b in p["beats"] if not b.get("orig_audio")]
outro = re.sub(r"\*\*", "", outro or "")
# 마무리 = 댓글 반응 읽기(구리) + 마무리 멘트. 웃음·울음 기호는 읽으면 어색해서 뺌.
def _clean(c):
    c = re.sub(r"[ㅋㅎㅠㅜ]{2,}|[ㅋㅎㅠㅜ]+$|[~;]+|\^+", " ", c)
    return re.sub(r"\s+", " ", c).strip(" .")
cm = [_clean(c.get("text", "") if isinstance(c, dict) else str(c)) for c in (p.get("end_comments") or [])]
cm = [c for c in cm if 2 <= len(c) <= (60 if p.get("end_label") else 25)][:int(p.get("outro_read", 2))]  # 28초 미만 유지: 짧은 댓글 2개만 (plan outro_read 로 줄임)
outro_lines = ([(p.get("end_label") or "댓글 반응") + "."] + [c + "." for c in cm] if cm else []) + ([outro] if outro else [])
(d / "더빙용" / "대본.txt").write_text("\n".join(body + outro_lines) + "\n", "utf-8")
# 문장별 다른 목소리(beat "voice", 예: 번역 읽기 '구리') → 본문 대본 줄 앞에 [이름] 표시 (크롬 Claude 가 그 줄만 그 캐릭터로)
body_tagged = [(f"[{b['voice']}] " if b.get("voice") else "") + re.sub(r"\*\*", "", b["narration"]) for b in p["beats"] if not b.get("orig_audio")]
(d / "더빙용" / "대본_본문.txt").write_text("\n".join(body_tagged) + "\n", "utf-8")
(d / "더빙용" / "대본_마무리.txt").write_text("\n".join(outro_lines) + "\n", "utf-8")
p["outro_spoken"] = " ".join(outro_lines)  # 합성 때 문장 경계 계산용 (자막은 마무리 멘트만)
(src / "plan.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), "utf-8")
# 목소리 기본 (2026-11-20 변경): 본문 = 필재(모든 종류), 마무리 댓글 반응 읽기 = 구리
vm, vo = (p.get("voices") or ["필재", "구리"])[:2]  # plan "voices" 로 편마다 바꿀 수 있음 (예: 김기장)
info["voices"] = [vm, vo]
info_f.write_text(json.dumps(info, ensure_ascii=False, indent=1), "utf-8")
(d / "voices").write_text(f"{vm} {vo}", "utf-8")
(d / "mood").write_text(p.get("mood") or "기본", "utf-8")
(d / "song_file").write_text(song_file, "utf-8")
EOF

# 2) 로컬 파일 서버 (크롬 저장 창·파일 선택 창 대신). 크롬은 공개 사이트 → 127.0.0.1 요청을 막으므로
#    로컬 페이지(_recv: 받기, _send: 보내기)를 팝업으로 열고 postMessage 로 주고받는다.
python3 "$REPO/scripts/mac/drop_server.py" "$DIR" "$PORT" & SERVER=$!
trap 'kill $SERVER 2>/dev/null; rm -f "$DIR/_recv.html" "$DIR/_send.html"' EXIT
cat > "$DIR/_recv.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>recv</title><body>recv ready
<script>
window.addEventListener('message', async (e) => { const d = e.data || {}; if (!d.file || !d.blob) return;
  try { const r = await fetch('/' + d.file, {method: 'PUT', body: d.blob}); e.source.postMessage({ack: d.file, status: r.status}, '*'); }
  catch (err) { e.source.postMessage({ack: d.file, error: String(err)}, '*'); } });
if (window.opener) window.opener.postMessage({ready: true}, '*');
</script>
HTML
cat > "$DIR/_send.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>send</title><body>send ready
<script>
window.addEventListener('message', async (e) => { const d = e.data || {}; if (!d.get) return;
  try { const b = await (await fetch('/' + d.get)).blob(); e.source.postMessage({file: d.get, blob: b}, '*'); }
  catch (err) { e.source.postMessage({file: d.get, error: String(err)}, '*'); } });
if (window.opener) window.opener.postMessage({ready: true}, '*');
</script>
HTML
sleep 1

SONG_FILE=$(cat "$DIR/song_file")
if [ "${SHORTS_PUBLISH:-1}" = "0" ] || [ -z "$SONG_FILE" ]; then PRIVACY=비공개; else PRIVACY=공개; fi
read MAIN_VOICE OUTRO_VOICE < "$DIR/voices"
ACCOUNT=$(cat "$WORK/upload_account.txt" 2>/dev/null)  # 업로드할 구글 계정 (저장소에 안 올림)
fill() { sed -e "s#{{DIR}}#$DIR#g" -e "s#{{PORT}}#$PORT#g" -e "s#{{MOOD}}#$(cat "$DIR/mood")#g" \
             -e "s#{{MAIN_VOICE}}#$MAIN_VOICE#g" -e "s#{{OUTRO_VOICE}}#$OUTRO_VOICE#g" -e "s#{{PRIVACY}}#$PRIVACY#g" -e "s#{{ACCOUNT}}#$ACCOUNT#g" "$1"; }

# 3) 타입캐스트 더빙 (이미 voice.mp3 가 있으면 건너뜀)
if [ ! -f "$SRC/voice.mp3" ]; then
  run_claude 더빙 .claude/prompts/shorts-chrome-dub.md
  # 본문 + (0.4초) + 마무리 → voice.mp3 (마무리만 다른 목소리)
  if [ -s "$DIR/더빙용/voice_main.mp3" ] && [ -s "$DIR/더빙용/voice_outro.mp3" ]; then
    ffmpeg -y -loglevel error -i "$DIR/더빙용/voice_main.mp3" -f lavfi -t 0.4 -i anullsrc=r=44100:cl=stereo -i "$DIR/더빙용/voice_outro.mp3" \
      -filter_complex "[0:a]aresample=44100,aformat=channel_layouts=stereo[a];[2:a]aresample=44100,aformat=channel_layouts=stereo[c];[a][1:a][c]concat=n=3:v=0:a=1" \
      -b:a 256k "$DIR/더빙용/voice.mp3" && cp "$DIR/더빙용/voice.mp3" "$SRC/voice.mp3" \
      && cp "$DIR/더빙용/voice_main.mp3" "$DIR/더빙용/voice_outro.mp3" "$SRC/"  # 합성 때 본문·마무리 따로 맞춤
  elif [ -s "$DIR/더빙용/voice.mp3" ]; then
    cp "$DIR/더빙용/voice.mp3" "$SRC/voice.mp3"
  fi
else
  cp "$SRC/voice.mp3" "$DIR/더빙용/voice.mp3"
fi
[ "${SHORTS_DUB_ONLY:-0}" = "1" ] && exit 0

# 4) 썸네일 + 더빙 넣어 렌더 (지정 곡 파일이 있으면 영상에 직접 깔기)
python3 -m bot.thumb "assets/samples/$SLUG" && cp "$SRC/thumb.jpg" "$DIR/thumb.jpg" 2>/dev/null
t0=$(date +%s)
PREMIX=0; [ -n "$SONG_FILE" ] && PREMIX=1
if [ -f "$SRC/voice.mp3" ] && SHORTS_SONG_PREMIX=$PREMIX SHORTS_SONG_FILE="$SONG_FILE" \
     python3 -c "from bot import shorts; shorts.render_sample('assets/samples/$SLUG')" \
   && cp shorts_sample.mp4 "$DIR/더빙용/영상.mp4" && cp shorts_sample.mp4 "$SRC/final.mp4"; then
  print -r -- '{"total_cost_usd":0,"num_turns":0}' | python3 scripts/mac/usage_log.py "$SLUG" 합성 "$(( $(date +%s) - t0 ))" >/dev/null
  # 5) 전달: 사용자가 휴대폰 유튜브 앱으로 올림 (사운드 추가 → 저장됨). SHORTS_UPLOAD=1 이면 예전처럼 크롬 자동 업로드.
  if [ "${SHORTS_UPLOAD:-0}" = "1" ]; then
    run_claude 업로드 .claude/prompts/shorts-chrome-upload.md
  else
    python3 "$REPO/scripts/mac/shorts_deliver.py" "$DIR" "$SLUG" >> "$DIR/결과.txt" 2>&1
    # 2026-11-22 사용자: 웍스 중단 → 카카오톡 '나와의 채팅'으로만 (SHORTS_KAKAO=0 이면 끔, SHORTS_WORKS=1 이면 웍스도)
    PKG=$(ls -dt "$HOME/Library/Mobile Documents/com~apple~CloudDocs/쇼츠업로드/"*/ 2>/dev/null | head -1)
    if [ "${SHORTS_TELEGRAM:-1}" = "1" ] && [ -n "$PKG" ]; then  # 2026-11-22 사용자: 텔레그램으로 전달
      "$REPO/scripts/mac/shorts_send_telegram.sh" "${PKG}영상.mp4" "$(cat "${PKG}제목.txt")" >> "$DIR/결과.txt" 2>&1
    fi
    if [ "${SHORTS_KAKAO:-0}" = "1" ] && [ -n "$PKG" ]; then
      "$REPO/scripts/mac/shorts_send_kakao.sh" "${PKG}영상.mp4" "$(cat "${PKG}제목.txt")" >> "$DIR/결과.txt" 2>&1
    fi
    if [ "${SHORTS_WORKS:-0}" = "1" ]; then
      PKG=$(ls -dt "$HOME/Library/Mobile Documents/com~apple~CloudDocs/쇼츠업로드/"*/ 2>/dev/null | head -1)
      [ -n "$PKG" ] && "$REPO/scripts/mac/shorts_send_works.sh" "${PKG}영상.mp4" \
        "$(cat "${PKG}제목.txt")" >> "$DIR/결과.txt" 2>&1  # 2026-11-20: 웍스엔 제목만
    fi
  fi
else
  echo "실패: 더빙 없음 → 업로드 안 함" >> "$DIR/결과.txt"
fi

command -v imac >/dev/null && imac screen off
echo "$DIR"
cat "$DIR/결과.txt"
