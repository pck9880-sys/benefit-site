[숏츠 업로드 준비 – 크롬 Claude 자동 입력 / **게시 버튼 절대 누르지 않음**]

작업 폴더: {{DIR}}  (로컬 서버 http://127.0.0.1:{{PORT}}/)
업로드 정보: {{DIR}}/업로드정보.json (title, description, tags, pin_comment, thumb)
올릴 영상: {{VIDEOS}}  (서버 기준 경로, 예: 원본/영상.mp4, 더빙용/영상.mp4)

영상마다:
1) studio.youtube.com 을 열고 '만들기 → 동영상 업로드'. 로그인 안 돼 있으면 '실패: 유튜브 로그인 필요' 를 {{DIR}}/결과.txt 에 쓰고 끝.
2) **'파일 선택' 버튼을 누르지 말 것 (파일 창이 떠서 멈춤).** 업로드 창이 열린 상태에서 페이지 안에서:
   ```js
   const b = await (await fetch('http://127.0.0.1:{{PORT}}/<영상 경로>')).blob();
   const f = new File([b], '<제목>.mp4', {type:'video/mp4'});
   const dt = new DataTransfer(); dt.items.add(f);
   const inp = document.querySelector('input[type=file]'); inp.files = dt.files;
   inp.dispatchEvent(new Event('change', {bubbles:true}));
   ```
3) 제목·설명 입력 (원본·더빙용 모두 같은 제목. 어느 초안이 어느 영상인지는 결과.txt 에만 적는다).
   '아동용 아님' 선택, 태그(자세히 보기)에 tags 입력.
   썸네일 칸이 있으면 같은 방식(fetch → DataTransfer)으로 thumb.jpg 를 넣는다. 숏츠라 썸네일 칸이 없으면 건너뛰고 결과.txt 에 '썸네일: 앱에서 선택 필요' 기록.
4) '다음'으로 '공개 상태' 화면까지만 간다. **비공개 상태 그대로 두고 '게시/저장/예약' 을 누르지 않는다.** 창을 X 로 닫으면 초안으로 남는다.
5) 스튜디오 콘텐츠 목록에서 초안 링크(영상 ID)를 확인해 결과.txt 에 `원본: https://studio.youtube.com/video/<ID>/edit` 형식으로 기록.
6) 확인창(confirm/alert) 띄우는 동작 금지. 연 탭은 끝나면 닫는다.
