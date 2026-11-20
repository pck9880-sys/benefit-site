#!/bin/zsh
# plan 폴더의 higgsfield.json 클립들을 크롬 Claude 가 ChatGPT 안 힉스필드 앱으로 생성 → 같은 폴더에 저장 → 1080 정사각 30fps 로 정리.
# 사용: scripts/mac/shorts_higgsfield.sh <slug>
set -u
REPO="$HOME/benefit-site"; DIR="$REPO/assets/samples/$1"; PORT=$((19500 + RANDOM % 400))
cd "$REPO" || exit 1
[ -f "$DIR/higgsfield.json" ] || { echo "higgsfield.json 없음"; exit 1; }
cat > "$DIR/_recv.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>recv</title><body>recv ready
<script>
window.addEventListener('message', async (e) => { const d = e.data || {}; if (!d.file || !d.blob) return;
  try { const r = await fetch('/' + d.file, {method: 'PUT', body: d.blob}); e.source.postMessage({ack: d.file, status: r.status}, '*'); }
  catch (err) { e.source.postMessage({ack: d.file, error: String(err)}, '*'); } });
if (window.opener) window.opener.postMessage({ready: true}, '*');
</script>
HTML
python3 scripts/mac/drop_server.py "$DIR" "$PORT" >/dev/null 2>&1 & SV=$!
trap 'kill $SV 2>/dev/null; rm -f "$DIR/_recv.html"' EXIT
sleep 1
T0=$(date +%s)
OUT=$(caffeinate -u claude -p --chrome --model "${SHORTS_CHROME_MODEL:-sonnet}" --output-format json \
  "$(sed -e "s#{{DIR}}#$DIR#g" -e "s#{{PORT}}#$PORT#g" .claude/prompts/shorts-chrome-higgsfield.md)" \
  --permission-mode acceptEdits --allowedTools "Bash,Read,Write,Glob,Grep,mcp__claude-in-chrome" < /dev/null 2>>"$DIR/hf.log")
print -r -- "$OUT" | python3 scripts/mac/usage_log.py "$1" 힉스필드 "$(( $(date +%s) - T0 ))" >> "$DIR/hf.log"
# 받은 클립을 장면 규격(1080x1080, 30fps, 무음 트랙 포함)으로
python3 - "$DIR" <<'EOF'
import json, subprocess, sys
from pathlib import Path
d = Path(sys.argv[1])
for c in json.loads((d / "higgsfield.json").read_text("utf-8")):
    f = d / c["file"]
    if not f.exists() or f.stat().st_size < 200_000:
        print("[higgsfield] 없음:", f.name); continue
    out = d / f"sq_{f.name}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(f), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex",
                    "[0:v]split[a][b];[a]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=30:5[bg];"
                    "[b]scale=1080:1080:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,setsar=1[v]",
                    "-map", "[v]", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", str(out)], check=True)
    print("[higgsfield] 정리:", out.name)
EOF
cat "$DIR/hf_result.txt" 2>/dev/null
