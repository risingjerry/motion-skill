#!/usr/bin/env python3
"""把多张静帧拼成一张带时间标签的检查图；也能直接从成片里按时间抽帧（从原分辨率抽，不先缩小）。

  python3 scripts/sheet.py images  out.jpg a.png b.png ...        # 拼已有图片
  python3 scripts/sheet.py video   out.jpg film.mp4 --times 1,2.5,4 [--save-frames 目录]
  python3 scripts/sheet.py video   out.jpg film.mp4 --every 0.5
  通用：--cols 4  --width 640（每格宽度）

--save-frames 会把抽出来的原分辨率帧（4K 片就是 4K）存成 PNG，方便放大看细节。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("缺少 Pillow：python3 -m pip install -r requirements.txt")


def probe_duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def grab(video, t, path):
    # -ss 放在 -i 后面：逐帧解码到准确时间，慢一点但不会抽错帧
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ss", f"{t:.3f}", "-frames:v", "1", path], check=True)


def tile(items, out, cols=4, cell_w=640):
    """items: [(PIL.Image, 标签)]"""
    if not items:
        sys.exit("没有可拼的图")
    first = items[0][0]
    cell_h = round(cell_w * first.height / first.width)
    label_h = 30
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * 8, rows * (cell_h + label_h) + (rows + 1) * 8), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=20)
    except TypeError:  # 旧版 Pillow
        font = ImageFont.load_default()
    for i, (im, label) in enumerate(items):
        r, c = divmod(i, cols)
        x = 8 + c * (cell_w + 8)
        y = 8 + r * (cell_h + label_h + 8)
        sheet.paste(im.convert("RGB").resize((cell_w, cell_h), Image.LANCZOS), (x, y))
        draw.text((x + 4, y + cell_h + 4), label, fill=(230, 230, 230), font=font)
    sheet.save(out, quality=92)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["images", "video"])
    ap.add_argument("out")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--times", help="逗号分隔的秒数")
    ap.add_argument("--every", type=float, help="每隔多少秒抽一帧")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--save-frames", help="把抽出的原分辨率帧另存到这个目录")
    a = ap.parse_args(argv)

    items = []
    if a.mode == "images":
        for p in a.inputs:
            items.append((Image.open(p), os.path.basename(p)))
    else:
        video = a.inputs[0]
        if a.times:
            times = [float(x) for x in a.times.split(",")]
        elif a.every:
            d = probe_duration(video)
            n = int(d / a.every)
            times = [round(i * a.every, 3) for i in range(n + 1) if i * a.every < d - 0.01]
        else:
            sys.exit("video 模式需要 --times 或 --every")
        with tempfile.TemporaryDirectory() as tmp:
            for t in times:
                p = os.path.join(a.save_frames or tmp, f"frame_{t:07.3f}.png")
                os.makedirs(os.path.dirname(p), exist_ok=True)
                grab(video, t, p)
                im = Image.open(p)
                im.load()
                items.append((im, f"{t:.2f}s  {im.width}x{im.height}"))
            tile(items, a.out, a.cols, a.width)
        print(a.out)
        return 0
    tile(items, a.out, a.cols, a.width)
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
