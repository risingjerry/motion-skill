---
name: motion
description: 用代码做 4K 动效短片，全程不用 AI 生图或生视频：产品发布片、App 宣传片、logo 动画、实物产品 3D 镜头、讲解/演示动效、接真人实拍的剪影转场。包括：先出带编号的分镜、HTML 逐帧渲染、浏览器里的 3D、Blender 单灯棚拍、逐帧检查（文字压物体、接缝、穿模、转速）、配乐对齐落点和音效混音。用户说“做个动效/动画/宣传片/发布视频/产品视频/logo 动画/App 演示动画/讲解动画/开场动画/motion graphics/product video/promo/launch video/explainer animation”，或要改这类片子时使用，即使没提“动效”两个字。
---

# 代码动效短片（motion）

片子是代码写的：每一帧都由时间 t 算出来，所以“这里慢一点”只是改一个数字再渲一遍，不用重拍。
不用任何 AI 生图、生视频模型；画面里的东西都来自真素材或代码。

## 先选做到哪一层

三层用同一套流程，越往下越像实拍，也越慢。按片子要什么来选，可以混用。

| 层 | 画面是什么 | 适合 | 起点 |
|---|---|---|---|
| 1. 平面动效 | 真 logo、真截图、形状一路变形 | App、软件、品牌开场 | `templates/2d.html` |
| 2. 浏览器 3D | 界面卡片摆在三维空间、镜头穿行；剪影转场接实拍 | 多屏界面展示、要接真人实拍的片子 | `templates/3d.html`、`scripts/silhouette.py` |
| 3. Blender 棚拍 | 实物产品模型、一盏灯、真实材质 | 耳机、手机、杯子这类实物 | `scripts/blender/studio.py` |

详细说明：`references/layers.md`。

## 流程（按顺序，不跳步）

1. **问清楚，备真料。** 产品是什么、给谁看、多长、在哪个平台放、结尾要观众做什么。素材一律用真的：
   官方 logo 文件、真机截图（先抹掉通知、头像、手机号）、品牌色和字体。不要用应用商店的宣传图当界面，不要凭记忆画 logo。
   做实物先要多角度照片，最好是用户自己拍的实物照片，之后拿来对照模型比例。
2. **定结尾。** 结尾只留图标和字标（或者接实拍）。不加“立即下载”“打开 XX”这类口号，也不放“概念片”免责小字（要说明就放在简介里）。
3. **出带编号的分镜，等对方点头。** 5–10 个镜头，每个写清：时间段、画面、动作、怎么变成下一镜、屏幕上的字。
   写 `shots.json`，跑 `node scripts/render.mjs board shots.json board.png` 出一张图给对方看。
   没点头就不做成片——这时候改最便宜。格式见 `references/storyboard.md`。
4. **搭页面。** 复制模板和 `templates/motion-kit.js` 到素材文件夹。所有节拍写在页面顶部的 `BEATS` 里，改节奏只改这一处。
   页面约定见 `references/html-engine.md`。
5. **逐帧自查，再给人看。** `render.mjs still` 抽关键时刻（每个转场抽 3–4 个点，不只看停住的画面），
   `scripts/sheet.py` 拼成一张图，自己先看一遍。再跑检查脚本：
   - `render.mjs probe` + `scripts/layout_check.py probe`：文字离主体至少 40 px（4K），主体在画面正中附近。
   - 3D：`scripts/blender/motion_check.py`（穿模、每帧最多转 6°、转速不跳）、`scripts/seam_check.py`（合盖接缝 ≤ 1 px）。
   清单见 `references/checklist.md`。
6. **只出 4K。** `node scripts/render.mjs video page.html 片名-4K.mp4 --scale 2`（1920x1080 页面 → 3840x2160）。
   一台电脑同时只跑一个 4K 渲染或 Blender 渲染。抽帧检查从 4K 成片里抽：`python3 scripts/sheet.py video ...`。
7. **画面定了才加声音。** 画面一改，所有节拍都会动。配乐和音效都要有；配乐最重的一拍对准画面的关键落点；
   整体 -14 LUFS、真峰值不超过 -1 dBTP；视频流原样拷贝不重编码。见 `references/sound.md`。
8. **改稿。** 每轮先备份，改完重新抽帧自查，用大白话说清改了什么。另存新版本，不覆盖、不删除对方的文件。
   如实说明查过什么：静帧不等于播放，看图不等于听过混音。

## 让片子好看的规矩

完整解释在 `references/transitions.md` 和 `references/blender-3d.md`，这里是必须记住的：

- **每一镜从上一镜变出来。** 不用淡入淡出、不用叠化。同一个物体变形、翻面、展开、收回，观众的眼睛不用重新找东西。
- **动作放画面正中。** 想象画面中心有个准星，主角一直在它附近。
- **画面一直在动。** 停住的镜头也要有很慢的推近或漂移。
- **一个动作一条曲线。** 推近就一路推近，不要推了又拉；转就一路转，不要转一半回头。快起、慢收，收的时间留长一点。
- **文字简短，从模糊浮上来变清楚**，不要弹跳、不要突然放大。文字不能压到主体上。
- **3D 只用一盏灯**，背景压黑。这是“像棚拍”的大半原因。
- **3D 要物理合理：** 合盖严丝合缝；物体之间不穿模；两个物体交换位置走 3D 公转，不要直线穿过对方；转速平滑不跳。
- **拿实物照片对照模型**，比例、圆角、开孔位置不对就改模型。
- **剪影转场从局部特写开始**，再拉开、再硬切回实拍。见 `references/silhouette.md`。
- **音画只整体平移，不变速、不变调。**

## 守规矩

- **品牌：** 只给对方拥有或获准使用的品牌做。别人的品牌只能当练习作品，不冒充官方、不投广告、不模仿对方真实投放。
- **素材：** 只用对方自己做的或有授权的素材、字体、音乐、模型，确认授权覆盖这种用途。
- **说法：** 片子里的数字和说法都要真实、有出处，不编数据、不编评价。
- **隐私：** 截图和实拍里的个人信息先去掉；出镜的人要同意。
- **付费服务**（配音、AI 音乐等）会花对方的额度，对方要求了才用。

## 脚本一览

| 脚本 | 干什么 |
|---|---|
| `scripts/render.mjs` | HTML 页面 → 静帧 / 4K mp4 / 位置记录（probe）/ 分镜板（board） |
| `scripts/sheet.py` | 静帧或成片按时间抽帧 → 一张带时间的检查图（从原分辨率抽） |
| `scripts/layout_check.py` | 文字和主体的距离、主体居中检查 |
| `scripts/seam_check.py` | 两个部件在真实机位下的接缝错位（像素） |
| `scripts/blender/studio.py` | 单灯棚拍场景 + EEVEE/Cycles 渲染，吃 GLB/glTF/USDZ/OBJ/FBX，`--demo` 自带示例模型 |
| `scripts/blender/motion_check.py` | 逐帧穿模、角速度、转速突变检查 |
| `scripts/silhouette.py` | 抠人蒙版（macOS Vision，可选）→ 平滑矢量剪影，可从特写拉开 |
| `scripts/audio/synth.py` | 代码合成音效包和配乐底（免版权） |
| `scripts/audio/mix.py` | 配乐对齐落点、音效按节拍放、侧链让路、响度归一化、合进视频 |
| `scripts/encode.py` | 逐帧 PNG → mp4 |
| `scripts/doctor.py` | 检查依赖，缺什么、怎么装 |

## 什么时候读哪个文件

| 你在… | 读 |
|---|---|
| 选层、估工作量 | `references/layers.md` |
| 写分镜 | `references/storyboard.md` |
| 写 HTML 页面、出片 | `references/html-engine.md` |
| 设计镜头之间怎么变 | `references/transitions.md` |
| 做实物产品 3D | `references/blender-3d.md` |
| 做剪影、接实拍 | `references/silhouette.md` |
| 加配乐和音效 | `references/sound.md` |
| 交付前自查 | `references/checklist.md` |
| 画面不对劲 | `references/pitfalls.md` |

## 环境

Node.js 18+、Python 3.9+（numpy、Pillow、opencv-python-headless）、ffmpeg、Google Chrome 或 Chromium。
第 3 层需要 Blender（免费）；剪影转场的自动抠像需要 macOS 14+，其他系统用别的工具出蒙版。
开始前跑 `python3 scripts/doctor.py`，缺什么先告诉对方怎么装。
Skill 目录里有 `.venv` 时，Python 脚本用 `.venv/bin/python` 运行（Windows：`.venv\Scripts\python`）；Windows 上把 `python3` 换成 `python`。
