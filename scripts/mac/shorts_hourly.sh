#!/bin/zsh
# Mac 숏츠 자동 제작 (크론: 하루 6편: 0·3·6시 + 12·16·20시). 중간 보고 없음. cron 이 이 파일을 실행.
# 흐름: ① 대본(카테고리 템플릿, 기본 모델) → ② ChatGPT 이미지 ∥ 타입캐스트 더빙 (동시, 크롬 단계는 sonnet)
#       → ③ 썸네일·합성 → ④ 업로드.  단계별 시간·사용량: ~/쇼츠작업/usage.tsv
# 옵션: SHORTS_FORCE_MOOD=웃긴글|감동|이슈 (순서 무시), SHORTS_PUBLISH=0 (비공개), SHORTS_PARALLEL=0 (동시 실행 끔)
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
cd "$HOME/benefit-site" || exit 1
LOG="$HOME/benefit-site/shorts_hourly.log"
# 이전 편이 아직 돌고 있으면 이번 회차는 건너뜀 (겹침 방지)
LOCK=/tmp/shorts_hourly.lock
if ! mkdir "$LOCK" 2>/dev/null; then echo "$(date) 이전 실행 중 → 건너뜀" >> "$LOG"; exit 0; fi
trap 'rmdir "$LOCK"' EXIT
export SHORTS_BGM=0
export VOICE_FILE_TEMPO=1.2 SHORTS_MAX_SECONDS=60  # 더빙 1.2배 고정
git pull -q --rebase || true
BEFORE=$(ls assets/samples)

# 종류 순서: 유머 2 → 감동 1 → 핫이슈 2 → 반복 (~/쇼츠작업/rotation.txt 에 다음 순번)
ROT="$HOME/쇼츠작업/rotation.txt"
SEQ=(웃긴글 웃긴글 감동 이슈 이슈)
N=$(cat "$ROT" 2>/dev/null || echo 0)
MOOD="${SHORTS_FORCE_MOOD:-${SEQ[$(( N % 5 + 1 ))]}}"
[ -z "${SHORTS_FORCE_MOOD:-}" ] && echo $(( N + 1 )) > "$ROT"

# ① 대본·자료 (공통 규칙 + 카테고리 규칙)
PROMPT="$(cat .claude/prompts/shorts-hourly.md)

$(cat .claude/prompts/shorts-cat-$MOOD.md)

[이번 회차] 종류: $MOOD"
T0=$(date +%s)
OUT=$(caffeinate -i claude -p "$PROMPT" --output-format json --permission-mode acceptEdits \
  --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch" 2>>"$LOG")
SLUG_NEW=$(comm -13 <(echo "$BEFORE") <(ls assets/samples) | head -1)
print -r -- "$OUT" | python3 scripts/mac/usage_log.py "${SLUG_NEW:-?}" "대본($MOOD)" "$(( $(date +%s) - T0 ))" >> "$LOG"

for slug in $(comm -13 <(echo "$BEFORE") <(ls assets/samples)); do
  [ -f "assets/samples/$slug/plan.json" ] || continue
  python3 -m bot.plan_tool check "$slug" >> "$LOG" 2>&1  # 장면 배치·썸네일 문구 최종 보정
  # ② 이미지 ∥ 더빙 (둘 다 대본만 있으면 되므로 동시에)
  if [ "${SHORTS_PARALLEL:-1}" = "1" ]; then
    scripts/mac/shorts_gpt_images.sh "$slug" >> "$LOG" 2>&1 &
    GP=$!
    sleep 20  # 크롬 탭이 겹쳐 열리지 않게 살짝 늦게
    SHORTS_DUB_ONLY=1 scripts/mac/shorts_chrome_prep.sh "$slug" >> "$LOG" 2>&1
    wait $GP
  else
    scripts/mac/shorts_gpt_images.sh "$slug" >> "$LOG" 2>&1
  fi
  # ③④ 썸네일·합성·업로드 (더빙이 이미 있으면 건너뜀)
  scripts/mac/shorts_chrome_prep.sh "$slug" >> "$LOG" 2>&1
  git add "assets/samples/$slug" && git commit -q -m "숏츠 $slug: 이미지·렌더" && { git pull -q --rebase; git -c http.postBuffer=524288000 push -q; } >> "$LOG" 2>&1
done
