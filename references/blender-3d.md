# 实物产品 3D（Blender）

所有操作都用命令行后台跑（`blender -b`），对方不需要打开 Blender。

## 快速开始

```bash
# 自带示例：代码生成一个圆角充电盒，盖子 8–40 帧打开；渲 2 帧 4K、8 采样
blender -b --python-exit-code 1 -P scripts/blender/studio.py -- --demo --frames 1,40 --samples 8 --out out/demo

# 你的模型
blender -b --python-exit-code 1 -P scripts/blender/studio.py -- --model 产品.glb --frames 1-90 \
    --turntable 40 --samples 32 --out out/frames
python3 scripts/encode.py out/frames 产品-4K.mp4 --fps 30
```

`blender` 命令找不到时，用 Blender 程序的完整路径（macOS 一般在 `/Applications/Blender.app/Contents/MacOS/Blender`）。

## 场景规矩

- **只用一盏灯。** `studio.py` 只放一盏左前上方的大面光，世界背景全黑，导入模型自带的灯和相机都会删掉。
  “像棚拍”大半来自这一点：一个方向的光，明暗过渡干净。要补暗部就把灯调大、换角度，不加第二盏。
- **长焦。** 默认 80 mm，产品不变形。物体占画宽默认 42%，给开盖、转动留余量。
- **景深慎用。** 产品近拍时景深非常浅，f/8 都可能糊掉一半。要用就 `--fstop 11` 到 16，对焦在物体中心。
- **EEVEE 先行。** 预览 960x540、8 采样；成片 4K、32–64 采样。Cycles 更真但慢很多。
- **运动模糊。** 快动作要 `--motion-blur 16`（或更多），默认子步数太少会出现一节一节的残影。

## 物理合理（必须查）

| 问题 | 怎么查 | 标准 |
|---|---|---|
| 合盖不严、盖子和盒身错位 | `seam_check.py`：盖子和盒身分别渲透明底（`--only Lid --transparent` / `--only Body --transparent`），比较接缝处外轮廓 | 真实机位下 ≤ 1 px（4K） |
| 穿模 | `motion_check.py --pairs A:B` 逐帧用 BVH 求交 | 0 帧相交 |
| 转得太快 | `motion_check.py --objects A` 逐帧角速度 | ≤ 6°/帧（30 fps） |
| 转速一顿一顿 | 同上，相邻帧角速度差 | ≤ 1.5°/帧 |
| 两个物体交换位置 | 看分镜和穿模检查 | 走 3D 公转（一个从前面绕、一个从后面绕），不直线穿过对方 |

```bash
blender -b --python-exit-code 1 -P scripts/blender/studio.py -- --demo --check Lid:Body --check-objects Lid --no-render
blender -b 场景.blend --python-exit-code 1 -P scripts/blender/motion_check.py -- --objects Lid --pairs Lid:Body --frames 1-120
python3 scripts/seam_check.py --top out/lid --bottom out/body --frames 1,24,48
```

`--demo-variant lid-offset`（盖子偏 0.4 mm）和 `--demo-variant wrong-hinge`（盖子往盒身里转）是故意做错的示例，用来确认检查真的会报红。

## 拿实物照片对照

模型对不对，不看“像不像”，看对照：

1. 请对方用手机拍实物：正面、侧面、俯视、打开状态，各一张。
2. 用同样的角度渲染模型（调 `--azimuth`、`--elevation`、`--lens`）。
3. 拼在一起看（`scripts/sheet.py images`），或半透明叠在一起：长宽比、圆角大小、缝的位置、开孔、铰链位置。
4. 不对就改模型，再对照一次。

## 模型常见坑

- **单位：** 有的文件是毫米，有的是米。导入后看 `studio.py` 打印的“物体尺寸”，和实物尺寸对一下。
- **转轴不在铰链上：** 展示用的模型常常只摆了“打开”的姿势，转轴空物体不在真实铰链处，转回去合不上。要按几何算铰链位置（盖子口沿和盒身口沿对齐），重设转轴。
- **AR 文件的材质太粗糙：** 手机 AR 用的模型材质通常是哑光的。换成产品真实质感（白色塑料大约粗糙度 0.2–0.3，加一层清漆）。
- **没有内腔：** 物体从盒子里升起时会和盒底“相交”，这是模型没建内腔，不算穿模，但要在报告里说明。

## 授权

厂商官网的 3D/AR 文件、商店图片都有版权。只在对方确认有权使用时用；开源分享的项目里不要附带这些文件。
