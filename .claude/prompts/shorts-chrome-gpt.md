[숏츠 이미지 – 크롬 Claude 가 ChatGPT(chatgpt.com)로 생성 / 사용자에게 묻지 않음 / 결제·업그레이드 금지]

0) 크롬이 여러 대 연결돼 있으면 **macOS(iMac) 크롬**을 쓴다 (Windows 등 다른 기기 크롬 금지). 선택이 필요하면 macOS 쪽을 고른다.
이미지 목록: {{DIR}}/plan.json 의 "gpt_images" (각 항목 file, prompt)
저장: 로컬 서버 http://127.0.0.1:{{PORT}}/ = {{DIR}} 폴더

1) 크롬에서 chatgpt.com 새 채팅을 연다. 로그인 안 돼 있으면 {{DIR}}/gpt_result.txt 에 '실패: ChatGPT 로그인 필요' 쓰고 끝.
2) 항목마다(한 채팅에서 이어서 해도 됨):
   "이미지 생성: 정사각형 1:1. <prompt>" 를 보내고 이미지가 완성될 때까지 기다린다(최대 3분).
   - **다운로드 버튼을 누르지 말 것 (저장 창이 떠서 멈춤).** 완성된 이미지의 <img> src 를 찾아 페이지 안에서:
     chatgpt.com 에서 127.0.0.1 로 바로 PUT 하면 보안 정책으로 막힌다 → 수신 페이지를 거친다:
     ① Bash 로 {{DIR}}/_recv.html 이 있는지 확인(스크립트가 미리 만들어 둠).
     ② chatgpt.com 페이지에서 `const w = window.open('http://127.0.0.1:{{PORT}}/_recv.html')` 로 팝업을 열고 ready 메시지를 기다린 뒤
        `const b = await (await fetch(SRC)).blob(); w.postMessage({file:'<file>', blob:b}, '*')` → ack status 201 이면 성공.
     팝업은 계속 재사용하고 끝나면 닫는다. 원본이 PNG 여도 그대로 보내면 스크립트가 JPG 로 바꾼다. Bash 로 `ls -l {{DIR}}/<file>` 확인(30KB 이상).
   - 생성을 거절하거나 실패하면 문구를 안전하게 바꿔 1번만 다시. 그래도 안 되면 건너뛰고 gpt_result.txt 에 '<file>: 실패 이유'.
   - 썸네일(thumb_src.jpg) 문구의 조건(성인·옷 다 입음·V넥 가슴골 살짝 허용·속옷/수영복/노출/선정적 자세 금지)은 빼거나 바꾸지 않는다.
   - 실존 인물 얼굴, 글자·로고가 들어간 이미지는 요청하지 않는다.
3) 한도 초과·업그레이드 안내가 나오면 멈추고 gpt_result.txt 에 '실패: 한도'.
4) 확인창(confirm/alert) 띄우는 동작 금지. 끝나면 연 탭을 닫는다. gpt_result.txt 에 성공한 파일 목록.
