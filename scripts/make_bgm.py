"""저작권 걱정 없는 배경음악: 코드 진행 + 플럭 아르페지오 + 킥/하이햇을 직접 합성."""
import numpy as np, subprocess, sys
SR = 44100
def note(f, dur, kind="pluck", vol=0.3):
    t = np.arange(int(SR * dur)) / SR
    if kind == "pluck":
        w = np.sign(np.sin(2*np.pi*f*t)) * 0.3 + np.sin(2*np.pi*f*t)
        env = np.exp(-t * 7)
    elif kind == "pad":
        w = sum(np.sin(2*np.pi*f*k*t + k) / k for k in (1, 2, 3))
        env = np.minimum(1, t * 4) * np.minimum(1, (dur - t) * 4)
    elif kind == "bass":
        w = np.sin(2*np.pi*f*t) + 0.3*np.sin(4*np.pi*f*t)
        env = np.exp(-t * 3)
    return w * env * vol
def kick(dur=0.3):
    t = np.arange(int(SR*dur))/SR
    return np.sin(2*np.pi*(50 + 90*np.exp(-t*30))*t) * np.exp(-t*9) * 0.8
def hat(dur=0.05):
    t = np.arange(int(SR*dur))/SR
    return np.random.randn(len(t)) * np.exp(-t*80) * 0.12
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def make(out, bpm, prog, seed, total=64):
    np.random.seed(seed)
    beat = 60 / bpm; bar = beat * 4
    L = int(SR * total); mix = np.zeros(L + SR * 2)
    def add(sig, at):
        i = int(at * SR); mix[i:i+len(sig)] += sig[:len(mix)-i]
    pattern = [0, 2, 1, 2, 0, 2, 1, 3]
    t, b = 0.0, 0
    while t < total:
        root, chord = prog[b % len(prog)]
        for n in chord: add(note(hz(root + n + 60), bar, "pad", 0.07), t)
        add(note(hz(root + 36), beat*2, "bass", 0.25), t); add(note(hz(root + 36), beat*2, "bass", 0.2), t + beat*2)
        for s in range(8):
            n = chord[pattern[(s + b) % 8] % len(chord)]
            add(note(hz(root + n + 72), beat/2, "pluck", 0.09 if s % 2 else 0.12), t + s*beat/2)
        for s in range(4):
            if s in (0, 2): add(kick(), t + s*beat)
            add(hat(), t + s*beat + beat/2)
        t += bar; b += 1
    mix = mix[:L]
    fade = int(SR*1.5); mix[:fade] *= np.linspace(0,1,fade); mix[-fade:] *= np.linspace(1,0,fade)
    mix = mix / np.max(np.abs(mix)) * 0.8
    pcm = (mix * 32767).astype(np.int16)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","s16le","-ar",str(SR),"-ac","1","-i","-",
                    "-ac","2","-b:a","128k",out], input=pcm.tobytes(), check=True)
d = sys.argv[1]
M = [0, 3, 7, 10]; Mj = [0, 4, 7, 11]
make(f"{d}/bgm1_curious.mp3", 110, [(57, M), (53, Mj), (48, Mj), (55, [0,4,7,10])], 1)   # Am-F-C-G 호기심
make(f"{d}/bgm2_bright.mp3", 120, [(48, Mj), (55, Mj), (57, M), (53, Mj)], 2)            # C-G-Am-F 경쾌
make(f"{d}/bgm3_tension.mp3", 100, [(50, M), (46, Mj), (48, Mj), (45, [0,3,7,10])], 3)   # Dm-Bb-C-Am 반전·긴장
