[종류 규칙: 핫이슈]
- 지금 한국 핫이슈 1개 (`python -m bot.trends` 또는 bot.trends.google_news). WebSearch 로 **2곳 이상 언론**에서 확인된 사실만.
- 실제 사진 1~3장: 기사 대표 이미지(og:image) 등을 bot.realimg 로 처리(사람 보이면 auto, 군중은 all).
- 기사 제목 카드: beat 2~3개에 overlay "headline", overlay_text(실제 기사 제목 원문), overlay_source(언론사명).
- end_comments 는 기사에 인용된 실제 반응·커뮤니티 실제 댓글.
- 짤은 쓰지 않거나 いらすとや 1장(`python -m bot.irasutoya <일본어>`).
