# 애니메이션 스킬 키트 (참고: artemnovitckii/claude-animation-skills, MIT)
출처: https://github.com/artemnovitckii/claude-animation-skills (로컬 사본 ~/claude-animation-skills)
2026-11-20 학습. 설치(install.sh / kit/setup.sh)는 권한 승인 대기 — 승인 전엔 아래 기법을 우리 엔진(bot/scene3d_pro.py)에 옮겨 쓴다.

## 스킬 11개 → 과학 숏츠에서 쓰는 곳
| 스킬 | 만드는 것 | 우리 쓰임 |
|---|---|---|
| graph | 선이 그려지며 큰 숫자 카운트업 (흑/백) | 수치 변화(온도·속도·인구) 장면. 실제 데이터만 |
| map-route | 흰 3D 도시 + 경로 그려짐 + 핀 낙하 + ETA 카운트다운 | 이동·거리 주제 (대권항로류) |
| breakdown | 3D 분해도, 층마다 지시선+라벨 | "속은 이렇게 생김" 원리 장면 (태양전지·배터리·눈 구조) |
| minimalistic-graphics / dan-koe | 검정 바탕 헤어라인 + 흰 점 | 개념 요약·결론 장면 |
| kurzgesagt(풍) | 플랫 벡터 우주, 한쪽 조명 행성+초승달 그림자+글로우, 알약 라벨 | 우주·스케일 비교. 그 채널 캐릭터·그림 복제 금지, 이름은 '플랫 우주풍' |
| low-poly | PS1 저폴리(360x640 렌더→3배 최근접 확대, 정점 흔들림, 디더링) | 슬프거나 신기한 실화 |
| minecraft(풍) | 블록이 하나씩 쌓이는 복셀 빌드 | "하나씩 쌓아서 만든다" 원리. 모장 텍스처 금지 |
| zach-d-films / zach-3d-films | 3D 만화 사람·소품, 슬로모션 충돌, 빨간 힘 파동 | **주인공 캐릭터(아인슈타인풍 등)·공중제비·충돌 장면** |
| stick-figure | 막대 인간 설명 릴스, 휩 전환, 코드 효과음 | 가벼운 역사·상식 |

## 고품질 3D 비법 (zach-d-films 엔진 main.js / human.js)
- 렌더러: ACESFilmic, exposure 1.0, PCFSoftShadow(맵 1536, bias -0.0004, normalBias 0.02, radius 4), HalfFloat 렌더타깃 + MSAA 4.
- **환경 반사**: PMREMGenerator 로 '하늘 구 + 소프트박스 판 3장(키 3.2·림 1.6·뒤 1.0)' 장면을 구워 scene.environment → 금속·광택이 진짜처럼.
- 하늘: 셰이더 그라데이션(top #2b78d6 → mid #5b9fea → horizon #92c3f2), 바닥은 ShadowMaterial(#1a3a66, 0.32) 로 그림자만.
- 조명: Hemisphere(#cfe4ff/#7f93ad 0.75) + 키(#fff3e6 2.3, 좌상앞) + 림(#dbe9ff 1.2, 뒤).
- 후처리 순서: Render → **Bokeh 피사계심도**(장면마다 focus/aperture) → Bloom(0.25,0.4,1.6 — 약하게) → Output → **그레이드(비네트 0.28 + 필름 그레인 0.018)**.
- 장면마다 update(t) 가 {dof, bloom, exposure} 를 돌려줌 → 컷마다 초점·빛 조절. update 는 t 만으로 결정(중간부터 렌더 가능).
- **캐릭터 얼굴**: 구 여러 개를 늘려 조립 — 두개골+볼+턱(jaw 그룹), 코 4구, 눈(흰자·홍채·동공 납작구)+**눈꺼풀 반구**(깜빡임·찡그림), 캡슐 눈썹, 귀, 콧수염, 윗입술/아랫입술/치아.
  setMouth(v)=턱 회전+입 늘림+눈썹 각도+눈꺼풀 → 말하기·놀람 표정. 관절 포즈 setPose({joint:[x,y,z]}) + lerpPose + 팔 IK.
- 연출: 2~4초마다 컷(문장 박자), 원리 장면 가장 길게, 충돌은 슬로모션+짧은 흔들림+불꽃+블룸, 'But/그런데' 반전에서 한 번 검은 화면 딥.
- 9:16 은 화각이 좁음(fov34 ≈ 19°) — 우리는 1080 정사각이라 여유 있지만, 자막 띠와 얼굴·핵심 소품이 겹치지 않게.

## 공통 규칙 (스킬들의 Taste)
- 숫자·사실은 출처 확인 후만. 그래프는 실제 값만(가짜 곡선 금지, 예시면 '예시'라고).
- 한 장면 = 한 아이디어, 라벨은 짧고 담백하게(슬로건·과한 화살표 금지).
- 렌더 전 스틸(--snap / stills) 로 먼저 확인 → 전체 렌더.
- 특정 채널·게임 이름/캐릭터/텍스처를 베끼지 않는다(스타일만).
