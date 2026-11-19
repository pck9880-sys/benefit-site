#!/bin/zsh
# Mac 에서 1시간마다 숏츠 1편 자동 제작 (업로드 안 함). cron/launchd 가 이 파일을 실행.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cd "$HOME/benefit-site" || exit 1
git pull -q --rebase || true
caffeinate -i claude -p "$(cat .claude/prompts/shorts-hourly.md)" \
  --permission-mode acceptEdits \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,mcp__claude_ai_Figma__generate_image,mcp__claude_ai_Figma__create_session,mcp__claude_ai_Figma__create_new_file" \
  >> "$HOME/benefit-site/shorts_hourly.log" 2>&1
osascript -e 'display notification "숏츠 1편 제작 끝 (_queue.md 확인)" with title "해요잉"' || true
