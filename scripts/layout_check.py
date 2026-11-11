#!/usr/bin/env python3
"""画面布局检查：文字不能压到物体上，主体要待在画面正中附近。退出码 1 = 有红项。

两种输入：

1) HTML 页面的 probe 结果（render.mjs probe 生成）：
     python3 scripts/layout_check.py probe probe.json [--pad 40] [--center hero --center-tol 0.08]
   每一帧里，所有 kind=text 的外框和所有主体外框之间的距离都要 >= pad（按 3840 宽的像素计，
   画面不是 4K 时自动换算）。--center 指定的元素，中心偏离画面中心不能超过 center-tol（占画宽的比例）。

2) 透明底的物体逐帧图（如 Blender 只渲物体、背景透明）+ 文字外框表：
     python3 scripts/layout_check.py mask --frames 目录 --fps 30 --text text.json [--pad 40]
   text.json：[{"name": "标题", "from": 1.2, "to": 3.0, "box": [x0, y0, x1, y1]}]，坐标是成片像素。
   帧文件按 0001.png、0002.png… 排（第 1 帧对应 0 秒），不透明度 > 0.5 的像素算物体。
"""
import argparse
import glob
import json
import math
import os
import sys


def rect_gap(a, b):
    """两个矩形之间的距离；重叠时返回负数（重叠深度）。"""
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    if dx >= 0 or dy >= 0:
        return math.hypot(max(dx, 0), max(dy, 0))
    return max(dx, dy)  # 两个都是负数，取较浅的那个当重叠深度


def check_probe(data, pad=40.0, centers=(), center_tol=0.08):
    W, H = data["output"]
    k = W / 3840.0
    worst = {}
    center_worst = {}
    for fr in data["frames"]:
        texts = [i for i in fr["items"] if i["kind"] == "text"]
        subjects = [i for i in fr["items"] if i["kind"] != "text"]
        for tx in texts:
            for sb in subjects:
                g = rect_gap(tx["box"], sb["box"]) / k
                key = (tx["name"], sb["name"])
                if key not in worst or g < worst[key][0]:
                    worst[key] = (g, fr["t"])
        for it in subjects:
            if it["name"] in centers:
                cx = (it["box"][0] + it["box"][2]) / 2
                cy = (it["box"][1] + it["box"][3]) / 2
                off = math.hypot(cx - W / 2, cy - H / 2) / W
                if it["name"] not in center_worst or off > center_worst[it["name"]][0]:
                    center_worst[it["name"]] = (off, fr["t"])
    rows = []
    red = False
    for (tn, sn), (g, t) in sorted(worst.items()):
        ok = g >= pad
        red |= not ok
        rows.append({"check": "text_clearance", "text": tn, "subject": sn, "min_gap_px_4k": round(g, 1), "at": t, "ok": ok})
    for n in centers:
        if n not in center_worst:
            rows.append({"check": "center", "subject": n, "ok": False, "note": "probe 里没有这个元素"})
            red = True
            continue
        off, t = center_worst[n]
        ok = off <= center_tol
        red |= not ok
        rows.append({"check": "center", "subject": n, "max_offset_of_width": round(off, 4), "at": t, "ok": ok})
    return red, rows


def load_alpha(path):
    from PIL import Image
    import numpy as np
    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    return np.asarray(im)[..., 3].astype("float32") / 255.0


def check_masks(frames_dir, fps, texts, pad=40.0, out_w=None):
    import numpy as np
    files = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    if not files:
        sys.exit(f"{frames_dir} 里没有 png")
    rows, red = [], False
    for tx in texts:
        f0 = max(0, int(math.floor(tx["from"] * fps)))
        f1 = min(len(files) - 1, int(math.ceil(tx["to"] * fps)))
        best = (float("inf"), None)
        for i in range(f0, f1 + 1):
            a = load_alpha(files[i])
            h, w = a.shape
            W = out_w or w
            s = W / w                     # 帧像素 → 成片像素
            k = W / 3840.0                # 成片像素 → 4K 像素
            ys, xs = np.nonzero(a > 0.5)
            if len(xs) == 0:
                continue
            X = (xs + 0.5) * s
            Y = (ys + 0.5) * s
            x0, y0, x1, y1 = tx["box"]
            inside = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
            if inside.any():
                d = np.minimum(np.minimum(X[inside] - x0, x1 - X[inside]), np.minimum(Y[inside] - y0, y1 - Y[inside]))
                g = -float(d.max()) / k
            else:
                dx = np.maximum(np.maximum(x0 - X, X - x1), 0)
                dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
                g = float(np.sqrt(dx * dx + dy * dy).min()) / k
            if g < best[0]:
                best = (g, round(i / fps, 3))
        ok = best[0] >= pad
        red |= not ok
        rows.append({"check": "text_vs_mask", "text": tx["name"], "min_gap_px_4k": None if best[1] is None else round(best[0], 1), "at": best[1], "ok": ok})
    return red, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("probe")
    p.add_argument("probe_json")
    p.add_argument("--pad", type=float, default=40)
    p.add_argument("--center", action="append", default=[], help="要求居中的元素名（data-qa），可多次")
    p.add_argument("--center-tol", type=float, default=0.08)
    m = sub.add_parser("mask")
    m.add_argument("--frames", required=True)
    m.add_argument("--fps", type=float, default=30)
    m.add_argument("--text", required=True)
    m.add_argument("--pad", type=float, default=40)
    m.add_argument("--out-width", type=int, help="成片宽度（帧图比成片小时用）")
    a = ap.parse_args(argv)
    if a.mode == "probe":
        red, rows = check_probe(json.load(open(a.probe_json, encoding="utf-8")), a.pad, a.center, a.center_tol)
    else:
        red, rows = check_masks(a.frames, a.fps, json.load(open(a.text, encoding="utf-8")), a.pad, a.out_width)
    for r in rows:
        print(("OK  " if r["ok"] else "RED ") + json.dumps(r, ensure_ascii=False))
    print("LAYOUT_CHECK", "RED" if red else "GREEN")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
