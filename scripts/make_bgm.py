"""저작권 걱정 없는 배경음악·효과음 직접 합성.
실행: python scripts/make_bgm.py  →  assets/bgm/*.mp3, assets/sfx/*.wav
"""
import subprocess
from pathlib import Path

import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parent.parent


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def rhodes(f, dur, vol):
    t = np.arange(int(SR * dur)) / SR
    w = np.sin(2 * np.pi * f * t + 0.8 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3))  # FM 전자피아노
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return w * trem * np.exp(-t * 1.6) * np.minimum(1, t * 200) * vol


def bass(f, dur, vol):
    t = np.arange(int(SR * dur)) / SR
    w = np.tanh(2.2 * np.sin(2 * np.pi * f * t))
    return w * np.exp(-t * 6) * np.minimum(1, t * 300) * vol


def kick():
    t = np.arange(int(SR * .35)) / SR
    return np.sin(2 * np.pi * (45 + 80 * np.exp(-t * 35)) * t) * np.exp(-t * 10) * .9


def snare(vol=.35):
    t = np.arange(int(SR * .2)) / SR
    return (np.random.randn(len(t)) * .7 + np.sin(2 * np.pi * 190 * t) * .5) * np.exp(-t * 22) * vol


def hat(vol=.08):
    t = np.arange(int(SR * .04)) / SR
    n = np.random.randn(len(t))
    n = n - np.convolve(n, np.ones(4) / 4, "same")  # 고음만
    return n * np.exp(-t * 90) * vol


def save_mp3(sig, out):
    sig = sig / np.max(np.abs(sig)) * .8
    pcm = (sig * 32767).astype(np.int16)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-ac", "2", "-b:a", "128k", str(out)], input=pcm.tobytes(), check=True)


def funk(out, bpm, prog, seed, total=48):
    """펑키하지만 잔잔한 루프: 전자피아노 9th 코드 + 싱코페이션 베이스 + 고스트노트 드럼."""
    rng = np.random.default_rng(seed)
    np.random.seed(seed)
    s16 = 60 / bpm / 4
    mix = np.zeros(int(SR * (total + 2)))

    def add(sig, at):
        i = int(at * SR)
        mix[i:i + len(sig)] += sig[:max(0, len(mix) - i)]
    bass_pat = [0, None, None, 0, None, None, 12, None, None, 0, None, 7, None, 10, 12, None]
    comp = [2, 6, 10, 14] if seed % 2 else [3, 7, 11, 14]
    t, bar = 0.0, 0
    while t < total:
        root, chord = prog[bar % len(prog)]
        for st in range(16):
            at = t + st * s16 + (s16 * .12 if st % 2 else 0)  # 스윙
            if bass_pat[st] is not None:
                add(bass(hz(root + 24 + bass_pat[st]), s16 * 1.8, .32), at)
            if st in comp:
                for n in chord:
                    add(rhodes(hz(root + 48 + n), s16 * 3, .045), at)
            if st in (0, 10):
                add(kick(), at)
            if st in (4, 12):
                add(snare(), at)
            elif rng.random() < .12:
                add(snare(.06), at)  # 고스트 노트
            add(hat(.07 if st % 2 == 0 else .035), at)
        t += s16 * 16
        bar += 1
    mix = mix[:int(SR * total)]
    f = int(SR * 1.2)
    mix[:f] *= np.linspace(0, 1, f)
    mix[-f:] *= np.linspace(1, 0, f)
    save_mp3(mix, out)


def sfx():
    d = ROOT / "assets" / "sfx"
    d.mkdir(parents=True, exist_ok=True)

    def wav(sig, name):
        sig = sig / np.max(np.abs(sig)) * .7
        pcm = (sig * 32767).astype(np.int16)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-ac", "2", str(d / name)], input=pcm.tobytes(), check=True)
    t = np.arange(int(SR * .09)) / SR
    wav(np.sin(2 * np.pi * (900 - 3000 * t) * t) * np.exp(-t * 45), "pop.wav")  # 자막 뜰 때 '뽁'
    t = np.arange(int(SR * .28)) / SR
    n = np.random.randn(len(t))
    sweep = np.convolve(n, np.ones(6) / 6, "same") * np.sin(np.pi * t / t[-1]) ** 2
    wav(sweep, "whoosh.wav")  # 장면 바뀔 때 '휙'
    t = np.arange(int(SR * .5)) / SR
    wav((np.sin(2 * np.pi * 1318 * t) + .5 * np.sin(2 * np.pi * 1976 * t)) * np.exp(-t * 7), "ding.wav")  # 반전 '띵'


if __name__ == "__main__":
    out = ROOT / "assets" / "bgm"
    for old in out.glob("*.mp3"):
        old.unlink()
    m9, M9, d9 = [0, 3, 7, 10, 14], [0, 4, 7, 11, 14], [0, 4, 7, 10, 14]
    funk(out / "funk1_chill.mp3", 96, [(50, m9), (55, d9)], 1)              # Dm9 - G9
    funk(out / "funk2_groove.mp3", 100, [(53, M9), (52, m9), (50, m9), (55, d9)], 2)  # Fmaj9-Em9-Dm9-G9
    funk(out / "funk3_night.mp3", 92, [(57, m9), (50, m9)], 3)             # Am9 - Dm9
    sfx()
