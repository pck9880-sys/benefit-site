"""완성 영상을 사용자 휴대폰에서 바로 올릴 수 있게 iCloud Drive 에 정리 (2026-11-20: 업로드는 사용자가 앱에서 직접 — 저장한 사운드 넣기 위해).
iCloud Drive/쇼츠업로드/<번호>_<날짜>_<제목>/ : 영상.mp4, 썸네일.jpg, 업로드정보.txt (제목·설명·태그·고정 댓글·넣을 곡)
사용: python3 shorts_deliver.py <작업폴더 ~/쇼츠작업/...> <slug>"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

work, slug = Path(sys.argv[1]), sys.argv[2]
info = json.loads((work / "업로드정보.json").read_text("utf-8"))
icloud = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
root = (icloud if icloud.exists() else Path.home() / "Desktop") / "쇼츠업로드"
root.mkdir(parents=True, exist_ok=True)
n = len([x for x in root.iterdir() if x.is_dir()]) + 1
title = re.sub(r'[\\/:*?"<>|#]', "", (info.get("title") or slug)).strip()[:30]
out = root / f"{n:03d}_{datetime.now():%m%d_%H%M}_{title}"
out.mkdir(exist_ok=True)
shutil.copy(work / "더빙용" / "영상.mp4", out / "영상.mp4")
if (work / "thumb.jpg").exists():
    shutil.copy(work / "thumb.jpg", out / "썸네일.jpg")
tags = info.get("tags") or []
txt = f"""[제목]
{info.get('title', '')}

[넣을 곡 — 앱에서 '사운드 추가 → 저장됨']
{info.get('song', '')}   (음악 볼륨은 목소리보다 작게)

[설명]
{info.get('description', '')}

[태그]
{', '.join(tags)}

[고정 댓글]
{info.get('pin_comment', '')}

[설정] 아동용 아님 · 'AI로 변경·합성된 콘텐츠' 예
"""
(out / "업로드정보.txt").write_text(txt, "utf-8")
(out / "제목.txt").write_text((info.get("title") or "").strip(), "utf-8")  # 제목만 (길게 눌러 바로 복사)
print(f"[deliver] {out}")
