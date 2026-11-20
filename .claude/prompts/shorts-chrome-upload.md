[숏츠 자동 업로드 – 크롬 Claude / 사용자에게 묻거나 중간 보고하지 않음]

0) 크롬이 여러 대 연결돼 있으면 **macOS(iMac) 크롬**을 쓴다 (Windows 등 다른 기기 크롬 금지). 선택이 필요하면 macOS 쪽을 고른다.
작업 폴더: {{DIR}}  (로컬 서버 http://127.0.0.1:{{PORT}}/)
업로드 정보: {{DIR}}/업로드정보.json (title, description, tags, pin_comment, thumb, music_concept)
올릴 영상: 더빙용/영상.mp4

1) studio.youtube.com 을 열고 **반드시 계정 {{ACCOUNT}} 의 채널인지 확인**(오른쪽 위 프로필 → 계정 전환).
   다른 계정이면 '계정 전환'으로 {{ACCOUNT}} 로 바꾼다. 그 계정이 목록에 없거나 로그인(비밀번호)이 필요하면
   업로드하지 말고 '실패: {{ACCOUNT}} 로그인 필요' 를 {{DIR}}/결과.txt 에 쓰고 끝. 확인되면 '만들기 → 동영상 업로드'.
2) **'파일 선택' 버튼을 누르지 말 것 (파일 창이 떠서 멈춤).** 스튜디오에서 127.0.0.1 로 바로 fetch 하면 크롬이 막는다 → 보내기 페이지를 거친다:
   `const w = window.open('http://127.0.0.1:{{PORT}}/_send.html')` (팝업이 막히면 임시 버튼 클릭으로 연다) → ready 후
   `w.postMessage({get:'더빙용/영상.mp4'}, '*')` → 받은 {blob} 으로
   ```js
   const f = new File([blob], 'shorts.mp4', {type:'video/mp4'});
   const dt = new DataTransfer(); dt.items.add(f);
   const inp = document.querySelector('input[type=file]'); inp.files = dt.files;
   inp.dispatchEvent(new Event('change', {bubbles:true}));
   ```
3) 제목·설명 입력, '아동용 아님', 태그(자세히 보기)에 tags.
   썸네일: 같은 방식(_send.html 로 thumb.jpg)으로 넣어 본다. 반응이 없으면(채널 인증 전) 1번만 시도하고 건너뛴다 — 첫 화면 카드가 기본 썸네일.
   'AI로 변경·합성된 콘텐츠' 는 '예'.
4) **음악**: 업로드정보.json 의 music 값.
   - "영상에 포함" → 이미 곡이 깔려 있음. 아무것도 하지 않는다.
   - "앱에서 추가 필요" → PC 스튜디오에는 저장한 사운드를 넣을 곳이 없다(2026-11-20 확인: 업로드 창·세부정보·편집기 모두 없음).
     **찾지 말고 바로 넘어간다** (시간 절약). 오디오 보관함 무료 곡도 넣지 않는다.
5) 공개 상태 **'{{PRIVACY}}'** 로 저장/게시. ('비공개'면 공개로 바꾸지 않는다.)
6) 게시 뒤 영상 링크를 결과.txt 에 `업로드({{PRIVACY}}): https://youtube.com/shorts/<ID>` 로 기록. '공개'일 때만 pin_comment 를 댓글로 달고 고정.
   결과 보고는 짧게(3줄 이내).
7) 확인창(confirm/alert) 띄우는 동작 금지. 결제·인증 요구 화면이 나오면 중단하고 결과.txt 에 이유 기록. 연 탭은 끝나면 닫는다.
