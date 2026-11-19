[숏츠 이미지 – 크롬 Claude 가 ChatGPT(chatgpt.com)로 생성 / 사용자에게 묻지 않음 / 결제·업그레이드 금지]

이미지 목록: {{DIR}}/plan.json 의 "gpt_images" (각 항목 file, prompt)
저장: 로컬 서버 http://127.0.0.1:{{PORT}}/ = {{DIR}} 폴더

1) 크롬에서 chatgpt.com 새 채팅을 연다. 로그인 안 돼 있으면 {{DIR}}/gpt_result.txt 에 '실패: ChatGPT 로그인 필요' 쓰고 끝.
2) 항목마다(한 채팅에서 이어서 해도 됨):
   "이미지 생성: 정사각형 1:1. <prompt>" 를 보내고 이미지가 완성될 때까지 기다린다(최대 3분).
   - **다운로드 버튼을 누르지 말 것 (저장 창이 떠서 멈춤).** 완성된 이미지의 <img> src 를 찾아 페이지 안에서:
     `const b = await (await fetch(SRC)).blob(); await fetch('http://127.0.0.1:{{PORT}}/<file>', {method:'PUT', body:b});`
     응답 201 이면 성공. Bash 로 `ls -l {{DIR}}/<file>` 확인(30KB 이상).
   - 생성을 거절하거나 실패하면 문구를 안전하게 바꿔 1번만 다시. 그래도 안 되면 건너뛰고 gpt_result.txt 에 '<file>: 실패 이유'.
   - 썸네일(thumb_src.jpg) 문구의 안전 조건(성인·옷 다 입음·노출/선정적 자세 금지)은 빼거나 바꾸지 않는다.
   - 실존 인물 얼굴, 글자·로고가 들어간 이미지는 요청하지 않는다.
3) 한도 초과·업그레이드 안내가 나오면 멈추고 gpt_result.txt 에 '실패: 한도'.
4) 확인창(confirm/alert) 띄우는 동작 금지. 끝나면 연 탭을 닫는다. gpt_result.txt 에 성공한 파일 목록.
