[숏츠 영상 클립 – 크롬 Claude 가 ChatGPT 안의 힉스필드(Higgsfield) 앱으로 생성 / 사용자에게 묻지 않음 / 결제·업그레이드 금지 / 보고 5줄 이내]

0) 크롬이 여러 대 연결돼 있으면 macOS(iMac) 크롬을 쓴다.
작업 폴더: {{DIR}}  (로컬 서버 http://127.0.0.1:{{PORT}}/ = 이 폴더, 받기 페이지 _recv.html)
만들 클립 목록: {{DIR}}/higgsfield.json — [{"file": "hf1.mp4", "prompt": "<영어 프롬프트>", "seconds": 5}, ...]

1) chatgpt.com 을 연다. 로그인 안 돼 있으면 {{DIR}}/hf_result.txt 에 '실패: ChatGPT 로그인 필요' 쓰고 끝.
2) ChatGPT 의 앱/GPT 에서 **Higgsfield** 를 찾는다 (채팅 입력창에 '@Higgsfield', 또는 '앱'·'GPT 탐색'에서 검색).
   없거나 연결(로그인)이 필요하면 진행하지 말고 hf_result.txt 에 '실패: 힉스필드 앱 없음/연결 필요 — <화면에 보인 안내>' 쓰고 끝.
3) 클립마다: 힉스필드에 프롬프트로 **세로 또는 정사각, 약 5초** 영상을 요청. 완성될 때까지 기다린다(최대 5분).
   - 다운로드 버튼은 누르지 않는다(저장 창). 영상 <video> 의 src(또는 결과 링크)를 찾아
     `const w = window.open('http://127.0.0.1:{{PORT}}/_recv.html')` (막히면 임시 버튼 클릭) → ready 후
     `const b = await (await fetch(SRC)).blob(); w.postMessage({file:'<file>', blob:b}, '*')` → ack 201.
   - Bash 로 `ls -l {{DIR}}/<file>` 확인(200KB 이상).
   - 실존 인물·로고·글자는 요청하지 않는다. 거절되면 문구를 바꿔 1번만 다시.
4) 크레딧 부족·결제 안내가 나오면 멈추고 hf_result.txt 에 '실패: 크레딧' 기록.
5) 확인창 금지. 끝나면 연 탭을 닫고 hf_result.txt 에 성공한 파일 목록과 쓴 크레딧(보이면).
