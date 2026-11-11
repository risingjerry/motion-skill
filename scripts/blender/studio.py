"""单灯棚拍：把一个产品模型放进黑色背景、只有一盏面光的场景，用 EEVEE（或 Cycles）渲成逐帧 PNG。
全程后台运行，不用打开 Blender 界面。

  blender -b --python-exit-code 1 -P scripts/blender/studio.py -- --model 产品.glb --out 输出目录 [选项]
  blender -b --python-exit-code 1 -P scripts/blender/studio.py -- --demo --out 输出目录 [选项]

模型格式：.glb .gltf .usdz .usd .usdc .usda .obj .fbx .stl .ply
--demo 不用任何外部文件：用代码搭一个圆角“充电盒”（盒身 + 带铰链的盖子），盖子在 1–40 帧打开。

常用选项：
  --res 3840x2160      输出分辨率（默认 4K）
  --frames 1-2         渲哪些帧（例如 1-48，或 1,40）
  --fps 30             帧率
  --samples 16         采样数（预览 8，成片 64 起）
  --engine eevee       eevee 或 cycles
  --lens 80            焦距（毫米），长焦更像产品棚拍
  --fstop 11           打开景深并设光圈（对焦在物体中心；产品近拍景深很浅，建议 11–16）
  --azimuth 30 --elevation 14   机位方向（度）
  --fill 0.42          物体占画面宽度的比例（要给开盖、转动留余量）
  --turntable 40       在帧范围内把物体绕竖轴平滑转多少度
  --push 0.05          帧范围内镜头慢慢推近多少（比例），画面永远在动
  --light-power 1.0    灯光强度倍数
  --motion-blur 16     打开运动模糊，并设子步数（快动作至少 16，否则会一节一节）
  --transparent        背景透明（给合成、layout_check、seam_check 用）
  --only Lid           只渲这些物体（逗号分隔），其余隐藏；配合 --transparent 做接缝检查
  --save-blend 文件    存一份 .blend，方便之后检查或手动看
  --check Lid:Body     搭好场景后跑 motion_check（逐帧穿模、转速）；--check-objects Lid
  --no-render          只搭场景（配合 --check / --save-blend）
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

IMPORTERS = {
    ".glb": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".gltf": lambda p: bpy.ops.import_scene.gltf(filepath=p),
    ".usdz": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".usd": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".usdc": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".usda": lambda p: bpy.ops.wm.usd_import(filepath=p),
    ".obj": lambda p: bpy.ops.wm.obj_import(filepath=p),
    ".fbx": lambda p: bpy.ops.import_scene.fbx(filepath=p),
    ".stl": lambda p: bpy.ops.wm.stl_import(filepath=p),
    ".ply": lambda p: bpy.ops.wm.ply_import(filepath=p),
}


def parse(argv):
    ap = argparse.ArgumentParser(prog="studio.py", description="单灯棚拍渲染")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--model")
    src.add_argument("--demo", action="store_true")
    ap.add_argument("--demo-variant", choices=["ok", "lid-offset", "wrong-hinge"], default="ok",
                    help="故意做错的示例，用来证明检查脚本能抓到问题")
    ap.add_argument("--out", default=None)
    ap.add_argument("--res", default="3840x2160")
    ap.add_argument("--frames", default="1-2")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--engine", choices=["eevee", "cycles"], default="eevee")
    ap.add_argument("--lens", type=float, default=80)
    ap.add_argument("--fstop", type=float, default=None)
    ap.add_argument("--azimuth", type=float, default=30)
    ap.add_argument("--elevation", type=float, default=14)
    ap.add_argument("--fill", type=float, default=0.42)
    ap.add_argument("--turntable", type=float, default=0)
    ap.add_argument("--push", type=float, default=0.05)
    ap.add_argument("--light-power", type=float, default=1.0)
    ap.add_argument("--motion-blur", type=int, default=0)
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--save-blend", default=None)
    ap.add_argument("--check", default="")
    ap.add_argument("--check-objects", default="")
    ap.add_argument("--max-deg", type=float, default=6.0)
    ap.add_argument("--no-render", action="store_true")
    return ap.parse_args(argv)


def frame_list(spec):
    if "-" in spec and "," not in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


# ---------- 示例几何：圆角充电盒 ----------

def rounded_box(w, d, h, r, seg=8):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * d, v.co.z * h + h / 2))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, offset_type="OFFSET", segments=seg, profile=0.5, affect="EDGES")
    return bm


def half(bm_src, z, keep_below):
    bm = bm_src.copy()
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1),
                                 clear_outer=keep_below, clear_inner=not keep_below)
    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return bm


def mesh_object(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def plastic(name, color, rough=0.25, coat=0.6):
    m = bpy.data.materials.new(name)
    if not m.node_tree:  # 新版本材质默认就有节点；旧版本要手动打开
        m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    for key in ("Coat Weight", "Clearcoat"):
        if key in p.inputs:
            p.inputs[key].default_value = coat
            break
    return m


def build_demo(frames, variant="ok"):
    """62×22×50 mm 的圆角盒，36 mm 高处切成盒身和盖子；盖子绕背面上沿的铰链打开 105°。单位：米。"""
    W, D, H, R, SEAM = 0.062, 0.022, 0.050, 0.008, 0.036
    GAP = 0.00001  # 0.01 mm：合盖时盖子和盒身不共面，避免穿模误报，画面上看不出
    white = plastic("白色塑料", (0.82, 0.82, 0.80))
    src = rounded_box(W, D, H, R)
    body = mesh_object("Body", half(src, SEAM, keep_below=True), white)
    lid_bm = half(src, SEAM, keep_below=False)
    src.free()
    for v in lid_bm.verts:  # 让盖子的原点落在铰链上
        v.co -= Vector((0, D / 2, SEAM))
    lid = mesh_object("Lid", lid_bm, white)
    lid.location = (0.0004 if variant == "lid-offset" else 0, D / 2, SEAM + GAP)  # 错位版：盖子横向偏 0.4 mm
    lid.rotation_mode = "XYZ"
    f0, f1 = min(frames), max(frames)
    open_start, open_end = 8, 40
    lid.rotation_euler = (0, 0, 0)
    lid.keyframe_insert("rotation_euler", frame=open_start)
    lid.rotation_euler = (math.radians(105 if variant == "wrong-hinge" else -105), 0, 0)  # 错误版：往盒身里转
    lid.keyframe_insert("rotation_euler", frame=open_end)
    root = bpy.data.objects.new("Subject", None)
    bpy.context.collection.objects.link(root)
    body.parent = root
    lid.parent = root
    bpy.context.scene.frame_start = min(f0, 1)
    bpy.context.scene.frame_end = max(f1, open_end + 8)
    return root


def import_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in IMPORTERS:
        raise SystemExit(f"不支持的格式 {ext}。支持：{' '.join(IMPORTERS)}")
    if not os.path.exists(path):
        raise SystemExit(f"找不到模型文件：{path}")
    names_before = {o.name for o in bpy.data.objects}
    IMPORTERS[ext](path)
    imported = [bpy.data.objects[n] for n in {o.name for o in bpy.data.objects} - names_before]
    if not imported:
        raise SystemExit("导入后没有任何物体")
    root = bpy.data.objects.new("Subject", None)
    bpy.context.collection.objects.link(root)
    for o in [x for x in imported if not x.parent]:
        o.parent = root
    for o in imported:  # 模型自带的灯和相机都去掉，保证只有一盏灯
        if o.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(o, do_unlink=True)
    return root


def world_bbox(root):
    bpy.context.view_layer.update()
    pts = []
    stack = [root]
    while stack:
        o = stack.pop()
        stack.extend(o.children)
        if o.type == "MESH" and not o.hide_render:
            pts.extend(o.matrix_world @ Vector(c) for c in o.bound_box)
    if not pts:
        raise SystemExit("场景里没有可渲染的网格")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def set_engine(scene, which, samples):
    if which == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
        return "CYCLES"
    for eid in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eid
            break
        except TypeError:
            continue
    ee = scene.eevee
    for attr, val in (("taa_render_samples", samples), ("use_raytracing", True), ("use_shadows", True)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    return scene.render.engine


def setup(a):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    frames = frame_list(a.frames)
    sc.render.fps = a.fps
    root = build_demo(frames, a.demo_variant) if a.demo else import_model(os.path.abspath(a.model))
    if not a.demo:
        sc.frame_start, sc.frame_end = min(frames), max(frames)

    # 把物体中心挪到原点
    lo, hi = world_bbox(root)
    center = (lo + hi) / 2
    root.location -= center
    lo, hi = lo - center, hi - center
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z)

    if a.only:
        keep = set()
        for n in a.only.split(","):
            ob = bpy.data.objects.get(n)
            if ob is None:
                raise SystemExit(f"--only：场景里没有 {n}")
            stack = [ob]
            while stack:
                o = stack.pop()
                keep.add(o.name)
                stack.extend(o.children)
        for o in bpy.data.objects:
            if o.type == "MESH" and o.name not in keep:
                o.hide_render = True

    if a.turntable:
        root.rotation_mode = "XYZ"
        root.rotation_euler = (0, 0, 0)
        root.keyframe_insert("rotation_euler", frame=sc.frame_start)
        root.rotation_euler = (0, 0, math.radians(a.turntable))
        root.keyframe_insert("rotation_euler", frame=sc.frame_end)

    # 相机：长焦，距离按“物体占画宽 fill”算；看向物体中心
    W, H = (int(x) for x in a.res.lower().split("x"))
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = a.lens
    cam_data.sensor_width = 36
    cam_data.sensor_fit = "HORIZONTAL"
    dist = size / a.fill * a.lens / 36
    cam_data.clip_start = dist / 100
    cam_data.clip_end = dist * 100
    cam = bpy.data.objects.new("Camera", cam_data)
    sc.collection.objects.link(cam)
    target = bpy.data.objects.new("Target", None)
    sc.collection.objects.link(target)
    az, el = math.radians(a.azimuth), math.radians(a.elevation)
    direction = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = direction * dist
    cam.keyframe_insert("location", frame=sc.frame_start)
    cam.location = direction * dist * (1 - a.push)
    cam.keyframe_insert("location", frame=sc.frame_end)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    if a.fstop:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_object = target
        cam_data.dof.aperture_fstop = a.fstop
    sc.camera = cam

    # 唯一的一盏灯：左前上方的大面光；世界全黑
    light_data = bpy.data.lights.new("KeyLight", "AREA")
    light_data.shape = "RECTANGLE"
    light_data.size = size * 2.5
    light_data.size_y = size * 3.5
    ld = size * 4
    light_data.energy = 120 * ld * ld * a.light_power  # 随距离平方放大，换模型尺寸也不用重新调
    light = bpy.data.objects.new("KeyLight", light_data)
    sc.collection.objects.link(light)
    laz = az - math.radians(75)
    light.location = Vector((math.sin(laz) * 0.8, -math.cos(laz) * 0.8, 0.75)) * ld
    lc = light.constraints.new("TRACK_TO")
    lc.target = target
    lc.track_axis = "TRACK_NEGATIVE_Z"
    lc.up_axis = "UP_Y"
    world = bpy.data.worlds.new("Black")
    if not world.node_tree:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0, 0, 0, 1)
    bg.inputs[1].default_value = 0.0
    sc.world = world

    eng = set_engine(sc, a.engine, a.samples)
    sc.render.film_transparent = a.transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if a.transparent else "RGB"
    sc.render.image_settings.color_depth = "8"
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        pass
    if a.motion_blur:
        sc.render.use_motion_blur = True
        if hasattr(sc.eevee, "motion_blur_steps"):
            sc.eevee.motion_blur_steps = a.motion_blur
        if hasattr(sc.render, "motion_blur_shutter"):
            sc.render.motion_blur_shutter = 0.5
    return frames, eng, size


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = parse(argv)
    frames, eng, size = setup(a)
    print(f"[studio] 引擎 {eng}，分辨率 {a.res}，帧 {frames[0]}–{frames[-1]}（共 {len(frames)}），物体尺寸 {size:.4f}")
    red = False
    if a.check or a.check_objects:
        import motion_check
        pairs = [tuple(p.split(":")) for p in a.check.split(",") if p]
        objs = [o for o in a.check_objects.split(",") if o]
        sc = bpy.context.scene
        red, _ = motion_check.run(objs, pairs, (sc.frame_start, sc.frame_end), max_deg=a.max_deg)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save_blend))
    if not a.no_render:
        if not a.out:
            raise SystemExit("需要 --out 输出目录")
        os.makedirs(a.out, exist_ok=True)
        sc = bpy.context.scene
        for f in frames:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(os.path.abspath(a.out), f"{f:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[studio] 写出 {sc.render.filepath}", flush=True)
    sys.exit(1 if red else 0)


if __name__ == "__main__":
    main()
