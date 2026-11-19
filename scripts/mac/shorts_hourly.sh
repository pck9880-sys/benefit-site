#!/bin/zsh
# Mac 에서 1시간마다 숏츠 1편 자동 제작 → 더빙·업로드는 게시 직전(초안)까지. cron/launchd 가 이 파일을 실행.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cd "$HOME/benefit-site" || exit 1
git pull -q --rebase || true
BEFORE=$(ls assets/samples)
caffeinate -i claude -p "$(cat .claude/prompts/shorts-hourly.md)" \
  --permission-mode acceptEdits \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,mcp__claude_ai_Figma__generate_image,mcp__claude_ai_Figma__create_session,mcp__claude_ai_Figma__create_new_file" \
  >> "$HOME/benefit-site/shorts_hourly.log" 2>&1
# 새로 만든 편: 크롬 Claude 로 더빙 → 유튜브 스튜디오 초안(게시 직전)까지. SHORTS_CHROME_PREP=0 이면 건너뜀
for slug in $(comm -13 <(echo "$BEFORE") <(ls assets/samples)); do
  [ -f "assets/samples/$slug/plan.json" ] || continue
  [ "${SHORTS_CHROME_PREP:-1}" = "1" ] && scripts/mac/shorts_chrome_prep.sh "$slug" >> "$HOME/benefit-site/shorts_hourly.log" 2>&1
done
osascript -e 'display notification "숏츠 1편 제작 끝 (_queue.md 확인)" with title "해요잉"' || true
