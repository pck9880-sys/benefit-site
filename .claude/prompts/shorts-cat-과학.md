[종류 규칙: 과학 — 위인 3D 템플릿 (기준 예시: assets/samples/galileo_falling '무거운 게 먼저 떨어질까? 갈릴레이의 답', 2026-11-20 사용자 확정)]
- **템플릿 고정**: `python -m bot.plan_tool new <slug> 과학` 이 8단계(질문→옛 상식→인물 의문→공중제비→실험→원리→현대 증명→결과)와 scenes3d.json 뼈대를 만든다. 그 흐름·연출(3D 캐릭터, 증명 클립이 ⑦·⑧·마무리까지 한 컷, 스틸 확인 후 렌더)을 그대로 따른다.
- 주제: 과학자(위인)가 이뤄낸 것 1개. 만든 편(아인슈타인 광전효과, 갈릴레이 낙하) 제외. 대본 공백 빼고 105~115자(더 길면 목소리가 빨라짐).
- 뼈대: `python -m bot.plan_tool new <slug> 과학`. 과학·원리 주제 1개 (일상에서 궁금한 것: 비행기·지구·날씨·우주·몸 등).
  이미 만든 주제(assets/samples/*/plan.json topic) 제외. 정치·사고·사망 제외.
- 사실 확인: WebSearch 로 공식·신뢰 자료(기관·교과서·백과·공식 해설) 2곳 이상. 숫자는 확인했거나 공식으로 직접 계산한 값만.
- 대본 8문장, **존댓말 설명체**('~입니다/~이죠'), 한 문장 30자 이내, 공백 빼고 130자 이내. 흐름 5단계:
  ① 문제(답답함/궁금증) ② **"~때문에 미쳐서 공중제비를 돌아버립니다"** 딱 1번 (이 장면 = 공중제비 flip)
  ③ 해결: 전문 용어 1~2개 쉬운 말로 ④ 원리(숫자·용어 정확히)
  ⑤ 결론은 outro 에: "**~해서 ~덕분에 ~된 겁니다**" — 도구가 뒤에 "정말 신기하죠?" 를 자동으로 붙인다(직접 쓰지 않아도 됨).
- 화면 (media 를 문장 수만큼 직접 지정, 화면 전환 적게):
  · 3D 장면: `python -m bot.scene3d <장면.json> assets/samples/<slug>/clip_*.mp4` — type: globe_route, map_compare, orbit_plane,
    moon_face(달 앞면), moon_far(달 뒷면 보이기), moon_lock(달 공전), moon_pullback(달에서 멀어지기), analogy(가운데를 보며 도는 사람 비유),
    two_dials(두 주기 비교 숫자 카운트, seconds 는 그 문장 길이에 맞게 2~3초), starfield(공중제비 배경용). 장면 설정은 scenes3d.json 에.
  · **같은 그림·클립 재탕 금지**(한 편 안에서 장면마다 다른 화면, 이전 편 장면 재사용 금지). 주제와 상관없는 지구본 끼워 넣기 금지.
  · 같은 클립을 두 문장에 이어 쓰면 자동으로 끊김 없이 이어짐(start 는 0 으로 둬도 됨).
    같은 클립을 이어 쓸 땐 {"video": "clip.mp4", "start": 초}, 클립보다 긴 장면은 마지막 프레임 이미지(`ffmpeg -sseof -0.1 -i clip.mp4 -frames:v 1 x.jpg`).
  · 3D 로 표현하기 어려운 장면은 gpt_images(극사실, 글자 없음) 1~2장.
  · **고품질 3D(기본)**: `python -m bot.scene3d_pro <장면.json> <출력.mp4>` — 빛 번짐·그림자·금속 질감. type: medal, photo(color blue/red), photon_hit, solar,
    scientist(mode flip=공중제비 / think / medal: 아인슈타인풍 만화 과학자). 새 주제면 장면을 scene3d_pro.py 에 추가해서 만든다.
  · **과학엔 일본짤(いらすとや) 안 씀** (2026-11-20). 공중제비는 3D 캐릭터(scientist flip 등)로.
- 더빙은 **필재 고정**(도구가 자동). 반응 댓글 카드 없음. 웍스엔 제목만 보낸다.
- yt_title, description(출처·계산 방법·이미지 출처), tags, sources, pin_comment, credits.

- **애니메이션 키트 참고**(2026-11-20): `.claude/skills/shorts/animation-kit.md` 를 읽고 장면을 고른다 — 수치=graph식 카운트업, 구조=breakdown식 분해도+지시선, 우주=플랫 우주풍, 캐릭터=zach식 만화 얼굴(눈꺼풀·입 표정)+피사계심도+비네트·그레인. 렌더 전 스틸 확인.
