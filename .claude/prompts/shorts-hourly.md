[숏츠 자동 제작 – 3시간마다 1편 / Mac 로컬용. 제작만 하고, 더빙·업로드는 다음 단계 스크립트가 자동으로 함]

0) 종류 고르기 — 직전 편들과 돌아가며: assets/samples/_queue.md 마지막 편들의 종류를 보고
   기본(일상 썰) → 웃긴글 → 기본 → 감동 → 이슈(뉴스) 순서 중 다음 것. plan.json 에 "mood" 기록
   (이슈는 "mood": "기본", "kind": "이슈").
   주제는 assets/samples/*/plan.json 의 topic, _queue.md 와 겹치지 않게.
   공통 제외: 정치·선거·사망·사고·범죄피해·연예인 사생활·특정 개인 비방. 스포츠는 축구만.

1) 종류별 규칙
   ■ 기본(일상 썰) — 커뮤니티 실제 썰 재구성
     - WebSearch/WebFetch 로 커뮤니티(더쿠·네이트판·인스티즈·에펨코리아·블라인드 등) 공개 글 2~3개를 찾아
       실제 썰의 상황들을 짜깁기해 하나의 이야기로 다시 쓴다. 문장은 직접 새로 쓴다(원문 통째 복사 금지).
       개인 신상(실명·회사·학교·지역 특정)은 빼거나 바꾼다.
     - 커뮤니티 댓글·반응 카드 2~3개: 원글에 **실제로 달린** 댓글만(지어내기 금지), overlay "comment", source "커뮤니티 반응".
       닉네임은 쓰지 않는다. 베스트 댓글 위주.
     - 설명란 끝에 "※ 커뮤니티 실제 사연 여러 개를 재구성했어요." 와 출처 사이트명.
     - 짤: いらすとや 1~2장 가능 (`python -m bot.irasutoya <일본어>` → bot.irasutoya.save).
   ■ 웃긴글 — 짤은 **페페(Pepe the Frog) 짤** 2~3장
     - 짤 보관함 ~/쇼츠작업/짤/페페/ 에서 상황에 맞는 것 고르기. 부족하면 WebSearch 로 페페 밈 이미지를 찾아
       `curl -sfL -o ~/쇼츠작업/짤/페페/<영어설명>.png <URL>` 로 보관함에 추가 후 사용 → 폴더에 zN.png 로 복사, media 에 {"zzal": "zN.png"}.
     - 혐오·정치 상징으로 쓰이는 페페 변형(나치·인종 관련 등)은 절대 쓰지 않는다.
     - 웃긴 썰도 커뮤니티 실제 글 기반('기본' 규칙처럼 재구성 + 실제 댓글 카드).
   ■ 감동 — **짤 사용 자제(0장)**. AI 이미지만, 잔잔하고 따뜻한 연출. caption_style "epic".
     실제 사연(기사·커뮤니티)을 바탕으로 쓰고, 지어낸 이야기를 실화처럼 쓰지 않는다.
   ■ 이슈(뉴스) — shorts 스킬의 '한국 뉴스형' 그대로. WebSearch 로 2곳 이상 언론 확인, 기사 제목 카드(headline) 2~3개.

2) 공통 제작
   - 대본 11~12문장(반말 썰 말투, 한 문장 30자 이내, 훅→상황→전개→반전→마무리). question 은 비움. 마무리는 자동('님들은 어떻게 생각해요잉?').
   - AI 이미지: Figma MCP generate_image 4장 (fileKey XPyCf7k9rdYwZF42krwyZ4). 사람은 가상 인물만, 글자·로고 없음, 예전 이미지 재사용 금지.
   - **배경음악은 넣지 않는다** (업로드 때 유튜브 '저장됨' 사운드에서 고름). plan.json 에 "music_concept": "잔잔한 감동" | "신나는 코믹" | "일상 브이로그" | "긴장감 이슈".
   - 썸네일(기본값): 웃긴글·기본이면 `python -m bot.thumb prompt assets/samples/<slug>` 문구 그대로 Figma generate_image(세로)
     → assets/samples/<slug>/thumb_src.jpg. 문구의 안전 조건(성인·옷 다 입음·노출/선정적 자세 금지)은 빼거나 바꾸지 않는다.
     감동이면 생략. 그 뒤 `python -m bot.thumb assets/samples/<slug>` → thumb.jpg.
   - 렌더(임시 음성): `SHORTS_BGM=0 python -c "from bot import shorts; shorts.render_sample('assets/samples/<slug>')"` → shorts_sample.mp4 를 assets/samples/<slug>/preview.mp4 로 복사.
   - plan.json 에 yt_title(#shorts), description, tags, sources, pin_comment 포함.

3) assets/samples/_queue.md 맨 아래에: 순서번호 · 만든 시각 · 종류 · slug · 제목 · 핵심 한 줄 · 녹음 대본(코드블록) · 설명 · 고정 댓글.
4) git add 로 그 폴더와 _queue.md 만 지정해서 커밋 (git commit -a 금지). push 는 가능하면.
5) 사용자에게 묻거나 보고하지 않는다. 실패하면 _queue.md 에 '실패: 이유' 한 줄만 남기고 끝낸다.
