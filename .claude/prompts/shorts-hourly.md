[숏츠 자동 제작 – 1회 1편 / Mac 로컬용. 대본·자료만 만들고, 이미지·더빙·합성·업로드는 다음 단계 스크립트가 자동으로 함]
사용자에게 묻거나 보고하지 않는다. 결과 보고는 3줄 이내.

0) 종류와 템플릿: 맨 아래 [이번 회차] 종류로 만든다. 먼저 뼈대 만들기:
   `python -m bot.plan_tool new <영문슬러그> <웃긴글|감동|이슈>` → assets/samples/<slug>/plan.json 의 빈칸만 채운다.
   주제는 assets/samples/*/plan.json 의 topic, _queue.md 와 겹치지 않게.
   공통 제외: 정치·선거·사망·사고·범죄피해·연예인 사생활·특정 개인 비방. 스포츠는 축구만.

1) 채울 것 (종류별 규칙은 아래 [종류 규칙])
   - topic, title_top/title_bottom: **각 줄 공백 빼고 9자 이내**, 짧고 임팩트 (예: "가격이 싸졌는데" / "살 수가 없음").
   - beats[].narration 11~12개: **음슴체 고정 "~함/~했음/~임/~됨/~라고 함"**. "~요/~습니다/해요잉" 금지. 한 문장 30자 이내.
     훅→상황→전개→반전→마무리. 마무리 멘트는 자동('님들 생각은 어떰?')이라 쓰지 않는다. 남는 빈 beat 는 지운다.
     실제 댓글을 중간 카드로 보여줄 beat 는 overlay "comment", overlay_text(실제 댓글), overlay_source "커뮤니티 반응" (1~2개).
   - gpt_images[].prompt: 장면별 영어 프롬프트 (구체적으로, 사람은 가상 인물). 스타일 꼬리·썸네일 문구는 도구가 자동으로 붙인다.
   - thumb_caption (15자 이내 훅, 감동은 비워도 됨), end_comments: 원글 **실제 댓글** 3~5개 [{"text","likes"}] (닉네임 제외, 지어내기 금지).
   - yt_title(20자 안팎, #shorts 자동), description(음슴체, 고지문은 도구가 자동), pin_comment(음슴체 질문), sources(출처 URL).
   - 실제 사진: `python -m bot.realimg <URL> assets/samples/<slug>/rN.jpg <none|auto|all>` (사람 보이면 auto/all, 제품·풍경만 none).
     워터마크·방송 로고 큰 사진, 개인 신상 보이는 사진 금지.
2) `python -m bot.plan_tool check <slug>` → '고칠 것' 이 나오면 고치고 다시. OK 가 나오면 끝(장면 배치·썸네일·고지문은 자동).
   렌더·썸네일 합성·이미지 생성은 하지 않는다.
3) assets/samples/_queue.md 맨 아래에: 순서번호 · 만든 시각 · 종류 · slug · 제목 · 핵심 한 줄 · 녹음 대본(코드블록).
4) git add 로 그 폴더와 _queue.md 만 지정해서 커밋 (git commit -a 금지). push 는 가능하면.
5) 실패하면 _queue.md 에 '실패: 이유' 한 줄만 남기고 끝낸다.
