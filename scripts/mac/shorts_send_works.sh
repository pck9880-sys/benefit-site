#!/bin/zsh
# 완성 영상을 네이버웍스 '나와의 대화'(박치경 본인)로 보내기 — 휴대폰 웍스 앱에서 바로 저장·업로드 (2026-11-20 사용자 요청)
# 사용: shorts_send_works.sh <영상.mp4> <보낼 글>
set -u
V="$1"; MSG="$2"
W=$(mktemp -d); cp "$V" "$W/v.mp4"
cat > "$W/_send.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>send</title><body>send ready
<script>
window.addEventListener('message', async (e) => { const d = e.data || {}; if (!d.get) return;
  try { const b = await (await fetch('/' + d.get)).blob(); e.source.postMessage({file: d.get, blob: b}, '*'); }
  catch (err) { e.source.postMessage({file: d.get, error: String(err)}, '*'); } });
if (window.opener) window.opener.postMessage({ready: true}, '*');
</script>
HTML
PORT=$((17000 + RANDOM % 900))
python3 "$HOME/benefit-site/scripts/mac/drop_server.py" "$W" "$PORT" >/dev/null 2>&1 & SV=$!
trap 'kill $SV 2>/dev/null; rm -rf "$W"' EXIT
sleep 1
NAME=$(python3 -c "import sys,os;print(os.path.basename(os.path.dirname(sys.argv[1]))[:30])" "$V").mp4  # 글자 단위로 자르기 (바이트로 자르면 한글 깨짐)
caffeinate -u claude -p --chrome --model sonnet "크롬 작업 (확인창 금지, 다른 사람에게 보내지 말 것, 연 탭은 끝나면 닫기, 보고 2줄):
네이버웍스 메신저에서 **본인 '박치경' 나와의 대화**에만 영상 1개를 보낸다. 로그인 안 돼 있으면 '실패: 웍스 로그인 필요'만 보고.
파일 선택 창 금지: 대화창에서 window.open('http://127.0.0.1:$PORT/_send.html') (막히면 임시 버튼 클릭) → ready 후
w.postMessage({get:'v.mp4'}, '*') → 받은 blob 으로 new File([blob], '$NAME', {type:'video/mp4'}) → 대화창 input[type=file] 에 DataTransfer 로 넣고 change (또는 drop 이벤트).
함께 보낼 글: '$MSG'. 전송 후 올라간 것 확인." --permission-mode acceptEdits --allowedTools "Read,mcp__claude-in-chrome" < /dev/null 2>&1 | tail -3
