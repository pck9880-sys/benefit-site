#!/bin/zsh
# 숏츠 1편: 로컬 작업 폴더 정리 → 크롬 Claude 로 타입캐스트 더빙 → 더빙 렌더 → 유튜브 스튜디오 초안(게시 직전)까지.
# 사용: scripts/mac/shorts_chrome_prep.sh <slug>
# 결과: ~/쇼츠작업/<날짜>_<slug>/{원본,더빙용}/영상.mp4, thumb.jpg, 업로드정보.json, 결과.txt
set -u
SLUG="$1"
REPO="$HOME/benefit-site"
SRC="$REPO/assets/samples/$SLUG"
DIR="$HOME/쇼츠작업/$(date +%Y%m%d)_$SLUG"
PORT=$((18000 + RANDOM % 1000))
cd "$REPO" || exit 1
[ -f "$SRC/plan.json" ] || { echo "plan.json 없음: $SRC"; exit 1; }
mkdir -p "$DIR/원본" "$DIR/더빙용"
python3 -c "from bot import songs; songs.ensure_dirs()"

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
desc = shorts.full_description(shorts.Plan(**p)) if hasattr(shorts, "full_description") else p.get("description", "")
info = {k: p.get(k) for k in ("yt_title", "tags", "pin_comment")}
info["title"], info["description"], info["thumb"] = info.pop("yt_title"), desc, "thumb.jpg"
(d / "업로드정보.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), "utf-8")
outro = p.get("outro") if p.get("outro_custom") else config.SHORTS_OUTRO
lines = [b["narration"] for b in p["beats"] if not b.get("orig_audio")] + ([outro] if outro else [])
(d / "더빙용" / "대본.txt").write_text("\n".join(re.sub(r"\*\*", "", x) for x in lines) + "\n", "utf-8")
(d / "voice_name").write_text(p.get("voice") or config.SHORTS_VOICE_CHAR, "utf-8")
EOF
: > "$DIR/결과.txt"

# 2) 로컬 파일 서버 (크롬 저장 창·파일 선택 창 대신)
python3 "$REPO/scripts/mac/drop_server.py" "$DIR" "$PORT" & SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
sleep 1

fill() { sed -e "s#{{DIR}}#$DIR#g" -e "s#{{PORT}}#$PORT#g" -e "s#{{VOICE}}#$(cat "$DIR/voice_name")#g" -e "s#{{VIDEOS}}#$1#g" "$2"; }
TOOLS="Bash,Read,Write,Glob,Grep,mcp__claude-in-chrome"

# 3) 타입캐스트 더빙 (이미 voice.mp3 가 있으면 건너뜀)
if [ ! -f "$SRC/voice.mp3" ]; then
  caffeinate -u claude -p --chrome "$(fill '' .claude/prompts/shorts-chrome-dub.md)" \
    --permission-mode acceptEdits --allowedTools "$TOOLS" >> "$DIR/chrome.log" 2>&1
  [ -s "$DIR/더빙용/voice.mp3" ] && cp "$DIR/더빙용/voice.mp3" "$SRC/voice.mp3"
else
  cp "$SRC/voice.mp3" "$DIR/더빙용/voice.mp3"
fi

# 4) 더빙 넣어 렌더
VIDEOS="원본/영상.mp4"
if [ -f "$SRC/voice.mp3" ]; then
  python3 -c "from bot import shorts; shorts.render_sample('assets/samples/$SLUG')" \
    && cp shorts_sample.mp4 "$DIR/더빙용/영상.mp4" && cp shorts_sample.mp4 "$SRC/final.mp4" \
    && VIDEOS="원본/영상.mp4, 더빙용/영상.mp4"
else
  echo "더빙: voice.mp3 없음 → 원본만 업로드 준비" >> "$DIR/결과.txt"
fi

# 5) 유튜브 스튜디오 초안 (게시 직전까지)
caffeinate -u claude -p --chrome "$(fill "$VIDEOS" .claude/prompts/shorts-chrome-upload.md)" \
  --permission-mode acceptEdits --allowedTools "$TOOLS" >> "$DIR/chrome.log" 2>&1

command -v imac >/dev/null && imac screen off
osascript -e "display notification \"$SLUG 업로드 직전까지 준비 끝 (결과.txt 확인)\" with title \"해요잉\"" || true
echo "$DIR"
cat "$DIR/결과.txt"
