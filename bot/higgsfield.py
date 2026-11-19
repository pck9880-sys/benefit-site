"""힉스필드 API로 짧은 AI 영상 클립 생성 (텍스트 → 영상). 키가 없으면 None."""
import time
import uuid

import requests

from . import config

BASE = "https://api.higgsfield.ai"
DONE = {"completed", "failed", "nsfw", "canceled"}


def enabled():
    return bool(config.HIGGSFIELD_KEY) and not config.MOCK


def _h():
    return {"Authorization": f"Key {config.HIGGSFIELD_KEY}", "Content-Type": "application/json"}


def estimate(body, model=None):
    model = model or config.HIGGSFIELD_MODEL
    try:
        r = requests.post(f"{BASE}/estimate/{model}", headers=_h(), json=body, timeout=30)
        return float(r.json().get("usd", 0)) if r.ok else 0.0
    except Exception:
        return 0.0


def submit(prompt, seconds=5):
    body = {"prompt": prompt, "duration": seconds, "aspect_ratio": "1:1", "resolution": "720p"}
    r = requests.post(f"{BASE}/{config.HIGGSFIELD_MODEL}", headers={**_h(), "Idempotency-Key": str(uuid.uuid4())},
                      json=body, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"힉스필드 요청 실패 HTTP {r.status_code}: {r.text[:200]}")
    return r.json()["status_url"], estimate(body)


def wait(status_url, timeout=600):
    delay, start = 2.0, time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(status_url, headers=_h(), timeout=30)
            if r.status_code in (401, 404):
                raise RuntimeError(f"힉스필드 상태 확인 실패 HTTP {r.status_code}")
            s = r.json()
            if s.get("status") in DONE:
                return s
        except requests.RequestException:
            pass
        time.sleep(delay)
        delay = min(delay * 1.5, 10)
    raise TimeoutError("힉스필드 생성 시간 초과")


def make_clips(prompts, out_dir, seconds=5):
    """여러 프롬프트를 한꺼번에 요청하고 기다림. (파일 경로 목록 — 실패한 자리는 None, 예상 비용 USD)"""
    jobs, cost = [], 0.0
    for p in prompts:
        try:
            url, c = submit(p, seconds)
            jobs.append(url)
            cost += c
        except Exception as e:
            print("[higgsfield]", e)
            jobs.append(None)
    files = []
    for i, url in enumerate(jobs):
        if not url:
            files.append(None)
            continue
        try:
            s = wait(url)
            if s.get("status") != "completed":
                print("[higgsfield] 생성 안 됨:", s.get("status"), s.get("error"))
                files.append(None)
                continue
            video = requests.get(s["video"]["url"], timeout=120)
            f = out_dir / f"clip{i}.mp4"
            f.write_bytes(video.content)
            files.append(f)
        except Exception as e:
            print("[higgsfield]", type(e).__name__, e)
            files.append(None)
    return files, cost
