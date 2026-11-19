#!/bin/zsh
# Mac 에서 3시간마다 숏츠 1편 자동 제작 → 크롬 Claude 더빙 → 유튜브 자동 업로드 (중간 보고 없음). cron/launchd 가 이 파일을 실행.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cd "$HOME/benefit-site" || exit 1
export SHORTS_BGM=0  # 음악은 업로드 때 유튜브 저장됨 사운드로
git pull -q --rebase || true
BEFORE=$(ls assets/samples)
EXTRA=""
[ -n "${SHORTS_FORCE_MOOD:-}" ] && EXTRA="

[이번 회차만] 종류는 순환 대신 '$SHORTS_FORCE_MOOD' 로 고정."
caffeinate -i claude -p "$(cat .claude/prompts/shorts-hourly.md)$EXTRA" \
  --permission-mode acceptEdits \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch" \
  >> "$HOME/benefit-site/shorts_hourly.log" 2>&1
# 새로 만든 편: 크롬 Claude 로 더빙 → 유튜브 자동 업로드. SHORTS_CHROME_PREP=0 이면 건너뜀
for slug in $(comm -13 <(echo "$BEFORE") <(ls assets/samples)); do
  [ -f "assets/samples/$slug/plan.json" ] || continue
  scripts/mac/shorts_gpt_images.sh "$slug" >> "$HOME/benefit-site/shorts_hourly.log" 2>&1  # ChatGPT 로 이미지
  [ "${SHORTS_CHROME_PREP:-1}" = "1" ] && scripts/mac/shorts_chrome_prep.sh "$slug" >> "$HOME/benefit-site/shorts_hourly.log" 2>&1
  git add "assets/samples/$slug" && git commit -q -m "숏츠 $slug: 이미지·렌더" && { git pull -q --rebase; git -c http.postBuffer=524288000 push -q; } >> "$HOME/benefit-site/shorts_hourly.log" 2>&1
done
