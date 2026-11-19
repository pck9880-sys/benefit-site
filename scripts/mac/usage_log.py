"""claude -p --output-format json 결과를 받아 ~/쇼츠작업/usage.tsv 에 한 줄 기록하고, 결과 글은 그대로 출력.
사용: ... | python3 usage_log.py <slug> <단계> <걸린초>"""
import json
import sys
from datetime import datetime
from pathlib import Path

slug, step, secs = sys.argv[1], sys.argv[2], sys.argv[3]
raw = sys.stdin.read()
try:
    d = json.loads(raw) if raw.strip() else {}
except Exception:
    d = {"result": raw}
u = d.get("usage") or {}
f = Path.home() / "쇼츠작업" / "usage.tsv"
new = not f.exists()
with f.open("a", encoding="utf-8") as w:
    if new:
        w.write("시각\tslug\t단계\t초\t턴\t입력토큰\t캐시읽기\t출력토큰\t비용USD\n")
    w.write(f"{datetime.now():%m-%d %H:%M}\t{slug}\t{step}\t{secs}\t{d.get('num_turns', '')}\t{u.get('input_tokens', '')}\t"
            f"{u.get('cache_read_input_tokens', '')}\t{u.get('output_tokens', '')}\t{d.get('total_cost_usd', '')}\n")
if d.get("result"):
    print(d["result"])
