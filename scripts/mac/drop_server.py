"""크롬 ↔ 로컬 폴더 파일 주고받기용 작은 서버 (127.0.0.1 전용).

크롬은 다운로드할 때 저장 창을 띄우고(원격이라 누를 수 없음), 업로드 때 파일 선택 창을 띄운다.
그래서 브라우저 페이지 안에서 fetch 로:
  - 받기: 사이트에서 받은 파일을 PUT http://127.0.0.1:<port>/<경로>  → 작업 폴더에 저장
  - 올리기: GET http://127.0.0.1:<port>/<경로> → Blob → File → <input type=file> 에 DataTransfer 로 넣기
사용: python3 drop_server.py <작업폴더> <포트>
"""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(sys.argv[1]).resolve()


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_PUT(self):
        target = (ROOT / unquote(self.path.split("?")[0]).lstrip("/")).resolve()
        if ROOT not in target.parents:
            self.send_response(403)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.rfile.read(n))
        self.send_response(201)
        self.end_headers()
        self.wfile.write(f"saved {target.name} {n} bytes".encode())


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])), H).serve_forever()
