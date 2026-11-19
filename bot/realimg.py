"""실제 사진(기사·커뮤니티·제품 사진)을 숏츠 장면으로 쓰기 — 사람이 나오면 모자이크.

사용: python -m bot.realimg <URL 또는 파일> <저장할 경로.jpg> [auto|all|none]
  auto(기본): 얼굴은 모자이크. 얼굴이 안 보이는 사람(옆·뒷모습)은 머리 부분 모자이크.
              얼굴/사람이 많으면(군중, 4명 이상) 사진 전체를 흐리게.
  all : 사진 전체 흐리게 (집회·군중 사진 등)
  none: 그대로 (제품·음식·풍경처럼 사람이 없는 사진)
사람 인식은 macOS Vision (scripts/mac/faces). 처음 쓸 때 자동으로 컴파일한다.
plan.json media 에서는 일반 이미지처럼 {"image": "r1.jpg"}. 설명란에 "※ 일부 실제 사진은 모자이크 처리" 표기.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
from PIL import Image, ImageFilter

from . import config

FACES = config.ROOT / "scripts" / "mac" / "faces"
CROWD = 4


def _detector():
    exe = FACES / "faces"
    if not exe.exists():
        subprocess.run(["swiftc", "-O", str(FACES / "main.swift"), "-o", str(exe)], check=True)
    return exe


def detect(path):
    try:
        out = subprocess.run([str(_detector()), str(path)], capture_output=True, text=True, timeout=60).stdout
        return json.loads(out)
    except Exception as ex:
        print("[realimg] 사람 인식 실패:", ex)
        return None


def _load(src):
    if str(src).startswith("http"):
        r = requests.get(src, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        f = Path(tempfile.mkstemp(suffix=".img")[1])
        f.write_bytes(r.content)
        return f
    return Path(src).expanduser()


def _pixelate(img, box, block=None):
    W, H = img.size
    x, y, w, h = box
    pad_w, pad_h = w * 0.25, h * 0.25  # 머리카락·귀까지 넉넉히
    l, t = max(0, int((x - pad_w) * W)), max(0, int((y - pad_h) * H))
    r, b = min(W, int((x + w + pad_w) * W)), min(H, int((y + h + pad_h) * H))
    if r - l < 2 or b - t < 2:
        return
    region = img.crop((l, t, r, b))
    n = block or max(6, (r - l) // 10)  # 모자이크 칸 크기
    small = region.resize((max(1, (r - l) // n), max(1, (b - t) // n)), Image.BILINEAR)
    img.paste(small.resize(region.size, Image.NEAREST), (l, t))


def _inside(face, person):
    fx, fy = face[0] + face[2] / 2, face[1] + face[3] / 2
    return person[0] <= fx <= person[0] + person[2] and person[1] <= fy <= person[1] + person[3]


def process(src, out, mode="auto"):
    f = _load(src)
    img = Image.open(f).convert("RGB")
    note = "그대로"
    if mode == "all":
        img = img.filter(ImageFilter.GaussianBlur(radius=max(img.size) / 45))
        note = "전체 흐림"
    elif mode == "auto":
        tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
        img.save(tmp, quality=92)
        d = detect(tmp) or {"faces": [], "people": []}
        faces, people = d.get("faces", []), d.get("people", [])
        if max(len(faces), len(people)) >= CROWD:
            img = img.filter(ImageFilter.GaussianBlur(radius=max(img.size) / 45))
            note = f"군중({max(len(faces), len(people))}명) → 전체 흐림"
        else:
            for fb in faces:
                _pixelate(img, fb)
            heads = 0
            for pb in people:  # 얼굴이 안 잡힌 사람(옆·뒷모습) → 머리 부분
                if not any(_inside(fb, pb) for fb in faces):
                    _pixelate(img, [pb[0] + pb[2] * 0.2, pb[1], pb[2] * 0.6, pb[3] * 0.22])
                    heads += 1
            note = (f"얼굴 {len(faces)}개, 머리 {heads}곳 모자이크" if faces or heads else "사람 없음 → 그대로")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=90)
    print(f"[realimg] {out} ({note})")
    return note


if __name__ == "__main__":
    process(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "auto")
