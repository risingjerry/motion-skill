"""在 Blender 里逐帧检查动画是否“物理合理”：转得太快、转速忽快忽慢、物体互相穿模。退出码 1 = 红。

  blender -b 场景.blend --python-exit-code 1 -P scripts/blender/motion_check.py -- \
      --objects Lid --pairs Lid:Body --frames 1-48 [--max-deg 6] [--max-jump 1.5] [--json 结果.json]

--objects  要查角速度的物体（逗号分隔）
--pairs    要查穿模的物体对，A:B，逗号分隔；名字也可以是集合（collection）名，会把里面所有网格合在一起
--max-deg  每帧最多转多少度（默认 6）
--max-jump 相邻两帧角速度最多差多少度（默认 1.5）
--touch    距离小于这个值（场景单位）算“贴着”，只报告不算红（默认 0）
studio.py 也可以用 --check 直接调用这里的 run()。
"""
import json
import os
import sys

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motion_math as mm  # noqa: E402


def parse(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="motion_check.py")
    ap.add_argument("--objects", default="")
    ap.add_argument("--pairs", default="")
    ap.add_argument("--frames", default=None, help="例如 1-48，默认用场景的帧范围")
    ap.add_argument("--max-deg", type=float, default=6.0)
    ap.add_argument("--max-jump", type=float, default=1.5)
    ap.add_argument("--touch", type=float, default=0.0)
    ap.add_argument("--json", default=None)
    return ap.parse_args(argv)


def meshes_for(name):
    """名字可以是物体（含其子物体）或集合。"""
    out = []
    ob = bpy.data.objects.get(name)
    if ob:
        stack = [ob]
        while stack:
            o = stack.pop()
            if o.type == "MESH":
                out.append(o)
            stack.extend(o.children)
        return out
    col = bpy.data.collections.get(name)
    if col:
        return [o for o in col.all_objects if o.type == "MESH"]
    raise SystemExit(f"场景里没有叫 {name} 的物体或集合")


def world_bvh(objs, depsgraph):
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(depsgraph)
        me = ev.to_mesh()
        M = ev.matrix_world
        base = len(verts)
        verts.extend([M @ v.co for v in me.vertices])
        polys.extend([[base + i for i in p.vertices] for p in me.polygons])
        ev.to_mesh_clear()
    if not verts:
        return None, []
    return BVHTree.FromPolygons(verts, polys), verts


def min_distance(ta, va, tb, vb, step=4):
    d = float("inf")
    for v in va[::step]:
        hit = tb.find_nearest(v)
        if hit[0] is not None:
            d = min(d, hit[3])
    for v in vb[::step]:
        hit = ta.find_nearest(v)
        if hit[0] is not None:
            d = min(d, hit[3])
    return d


def run(objects=(), pairs=(), frames=None, max_deg=6.0, max_jump=1.5, touch=0.0, json_path=None):
    sc = bpy.context.scene
    f0, f1 = frames or (sc.frame_start, sc.frame_end)
    quats = {n: [] for n in objects}
    pair_res = {f"{a}:{b}": {"overlap_frames": [], "min_distance": float("inf"), "min_at": None} for a, b in pairs}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for n in objects:
            ob = bpy.data.objects.get(n)
            if ob is None:
                raise SystemExit(f"场景里没有物体 {n}")
            q = ob.matrix_world.to_quaternion()
            quats[n].append((q.w, q.x, q.y, q.z))
        for a, b in pairs:
            ta, va = world_bvh(meshes_for(a), dg)
            tb, vb = world_bvh(meshes_for(b), dg)
            r = pair_res[f"{a}:{b}"]
            if ta is None or tb is None:
                continue
            if ta.overlap(tb):
                r["overlap_frames"].append(f)
                d = 0.0
            else:
                d = min_distance(ta, va, tb, vb)
            if d < r["min_distance"]:
                r["min_distance"], r["min_at"] = d, f
    red = False
    report = {"frames": [f0, f1], "rotation": {}, "pairs": pair_res}
    for n, qs in quats.items():
        sp = mm.angular_speeds(qs)
        probs = mm.speed_problems(sp, max_deg, max_jump, first_frame=f0)
        red |= bool(probs)
        report["rotation"][n] = {"max_deg_per_frame": round(max(sp) if sp else 0.0, 3), "problems": probs}
        print(f"[转速] {n}: 最快 {report['rotation'][n]['max_deg_per_frame']}°/帧（上限 {max_deg}）" + ("  OK" if not probs else f"  RED {probs[:5]}"))
    for k, r in pair_res.items():
        bad = bool(r["overlap_frames"])
        red |= bad
        md = r["min_distance"]
        note = "贴着" if (not bad and md <= touch) else ""
        print(f"[穿模] {k}: 相交帧 {r['overlap_frames'][:20]}{'…' if len(r['overlap_frames']) > 20 else ''}，最小间距 {md:.6f}（第 {r['min_at']} 帧）{note}" + ("  RED" if bad else "  OK"))
    print("MOTION_CHECK", "RED" if red else "GREEN")
    report["result"] = "RED" if red else "GREEN"
    if json_path:
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=1, default=str)
    return red, report


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = parse(argv)
    objects = [s for s in a.objects.split(",") if s]
    pairs = [tuple(p.split(":")) for p in a.pairs.split(",") if p]
    frames = tuple(int(x) for x in a.frames.split("-")) if a.frames else None
    red, _ = run(objects, pairs, frames, a.max_deg, a.max_jump, a.touch, a.json)
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
