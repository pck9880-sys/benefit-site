#!/bin/zsh
# 완성 영상을 텔레그램 봇으로 나에게 보내기 (2026-11-22 사용자: 웍스·카톡 대신 텔레그램)
# 사용: shorts_send_telegram.sh <영상.mp4> <글>
# 비밀값: ~/쇼츠작업/telegram.env (TELEGRAM_BOT_TOKEN=..., TELEGRAM_CHAT_ID=... — 채팅 ID 가 없으면 봇에게 마지막으로 말 건 사람으로 자동 저장). 깃에 올리지 않음.
set -u
F="$1"; MSG="${2:-}"; ENV="$HOME/쇼츠작업/telegram.env"
[ -f "$ENV" ] && source "$ENV"
: "${TELEGRAM_BOT_TOKEN:=}"; : "${TELEGRAM_CHAT_ID:=}"
[ -n "$TELEGRAM_BOT_TOKEN" ] || { echo "실패(텔레그램): 토큰 없음 ($ENV)"; exit 1; }
API="https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN"
if [ -z "$TELEGRAM_CHAT_ID" ]; then
  TELEGRAM_CHAT_ID=$(curl -s "$API/getUpdates" | python3 -c "import sys,json;r=json.load(sys.stdin).get('result',[]);ids=[(u.get('message') or u.get('edited_message') or {}).get('chat',{}).get('id') for u in r];ids=[i for i in ids if i];print(ids[-1] if ids else '')")
  [ -n "$TELEGRAM_CHAT_ID" ] || { echo "실패(텔레그램): 채팅 ID 없음 — 휴대폰 텔레그램에서 봇에게 아무 말이나 한 번 보내 주세요"; exit 1; }
  echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID" >> "$ENV"
fi
[ -f "$F" ] || { echo "실패(텔레그램): 파일 없음 $F"; exit 1; }
R=$(curl -s -F chat_id="$TELEGRAM_CHAT_ID" -F supports_streaming=true --form-string caption="$MSG" -F video=@"$F" "$API/sendVideo")
echo "$R" | python3 -c "import sys,json;r=json.load(sys.stdin);print('성공(텔레그램): 영상 보냄' if r.get('ok') else '실패(텔레그램): '+str(r.get('description'))[:200])"
