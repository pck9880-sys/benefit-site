# Mac 에서 숏츠 자동화 돌리기

## 1. 한 번만 설치 (터미널)
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git python@3.12 ffmpeg node
npm install -g @anthropic-ai/claude-code
cd ~ && git clone https://github.com/pck9880-sys/benefit-site.git && cd benefit-site
python3 -m pip install -r requirements.txt playwright edge-tts
python3 -m playwright install chromium
```

## 2. Claude Code 로그인 + Figma 연결
```
cd ~/benefit-site && claude          # 처음 한 번 로그인
claude mcp add --transport http figma https://mcp.figma.com/mcp   # Figma 공식 MCP (안 되면 Figma 도움말의 주소 사용)
```
claude 안에서 `/mcp` → figma 로그인. 스킬은 저장소의 `.claude/skills/shorts/` 가 자동으로 잡힘.

## 3. 테스트 1번
```
~/benefit-site/scripts/mac/shorts_hourly.sh && tail -30 ~/benefit-site/shorts_hourly.log
```

## 4. 1시간마다 실행 (새벽 1~8시, 매시 7분)
```
crontab -e
```
아래 한 줄 붙여넣기:
```
7 1-8 * * * /bin/zsh -lc "$HOME/benefit-site/scripts/mac/shorts_hourly.sh"
```
- Mac 이 잠들면 안 돌아감: 시스템 설정 → 배터리/에너지 → '디스플레이가 꺼져 있을 때 자동 잠자기 방지' 켜기, 전원 연결.
- cron 이 파일에 접근하려면: 시스템 설정 → 개인정보 보호 → 전체 디스크 접근 → `/usr/sbin/cron` 추가.
- 끄기: `crontab -e` 에서 그 줄 앞에 `#`.

## 5. 아침에
- `assets/samples/_queue.md` 에 대본·설명·고정 댓글, 각 폴더 `preview.mp4` 에 미리보기.
- 용식 녹음(1.0배속) → `assets/samples/<slug>/voice.mp3` 로 저장 →
  `python3 -c "from bot import shorts; shorts.render_sample('assets/samples/<slug>')"` → `shorts_sample.mp4` 가 최종본.
  (또는 Claude Code 에 "○○ 더빙 넣어줘")
