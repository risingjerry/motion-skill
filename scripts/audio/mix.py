#!/usr/bin/env python3
"""配乐 + 音效混音：配乐最重的一拍对准画面落点，音效按节拍放，音效响时配乐自动让路，
最后把整体响度做到 -14 LUFS、真峰值不超过 -1 dBTP。可选直接合进视频（视频流原样拷贝，不重新编码）。

  python3 scripts/audio/mix.py sound.json 输出.wav [--video 成片.mp4 --out-video 成片-有声.mp4]

sound.json（路径都相对这个文件，或相对 --base 指定的目录）：
{
  "duration": 10.0,                      # 或省略，用 --video 的时长
  "beats": "film.beats.json",            # 可选：render.mjs 出片时写的节拍表，之后可以写 "beat:名字"
  "offset": 0.0,                         # 声音整体平移（秒）。只平移，从不变速、变调
  "music": {"file": "bed.wav", "hit_in_file": "auto", "hit_at": "beat:lockup",
            "gain_db": 0, "fade_in": 0.2, "fade_out": [9.3, 10.0]},
  "cues": [{"name": "硬币", "file": "sfx/pop.wav", "at": "beat:coin", "align": "onset", "gain_db": -8}],
  "duck": {"depth_db": 5, "release": 0.25},
  "loudness": {"lufs": -14, "true_peak": -1.0}
}
hit_in_file："auto" 自动找配乐里最重的一拍；"json" 读配乐同名 .json 里的 hit；或直接写秒数。
align：start = 文件开头对到 at；onset = 声音起来的那一刻对到 at；peak = 最响处对到 at。
"""
import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, db, ff, load, measure, need_ffmpeg, oversample4, save  # noqa: E402


def lowpass_fft(x, fc):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f > fc] = 0
    return np.fft.irfft(X, n=len(x), axis=0)


def find_hit(x, win=0.01, span=0.3):
    """找配乐里“最重的一拍”：低频（<150 Hz）能量在前后 0.3 秒对比下跳得最多、且跳完整体很响的那一刻。返回秒。"""
    lo = lowpass_fft(x.mean(axis=1), 150)
    full = x.mean(axis=1)
    hop = int(win * SR)
    k = len(lo) // hop
    e_lo = (lo[: k * hop] ** 2).reshape(k, hop).mean(1)
    e_all = (full[: k * hop] ** 2).reshape(k, hop).mean(1)
    w = max(1, int(span / win))
    c_lo = np.concatenate([[0], np.cumsum(e_lo)])
    c_all = np.concatenate([[0], np.cumsum(e_all)])
    score = np.zeros(k)
    for i in range(w, k - w):
        before = (c_lo[i] - c_lo[i - w]) / w
        after = (c_lo[i + w] - c_lo[i]) / w
        loud = (c_all[i + w] - c_all[i]) / w
        score[i] = max(0.0, 10 * np.log10((after + 1e-10) / (before + 1e-10))) * np.sqrt(loud)
    i = int(np.argmax(score))
    # 在这一格前后找精确起音：低频包络第一次达到附近峰值 15% 的采样
    s0 = max(0, (i - 3) * hop)
    seg = np.abs(lo[s0:s0 + 6 * hop])
    j = int(np.argmax(seg >= seg.max() * 0.15))
    return (s0 + j) / SR


def anchor_offset(x, align):
    """返回这个音效里“对齐点”距离文件开头多少秒。"""
    if align == "start":
        return 0.0
    env = np.abs(x).max(axis=1)
    if align == "peak":
        return float(np.argmax(env)) / SR
    if align == "onset":
        return float(np.argmax(env >= env.max() * 0.1)) / SR
    raise ValueError(f"align 只能是 start / onset / peak，收到 {align}")


def place(buf, clip, start_s):
    s = int(round(start_s * SR))
    if s < 0:
        clip = clip[-s:]
        s = 0
    if s >= len(buf) or len(clip) == 0:
        return
    m = min(len(clip), len(buf) - s)
    buf[s:s + m] += clip[:m]


def resolve_time(v, beats):
    """数字 = 秒；"beat:名字" = 节拍表里的时间；"beat:名字+0.4" / "beat:名字-0.2" = 再前后挪一点。"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.startswith("beat:"):
        m = re.fullmatch(r"(.+?)([+-]\d+(?:\.\d+)?)?", v[5:])
        body, shift = m.group(1), float(m.group(2) or 0)
        if body not in beats:
            sys.exit(f"节拍表里没有 {body}。现有：{', '.join(beats)}")
        return float(beats[body]) + shift
    return float(v)


def duck_gain(key, depth_db, release, attack=0.01, block=0.005):
    """侧链让路：音效越响，配乐压得越多（最多 depth_db）。返回每个采样的增益。"""
    hop = int(block * SR)
    k = int(np.ceil(len(key) / hop))
    pad = np.zeros(k * hop)
    pad[: len(key)] = np.abs(key).max(axis=1)
    lvl = 20 * np.log10(pad.reshape(k, hop).max(1) + 1e-9)
    amount = np.clip((lvl + 40) / 20, 0, 1)        # -40 dBFS 开始压，-20 dBFS 以上压满
    sm = np.empty(k)
    a_up = 1 - np.exp(-block / attack)
    a_dn = 1 - np.exp(-block / release)
    acc = 0.0
    for i in range(k):
        acc += (amount[i] - acc) * (a_up if amount[i] > acc else a_dn)
        sm[i] = acc
    g_db = -depth_db * sm
    centers = (np.arange(k) + 0.5) * hop
    return db(np.interp(np.arange(len(key)), centers, g_db))


def limit(x, ceiling_db, lookahead=0.004, release=0.08, block=0.001):
    """真峰值限幅：按 4 倍过采样的峰值算增益，提前 lookahead 秒压下去，再慢慢放开。"""
    ceil = db(ceiling_db)
    up = np.abs(oversample4(x)).max(axis=1)
    peak = up.reshape(-1, 4).max(axis=1)
    hop = max(1, int(block * SR))
    k = int(np.ceil(len(peak) / hop))
    p = np.zeros(k * hop)
    p[: len(peak)] = peak
    need = np.minimum(1.0, ceil / (p.reshape(k, hop).max(1) + 1e-12))
    la = int(np.ceil(lookahead / block))
    g = need.copy()
    for s in range(1, la + 1):          # 往前扩：峰值来之前就开始压
        g[:-s] = np.minimum(g[:-s], need[s:])
    out = np.empty(k)
    acc = 1.0
    a_rel = 1 - np.exp(-block / release)
    for i in range(k):
        acc = g[i] if g[i] < acc else acc + (g[i] - acc) * a_rel
        out[i] = acc
    gain = np.interp(np.arange(len(x)), (np.arange(k) + 0.5) * hop, out)
    gain = np.minimum(gain, np.repeat(g, hop)[: len(x)])
    return x * gain[:, None]


def master(x, lufs, tp, rounds=4):
    """先整体增益到目标响度，再限真峰值；限幅会让响度略降，所以迭代几次。"""
    y = x
    for _ in range(rounds):  # noqa: B007
        m = measure(y)
        y = y * db(lufs - m["lufs"])
        y = limit(y, tp - 0.4)
        m2 = measure(y)
        if abs(m2["lufs"] - lufs) <= 0.3 and m2["true_peak"] <= tp:
            return y, m2
    return y, measure(y)


def video_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def mux(video, wav, out):
    """视频流原样拷贝，只加声音；时长以视频为准。"""
    dur = video_duration(video)
    subprocess.run([ff(), "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", str(SR), "-t", f"{dur:.3f}",
                    "-movflags", "+faststart", out], check=True)
    return out


def run(spec_path, out_wav, video=None, out_video=None, quiet=False, base=None):
    need_ffmpeg()
    spec = json.load(open(spec_path, encoding="utf-8"))
    base = os.path.abspath(base) if base else os.path.dirname(os.path.abspath(spec_path))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)  # noqa: E731
    beats = {}
    if spec.get("beats"):
        bj = json.load(open(rel(spec["beats"]), encoding="utf-8"))
        beats = bj.get("beats", bj)
    dur = spec.get("duration") or (video_duration(video) if video else None)
    if not dur:
        sys.exit("sound.json 里写 duration，或者给 --video")
    n = int(round(dur * SR))
    off = float(spec.get("offset", 0.0))
    report = {"duration": dur, "offset": off, "cues": []}

    music = np.zeros((n, 2))
    mu = spec.get("music")
    if mu:
        x = load(rel(mu["file"])) * db(mu.get("gain_db", 0))
        h = mu.get("hit_in_file", "auto")
        if h == "auto":
            src_hit = find_hit(x)
        elif h == "json":
            src_hit = float(json.load(open(os.path.splitext(rel(mu["file"]))[0] + ".json"))["hit"])
        else:
            src_hit = float(h)
        film_hit = resolve_time(mu["hit_at"], beats) + off
        start = film_hit - src_hit           # 配乐文件第 0 秒放在片子的哪一秒（可以是负数 = 从配乐中间开始）
        place(music, x, start)
        t = np.arange(n) / SR
        env = np.ones(n)
        fi = float(mu.get("fade_in", 0))
        if fi > 0:
            env *= np.clip((t - max(start, 0)) / fi, 0, 1)
        if mu.get("fade_out"):
            f0, f1 = mu["fade_out"]
            env *= np.clip((f1 - t) / max(f1 - f0, 1e-3), 0, 1)
        music *= env[:, None]
        report["music"] = {"hit_in_file": round(src_hit, 4), "hit_at_film": round(film_hit, 4), "music_starts_at": round(start, 4)}

    sfx = np.zeros((n, 2))
    for c in spec.get("cues", []):
        x = load(rel(c["file"])) * db(c.get("gain_db", 0))
        at = resolve_time(c["at"], beats) + off
        a = anchor_offset(x, c.get("align", "onset"))
        place(sfx, x, at - a)
        report["cues"].append({"name": c.get("name", os.path.basename(c["file"])), "at": round(at, 4), "align": c.get("align", "onset")})

    d = spec.get("duck", {})
    if mu and d.get("depth_db", 0) > 0 and np.any(sfx):
        music *= duck_gain(sfx, d["depth_db"], d.get("release", 0.25))[:, None]

    mix = music + sfx
    if not np.any(mix):
        sys.exit("混出来是静音：检查 music / cues")
    lo = spec.get("loudness", {})
    target, tp = float(lo.get("lufs", -14)), float(lo.get("true_peak", -1.0))
    mix, m = master(mix, target, tp)
    save(mix, out_wav)
    report["wav"] = {"file": out_wav, **m}
    if video and out_video:
        mux(video, out_wav, out_video)
        report["video"] = {"file": out_video, **measure(out_video)}
    if not quiet:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("out_wav")
    ap.add_argument("--video")
    ap.add_argument("--out-video")
    ap.add_argument("--base", help="相对路径按这个目录解析（默认是 sound.json 所在目录）")
    a = ap.parse_args(argv)
    run(a.spec, a.out_wav, a.video, a.out_video, base=a.base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
