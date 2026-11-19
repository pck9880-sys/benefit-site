[숏츠 자동 제작 – 1회 실행에 1편, 업로드 금지 / Mac 로컬용]

1) shorts 스킬(.claude/skills/shorts/SKILL.md)의 '한국 뉴스형' 규칙대로 숏츠 1편을 만든다.
   - 주제: 지금 한국 핫이슈 1개 (`python -m bot.trends` 또는 bot.trends.google_news). 정치·선거·사망·사고·범죄피해·연예인 사생활 제외, 스포츠는 축구만.
     assets/samples/*/plan.json 의 topic, assets/samples/_queue.md 에 있는 주제와 겹치지 않게.
   - 사실 확인: WebSearch 로 2곳 이상 언론에서 확인된 사실만. 실제 기사 제목 카드(headline) 2~3개, 언론사명 정확히.
   - 대본 11~12문장(반말, 한 문장 30자 이내, 훅→배경→숫자→반전→쟁점). question 은 비움. 마무리는 자동('님들은 어떻게 생각해요잉?').
     caption_style "box".
   - 이미지: Figma MCP generate_image 로 새 AI 이미지 4장 (fileKey XPyCf7k9rdYwZF42krwyZ4). 자극적·영화 같은 연출, 얼굴·글자·로고 없음, 예전 이미지 재사용 금지.
     + いらすとや 짤 2~3장 (`python -m bot.irasutoya <일본어>` → bot.irasutoya.save). 저작권 캐릭터 짤 금지.
   - 렌더(임시 음성): `python -c "from bot import shorts; shorts.render_sample('assets/samples/<slug>')"` → 결과 shorts_sample.mp4 를 assets/samples/<slug>/preview.mp4 로 복사.
   - plan.json 에 yt_title, description, tags, sources, pin_comment 포함.
   - plan.json 에 "mood": "감동" | "웃긴글" | "기본" (배경음악은 bot.songs 가 ~/쇼츠작업/음원/<mood>/ 의 인기곡으로 자동 선택).
   - 썸네일(기본값): 웃긴글·기본이면 `python -m bot.thumb prompt assets/samples/<slug>` 문구 그대로 Figma generate_image(세로)
     → assets/samples/<slug>/thumb_src.jpg. 문구의 안전 조건(성인·옷 다 입음·노출/선정적 자세 금지)은 빼거나 바꾸지 않는다.
     감동이면 생략(장면 컷 사용). 그 뒤 `python -m bot.thumb assets/samples/<slug>` → thumb.jpg.
2) assets/samples/_queue.md 맨 아래에: 순서번호 · 만든 시각 · slug · 제목 · 핵심 한 줄 · 용식 녹음 대본(코드블록, 마지막 줄 '님들은 어떻게 생각해요잉?') · 설명 · 고정 댓글.
3) git add 로 그 폴더와 _queue.md 만 지정해서 커밋 (git commit -a 금지). push 는 가능하면.
4) 업로드·텔레그램 전송 금지 (더빙·스튜디오 초안은 다음 단계 스크립트가 따로 함). 실패하면 _queue.md 에 '실패: 이유' 한 줄만 남기고 끝낸다.
