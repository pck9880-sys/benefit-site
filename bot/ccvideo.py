"""크리에이티브 커먼즈 영상 찾기·받기·장면 추출 (숏츠 재가공용).

출처: 위키미디어 공용(유튜브 CC BY 영상 이관본 포함, 라이선스 검수됨) → Pexels 영상(키 있을 때).
허용 라이선스: CC BY, CC0, 퍼블릭 도메인, Pexels 라이선스.
제외: NC(비상업) · ND(변경 금지) · SA(동일조건 — 우리 영상에도 같은 라이선스 강제) · 라이선스 불명.
"""
import json
import re
import subprocess

import requests

from . import config

UA = {"User-Agent": "jiwon-shorts-bot/1.0 (https://github.com/pck9880-sys/benefit-site; automated video tool) python-requests"}


def license_ok(lic):
    l = (lic or "").lower()
    if re.search(r"kogl[ -]?type[ -]?1\b|공공누리\s*제?1\s*유형", l):  # 공공누리 1유형: 출처표시만 하면 상업·변경 가능
        return True
    if not l or "kogl" in l or any(x in l for x in ("nc", "nd", "sa", "fair use", "non-free")):
        return False
    return bool(re.search(r"cc[ -]?by|cc0|public domain|pd", l))


def wikimedia(query, n=12):
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{query} filetype:video", "gsrlimit": n,
        "prop": "imageinfo|videoinfo", "iiprop": "url|extmetadata|size|mediatype",
        "viprop": "derivatives|size", })
    r.raise_for_status()
    out = []
    for pg in sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        vi = (pg.get("videoinfo") or [{}])[0]
        m = ii.get("extmetadata") or {}
        lic = (m.get("LicenseShortName") or {}).get("value", "")
        if not license_ok(lic):
            print(f"[ccvideo] 제외(라이선스 {lic or '없음'}): {pg['title'][:60]}")
            continue
        dur = float(vi.get("duration") or ii.get("duration") or 0)
        if dur and dur < 4:
            continue
        derivs = vi.get("derivatives") or []
        # 720p 이하 중 가장 큰 것 (용량·속도)
        best = None
        for d_ in derivs:
            h = int(d_.get("height") or 0)
            if 360 <= h <= 720 and (not best or h > int(best.get("height") or 0)):
                best = d_
        url = (best or {}).get("src") or ii.get("url")
        artist = re.sub(r"<[^>]+>", "", (m.get("Artist") or {}).get("value", "unknown")).strip()[:60]
        out.append({"source": "wikimedia", "title": pg["title"].replace("File:", ""), "url": url, "duration": dur,
                    "license": lic, "page": ii.get("descriptionurl", ""),
                    "credit": f"Video: {artist} ({lic}) {ii.get('descriptionurl', '')}",
                    "desc": re.sub(r"<[^>]+>", "", (m.get("ImageDescription") or {}).get("value", ""))[:200]})
    return out


def pexels(query, n=8):
    if not config.PEXELS_API_KEY:
        return []
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": config.PEXELS_API_KEY},
                     params={"query": query, "per_page": n, "size": "medium"}, timeout=30)
    r.raise_for_status()
    out = []
    for v in r.json().get("videos", []):
        files = sorted([f for f in v.get("video_files", []) if (f.get("height") or 0) <= 1280],
                       key=lambda f: -(f.get("height") or 0))
        if not files:
            continue
        out.append({"source": "pexels", "title": v.get("url", "").rstrip("/").split("/")[-1], "url": files[0]["link"],
                    "duration": float(v.get("duration") or 0), "license": "Pexels License",
                    "page": v.get("url", ""), "credit": f"Video: {v['user']['name']} / Pexels {v.get('url', '')}",
                    "desc": ""})
    return out


def search(query):
    out = []
    for fn in (wikimedia, pexels):
        try:
            out += fn(query)
        except Exception as e:
            print(f"[ccvideo] {fn.__name__} 실패: {type(e).__name__} {str(e)[:100]}")
    return out


def download(c, out):
    with requests.get(c["url"], headers=UA, timeout=120, stream=True) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
                if f.tell() > 300 * 1024 * 1024:
                    raise RuntimeError("영상이 너무 큼")
    return out


def scenes(video, threshold=0.3):
    """장면이 바뀌는 시각 목록 (초)."""
    r = subprocess.run(["ffmpeg", "-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an",
                        "-f", "null", "-"], capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def pick_segments(video, n, seg_len):
    """영상에서 n 개 구간 시작점 고르기: 장면 전환 직후를 우선, 없으면 고르게 나눔 (앞뒤 5% 제외)."""
    from .shorts import duration
    total = duration(video)
    lo, hi = total * 0.05, max(total * 0.95 - seg_len, total * 0.05)
    cuts = [t + 0.2 for t in scenes(video) if lo <= t <= hi]
    if len(cuts) >= n:
        step = len(cuts) / n
        return [cuts[int(i * step)] for i in range(n)]
    if hi <= lo:
        return [0.0] * n
    return [lo + (hi - lo) * i / max(n - 1, 1) for i in range(n)]


def contact_sheet(video, out, n=6):
    """후보 영상 미리보기 (가로로 n 장)."""
    from .shorts import duration
    total = duration(video)
    frames = []
    for i in range(n):
        f = out.parent / f"{out.stem}_{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{total * (i + 0.5) / n:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=240:-2", str(f)])
        if f.exists():
            frames.append(f)
    if frames:
        args = []
        for f in frames:
            args += ["-i", str(f)]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex",
                        f"{''.join(f'[{i}]scale=240:135,setsar=1[v{i}];' for i in range(len(frames)))}"
                        f"{''.join(f'[v{i}]' for i in range(len(frames)))}hstack={len(frames)}", str(out)])
    return out


def find_cli(queries, out_dir, per=3):
    """검색어별 후보를 받아 미리보기 시트와 목록(json)을 만든다 (GitHub Actions 에서 실행 → 아티팩트)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    found = []
    for q in queries:
        for c in search(q)[:per]:
            idx = len(found)
            f = out_dir / f"cand{idx}.{'webm' if c['url'].endswith('webm') else 'mp4'}"
            try:
                download(c, f)
                contact_sheet(f, out_dir / f"cand{idx}_sheet.jpg")
                c.update(query=q, file=f.name)
                found.append(c)
                print(f"[ccvideo] {idx}: {c['title'][:60]} | {c['license']} | {c['duration']:.0f}s")
            except Exception as e:
                print(f"[ccvideo] 받기 실패 {c['title'][:40]}: {e}")
    (out_dir / "candidates.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), "utf-8")
    return found
