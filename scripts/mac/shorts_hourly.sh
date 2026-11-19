#!/bin/zsh
# Mac 숏츠 자동 제작 (크론: 하루 6편: 0·3·6시 + 12·16·20시) → 크롬 Claude 더빙 → 유튜브 자동 업로드 (중간 보고 없음). cron/launchd 가 이 파일을 실행.
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cd "$HOME/benefit-site" || exit 1
# 이전 편이 아직 돌고 있으면 이번 회차는 건너뜀 (겹침 방지)
LOCK=/tmp/shorts_hourly.lock
if ! mkdir "$LOCK" 2>/dev/null; then echo "$(date) 이전 실행 중 → 건너뜀" >> shorts_hourly.log; exit 0; fi
trap 'rmdir "$LOCK"' EXIT
export SHORTS_BGM=0  # 음악은 업로드 때 유튜브 저장됨 사운드로
git pull -q --rebase || true
BEFORE=$(ls assets/samples)
# 종류 순서: 유머 2 → 감동 1 → 핫이슈 2 → 반복 (~/쇼츠작업/rotation.txt 에 다음 순번)
ROT="$HOME/쇼츠작업/rotation.txt"
SEQ=(웃긴글 웃긴글 감동 이슈 이슈)
N=$(cat "$ROT" 2>/dev/null || echo 0)
MOOD="${SHORTS_FORCE_MOOD:-${SEQ[$(( N % 5 + 1 ))]}}"
[ -z "${SHORTS_FORCE_MOOD:-}" ] && echo $(( N + 1 )) > "$ROT"
EXTRA="

[이번 회차] 종류: $MOOD"
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
