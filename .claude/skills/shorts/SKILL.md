---
name: shorts
description: "이슈해요잉" 유튜브 숏츠 1편을 빠르게 만드는 작업 순서 (뉴스 이슈형 + CC 영상 재가공형). 사용자가 숏츠/쇼츠 제작, 오늘 이슈 영상, 더빙 파일(mp3) 첨부, 영상 업로드를 요청할 때 사용. 주제 3개 추천 → 사실 확인 → 대본 → Figma GPT 이미지 → 타입캐스트 더빙 프롬프트 → 합성·미리보기 → 컨펌 후 업로드.
---

# 숏츠 1편 제작 (반자동)

답변은 한국어 **요약 형식**(표·짧은 목록)으로. 사용자는 휴대폰으로 본다.

## 0. 원칙 (꼭 지킬 것)
- 주제: 그날 핫이슈. **스포츠는 축구만**. 정치·선거, 사망·사고·자살, 범죄 피해자, 연예인 사생활·루머, 특정 개인 비방은 제외.
- 사실만: 웹 검색 + 기사 본문(web-fetch 에이전트)으로 확인한 사실만. 제목에서만 확인된 내용은 2개 이상 언론사일 때만, "~라고 함"으로.
- 남의 영상·기사 화면·댓글을 **캡처하지 않는다**. 기사 제목/여론/발언은 카드로 **직접 그린다**(overlay). 여론은 기사에 인용된 실제 반응만, 지어내기 금지, 닉네임·프로필은 흐림(코드가 자동 처리).
- 실존 인물 얼굴을 AI로 만들지 않는다 (뒷모습·손·사물로 연출).
- 미리보기는 **이 채팅에 먼저**(SendUserFile) → 사용자 "컨펌" 후에만 업로드·텔레그램.
- 커밋은 경로를 지정해서(`git add bot assets/...`). **`git commit -a` 금지** (data/ 덮어쓰기 사고 이력). 테스트는 `tests/_sandbox.py` 덕분에 data/ 를 안 건드림.

## 1. 주제 3개 추천
```bash
cd /home/user/benefit-site && python -c "
from bot import trends
for c,t in trends.google_news(per=8): print(c,'|',t)
for x in trends.google_trends()[:15]: print('검색어',x['title'],x['traffic'])"
```
분야가 겹치지 않게 3개 → AskUserQuestion 으로 선택받기 (추천 1개 표시).

## 2. 사실 확인
WebSearch + web-fetch 에이전트로 기사 본문 2~4개. 확인할 것: 숫자·이름·날짜, **실제 기사 제목 원문 2~3개(언론사명)**, **기사에 인용된 시민·네티즌 반응 2~3개**, 발언 인용.

## 3. 대본 (plan.json)
- 제목 2줄: `title_top`(상황, 13자 내외) / `title_bottom`(노란색, 궁금증·ㄷㄷ).
- beats 5개: 반말 썰 말투("~라는데", "~거든", "~했다고 함"), 문장당 24자 이내, '~입니다/~해요' 금지.
- 카드: beats 중 2~3개에 `overlay`: `headline`(기사 제목 원문, `overlay_source`=언론사) / `comment`(실제 반응, source="온라인 반응") / `quote`. 강조는 `**굵게**`.
- 목소리: 기본 **용식** → `outro` = "다들 ~해요잉~" / 요청 시 **박창수**(해요잉~) 또는 **태우**("다들 ~하자!"). `voice` 필드에 이름.
- 폴더: `assets/samples/<영문슬러그>/plan.json` (형식은 `assets/samples/suneung_alert/plan.json` 참고. 필드: topic,title_top,title_bottom,character,hook_video,photo_fallbacks,beats[narration,card,twist,visual,query,ai_prompt,overlay,overlay_text,overlay_source],voice,outro,yt_title(#shorts),description,tags,sources).

## 4. 이미지 5장 (Figma GPT 이미지)
- `mcp__Figma__create_session`(fileKey `XPyCf7k9rdYwZF42krwyZ4`) → `mcp__Figma__generate_image` 5번 **병렬**, model `gpt-image-2.5-flare`, 1024×1024.
- 프롬프트: "Photorealistic candid photo ... natural light ... No readable text, no logos, no faces(필요 시)". 문장 내용이 한눈에 보이게 구체적으로. 실패하면 문구 바꿔 1번 재시도.
- 다운로드: `curl -sfL -o /tmp/x.png "<image.url>" && ffmpeg -y -i /tmp/x.png -q:v 3 assets/samples/<slug>/img{0..4}.jpg` (beat 순서대로).

## 5. 더빙 (사용자 → 타입캐스트 웹, 베이직 요금제)
타입캐스트 API는 무료 계정 차단(403 UNUSUAL_ACTIVITY) 상태 — 호출하지 말 것. 사용자에게 Chrome Claude 프롬프트 제공:
"캐릭터 <용식|박창수|태우>, 아래 6줄을 한 줄에 한 문장씩, 속도 등 전부 기본값(1.0), 전체 합치기 mp3 다운로드, 업그레이드 창 뜨면 결제 금지" + 6줄(beats 5 + outro).
사용자가 mp3를 첨부하면 경로는 `/root/.claude/uploads/<session>/...mp3` → `assets/samples/<slug>/voice.mp3` 로 복사.
(사용자는 1.0배로 녹음 → 코드가 `VOICE_FILE_TEMPO`=**1.4배**로 변환 후 타이밍 맞춤. 녹음은 자르지 않고 통째로 깔고 문장 경계는 글자 수 비율+무음으로 자동 탐지.)

## 6. 합성·미리보기
배경음악(Born Free, Jamendo)은 로컬에 키가 없으므로 한 번 받아 임시로 둔다:
```bash
cd /home/user/benefit-site
ls /tmp/claude-0/sh/bgm/bgm_1179546.mp3 2>/dev/null || (gh workflow run bgm-get.yml --ref main && sleep 8 && id=$(gh run list --workflow bgm-get.yml -L 1 --json databaseId -q '.[0].databaseId') && until [ "$(gh run view $id --json status -q .status)" = completed ]; do sleep 5; done && gh run download $id -n bgm -D /tmp/claude-0/sh/bgm)
mkdir -p assets/bgm && cp /tmp/claude-0/sh/bgm/bgm_*.mp3 assets/bgm/tmp.mp3
export CHROMIUM_PATH=$(ls -d /opt/pw-browsers/chromium-*/chrome-linux*/chrome | head -1)
python -c "from bot import shorts; shorts.render_sample('assets/samples/<slug>')"
rm -rf assets/bgm
cp shorts_sample.mp4 assets/samples/<slug>/final.mp4 && cp shorts_sample.mp4 shorts_<slug>.mp4
```
- 프레임 확인: `ffmpeg -ss <t> -i shorts_<slug>.mp4 -frames:v 1 -vf scale=300:-2 /tmp/f.png` 몇 장 → hstack → Read 로 눈으로 확인.
- `SendUserFile`(display render)로 `shorts_<slug>.mp4` 전송 → 컨펌 대기. (shorts_*.mp4 는 .gitignore)
- 더빙 전 임시 미리보기가 필요하면 voice.mp3 없이 렌더(무료 edge 음성; 로컬은 `import certifi; certifi.where=lambda:"/root/.ccr/ca-bundle.crt"` 필요).

## 7. 컨펌 후 업로드
```bash
git add assets/samples/<slug> && git commit -m "숏츠: <주제>" && git push   # (pull --rebase 후 재시도)
gh workflow run shorts-upload.yml --ref main -f folder=assets/samples/<slug> \
  -f 'music=Music: "Born Free" by Pokki DJ (Jamendo) License: http://creativecommons.org/licenses/by/3.0/'
# 완료 후 로그에서 [upload] URL 확인 → 사용자에게 youtube.com/shorts/<id> 로 안내
```
- Upload-Post 무료 월 10개 한도. 업로드 수를 알려줄 것.
- 유튜브 연결이 끊기면 `youtube-connect.yml` 대신 app.upload-post.com/manage-users 에서 직접 연결하도록 안내.

## 참고 (설정·구조)
- 코드: `bot/shorts.py`(render_sample, make_video, overlay_html, signature, split_voice), 설정 `bot/config.py`.
- 화면: 1080×1920, 상단 2줄 제목(흰/노랑, 자동 크기 맞춤), 가운데 1080×1080 장면(천천히 줌), 하단 자막. 효과음 없음, 배경음악 -33 LUFS(더빙 9:1).
- 매일 자동 제작은 이미지 키(OPENAI_API_KEY/HIGGSFIELD_KEY)가 없으면 쉰다 (`has_image_source`).


---

# CC 영상 재가공형 (크리에이티브 커먼즈 영상 + AI 이미지 섞기, 최대 25초)

## 장르 분류 (흥미 소스) — 매번 다른 칸에서 고르기
| 분류 | 예시 검색어(영어) | 주 출처 |
|---|---|---|
| 🌋 극한 자연 | volcano lava, tornado, lightning, avalanche | USGS·NOAA(퍼블릭 도메인) |
| 🚀 우주·로켓 | rocket launch, ISS spacewalk, mars rover | NASA(퍼블릭 도메인) |
| 🐙 신기한 동물 | octopus camouflage, mantis shrimp, deep sea creature | NOAA, 위키미디어 CC BY |
| 🔬 실험·과학 | slow motion, liquid nitrogen, chemical reaction | 위키미디어 CC BY |
| 🛠 신기한 직업·현장 | lava sampling, bomb disposal robot, wind turbine climber | 정부기관 퍼블릭 도메인 |
| 🏛 역사 실제 영상 | moon landing, first flight, old city footage | 퍼블릭 도메인 아카이브 |
| ⚽ 스포츠·이슈 | (방송 영상은 불가) → AI 이미지 + 기사 카드 | — |

## 순서
1. 분류표에서 주제 3개 추천 → 선택.
2. 후보 영상 찾기 (서버에서 실행 — 위키미디어는 이 컨테이너에서 429 차단됨):
   `gh workflow run cc-find.yml --ref main -f "queries=검색어1|검색어2"` → 완료 후
   `gh run download <id> -n cc -D /tmp/claude-0/sh/cc` → `candidates.json`(제목·라이선스·길이·credit), `candN_sheet.jpg`(미리보기 6컷)
   - 라이선스는 코드가 자동 필터: CC BY·CC0·퍼블릭 도메인·Pexels만 (NC·ND·SA·불명 제외).
3. 미리보기를 Read 로 보고 장면 고르기: 필요하면 `ffmpeg -ss <t> -i candN.webm -frames:v 1 -vf scale=240:135,setsar=1 p_N_t.jpg` 여러 장 hstack.
4. 사실 확인: 영상 설명(candidates.json desc) + 공식 출처(예: usgs.gov, nasa.gov) 웹 검색.
5. 클립 자르기 (8초, 무음, 720p):
   `ffmpeg -ss <시작> -t 8 -i candN.webm -an -vf scale=-2:720 -c:v libx264 -preset veryfast -crf 23 assets/samples/<slug>/clipK.mp4`
6. AI 이미지 1~2장(Figma)을 중간에 섞기 — 영상에 없는 '결정적 장면'(예: 용암을 물에 식히는 순간, 실험실 분석).
7. plan.json 에 `"media"` 로 장면별 소재 지정 (beats + question + outro 순서, 질문·마무리는 마지막 영상 재사용):
   `[{"video":"clip0.mp4"},{"video":"clip1.mp4","start":0},{"image":"img3.jpg"}, ...]`
   설명란에 `영상 출처` 목록(candidates.json 의 credit)을 넣기 — CC BY 필수 조건.
8. 더빙(용식, 1.0으로 녹음 → 코드가 1.4배속, **25초 넘으면 자동으로 더 빠르게**) → 합성 → 미리보기 → 컨펌 → 업로드 (위 6·7단계와 동일).
   예시 폴더: `assets/samples/lava_sampling/`.

## 유튜브 CC 영상에 대해
- 유튜브 'Creative Commons' 영상은 **라이선스상 재사용 가능**하지만, 유튜브 약관은 **외부 프로그램으로 내려받기를 금지**하고 서버에서는 봇 차단도 됨 → 다운로더를 만들지 않는다.
- 대신 유튜브 CC 영상 상당수가 **위키미디어 공용에 라이선스 검수 후 옮겨져 있음**(video2commons) → cc-find 가 그걸 찾는다.
- 유튜브에서 찾은 영상을 쓰고 싶으면: 같은 제목으로 위키미디어 검색 → 있으면 사용. 없으면 사용자가 원작자 공식 채널인지·CC BY인지 확인 후 직접 받아 첨부(사용자 판단·책임) → `assets/samples/<slug>/` 에 넣고 같은 순서.
- 재사용 콘텐츠 정책: 자르기만 하면 수익화 거절 → 반드시 내레이션·자막·카드·질문으로 재가공.
