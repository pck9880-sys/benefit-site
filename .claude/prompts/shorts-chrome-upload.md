[숏츠 자동 업로드 – 크롬 Claude / 사용자에게 묻거나 중간 보고하지 않음]

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
4) **음악** (업로드정보.json 의 music 값):
   - "영상에 포함" 이면 건너뛴다.
   - 아니면 업로드 후 스튜디오 **'편집기 → 오디오 → 오디오 보관함'(무료 음악)** 에서 music_concept 에 맞는 곡 1개
     (분위기·장르 필터 사용, 저작자 표시 필요 없는 곡 우선) → 영상 전체 길이에 배치 → 음악 볼륨은 목소리보다 작게(20~30%) → 저장.
     ('저장됨' 사운드는 휴대폰 앱 전용이라 PC 스튜디오에 없음.) 편집기 처리 중이어도 공개 전환은 가능.
   - 실패하면 음악 없이 진행하고 결과.txt 에 '음악: 실패 이유'. 고른 곡 이름은 결과.txt 에 기록.
5) 공개 상태 **'{{PRIVACY}}'** 로 저장/게시. ('비공개'면 테스트용 — 공개로 바꾸지 않는다.)
6) 게시 뒤 영상 링크를 결과.txt 에 `업로드({{PRIVACY}}): https://youtube.com/shorts/<ID>` 로 기록. pin_comment 가 있으면 영상 댓글로 달고 고정.
7) 확인창(confirm/alert) 띄우는 동작 금지. 결제·인증 요구 화면이 나오면 중단하고 결과.txt 에 이유 기록. 연 탭은 끝나면 닫는다.
