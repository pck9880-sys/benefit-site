# 정부혜택 자동 게시 사이트

공공데이터(정부24 혜택 정보) → Claude가 쉬운 안내글 작성 → 텔레그램으로 승인 요청 → 사이트 자동 게시 → 애드센스 수익.

**서버 없이 GitHub Actions만으로 매시간 자동 실행됩니다.**

```
매시간        텔레그램 버튼(승인/거절) 확인 → 반영
매일 7시      많이 찾는 혜택 5개 선택 → Claude가 글 작성 → 텔레그램으로 전송
12시간 무응답  자동 게시
게시 후       사이트 재빌드 (GitHub Pages, 무료)
```

## 처음 한 번만 하는 설정 (약 20분)

### 1. API 키 3개 받기
| 키 이름 | 받는 곳 | 비용 |
|---|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys (크레딧 $5 충전) | Sonnet 기준 글 1개 약 40원 (월 약 6천 원) |
| `DATA_GO_KR_KEY` | https://www.data.go.kr/data/15113968/openapi.do → 활용신청 → 마이페이지의 **일반 인증키(Decoding)** | 무료 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램에서 `@BotFather` → `/newbot` → 받은 토큰 | 무료 |

### 2. GitHub 저장소 설정
1. 저장소 **Settings → Secrets and variables → Actions → New repository secret** 에 위 3개 키 등록
2. **Settings → Pages → Source** 를 **GitHub Actions** 로 변경
3. **Actions** 탭 → `auto-pipeline` → **Run workflow** 로 첫 실행

### 3. 텔레그램 봇 연결
만든 봇에게 아무 메시지나 보내면 다음 실행(1시간 이내) 때 자동으로 주인으로 등록되고 안내 메시지가 옵니다.
바로 글을 받아보려면 봇에게 `/now` 를 보내세요.

## 이후 할 일
- 매일 텔레그램으로 오는 초안에 ✅ / ❌ 만 누르기 (안 눌러도 12시간 뒤 자동 게시)
- 글이 20~30개 쌓이면 (약 1주) https://adsense.google.com 신청 → 받은 `ca-pub-...` 를 Variables 의 `ADSENSE_CLIENT` 에 등록
- 구글 서치콘솔 / 네이버 서치어드바이저에 사이트 등록 + `sitemap.xml` 제출 (인증 코드는 Variables 에 등록)

## 봇 명령어
`/status` 현황·비용 · `/pause` 일시정지 · `/resume` 재개 · `/now` 즉시 생성 · `/approveall` 대기 초안 전부 승인

## 선택 설정 (Settings → Secrets and variables → Actions → Variables)
| 이름 | 기본값 | 설명 |
|---|---|---|
| `SITE_NAME` | 정부혜택 한눈에 | 사이트 이름 |
| `SITE_URL` | 자동 (github.io 주소) | 도메인 연결 시 변경 |
| `CLAUDE_MODEL` | claude-sonnet-5-5 | 비용을 줄이려면 `claude-haiku-5-5`, 품질을 더 올리려면 `claude-opus-5-5` |
| `POSTS_PER_DAY` | 5 | 하루 생성 글 수 |
| `GENERATE_HOUR_KST` | 7 | 생성 시각 (한국시간) |
| `AUTO_APPROVE_HOURS` | 12 | 무응답 시 자동 게시까지 시간 (0 = 승인해야만 게시) |
| `MAX_MONTHLY_USD` | 50 | 월 API 비용 상한 (넘으면 자동 중단) |
| `ADSENSE_CLIENT` | - | 애드센스 승인 후 `ca-pub-...` |
| `GOOGLE_SITE_VERIFICATION` / `NAVER_SITE_VERIFICATION` | - | 검색엔진 소유 확인 코드 |

## 로컬 테스트
```bash
pip install -r requirements.txt
MOCK=1 python -m tests.test_flow
```

## 🏆 공모전 출품안 자동 생성
매일 오전 8시(한국시간) 콘테스트코리아의 **네이밍·슬로건 / 아이디어** 공모전을 확인해서,
조건(접수 중 · 무료 · 온라인 접수 · 일반인 참가 · AI 사용 금지 문구 없음)에 맞는 것 중 상금이 큰 순으로
하루 최대 3개를 골라 Claude가 출품안 5개씩 만들어 텔레그램으로 보냅니다. **제출은 직접** 합니다.

- 필요한 키: `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN` (공공데이터 키는 필요 없음)
- 텔레그램 명령어: `/contest` 지금 받기 · `/contestoff` 끄기 · `/conteston` 켜기
- 설정(Variables): `CONTESTS_PER_DAY`(기본 3), `CONTEST_HOUR_KST`(기본 8)
- 개인 경험이 필요한 수기·사연, 사진·영상·디자인 공모전은 제외합니다.
