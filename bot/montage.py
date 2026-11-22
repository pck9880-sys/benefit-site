"""원본 소리 몰입형 모음 영상: 여러 컷을 크로스페이드(디졸브)로 이어 한 파일로 — 장면 전환이 뚝뚝 끊기지 않게 (2026-11-22 사용자 요청).

  from bot import montage
  offs = montage.build(src_url_or_file, [(시작초, 보일 길이), ...], out_mp4, fade=0.6)
  → out_mp4 (1080 정사각, 30fps, 원본 소리 포함, 소리도 acrossfade) + 각 장면이 시작되는 위치(초) 목록
plan.json 의 media 를 [{"video": "montage.mp4", "start": offs[i]}] 로, durations 를 장면 길이로 쓰면
장면 경계가 디졸브 한가운데에 와서 자연스럽게 넘어간다.
"""
import subprocess
import tempfile
from pathlib import Path

VF = "crop=ih:ih,scale=1080:1080,fps=30,setsar=1,format=yuv420p,settb=AVTB"


def build(src, cuts, out, fade=0.6):
    tmp = Path(tempfile.mkdtemp(prefix="mont-"))
    parts = []
    for i, c in enumerate(cuts):  # 앞뒤 디졸브 여유만큼 길게 자름. c = (시작, 길이) 또는 (원본, 시작, 길이)
        csrc, s, d = c if len(c) == 3 else (src, *c)
        L = d + fade
        f = tmp / f"p{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0, s - fade / 2):.3f}", "-t", f"{L:.3f}", "-i", str(csrc),
                        "-vf", VF, "-af", "aresample=44100,aformat=channel_layouts=stereo", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(f)], check=True)
        parts.append((f, L))
    inputs, fc = [], []
    for f, _ in parts:
        inputs += ["-i", str(f)]
    v, a, acc = "[0:v]", "[0:a]", parts[0][1]
    for i in range(1, len(parts)):
        off = acc - fade
        fc.append(f"{v}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[v{i}]")
        fc.append(f"{a}[{i}:a]acrossfade=d={fade}[a{i}]")
        v, a = f"[v{i}]", f"[a{i}]"
        acc = off + parts[i][1]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs]
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", v, "-map", a]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(out)]
    subprocess.run(cmd, check=True)
    # 장면 i 의 시작 = 앞 디졸브의 한가운데 (첫 장면은 0)
    offs, t = [], 0.0
    for i, c in enumerate(cuts):
        d = c[-1]
        offs.append(round(0.0 if i == 0 else t + fade / 2, 3))
        t += d
    return offs


def durations(cuts, fade=0.6):
    """장면별 보일 길이 (첫 장면은 첫 디졸브 한가운데까지라 fade/2 더 김) — offs 와 짝지어 쓰면 빈틈·겹침 없음."""
    return [round(c[-1] + (fade / 2 if i == 0 else 0), 3) for i, c in enumerate(cuts)]
