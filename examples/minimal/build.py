#!/usr/bin/env python3
"""把最小示例从头做一遍：分镜板 → 4K 成片 → 布局检查 → 抽帧检查图 → 合成声音 → 混音合进成片 → 测响度。

  python3 examples/minimal/build.py                 # 输出到 examples/minimal/out/
  python3 examples/minimal/build.py --out 某个目录   # 输出到别处
  python3 examples/minimal/build.py --scale 1       # 快速试跑（1920x1080），不是 4K

全部只用本仓库的脚本，不联网、不需要任何外部素材。
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PY = sys.executable


def step(title, cmd):
    print(f"\n== {title}\n   $ {' '.join(cmd)}", flush=True)
    t = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"失败：{title}（退出码 {r.returncode}）")
    print(f"   用时 {time.time() - t:.1f}s", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--scale", default="2", help="2 = 3840x2160（默认）；1 = 1920x1080 快速试跑")
    ap.add_argument("--fps", default="30")
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    page = os.path.join(HERE, "ad.html")
    video = os.path.join(out, "ad.mp4")
    final = os.path.join(out, "ad-sound.mp4")

    step("1/7 分镜板（出片前先给人看的那张图）", ["node", "scripts/render.mjs", "board", os.path.join(HERE, "shots.json"), os.path.join(out, "storyboard.png"), "--quiet"])
    step("2/7 逐帧渲染成片", ["node", "scripts/render.mjs", "video", page, video, "--scale", a.scale, "--fps", a.fps])
    step("3/7 记录每一帧的文字和主体位置", ["node", "scripts/render.mjs", "probe", page, os.path.join(out, "probe.json"), "--step", "0.1", "--scale", a.scale, "--quiet"])
    step("4/7 布局检查：文字离主体 ≥ 40px@4K，主体在正中附近", [PY, "scripts/layout_check.py", "probe", os.path.join(out, "probe.json"), "--center", "hero", "--center-tol", "0.15"])
    step("5/7 从成片原分辨率抽 3 帧拼检查图", [PY, "scripts/sheet.py", "video", os.path.join(out, "frames.jpg"), video, "--times", "1.0,4.6,9.6", "--save-frames", os.path.join(out, "frames"), "--cols", "3"])
    step("6/7 用代码合成音效和配乐底", [PY, "scripts/audio/synth.py", "kit", os.path.join(out, "audio", "sfx")])
    step("6/7 （续）配乐底：最重一拍在 9.0 秒", [PY, "scripts/audio/synth.py", "bed", os.path.join(out, "audio", "bed.wav"), "--duration", "14", "--hit", "9.0"])
    step("7/7 混音 + 合进成片（视频流原样拷贝）", [PY, "scripts/audio/mix.py", os.path.join(HERE, "sound.json"), os.path.join(out, "mix.wav"),
                                            "--base", out, "--video", video, "--out-video", final])

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                            "-of", "json", final], capture_output=True, text=True, check=True).stdout
    info = json.loads(probe)
    print("\n== 成片信息")
    for s in info["streams"]:
        print("  ", {k: s.get(k) for k in ("codec_type", "codec_name", "width", "height", "r_frame_rate") if s.get(k)})
    print("   时长", info["format"]["duration"], "秒")
    print(f"\n完成。成片：{final}\n分镜板：{os.path.join(out, 'storyboard.png')}\n检查图：{os.path.join(out, 'frames.jpg')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
