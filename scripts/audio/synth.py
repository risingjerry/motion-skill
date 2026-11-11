#!/usr/bin/env python3
"""用代码合成一套免版权的示例声音：音效包 + 一段简单的配乐底。

  python3 scripts/audio/synth.py kit  输出目录            # pop / tick / click / whoosh / riser / impact / shimmer
  python3 scripts/audio/synth.py bed  输出.wav --duration 14 --hit 9.0 [--bpm 96]

配乐底会在 --hit 秒处放“最重的一拍”（低音下潜 + 镲 + 和弦回到主音），并写一个同名 .json 记下这个时间，
mix.py 用它把这一拍对到画面的关键落点上。全部是确定性的（固定随机种子），每次生成结果一样。
这些声音由本仓库代码生成，跟仓库一样按 MIT 许可使用。
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, save  # noqa: E402

RNG = np.random.default_rng(20261111)


def t_axis(sec):
    return np.arange(int(round(sec * SR))) / SR


def env_ad(n, attack, decay_tau):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / decay_tau)


def one_pole_sweep(x, cutoffs):
    """随时间变化的一阶低通（cutoffs 每个采样一个截止频率）。"""
    y = np.empty_like(x)
    acc = 0.0
    a = np.exp(-2 * np.pi * cutoffs / SR)
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def stereo(m, width=0.0):
    if width <= 0:
        return np.stack([m, m], axis=1)
    d = np.roll(m, int(0.0007 * SR)) * width
    return np.stack([m + d, m - d], axis=1) / (1 + width)


def norm(x, peak_db=-3.0):
    p = np.max(np.abs(x)) + 1e-12
    return x / p * 10 ** (peak_db / 20)


def pop():
    t = t_axis(0.18)
    f = 300 + 650 * np.exp(-t / 0.018)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_ad(len(t), 0.002, 0.045)
    s[: int(0.003 * SR)] += RNG.standard_normal(int(0.003 * SR)) * 0.3
    return stereo(norm(s, -3))


def tick():
    t = t_axis(0.05)
    s = np.sin(2 * np.pi * 2400 * t) * env_ad(len(t), 0.0005, 0.008)
    s += RNG.standard_normal(len(t)) * env_ad(len(t), 0.0003, 0.003) * 0.4
    return stereo(norm(s, -6))


def click():
    t = t_axis(0.03)
    s = RNG.standard_normal(len(t)) * env_ad(len(t), 0.0002, 0.0025)
    s += np.sin(2 * np.pi * 3200 * t) * env_ad(len(t), 0.0002, 0.004) * 0.6
    return stereo(norm(s, -6))


def whoosh(dur=0.9, peak_at=0.55):
    n = int(dur * SR)
    t = np.arange(n) / SR
    shape = np.exp(-((t - peak_at) ** 2) / (2 * (dur * 0.18) ** 2))
    cut = 300 + 5200 * shape
    noise = RNG.standard_normal(n)
    s = one_pole_sweep(noise, cut) - 0.6 * one_pole_sweep(noise, cut * 0.25)
    return stereo(norm(s * shape, -4), width=0.6)


def riser(dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    p = t / dur
    f = 180 * (2 ** (p * 2.5))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    noise = one_pole_sweep(RNG.standard_normal(n), 400 + 7000 * p ** 2) * 0.8
    s = (tone + noise) * p ** 2
    s[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return stereo(norm(s, -4), width=0.4)


def impact(dur=1.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 42 + 70 * np.exp(-t / 0.05)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.55)
    crack = one_pole_sweep(RNG.standard_normal(n), np.full(n, 3500.0)) * env_ad(n, 0.0005, 0.06) * 0.7
    tail = one_pole_sweep(RNG.standard_normal(n), np.full(n, 1200.0)) * env_ad(n, 0.01, 0.6) * 0.15
    return stereo(norm(boom + crack + tail, -2), width=0.3)


def shimmer(dur=1.6):
    t = t_axis(dur)
    s = np.zeros_like(t)
    for i, f in enumerate([1568.0, 2093.0, 2637.0, 3136.0]):
        s += np.sin(2 * np.pi * f * (1 + 0.0015 * i) * t + i) * np.exp(-t / (0.5 - 0.08 * i)) / (1 + i * 0.6)
    s *= np.clip(t / 0.004, 0, 1)
    return stereo(norm(s, -8), width=0.8)


KIT = {"pop": pop, "tick": tick, "click": click, "whoosh": whoosh, "riser": riser, "impact": impact, "shimmer": shimmer}


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def pad_chord(midis, n, attack=0.25):
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in midis:
        f = note(m)
        for k in range(1, 8):  # 柔和的锯齿：只叠前几次谐波
            if f * k > 4000:
                break
            s += np.sin(2 * np.pi * f * k * t + 0.3 * k) / k ** 1.4
    e = np.clip(t / attack, 0, 1) * np.clip((n / SR - t) / 0.08, 0, 1)
    return s * e / len(midis)


def kick():
    t = t_axis(0.35)
    f = 48 + 90 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(len(t), 0.001, 0.12)


def hat():
    n = int(0.06 * SR)
    x = RNG.standard_normal(n)
    x = x - one_pole_sweep(x, np.full(n, 6000.0))
    return x * env_ad(n, 0.0005, 0.015) * 0.25


def bed(duration, hit, bpm=96):
    """一段 4/4 拍的配乐底：和弦铺底 + 底鼓 + 踩镲，hit 处是全曲最重的一拍。"""
    n = int(round(duration * SR))
    out = np.zeros((n, 2))
    beat = 60.0 / bpm
    bar = 4 * beat
    first = hit - np.floor(hit / bar) * bar  # 让 hit 正好落在小节第一拍
    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55, 60], [55, 59, 62]]  # Am F C G
    b = 0
    t0 = first - bar
    while t0 < duration:
        s0 = int(max(t0, 0) * SR)
        s1 = int(min(t0 + bar, duration) * SR)
        if s1 > s0:
            chord = [48, 52, 55, 60, 64] if abs(t0 - hit) < 1e-6 else prog[b % 4]
            level = 0.55 if t0 >= hit - 1e-6 else 0.32
            seg = pad_chord(chord, s1 - s0) * level
            out[s0:s1] += stereo(seg, 0.5)
            bass = np.sin(2 * np.pi * note(chord[0] - 12) * np.arange(s1 - s0) / SR) * 0.25 * level / 0.32
            out[s0:s1] += stereo(bass * np.clip(np.arange(s1 - s0) / (0.02 * SR), 0, 1))
        for k in range(4):  # 底鼓每拍一下，踩镲在反拍；hit 前一拍留空，制造“吸气”
            tb = t0 + k * beat
            if tb < 0 or tb >= duration or abs(tb - (hit - beat)) < 1e-6:
                continue
            if tb < hit - 1e-6 or tb >= hit + bar - 1e-6:
                place(out, stereo(kick() * 0.6), tb)
                place(out, stereo(hat()), tb + beat / 2)
        t0 += bar
        b += 1
    place(out, impact() * 0.9, hit)
    place(out, shimmer() * 0.5, hit)
    r = riser(min(1.6, hit))
    place(out, r * 0.35, hit - len(r) / SR)
    out[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
    return norm(out, -3), first


def place(buf, clip, at):
    s = int(round(at * SR))
    if s >= len(buf):
        return
    c = clip[max(0, -s):]
    s = max(s, 0)
    m = min(len(c), len(buf) - s)
    buf[s:s + m] += c[:m]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kit")
    k.add_argument("out_dir")
    b = sub.add_parser("bed")
    b.add_argument("out")
    b.add_argument("--duration", type=float, default=14.0)
    b.add_argument("--hit", type=float, default=9.0)
    b.add_argument("--bpm", type=float, default=96)
    a = ap.parse_args(argv)
    if a.cmd == "kit":
        os.makedirs(a.out_dir, exist_ok=True)
        meta = {}
        for name, fn in KIT.items():
            x = fn()
            p = os.path.join(a.out_dir, f"{name}.wav")
            save(x, p)
            env = np.abs(x).max(axis=1)
            meta[name] = {"file": f"{name}.wav", "seconds": round(len(x) / SR, 3), "peak_at": round(int(np.argmax(env)) / SR, 3)}
            print(p)
        with open(os.path.join(a.out_dir, "kit.json"), "w", encoding="utf-8") as f:
            json.dump({"source": "synth.py（代码合成，MIT）", "sounds": meta}, f, ensure_ascii=False, indent=1)
    else:
        if a.hit >= a.duration:
            sys.exit("--hit 必须小于 --duration")
        x, _ = bed(a.duration, a.hit, a.bpm)
        save(x, a.out)
        with open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump({"hit": a.hit, "bpm": a.bpm, "duration": a.duration, "source": "synth.py（代码合成，MIT）"}, f, ensure_ascii=False, indent=1)
        print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
