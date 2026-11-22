#!/bin/zsh
# 완성 영상을 맥 카카오톡 '나와의 채팅'으로 보내기 (2026-11-22 사용자: 웍스 대신 카톡만)
# 사용: shorts_send_kakao.sh <영상.mp4> <보낼 글>
# 안전장치: 창 이름이 ~/쇼츠작업/kakao_chat.txt (기본 '나와의 채팅') 와 정확히 같은 채팅창이 맨 앞일 때만 붙여넣기·전송. 아니면 아무것도 안 보내고 실패.
# 필요: 카카오톡 로그인 + 그 채팅창을 열어 둔 상태, 화면 켜짐·잠금 해제, 터미널(또는 실행 앱)에 '손쉬운 사용' 권한.
set -u
F="$1"; MSG="${2:-}"
CHAT=$(cat "$HOME/쇼츠작업/kakao_chat.txt" 2>/dev/null || echo "나와의 채팅")
[ -f "$F" ] || { echo "실패(카톡): 파일 없음 $F"; exit 1; }
osascript - "$F" "$MSG" "$CHAT" <<'OSA'
on run argv
  set f to item 1 of argv
  set msg to item 2 of argv
  set chatName to item 3 of argv
  with timeout of 40 seconds
    tell application "KakaoTalk" to activate
    delay 1.2
    tell application "System Events" to tell process "KakaoTalk"
      set wins to name of every window
      if wins does not contain chatName then error "채팅창 '" & chatName & "' 이 열려 있지 않음 (열린 창: " & (wins as text) & ")"
      perform action "AXRaise" of window chatName
      delay 0.6
      if name of front window is not chatName then error "맨 앞 창이 '" & chatName & "' 이 아님"
    end tell
    set the clipboard to (POSIX file f)
    tell application "System Events" to keystroke "v" using command down
    delay 2.5
    tell application "System Events" to key code 36 -- 파일 전송 확인(Enter)
    delay 4
    if msg is not "" then
      tell application "System Events" to tell process "KakaoTalk"
        if name of front window is not chatName then error "전송 후 맨 앞 창이 바뀜 — 글은 안 보냄"
      end tell
      set the clipboard to msg
      tell application "System Events" to keystroke "v" using command down
      delay 0.6
      tell application "System Events" to key code 36
    end if
  end timeout
  return "성공(카톡): '" & chatName & "' 에 영상과 글 보냄"
end run
OSA
RC=$?
[ $RC -eq 0 ] || echo "실패(카톡): 위 오류 — 아무것도 안 보냈거나 일부만 보냈을 수 있음"
exit $RC
