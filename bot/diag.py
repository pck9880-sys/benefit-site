"""API 키 형식과 연결 상태 진단 (키 값은 기록하지 않음)."""
import json
import os

import requests

from . import config

k = os.environ.get("ANTHROPIC_API_KEY", "")
info = {
    "length": len(k),
    "length_stripped": len(k.strip()),
    "starts_with_sk_ant": k.strip().startswith("sk-ant-"),
    "ascii_only": all(ord(c) < 128 for c in k),
    "has_inner_whitespace": any(c.isspace() for c in k.strip()),
    "has_newline": "\n" in k or "\r" in k,
}
try:
    r = requests.get("https://api.anthropic.com/v1/models", timeout=20,
                     headers={"x-api-key": k.strip(), "anthropic-version": "2023-06-01"})
    info["http_status"] = r.status_code
    info["body"] = r.text[:200] if r.status_code != 200 else "ok"
except Exception as e:
    info["error"] = f"{type(e).__name__}: {str(e)[:200]}"
(config.DATA_DIR / "diag.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), "utf-8")
print(info)
