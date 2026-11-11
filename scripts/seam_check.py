#!/usr/bin/env python3
"""接缝检查：两个上下相接的部件（例如盒盖和盒身）在真实机位下，外轮廓在接缝处有没有错位。退出码 1 = 红。

做法：把两个部件分别渲成透明底的图（同一机位、同一帧，一次只显示一个部件），
在左右两侧各找“上部件外轮廓交给下部件外轮廓”的那一行，比较交接处两条外边缘的横向位置差。
差值换算成 4K 像素，默认要求 <= 1 px。

  python3 scripts/seam_check.py --top 盖子帧目录 --bottom 盒身帧目录 --frames 1,24,48 [--tol 1]
  帧文件名：0001.png 这样四位数字（Blender 默认）。也可以 --top-file / --bottom-file 直接给两张图。
"""
import argparse
import os
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit("缺少 Pillow：python3 -m pip install -r requirements.txt")


def alpha(path):
    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    return np.asarray(im)[..., 3].astype(np.float64) / 255.0


def edge_x(row, side):
    """一行里最左（L）或最右（R）的轮廓位置，按 alpha=0.5 做亚像素插值。没有就返回 nan。"""
    idx = np.nonzero(row > 0.5)[0]
    if len(idx) == 0:
        return np.nan
    if side == "L":
        x = idx[0]
        prev = row[x - 1] if x > 0 else 0.0
        return x - (row[x] - 0.5) / max(1e-6, row[x] - prev) + 0.5
    x = idx[-1]
    nxt = row[x + 1] if x + 1 < len(row) else 0.0
    return x + (row[x] - 0.5) / max(1e-6, row[x] - nxt) + 0.5


def seam_offsets(top, bottom):
    """返回 {'L': (交接行, 横向差 px), 'R': ...}，差值是该图自己的像素。

    沿左（右）侧从上往下看外轮廓：上部件是最外侧的最后一行就是“交接行”，
    比较这一行上部件的外边缘和下一行下部件的外边缘。轮廓连续时差值接近 0；
    盖子比盒身宽、窄或错位时会出现台阶。
    """
    if top.shape != bottom.shape:
        raise ValueError("两张图尺寸不同")
    H = top.shape[0]
    res = {}
    for side in ("L", "R"):
        tx = np.array([edge_x(top[y], side) for y in range(H)])
        bx = np.array([edge_x(bottom[y], side) for y in range(H)])
        bnext = np.append(bx[1:], np.nan)          # 下一行的下部件外边缘
        adj = ~np.isnan(tx) & ~np.isnan(bnext)     # 上部件这一行有、下部件下一行也有
        if not adj.any():
            res[side] = (None, None)
            continue
        outer = (tx <= bnext + 0.5) if side == "L" else (tx >= bnext - 0.5)
        rows = np.nonzero(adj & outer)[0]
        # 上部件一直比下部件窄（缩进去）时，没有“上部件在最外”的行，取最靠下的相邻行
        y = int(rows.max()) if len(rows) else int(np.nonzero(adj)[0].max())
        res[side] = (y, float(tx[y] - bnext[y]))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top")
    ap.add_argument("--bottom")
    ap.add_argument("--frames", help="逗号分隔的帧号")
    ap.add_argument("--top-file")
    ap.add_argument("--bottom-file")
    ap.add_argument("--tol", type=float, default=1.0, help="允许的错位，4K 像素")
    a = ap.parse_args(argv)
    pairs = []
    if a.top_file and a.bottom_file:
        pairs.append(("file", a.top_file, a.bottom_file))
    elif a.top and a.bottom and a.frames:
        for f in a.frames.split(","):
            n = int(f)
            pairs.append((n, os.path.join(a.top, f"{n:04d}.png"), os.path.join(a.bottom, f"{n:04d}.png")))
    else:
        ap.error("给 --top/--bottom/--frames，或 --top-file/--bottom-file")
    red = False
    for name, tp, bp in pairs:
        T, B = alpha(tp), alpha(bp)
        k = 3840.0 / T.shape[1]
        parts = []
        for side, (y, off) in seam_offsets(T, B).items():
            if y is None:
                parts.append(f"{side}: 找不到轮廓")
                red = True
                continue
            o4 = off * k
            ok = abs(o4) <= a.tol
            red |= not ok
            parts.append(f"{side}: 接缝行 {y} 错位 {o4:+.2f} px@4K {'OK' if ok else 'RED'}")
        print(f"帧 {name}: " + " | ".join(parts))
    print("SEAM_CHECK", "RED" if red else "GREEN", f"(容差 ±{a.tol} px @4K)")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
