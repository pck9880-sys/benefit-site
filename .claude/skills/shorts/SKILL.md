---
name: shorts
description: 유튜브 숏츠 1편을 빠르게 만드는 작업 순서 (뉴스 이슈형 + CC 영상 재가공형). 사용자가 숏츠/쇼츠 제작, 오늘 이슈 영상, 더빙 파일(mp3) 첨부, 영상 업로드를 요청할 때 사용. 주제 3개 추천 → 사실 확인 → 대본 → Figma GPT 이미지 → 타입캐스트 더빙 프롬프트 → 합성·미리보기 → 컨펌 후 업로드.
---

# 숏츠 1편 제작 (반자동)

## ★ 기본값 (2026-11-20, 자동 운영)
- **주기**: 하루 6편(0·3·6·12·16·20시) 제작 → 크롬 Claude 더빙 → 유튜브 **자동 공개 업로드**. 중간 보고·확인 없음. (`scripts/mac/shorts_hourly.sh`, 크론 `7 0,3,6,12,16,20 * * *`)
- **카테고리 템플릿(2026-11-20)**: `templates/shorts/{웃긴글,감동,이슈}.json` + `python -m bot.plan_tool new|check <slug>` (뼈대 생성 → 빈칸만 채움 → 자동 보정·검사).
  프롬프트: 공통 `.claude/prompts/shorts-hourly.md` + 종류별 `shorts-cat-<종류>.md`.
- **속도·사용량**: 이미지(ChatGPT)와 더빙(타입캐스트)을 동시에, 크롬 단계는 `--model sonnet`. 단계별 시간·토큰은 `~/쇼츠작업/usage.tsv`.
- **종류 순환**: 유머 2 → 감동 1 → 핫이슈 2 → 반복 (`~/쇼츠작업/rotation.txt`). 규칙은 `.claude/prompts/shorts-hourly.md`.
  - 기본: 커뮤니티 실제 썰 2~3개 재구성 + 실제 댓글 카드. / 웃긴글: 페페 짤(`~/쇼츠작업/짤/페페/`, 혐오 변형 금지). / 감동: 짤 0장.
- **음악(필수)**: 업로드 때 PC 스튜디오에서 저장한 사운드 곡을 넣음. 유머·핫이슈 = 영원은 그렇듯 → Machi No Dorufin → Helios, 감동 = 은방울 → 꿈꾸던 어른이 되었나요? 돌아가며 (`shorts_chrome_prep.sh` SONGS). 못 넣으면 공개 안 함.
- **끝 장면**: `shorts.comments_card` — 실제 댓글 캡처 카드(`end_comments`), 2.5초 더 길게. **더빙 1.2배 고정**.
- **업로드 계정**: `~/쇼츠작업/upload_account.txt` 의 구글 계정 채널로만 (저장소엔 안 올림).
- **더빙**: 타입캐스트 **자바바·제롬·구리** 셋만. 한 편에 2명 — 본문 1명 + 마지막 멘트만 다른 1명 (편마다 돌아가며, `~/쇼츠작업/voice_rotation.txt`).
- **첫 장면**: `shorts.intro_card` — 커뮤니티 글 첫 화면 카드(이모지·게시판 이름 초록 + 글 제목). 기본 켜짐, `"intro_post": false` 로 끔.
- **자막**: `caption_style: "mix"` — 4종(흰/검정테두리, 빨강/흰테두리, 검정/흰테두리 Jua, 주황빨강 그라데이션/검정테두리 도현)을 장면마다 돌아가며. 폰트는 assets/fonts(OFL).
- **AI 이미지**: Figma 대신 **ChatGPT 웹**(크롬 Claude) — plan `gpt_images` → `scripts/mac/shorts_gpt_images.sh <slug>`. 실패 장면은 폴더의 다른 이미지로 채움.
- **실제 사진**: `python -m bot.realimg <URL> rN.jpg auto|all|none` — 사람 얼굴·머리 자동 모자이크(macOS Vision, `scripts/mac/faces`), 군중은 전체 흐림, 제품은 그대로. AI 이미지와 섞어 씀.
- **썸네일**: `bot/thumb.py` — 웃긴글·기본 = AI 성인 여성(핏 좋은 옷, V넥 가슴골 살짝 허용, 속옷·수영복·노출·선정 자세 금지) + 리액션 + 제목 / 감동 = 장면 컷.
- **파일**: `~/쇼츠작업/<날짜>_<slug>/{원본,더빙용}`, `결과.txt`(업로드 링크·고른 곡). 크롬 저장·파일 창 대신 `scripts/mac/drop_server.py`.

## ★ 한국 뉴스형 (지금 기본, 예: ai_suneung 'AI 전담 감독관')
- 한국 핫이슈 + AI 이미지 + 중간중간 **짤 1~2장(いらすとや)** + 기사·여론 카드 + 용식 더빙. **길이 30초 기본** (SHORTS_MAX_SECONDS=30).
- 대본은 '말하려는 핵심 한 줄'을 먼저 정하고: 훅 → 배경 → 핵심 사실(숫자) → 쟁점 → 정리. 문장 6~7개.
- 마무리는 고정: **"님들은 어떻게 생각해요잉?"** (config.SHORTS_OUTRO, 자동으로 붙음). 별도 question 은 비움.
  다른 마무리를 쓰려면 plan 에 `"outro_custom": true` + outro.
- 짤: `python -m bot.irasutoya <일본어 검색어>` (예: カンニング, 試験, 驚く, 会社員) → `irasutoya.save(url, 폴더/zN.png)`.
  N = 장면 번호 → 흰 바탕 가운데에 통째로 표시. media 목록에선 `{"zzal": "z3.png"}`.
  いらすとや 규약: 상업 이용 가능, 한 작품 20장 이하, 비방 용도 금지 → 1편에 1~3장만.

## 게임형 템플릿 = 밈 자막 + 게임 대사 섞기
새 숏츠는 특별한 요청이 없으면 아래 '밈 자막 + 게임 대사 섞기' 형식으로 만든다 (기준 예시: `assets/samples/kcd2/`).
- `caption_style: "meme"`, `mixed_audio: true`, 대사 장면 `orig_audio: true`, 더빙 장면 durations 0, 길이 최대 30초.
- 끝: 토론 질문(A냐 B냐) + 대중 입장 한마디. **시그니처 문구(해요잉 등) 사용 안 함.**
- 사용자에게 더빙 문장만(대사 장면 제외) 1.0배속 녹음 요청 → 코드가 1.4배속.

## 0. 원칙 (꼭 지킬 것)
- 주제: 그날 핫이슈. **스포츠는 축구만**. 정치·선거, 사망·사고·자살, 범죄 피해자, 연예인 사생활·루머, 특정 개인 비방은 제외.
- 사실만: 웹 검색 + 기사 본문(web-fetch 에이전트)으로 확인한 사실만. 제목에서만 확인된 내용은 2개 이상 언론사일 때만, "~라고 함"으로.
- 남의 영상·기사 화면·댓글을 **캡처하지 않는다**. 기사 제목/여론/발언은 카드로 **직접 그린다**(overlay). 여론은 기사에 인용된 실제 반응만, 지어내기 금지, 닉네임·프로필은 흐림(코드가 자동 처리).
- 실존 인물 얼굴을 AI로 만들지 않는다 (뒷모습·손·사물로 연출).
- **예전 영상에 쓴 이미지는 재사용 금지** — 매번 새로 생성. 이미지는 자극적·영화 같은 연출(빨간 조명, 현행범 순간, 스릴러 분위기 등), 단 얼굴·글자·로고 없이.
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
- 목소리: 기본 **용식** / 요청 시 **박창수**·**태우**. `voice` 필드에 이름.
- 마무리(`outro`): **시그니처(해요잉 등) 쓰지 않음** → 시청자(대중) 입장 공감 한마디 (예: "솔직히 이 정도면 인정이지").
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
8. 마무리: 시청자(대중) 입장 한마디 (예: '솔직히 난 열 배 줘도 못 함'). 질문은 그대로 둔다.
9. 더빙(용식, 1.0으로 녹음 → 코드가 1.4배속, **25초 넘으면 자동으로 더 빠르게**) → 합성 → 미리보기 → 컨펌 → 업로드 (위 6·7단계와 동일).
   예시 폴더: `assets/samples/lava_sampling/`.

## 유튜브 CC 영상에 대해
- 유튜브 'Creative Commons' 영상은 **라이선스상 재사용 가능**하지만, 유튜브 약관은 **외부 프로그램으로 내려받기를 금지**하고 서버에서는 봇 차단도 됨 → 다운로더를 만들지 않는다.
- 대신 유튜브 CC 영상 상당수가 **위키미디어 공용에 라이선스 검수 후 옮겨져 있음**(video2commons) → cc-find 가 그걸 찾는다.
- 유튜브에서 찾은 영상을 쓰고 싶으면: 같은 제목으로 위키미디어 검색 → 있으면 사용. 없으면 사용자가 원작자 공식 채널인지·CC BY인지 확인 후 직접 받아 첨부(사용자 판단·책임) → `assets/samples/<slug>/` 에 넣고 같은 순서.
- 재사용 콘텐츠 정책: 자르기만 하면 수익화 거절 → 반드시 내레이션·자막·카드·질문으로 재가공.


## 더빙 없이 현장음 살리기 모드 (keep_audio)
- plan.json 에 `"keep_audio": true`, `"durations": [장면별 초 ...]`(beats+question+outro 개수, 합계 25초 이하) → 원본 영상 소리를 장면마다 그대로 쓰고 자막만 띄움. 배경음악 자동 끔, 소리 크기 자동 맞춤(-14 LUFS).
- 클립은 소리 포함해서 자르기: `ffmpeg -ss <t> -t 6 -i candN.webm -vf scale=-2:720 -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 160k -ar 44100 -ac 2 clipK.mp4`
- 자를 때 `volumedetect` 로 mean_volume 확인 — -60dB 이하는 무음이라 다른 구간으로 교체.
- beats 의 narration 은 '자막 문구'(짧게, 12자 내외). 예시: `assets/samples/black_eagles/`.

## 국내 사용 가능 영상
- 위키미디어의 **공공누리 1유형(KOGL Type 1)** 허용 (코드 반영) — 국방부·KTV 등. 2~4유형은 제외.
- 미 국방부·NASA 촬영본은 퍼블릭 도메인 (한국 행사여도 미군 촬영이면 가능, 예: 서울 ADEX).
- 위키미디어 검색은 영어 단어가 엉뚱하게 매칭될 수 있음(예: drum→buk) → 결과 제목 꼭 확인.
- 경복궁 수문장 교대식처럼 SA 라이선스만 있는 주제는 불가 → 사용자가 공공누리(kogl.or.kr) 1유형 영상을 직접 받아 첨부하면 사용.


## 현장음·국뽕형 옵션 (plan.json)
- `"caption_style": "epic"` — 박스 없는 굵은 흰 자막 + 검은 테두리, `**강조**` 는 금색, 부드럽게 나타남, 아래쪽 그라데이션.
- 자막 앞에 `[현장 MC]` 처럼 쓰면 빨간 배지로 표시 (실제 발언 장면).
- beat `"slowmo": true` 하이라이트 슬로모션 / `"outro_impact": true` 마무리 흰 플래시 + 화면 가운데 큰 자막.
- `"bgm": {"file":"bgm.mp3","start":14,"lufs":-24,"credit":"..."}` — 옅은 음악, 현장음이 크면 자동으로 더 작아짐(덕킹). 음악은 `bgm-get.yml -f mode=tag:epic` 로 후보 받기, 마무리 쯤 커지는 구간을 start 로.
- **현장음형은 'A vs B 뭐가 더 좋음?' 질문을 넣지 않는다** (`"question": ""`). 마무리는 강렬한 한마디(예: "이게 **대한민국 공군**이다").
- 장면 전환 때 현장음은 자동으로 짧게 페이드(끊김 방지). 장면 첫 1초가 엉뚱하면 media 에 `"start"` 로 건너뛰기.
- 실제 음성(인터뷰·MC) 찾기: 원본 오디오를 16kHz wav 로 뽑아 `faster-whisper`(pip, 모델 small/medium)로 받아쓰기 → 신뢰도 높은 구간만 자막과 함께 사용. 불확실하면 쓰지 않는다.


## 예능 편집형 (동물·일상 CC 영상 + 예능 자막)
- 공중파·유튜브 예능 클립은 저작권 때문에 사용 불가 → CC BY 동물·일상 영상에 예능 자막을 입힌다.
- 위키미디어 검색은 학명이 정확함 (예: Pygoscelis papua, Ailurus fulgens, Enhydra lutris).
- `"caption_style": "variety"` — 색 박스(노랑·핑크·하늘·연두·주황 순환) + 검은 테두리 + 살짝 기울기 + 부드럽게 등장.
  beat 에 `"sticker": "ㅋㅋㅋ"` 같은 리액션 스티커(오른쪽 위).
- **더빙은 첫 문장만**: `"keep_audio": true, "intro_voice": true, "durations": [0, ...]` (0 = 첫 장면 길이를 목소리 길이에 자동 맞춤).
  사용자에게 첫 문장만 녹음받아 `voice.mp3` 로 → 1.4배속, 목소리 나올 때 현장음 자동으로 줄임. 녹음 없으면 임시 음성.
- 마무리는 대중 입장 공감 한마디 (질문 없음). 예시: `assets/samples/penguin/`.


## 게임형 (스팀 공식 영상 + 평점/실사/AI)
- 게임 영상은 **게임사가 스팀 상점에 올린 공식 트레일러·게임플레이**만 사용 (개인 유튜버 플레이 영상은 그 사람 저작물이라 불가).
  인기 게임: `curl -s "https://store.steampowered.com/api/featuredcategories?cc=kr&l=koreana"` (top_sellers 등)
  영상 주소: `api/appdetails?appids=<id>` → movies[].hls_h264 → `ffmpeg -i "<m3u8>" -c copy trailer.mp4`
  장면 컷은 `-an` (트레일러 음악은 Content ID 위험 → 우리 음악·더빙 사용).
- 카드: `overlay: "score"` (overlay_text "Metacritic|78|100;OpenCritic|80|100") / `overlay: "steam"` ("복합적|대체로 긍정적|기간 설명").
  점수는 OpenCritic·Kotaku 등 보도로 확인, 설명란에 "점수는 보도 기준".
- 실사: 같은 주제의 위키미디어 CC BY/CC0/PD 사진·영상 (SA 제외) — `photo-check.yml -f "query=검색어1|검색어2"` → 아티팩트 photos.
- AI 이미지: 게임과 현실을 잇는 장면 (예: 1403년 도시 재현).
- 길이 최대 30초 (`SHORTS_MAX_SECONDS` 기본 25 — 게임형은 대본을 짧게 유지). 예시: `assets/samples/crimson_desert/`, `assets/samples/kcd2/`.


## 밈 자막 + 게임 대사 섞기 (게임형 추천 조합)
- `"caption_style": "meme"` — Black Han Sans(assets/fonts, OFL), 영상 가운데, 기울임 + 두꺼운 검은 테두리, **줄마다 색이 다름**(흰·핑크·노랑·하늘), 대사는 “따옴표”. 제목도 두 줄 모두 흰색 큰 글씨.
- `"mixed_audio": true` + 대사 장면 beat 에 `"orig_audio": true` → 그 장면은 **게임 원본 대사**(자막은 한국어 번역), 나머지 장면만 더빙.
  durations 는 대사 장면만 초 단위(나머지 0 = 더빙 길이 자동). 대사 클립은 소리 포함해서 자르기.
- 대사 찾기: 트레일러 오디오를 faster-whisper 로 받아쓰기 → 또렷한 문장 구간 사용.
- 사용자에게는 **더빙 문장만**(대사 장면 제외) 녹음 요청 → 1.4배속, 대사 사이 빈 구간에 자동 배치.
- 시네마 레터박스는 `ffmpeg cropdetect` 로 확인 후 클립 자를 때 crop.


## 스팀에 없는 게임 (예: GTA6) — 공식 미디어 자료
- 게임사 공식 사이트의 미디어/프레스 페이지에서 직접 받기. 록스타: `https://www.rockstargames.com/VI/media` → HTML 안의 `media-rockstargames-com.akamaized.net/.../downloads/videos/<이름>/<이름>.mp4` 와 `downloads/screenshots/*.zip`.
- **용량 먼저 확인** (`curl -sI` 로 content-length): 'An Extended Look' 같은 긴 영상은 14GB → 받지 말 것. 런치 트레일러(약 750MB)·스크린샷 zip(약 110MB)이면 충분.
- 트레일러 소리는 빼고(-an) 더빙 + 배경음악. 설명란에 "게임사 공식 미디어 자료" 표기. 록스타는 수익 영상은 정책 범위 밖 → 사용자에게 신고 위험 안내.
- 예시: `assets/samples/gta6_launch/`.

## 효과음
- 기본은 넣지 않는다 (SHORTS_SFX=0). 소리 파일(똑 pop.wav / 띵 ding.wav)은 assets/sfx 에 보관 — 요청할 때만 `SHORTS_SFX=1`.

## 채널 성장 규칙 (2026-11-20 반영)
- **하루 1~2개**만 업로드 (유튜브 하루 한도 + 신선도). 다음날 올릴 영상은 전날 밤에 미리 만들어 둔다. 대본은 '내일 아침 기준' 시제로.
- **시리즈 이름**을 제목·설명에 붙인다: 예) `[오늘의 이슈]`, `[AI 부정행위 시리즈 #2]`. 같은 주제가 이어지면 마지막 정리 문장에 "다음 편은 ○○" 한 줄.
- **고정 댓글** 문구를 매번 같이 준다: 영상 질문 + A/B 선택지 (예: "🅰 찬성 / 🅱 반대 — 님들은 어떻게 생각해요잉?").
- 사용자에게 줄 것: 최종 mp4 + 제목 + 설명 + 고정 댓글 (사용자가 직접 업로드).
- 채널 배너: `kmong/channel/banner_G_30s.png` ("30초 만에 정리해요잉~").
- 자막(box): **한 문장 = 한 자막**, 중간에 끊지 않음 (단어 단위 줄바꿈, 최대 2줄 균형). 문장은 30자 이내로 쓴다.
