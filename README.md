简体中文 · [English](#english)

# motion-ad-skill：让 Claude 用代码做 4K 产品动效广告片

一个开源的 Claude Skill。装上以后，对 Claude 说“给我的 App 做一条 10 秒的动效广告”，它会先出带编号的分镜给你看，
你点头后用 HTML（或 Blender）一帧一帧渲出 **3840×2160 的成片**，逐帧检查，最后配上配乐和音效。
**全程不用任何 AI 生图、生视频**，画面全是代码和你的真素材。

![示例成片：硬币翻面变成 App 图标，展开成手机界面，最后收回成图标加字标](docs/demo.gif)

上面这条 10 秒示例（虚构的记账 App “Tallybird”）就是用仓库自带的脚本从零做出来的：
`python3 examples/minimal/build.py`，在一台 8 核笔记本上约 1 分钟出 4K 有声成片。

## 安装

需要：Node.js 18+、Python 3.9+、ffmpeg、Google Chrome（或 Chromium）。Blender 可选。

```bash
git clone https://gitee.com/risingjerry/motion-ad-skill.git ~/.claude/skills/motion-ad
cd ~/.claude/skills/motion-ad
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py
```

应该看到每一项前面是 `OK`，最后一行是“必需的都齐了，可以开始。”；缺什么它会写出怎么装。
Windows 用 `%USERPROFILE%\.claude\skills\motion-ad`，把 `.venv/bin/` 换成 `.venv\Scripts\`。

## 先跑一遍示例

```bash
.venv/bin/python examples/minimal/build.py
```

会在 `examples/minimal/out/` 里生成：

| 文件 | 是什么 |
|---|---|
| `storyboard.png` | 带编号的分镜板（真正做片时，这一步要等对方点头） |
| `ad.mp4` | 3840×2160、30 fps 的无声成片 |
| `frames.jpg` + `frames/` | 从 4K 成片里抽的 3 帧（原尺寸 PNG） |
| `ad-sound.mp4` | 加了配乐和音效的成片（视频流原样拷贝，没有重新编码） |
| `mix.wav` | 混音，-14 LUFS、真峰值 ≤ -1 dBTP |

终端里会打印布局检查（`LAYOUT_CHECK GREEN`）和混音报告（配乐最重的一拍落在第几秒、响度多少）。

![分镜板：6 个编号镜头，每格写着时间、画面、动作、怎么变成下一镜](docs/storyboard.png)

## 在 Claude Code 里用

装到 `~/.claude/skills/motion-ad` 后，Claude Code 会自动发现这个 Skill。直接说：

- “用 motion-ad 给我的记账 App 做一条 12 秒的动效广告，logo 在 `assets/logo.svg`，截图在 `assets/screens/`。”
- “我有耳机充电盒的 glb 模型，做一条 Blender 单灯棚拍的开盖展示，先给我分镜。”
- “把第 3 镜到第 4 镜的变形放慢一点，配乐最重的一拍对到图标落定。”

Codex、Cursor 等其他 Agent 读仓库根目录的 `AGENTS.md`。

## 它会怎么做

1. **问清楚、备真料**：真 logo、真机截图（先抹掉个人信息）、品牌色。实物产品先要实物照片。
2. **出编号分镜，等你点头**：`render.mjs board` 出一张分镜板。没点头不做成片。
3. **写页面**：从 `templates/2d.html`（平面）或 `templates/3d.html`（CSS 3D）起步，所有节拍集中在一处。
4. **逐帧自查**：抽每个转场的 3–4 帧拼图看；脚本量文字有没有压到物体、主体是否居中；3D 查穿模、转速、合盖接缝。
5. **只出 4K**：`render.mjs video --scale 2`。
6. **最后加声音**：配乐最重的一拍对准关键落点，音效按节拍放，音效响时配乐让路，响度做到 -14 LUFS。

做片子的规矩（每一镜从上一镜变出来、动作放正中、画面一直在动、3D 只用一盏灯、结尾只留图标和字标……）写在 [`SKILL.md`](SKILL.md) 和 [`references/`](references/)。

## 三层

| 层 | 画面 | 工具 |
|---|---|---|
| 1. 平面动效 | 真 logo、截图、形状一路变形 | `templates/2d.html`、`scripts/render.mjs` |
| 2. 浏览器 3D + 接实拍 | 界面卡片在三维空间里、镜头穿行；剪影转场接真人实拍 | `templates/3d.html`、`scripts/silhouette.py` |
| 3. Blender 棚拍 | 实物产品模型、一盏灯、真实材质 | `scripts/blender/studio.py`、`motion_check.py`、`seam_check.py` |

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/render.mjs` | HTML → 静帧 / 4K mp4 / 元素位置记录 / 分镜板 |
| `scripts/sheet.py` | 按时间从成片原分辨率抽帧，拼成检查图 |
| `scripts/layout_check.py` | 文字离主体 ≥ 40 px（4K）、主体居中 |
| `scripts/seam_check.py` | 两个部件在真实机位下的接缝错位 ≤ 1 px |
| `scripts/blender/studio.py` | 单灯棚拍 + EEVEE/Cycles 渲染，吃 GLB/glTF/USDZ/OBJ/FBX/STL/PLY，`--demo` 自带示例模型 |
| `scripts/blender/motion_check.py` | 逐帧穿模（BVH）、角速度 ≤ 6°/帧、转速不跳 |
| `scripts/silhouette.py` | 抠人蒙版（macOS Vision，可选）→ 平滑矢量剪影，从局部特写拉开 |
| `scripts/audio/synth.py` | 代码合成音效包和配乐底（免版权） |
| `scripts/audio/mix.py` | 配乐对齐落点、音效按节拍放、侧链让路、响度归一化、合进视频 |
| `scripts/encode.py` | 逐帧 PNG → mp4 |
| `scripts/doctor.py` | 检查依赖（`--json` 给 Agent 读） |

## 限制

- **速度**：HTML 动效 10 秒 4K 约 1–3 分钟；Blender EEVEE 4K 每帧几秒到十几秒，一条 15 秒的 3D 片可能要一小时。同时只跑一个 4K 任务，否则容易卡死电脑。
- **剪影的自动抠像只在 macOS 14+ 上能用**（系统自带的 Vision）。其他系统用 rembg、MediaPipe 或剪辑软件导出黑白蒙版，脚本照样能画剪影。
- **Blender 是可选的**：没有它，第 1、2 层照常用。
- **声音没有“听”过**：脚本能对齐时间、测响度，但好不好听要人戴耳机听。
- **不附带任何品牌素材、3D 模型、音效库或音乐**。示例只用自己画的 SVG 和代码合成的声音；你的素材需要你自己有授权。

## 常见问题

### 不用 AI 生成视频，怎么做出动效广告？
画面是一个 HTML 页面（或 Blender 场景），每一帧由时间算出来；脚本让浏览器按时间逐帧截图，再用 ffmpeg 编成 4K 视频。

### 需要会写代码、会用 Blender 吗？
不需要。代码由 Claude 写，Blender 在后台运行，你不用打开它。你要做的是提供真素材、看分镜、提意见。

### 能做多长的片子？
设计目标是 8–20 秒的广告片。更长也能渲染，但这套流程（每一镜都从上一镜变出来）适合短片。

### 为什么一定要先出分镜？
分镜阶段改一句话就是改一个镜头，渲染之后再改要重来。编号让你能精确地说“3 变 4 太快”。

### 怎么让配乐的高潮正好落在画面关键时刻？
`mix.py` 会自动找配乐里最重的一拍（或你手动写秒数），把整首配乐平移到让它落在你指定的节拍上。只平移，不变速、不变调。

### 可以用别人品牌的 logo 做吗？
只给你拥有或获准使用的品牌做。练习作品不要冒充官方、不要拿去投放。

### 在 Windows 上能用吗？
HTML 渲染、检查脚本、声音脚本、Blender 部分都是跨平台写的；作者只在 macOS 上实测过。剪影的自动抠像只支持 macOS。

## 数据和隐私

所有脚本都在本机运行，不联网（`npm install` / `pip install` 装依赖时除外）、不上传任何文件、不需要账号或密钥。
渲染用的是本机的无头浏览器和一个临时的空白浏览器配置，不会读你日常浏览器的数据。

## 问题反馈

遇到 bug 或有想法，在 Gitee 仓库提 Issue，附上 `python3 scripts/doctor.py --json` 的输出和出错的命令。

## 卸载

```bash
rm -rf ~/.claude/skills/motion-ad
```

## 致谢

思路受 Rourke（GenHQ）的视频启发：https://www.youtube.com/watch?v=cDb-wPq0Iyk
本仓库的文字和代码都是独立编写的。

## 许可（License）

[MIT](LICENSE)。示例里的 Tallybird 名字和 logo 是虚构的，随仓库一起按 MIT 使用；`synth.py` 生成的声音同样可以商用。

如果它帮你做出了片子，点个 Star 能让更多人找到它。

---

## English

**motion-ad-skill** is an open-source Claude Skill for making 8–20 second product motion ads as code, rendered to 4K, with no AI image or video generation.
Claude drafts a numbered storyboard first, waits for your approval, then builds the animation as an HTML page (or a Blender scene),
renders it frame by frame to 3840×2160, runs automated checks (text overlapping the subject, centering, mesh collisions, rotation speed, lid seam alignment),
and finally adds music and sound effects aligned to the key beats, mastered to -14 LUFS.

```bash
git clone https://gitee.com/risingjerry/motion-ad-skill.git ~/.claude/skills/motion-ad
cd ~/.claude/skills/motion-ad
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py
.venv/bin/python examples/minimal/build.py   # renders the 10 s 4K example with sound
```

Requirements: Node.js 18+, Python 3.9+, ffmpeg, Google Chrome or Chromium. Optional: Blender (product shots), macOS 14+ (automatic person masks for silhouette transitions).
The docs and in-repo instructions are written in Chinese; script names, flags and outputs are self-explanatory.
Inspired by a video from Rourke (GenHQ): https://www.youtube.com/watch?v=cDb-wPq0Iyk . All text and code here are original. MIT licensed.
