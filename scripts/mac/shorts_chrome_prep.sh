#!/bin/zsh
# 숏츠 1편: 로컬 작업 폴더 정리 → 크롬 Claude 로 타입캐스트 더빙(찜한 두 캐릭터) → 더빙 렌더 → 유튜브 자동 업로드(공개).
# 음악은 영상에 넣지 않고, 업로드 때 유튜브 '저장됨' 사운드에서 컨셉에 맞게 고른다.
# 사용: scripts/mac/shorts_chrome_prep.sh <slug>
# 결과: ~/쇼츠작업/<날짜>_<slug>/{원본,더빙용}/영상.mp4, thumb.jpg, 업로드정보.json, 결과.txt
set -u
export SHORTS_BGM=0  # 배경음악 미리 깔지 않음
SLUG="$1"
REPO="$HOME/benefit-site"
SRC="$REPO/assets/samples/$SLUG"
WORK="$HOME/쇼츠작업"
DIR="$WORK/$(date +%Y%m%d)_$SLUG"
PORT=$((18000 + RANDOM % 1000))
cd "$REPO" || exit 1
[ -f "$SRC/plan.json" ] || { echo "plan.json 없음: $SRC"; exit 1; }
mkdir -p "$DIR/원본" "$DIR/더빙용"

# 1) 원본(임시 음성) 영상 + 썸네일 + 업로드 정보 + 더빙 대본
if [ ! -f "$SRC/preview.mp4" ]; then
  python3 -c "from bot import shorts; shorts.render_sample('assets/samples/$SLUG')" && cp shorts_sample.mp4 "$SRC/preview.mp4"
fi
cp "$SRC/preview.mp4" "$DIR/원본/영상.mp4"
python3 -m bot.thumb "assets/samples/$SLUG" && cp "$SRC/thumb.jpg" "$DIR/thumb.jpg" 2>/dev/null
python3 - "$SRC" "$DIR" <<'EOF'
import json, re, sys
from pathlib import Path
src, d = Path(sys.argv[1]), Path(sys.argv[2])
p = json.loads((src / "plan.json").read_text("utf-8"))
from bot import config, shorts
info = {"title": p.get("yt_title"), "description": shorts.full_description(shorts.Plan(**p)),
        "tags": p.get("tags"), "pin_comment": p.get("pin_comment"), "thumb": "thumb.jpg",
        "music_concept": p.get("music_concept") or {"감동": "잔잔한 감동", "웃긴글": "신나는 코믹"}.get(p.get("mood"), "일상 브이로그")}
(d / "업로드정보.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), "utf-8")
outro = p.get("outro") if p.get("outro_custom") else config.SHORTS_OUTRO
lines = [b["narration"] for b in p["beats"] if not b.get("orig_audio")] + ([outro] if outro else [])
(d / "더빙용" / "대본.txt").write_text("\n".join(re.sub(r"\*\*", "", x) for x in lines) + "\n", "utf-8")
(d / "mood").write_text(p.get("mood") or "기본", "utf-8")
EOF
: > "$DIR/결과.txt"

# 2) 로컬 파일 서버 (크롬 저장 창·파일 선택 창 대신)
python3 "$REPO/scripts/mac/drop_server.py" "$DIR" "$PORT" & SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
sleep 1

PRIVACY=$([ "${SHORTS_PUBLISH:-1}" = "0" ] && echo 비공개 || echo 공개)  # SHORTS_PUBLISH=0 → 테스트(비공개)
LAST_VOICE=$(cat "$WORK/last_voice.txt" 2>/dev/null || echo "없음")
fill() { sed -e "s#{{DIR}}#$DIR#g" -e "s#{{PORT}}#$PORT#g" -e "s#{{MOOD}}#$(cat "$DIR/mood")#g" \
             -e "s#{{LAST_VOICE}}#$LAST_VOICE#g" -e "s#{{PRIVACY}}#$PRIVACY#g" "$1"; }
TOOLS="Bash,Read,Write,Glob,Grep,mcp__claude-in-chrome"

# 3) 타입캐스트 더빙 (이미 voice.mp3 가 있으면 건너뜀)
if [ ! -f "$SRC/voice.mp3" ]; then
  caffeinate -u claude -p --chrome "$(fill .claude/prompts/shorts-chrome-dub.md)" \
    --permission-mode acceptEdits --allowedTools "$TOOLS" >> "$DIR/chrome.log" 2>&1
  [ -s "$DIR/더빙용/voice.mp3" ] && cp "$DIR/더빙용/voice.mp3" "$SRC/voice.mp3"
  [ -s "$DIR/voice_used.txt" ] && cp "$DIR/voice_used.txt" "$WORK/last_voice.txt"
else
  cp "$SRC/voice.mp3" "$DIR/더빙용/voice.mp3"
fi

# 4) 더빙 넣어 렌더 → 5) 자동 업로드. 더빙이 없으면 올리지 않음 (임시 음성 영상은 올리지 않음)
if [ -f "$SRC/voice.mp3" ] && python3 -c "from bot import shorts; shorts.render_sample('assets/samples/$SLUG')" \
   && cp shorts_sample.mp4 "$DIR/더빙용/영상.mp4" && cp shorts_sample.mp4 "$SRC/final.mp4"; then
  caffeinate -u claude -p --chrome "$(fill .claude/prompts/shorts-chrome-upload.md)" \
    --permission-mode acceptEdits --allowedTools "$TOOLS" >> "$DIR/chrome.log" 2>&1
else
  echo "실패: 더빙 없음 → 업로드 안 함" >> "$DIR/결과.txt"
fi

command -v imac >/dev/null && imac screen off
echo "$DIR"
cat "$DIR/결과.txt"
