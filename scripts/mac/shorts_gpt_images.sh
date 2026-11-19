#!/bin/zsh
# plan.json 의 gpt_images 를 크롬 Claude 가 ChatGPT 웹으로 생성 → assets/samples/<slug>/ 에 저장 → JPG 로 변환.
# 실패한 장면은 폴더의 다른 이미지로 채워서 렌더가 멈추지 않게 한다.
# 사용: scripts/mac/shorts_gpt_images.sh <slug>
set -u
REPO="$HOME/benefit-site"
DIR="$REPO/assets/samples/$1"
PORT=$((19000 + RANDOM % 1000))
cd "$REPO" || exit 1
[ -f "$DIR/plan.json" ] || { echo "plan.json 없음"; exit 1; }
python3 -c "import json,sys; sys.exit(0 if json.load(open('$DIR/plan.json')).get('gpt_images') else 1)" || { echo "gpt_images 없음"; exit 0; }

python3 scripts/mac/drop_server.py "$DIR" "$PORT" & SERVER=$!
trap 'kill $SERVER 2>/dev/null; rm -f "$DIR/_recv.html"' EXIT
cat > "$DIR/_recv.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>recv</title><body>recv ready
<script>
window.addEventListener('message', async (e) => {
  const d = e.data || {};
  if (!d.file || !d.blob) return;
  try { const r = await fetch('/' + d.file, {method: 'PUT', body: d.blob}); e.source.postMessage({ack: d.file, status: r.status}, '*'); }
  catch (err) { e.source.postMessage({ack: d.file, error: String(err)}, '*'); }
});
if (window.opener) window.opener.postMessage({ready: true}, '*');
</script>
HTML
sleep 1
caffeinate -u claude -p --chrome "$(sed -e "s#{{DIR}}#$DIR#g" -e "s#{{PORT}}#$PORT#g" .claude/prompts/shorts-chrome-gpt.md)" \
  --permission-mode acceptEdits --allowedTools "Bash,Read,Write,Glob,Grep,mcp__claude-in-chrome" >> "$DIR/gpt.log" 2>&1

python3 - "$DIR" <<'EOF'
import json, shutil, sys
from pathlib import Path
from PIL import Image
d = Path(sys.argv[1])
p = json.loads((d / "plan.json").read_text("utf-8"))
ok, miss = [], []
for it in p["gpt_images"]:
    f = d / it["file"]
    try:
        if f.exists() and f.stat().st_size > 30_000:
            Image.open(f).convert("RGB").save(f, "JPEG", quality=90)  # png/webp 로 받아도 진짜 JPG 로
            ok.append(f.name)
            continue
    except Exception as ex:
        print("[gpt] 변환 실패", f.name, ex)
    miss.append(f.name)
# 빠진 장면 이미지는 폴더의 다른 이미지로 채움 (썸네일 원본은 비워 두면 thumb.py 가 장면 컷 사용)
pool = [x for x in sorted(d.glob("*.jpg")) + sorted(d.glob("z*.png")) if x.name in ok or x.name.startswith(("r", "z"))]
for name in miss:
    if name.startswith("thumb_src"):
        continue
    if pool:
        shutil.copy(pool[len(name) % len(pool)], d / name)
print(f"[gpt] 성공 {len(ok)}장 {ok}, 실패 {miss}")
EOF
