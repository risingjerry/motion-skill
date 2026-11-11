#!/usr/bin/env python3
"""剪影转场：把实拍里的人（或主体）变成边缘干净的纯色剪影，可以从局部特写慢慢拉开。

第一步，抠蒙版（白=前景）：
  python3 scripts/silhouette.py mask 实拍帧目录 蒙版目录
    macOS 14+ 用系统自带的 Vision，不用装别的。其他系统会提示替代方案，
    也可以用任何工具（rembg、MediaPipe、达芬奇 Magic Mask、AE Roto Brush、剪映抠像）导出黑白蒙版序列，直接进第二步。

第二步，画剪影：
  python3 scripts/silhouette.py draw 蒙版目录 输出目录 [--size 3840x2160] [--fg 0,0,0] [--bg 255,255,255]
      [--crop-start 0.42,0.18,0.2,0.2] [--crop-end 0,0,1,1] [--temporal 1] [--sigma 6] [--smooth 10] [--alpha]

做法：相邻帧蒙版平均（去闪）→ 高斯平滑去毛刺 → 只留最大的一块、补掉小洞 → 提取轮廓并沿曲线平滑 →
按取景框把矢量轮廓重新画到输出尺寸（2 倍超采样再缩小），所以从很近的特写放大也不会有锯齿。
--crop-start / --crop-end 是相对原画面的取景框（x, y, 宽, 高，0–1），中间按缓动过渡：从局部特写开始，拉到全身。
"""
import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys

import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("缺少 opencv：python3 -m pip install -r requirements.txt")

HERE = os.path.dirname(os.path.abspath(__file__))

ALTERNATIVES = """当前系统用不了 macOS Vision。可以用这些方法拿到黑白蒙版序列（白=人，黑=背景），再跑 draw：
  - rembg（pip install rembg）：rembg p -om 实拍帧目录 蒙版目录
  - MediaPipe Selfie Segmentation（Python，免费）
  - 达芬奇 Resolve 的 Magic Mask、After Effects 的 Roto Brush、剪映的智能抠像：导出黑白蒙版视频后用 ffmpeg 拆帧
"""


def cmd_mask(frames_dir, masks_dir):
    if platform.system() != "Darwin" or not shutil.which("swift"):
        print(ALTERNATIVES, file=sys.stderr)
        return 2
    script = os.path.join(HERE, "silhouette", "vision_mask.swift")
    r = subprocess.run(["swift", script, frames_dir, masks_dir])
    if r.returncode != 0:
        print("Vision 抠像失败（需要 macOS 14+ 和 Xcode 命令行工具：xcode-select --install）。\n" + ALTERNATIVES, file=sys.stderr)
    return r.returncode


def ease(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def clean_mask(m, sigma, hole_frac=0.002):
    """平滑 → 二值 → 最大连通块 → 补小洞。m: float 0..1"""
    if sigma > 0:
        m = cv2.GaussianBlur(m, (0, 0), sigma)
    b = (m > 0.5).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(b, 8)
    if n <= 1:
        return np.zeros_like(b)
    keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    b = (lab == keep).astype(np.uint8)
    inv = 1 - b
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, 4)
    H, W = b.shape
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        touches = x == 0 or y == 0 or x + w == W or y + h == H
        if not touches and area < hole_frac * W * H:
            b[lab == i] = 1
    return b


def smooth_contour(c, radius):
    """沿曲线做循环高斯平滑，去掉轮廓上的小锯齿。c: (n, 2)"""
    if radius <= 0 or len(c) < 2 * radius + 1:
        return c.astype(np.float64)
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / (radius / 2.0)) ** 2)
    k /= k.sum()
    pad = np.concatenate([c[-radius:], c, c[:radius]]).astype(np.float64)
    xs = np.convolve(pad[:, 0], k, mode="valid")
    ys = np.convolve(pad[:, 1], k, mode="valid")
    return np.stack([xs, ys], axis=1)


def draw_frame(mask, size, crop, fg, bg, smooth, supersample=2, alpha=False):
    """把二值蒙版的矢量轮廓画到 size 大小的画面上，取景框 crop=(x, y, w, h)（蒙版像素）。"""
    W, H = size
    S = supersample
    contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    cx, cy, cw, ch = crop
    sx, sy = W / cw, H / ch
    canvas = np.zeros((H * S, W * S), np.uint8)
    if contours:
        polys_out, polys_hole = [], []
        for i, c in enumerate(contours):
            pts = smooth_contour(c[:, 0, :], smooth)
            pts = np.stack([(pts[:, 0] + 0.5 - cx) * sx * S, (pts[:, 1] + 0.5 - cy) * sy * S], axis=1)
            poly = np.round(pts * 4).astype(np.int32)  # 再细 4 倍，用 shift=2 做亚像素
            (polys_hole if hier[0][i][3] >= 0 else polys_out).append(poly)
        cv2.fillPoly(canvas, polys_out, 255, lineType=cv2.LINE_AA, shift=2)
        if polys_hole:
            cv2.fillPoly(canvas, polys_hole, 0, lineType=cv2.LINE_AA, shift=2)
    cov = cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    if alpha:
        out = np.zeros((H, W, 4), np.uint8)
        out[..., :3] = fg[::-1]
        out[..., 3] = np.round(cov * 255).astype(np.uint8)
        return out
    fgv = np.array(fg[::-1], np.float32)
    bgv = np.array(bg[::-1], np.float32)
    return np.round(bgv + (fgv - bgv) * cov[..., None]).astype(np.uint8)


def parse_box(s):
    v = [float(x) for x in s.split(",")]
    if len(v) != 4:
        raise argparse.ArgumentTypeError("取景框写成 x,y,宽,高（0–1）")
    return v


def cmd_draw(a):
    files = sorted(glob.glob(os.path.join(a.masks, "*.png")))
    if not files:
        print(f"{a.masks} 里没有 png 蒙版", file=sys.stderr)
        return 2
    os.makedirs(a.out, exist_ok=True)
    W, H = (int(x) for x in a.size.lower().split("x"))
    fg = tuple(int(x) for x in a.fg.split(","))
    bg = tuple(int(x) for x in a.bg.split(","))
    raw = [cv2.imread(f, cv2.IMREAD_GRAYSCALE) for f in files]
    if any(r is None for r in raw):
        print("有蒙版读不出来", file=sys.stderr)
        return 2
    mh, mw = raw[0].shape
    n = len(raw)
    for i in range(n):
        lo, hi = max(0, i - a.temporal), min(n, i + a.temporal + 1)
        m = np.mean([raw[j].astype(np.float32) / 255.0 for j in range(lo, hi)], axis=0)
        b = clean_mask(m, a.sigma * mw / 1920.0)
        p = ease(i / max(1, n - 1))
        c0, c1 = a.crop_start, a.crop_end
        box = [(c0[k] + (c1[k] - c0[k]) * p) for k in range(4)]
        crop = (box[0] * mw, box[1] * mh, box[2] * mw, box[3] * mh)
        img = draw_frame(b, (W, H), crop, fg, bg, a.smooth, alpha=a.alpha)
        cv2.imwrite(os.path.join(a.out, f"{i + 1:04d}.png"), img)
    print(f"写出 {n} 帧 → {a.out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mask")
    m.add_argument("frames")
    m.add_argument("masks")
    d = sub.add_parser("draw")
    d.add_argument("masks")
    d.add_argument("out")
    d.add_argument("--size", default="3840x2160")
    d.add_argument("--fg", default="0,0,0")
    d.add_argument("--bg", default="255,255,255")
    d.add_argument("--crop-start", type=parse_box, default=[0, 0, 1, 1])
    d.add_argument("--crop-end", type=parse_box, default=[0, 0, 1, 1])
    d.add_argument("--temporal", type=int, default=1, help="前后各取几帧蒙版做平均")
    d.add_argument("--sigma", type=float, default=6, help="平滑半径（按 1920 宽的像素）")
    d.add_argument("--smooth", type=int, default=10, help="轮廓沿曲线平滑的点数")
    d.add_argument("--alpha", action="store_true", help="输出透明底，剪影用 --fg 颜色")
    a = ap.parse_args(argv)
    if a.cmd == "mask":
        return cmd_mask(a.frames, a.masks)
    return cmd_draw(a)


if __name__ == "__main__":
    sys.exit(main())
