"""OpenAI GPT 이미지 API 로 장면 이미지 생성 (키 OPENAI_API_KEY 가 있을 때). 여러 장을 동시에 요청한다."""
import base64
from concurrent.futures import ThreadPoolExecutor

import requests

from . import config

# 1024x1024 1장 대략 가격 (USD) — 비용 기록용
PRICE = {"low": 0.009, "medium": 0.034, "high": 0.133}


def enabled():
    return bool(config.OPENAI_API_KEY) and not config.MOCK


def _one(prompt, out):
    r = requests.post("https://api.openai.com/v1/images/generations", timeout=180,
                      headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                      json={"model": config.OPENAI_IMAGE_MODEL, "prompt": prompt, "size": "1024x1024",
                            "quality": config.OPENAI_IMAGE_QUALITY, "n": 1})
    if r.status_code != 200:
        raise RuntimeError(f"GPT 이미지 HTTP {r.status_code}: {r.text[:200]}")
    d = r.json()["data"][0]
    if d.get("b64_json"):
        out.write_bytes(base64.b64decode(d["b64_json"]))
    else:
        out.write_bytes(requests.get(d["url"], timeout=60).content)
    return out


def make_images(prompts, out_dir):
    """(파일 경로 목록 — 실패한 자리는 None, 예상 비용 USD)"""
    def job(i_p):
        i, p = i_p
        try:
            return _one(p, out_dir / f"gpt{i}.png")
        except Exception as e:
            print("[gpt-image]", str(e)[:200])
            return None
    with ThreadPoolExecutor(max_workers=5) as ex:
        files = list(ex.map(job, enumerate(prompts)))
    cost = sum(1 for f in files if f) * PRICE.get(config.OPENAI_IMAGE_QUALITY, 0.04)
    return files, cost
