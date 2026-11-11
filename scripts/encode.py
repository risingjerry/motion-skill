#!/usr/bin/env python3
"""把逐帧 PNG（例如 Blender 渲出来的 0001.png、0002.png…）编成 mp4。

  python3 scripts/encode.py 帧目录 输出.mp4 [--fps 30] [--crf 14] [--start 1]

色彩按 BT.709 标好，H.264 + yuv420p，常见播放器和平台都能直接放。
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("frames")
    ap.add_argument("out")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--crf", type=int, default=14)
    ap.add_argument("--start", type=int, default=None, help="第一帧的编号（默认取目录里最小的）")
    a = ap.parse_args(argv)
    if not shutil.which("ffmpeg"):
        sys.exit("找不到 ffmpeg。macOS：brew install ffmpeg；Windows：winget install ffmpeg；Linux：apt install ffmpeg")
    files = sorted(glob.glob(os.path.join(a.frames, "[0-9][0-9][0-9][0-9].png")))
    if not files:
        sys.exit(f"{a.frames} 里没有 0001.png 这样的帧")
    start = a.start if a.start is not None else int(os.path.basename(files[0])[:4])
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-start_number", str(start),
           "-i", os.path.join(a.frames, "%04d.png"),
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
