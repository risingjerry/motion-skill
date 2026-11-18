<div align="center">

# motion-skill：Claude 动效 Skill

**装上它，Claude 就能用代码给你的产品做 4K 动效视频：先出分镜，你点头后渲染成片，再配好音乐和音效。全程不用 AI 生视频，也不用你会剪辑。**

[![视频教程 · B 站](https://img.shields.io/badge/视频教程-B%20站-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1n3s16fEkM)
[![Video tutorial · YouTube](https://img.shields.io/badge/视频教程-YouTube-FF0000?logo=youtube&logoColor=white)](https://youtu.be/LmCttBxh5xg)
[![CI](https://github.com/risingjerry/motion-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/risingjerry/motion-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-7C5CFF.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/risingjerry/motion-skill?color=E8735F)](https://github.com/risingjerry/motion-skill/releases)

[English](README.md) · 简体中文

![示例成片：硬币翻面变成 App 图标，展开成手机界面，最后收回成图标加字标](docs/demo.gif)

</div>

上面这条 10 秒的片子（虚构的记账 App “Tallybird”）是仓库自带的示例，一行命令就能在你电脑上重新做出来，出 4K 有声成片。画面全是代码和真素材，没有用任何生图、生视频模型。

> **从视频过来的？** 这就是视频里说的那个免费 Skill。完整教程：[B 站](https://www.bilibili.com/video/BV1n3s16fEkM) · [YouTube](https://youtu.be/LmCttBxh5xg)。
> 视频里的 Apple Music、AirPods、抖音那几条案例片用了这些品牌的素材，没有授权放进开源仓库；做法都在这个 Skill 里。

## 三步用起来

**第 1 步：装好 Claude Code。** 用 Claude 桌面 App 里的 Claude Code，或者终端里的 `claude` 都行。

**第 2 步：把下面这段话原样发给 Claude Code，它会自己装好。**

```text
帮我安装这个 Skill：https://github.com/risingjerry/motion-skill
按它 README 里“自己动手安装”那一节，装到 ~/.claude/skills/motion。
缺 Node.js、Python、ffmpeg、Chrome 就先帮我装上（Mac 用 Homebrew），
最后跑 doctor 检查，再跑一遍 1080p 的示例给我看结果。
```

要做 3D 实物镜头的话，再装一个免费的 [Blender](https://www.blender.org/download/)。装好就行，不用打开，Claude 会自己在后台用它。

**第 3 步：建一个文件夹，放素材，跟 Claude 说一句话。**

1. 新建一个文件夹，放进你的高清 logo（最好是 SVG 或透明背景的 PNG）和 App 的真实截图（先把头像、手机号这类个人信息抹掉）。
2. 在 Claude Code 里打开这个文件夹。
3. 对它说：

```text
用 motion 给我的 App 做一条 10 秒的宣传视频。素材都在这个文件夹里。
先给我出带编号的分镜，我确认了再做。
每个镜头都要从上一个镜头自然变出来，不要用交叉溶解。
```

它会先给你一张分镜图。哪里不满意直接说（比如“3 变 4 太快”），改到满意再让它渲染。画面定了，再把下载好的音效和配乐放进文件夹，让它按节拍配上。

## 视频里的 12 个技巧，Skill 里都写进去了

视频里讲的每一条，Claude 装了这个 Skill 后都会默认照做；你在对话里再强调一遍效果更稳。

| # | 技巧 | Skill 里怎么做 |
|---|---|---|
| 1 | 用真实、高清的素材，不用商店宣传图，不让它凭记忆画 logo | 第 1 步先要真 logo、真截图；缺了先问你要 |
| 2 | 先出带编号的分镜，你点头再动手 | 出一张分镜板（`render.mjs board`），没点头不做成片 |
| 3 | 每个镜头从上一个镜头变出来，不用交叉溶解 | 分镜每格写清“哪个形状变成哪个形状”；拿不准就给你 2–3 个变法挑 |
| 4 | 动作放在画面正中 | `layout_check.py` 逐帧量主体离中心多远 |
| 5 | 画面一直有东西在动 | 整个画面全程慢推，没有静止帧 |
| 6 | 先做画面，最后做声音 | 画面定稿才混音，节拍从渲染时写的节拍表读 |
| 7 | 加景深，有电影感 | 3D 模板按离焦距离自动虚化背景 |
| 8 | 结尾只留 App 图标，不加口号 | 结尾只留图标和字标 |
| 9 | 字逐词往上滑到位，不弹跳、不逐字淡入 | `slideUp()`，中文自动分词 |
| 10 | 让 Claude 写 Suno 配乐提示词，最响的一下卡在图标出现 | 它按片长和节拍写提示词；你生成后交回，`mix.py` 自动对齐最重一拍、裁长度、调响度 |
| 11 | 3D 场景只开一盏灯 | Blender 棚拍脚本只放一盏灯、背景全黑 |
| 12 | 拿真东西对照动画，一处一处改 | 同角度渲染和实物照片并排对照；脚本查穿模、合盖接缝、转速 |

再补几条做案例片时踩过的坑：配乐和音效两样都要有（只有音效会“没感觉”）；全片只用一种嗖声会乏味；界面里别出现陌生人的头像和作品；3D 接实拍时别从纯黑一刀切进亮画面。都写在 [`references/`](references/) 里。

## 自己动手安装

需要：Node.js 20+、Python 3.9+、ffmpeg、Google Chrome（或 Chromium）。Blender 可选。

```bash
git clone https://github.com/risingjerry/motion-skill.git ~/.claude/skills/motion
cd ~/.claude/skills/motion
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py
```

应该看到每一项前面是 `OK`，最后一行是“必需的都齐了，可以开始。”；缺什么它会写出怎么装。
Windows 用 `%USERPROFILE%\.claude\skills\motion`，把 `.venv/bin/` 换成 `.venv\Scripts\`。

只想在某一个项目里用：把上面的 `~/.claude/skills/motion` 换成 `你的项目/.claude/skills/motion`。

<details>
<summary>也可以用 <code>npx skills</code> 安装</summary>

```bash
npx skills add risingjerry/motion-skill -g -a claude-code
cd ~/.claude/skills/motion
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

`-a claude-code` 会装到 `~/.claude/skills/motion`；不加 `-a` 时它会问你装给哪些 Agent。这个 Skill 要跑自带的脚本，所以装好后仍要在安装目录里执行 `npm install` 和 `pip install`。

</details>

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

终端里会打印布局检查（`LAYOUT_CHECK GREEN`）和混音报告（配乐最重的一拍落在第几秒、响度多少）。加 `--scale 1` 可以用 1080p 快速试跑。

![分镜板：6 个编号镜头，每格写着时间、画面、动作、怎么变成下一镜](docs/storyboard.png)

## 在 Claude Code、Codex 等 Agent 里用

装到 `~/.claude/skills/motion` 后，Claude Code 会自动发现这个 Skill。更多说法：

- “用 motion 给我的记账 App 做一条 12 秒的发布视频，logo 在 `assets/logo.svg`，截图在 `assets/screens/`。”
- “我有耳机充电盒的 glb 模型，做一条 Blender 单灯棚拍的开盖镜头，先给我分镜。”
- “给我们的 logo 做一段 5 秒的开场动画，再用真截图做一段 20 秒的同步功能讲解动效。”
- “画面定了。给这条片子写一段 Suno 配乐提示词，最响的那一下要落在图标出现的那一刻。”
- “我把音效和配乐放进 sound 文件夹了，按节拍放到最准的时间点上。”

Codex、Cursor 等其他 Agent 读仓库根目录的 [`AGENTS.md`](AGENTS.md)。

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

检查类脚本最后一行打印 `... GREEN` 或 `... RED`，退出码 0 = 绿、1 = 红、2 = 用法错误。

## 限制

- **速度**：HTML 动效 10 秒 4K 约 1–3 分钟；Blender EEVEE 4K 每帧几秒到十几秒，一条 15 秒的 3D 镜头可能要一小时。同时只跑一个 4K 任务，否则容易卡死电脑。
- **剪影的自动抠像只在 macOS 14+ 上能用**（系统自带的 Vision）。其他系统用 rembg、MediaPipe 或剪辑软件导出黑白蒙版，脚本照样能画剪影。
- **Blender 是可选的**：没有它，第 1、2 层照常用。
- **声音没有“听”过**：脚本能对齐时间、测响度，但好不好听要人戴耳机听。
- **不附带任何品牌素材、3D 模型、音效库或音乐**。示例只用自己画的 SVG 和代码合成的声音；你的素材需要你自己有授权。
- 作者在 macOS 上实测；CI 在 Ubuntu 上跑测试和示例。

## 常见问题

### motion-skill 是什么？
一个免费开源的 Claude Skill（MIT 许可），也就是大家说的“Claude 动效 Skill”。装进 Claude Code 后，Claude 会按一套固定流程给你的产品做动效短片：备真素材 → 出编号分镜 → 写成 HTML 或 Blender 场景 → 逐帧渲染成 4K → 自己抽帧检查 → 配乐和音效对齐节拍。

### 免费吗？要账号或 API Key 吗？
Skill 本身免费，不需要额外的账号或密钥，所有脚本都在你电脑上跑。你需要的只是能用 Claude Code（它按你的 Claude 订阅或额度计费）。音效库、Suno 这类服务是你自己选的，用不用、花不花钱由你定。

### 视频里的 Apple Music、AirPods、抖音案例片在仓库里吗？
不在。那几条用了品牌的 logo、模型和界面，没有授权放进公开仓库。仓库里放的是同样做法的示例（虚构的 Tallybird），以及做那几条时总结的全部规矩和检查脚本。

### 能和 AI 生成的图片、视频一起用吗？
能。Skill 默认不调用任何生图、生视频模型，但你自己生成的图或视频放进素材文件夹，Claude 会把它们当素材用。

### 用哪个 Claude 模型？
Claude Code 里能用的模型都行。越新、越强的模型，写出来的动画越细，自查也越仔细。

### 不用 AI 生成视频，怎么做产品宣传片和动效？
把动画写成代码。这里每一帧是一个 HTML 页面（或 Blender 场景），由时间 `t` 算出来；无头浏览器逐帧截图，ffmpeg 编成 4K 视频。“这里慢一点”只是改一个数字再渲一遍。

### Claude Code 能做视频吗？
能，装上这个 Skill 就行。Claude 写动画页面、用自带脚本渲染、自己逐帧检查、再混好声音；你提供真素材、点头分镜。

### 需要会写代码、会用 Blender 吗？
不需要。代码由 Claude 写，Blender 在后台运行，你不用打开它。你要做的是提供真素材、看分镜、提意见。

### 能做多长的片子？
适合短片：发布片、宣传片、logo 开场、产品镜头、讲解片段；这套规矩是在 8–20 秒的片子上调出来的。更长也能渲染，但“每一镜都从上一镜变出来”的做法更适合短片。

### 为什么一定要先出分镜？
分镜阶段改一句话就是改一个镜头，渲染之后再改要重来。编号让你能精确地说“3 变 4 太快”。

### 怎么让配乐的高潮正好落在画面关键时刻？
`mix.py` 会自动找配乐里最重的一拍（或你手动写秒数），把整首配乐平移到让它落在你指定的节拍上。只平移，不变速、不变调。

### 可以用别人品牌的 logo 做吗？
只给你拥有或获准使用的品牌做。练习作品不要冒充官方、不要拿去投放。

### 在 Windows、Linux 上能用吗？
HTML 渲染、检查脚本、声音脚本、Blender 部分都是跨平台写的，CI 在 Linux 上跑；作者只在 macOS 上实测过。剪影的自动抠像只支持 macOS。

## 数据和隐私

所有脚本都在本机运行，不联网（`npm install` / `pip install` 装依赖时除外）、不上传任何文件、不需要账号或密钥。
渲染用的是本机的无头浏览器和一个临时的空白浏览器配置，不会读你日常浏览器的数据。

## 卸载

```bash
rm -rf ~/.claude/skills/motion
```

## 提问、反馈和安全

遇到 bug 或有想法，在 [Issues](https://github.com/risingjerry/motion-skill/issues) 里提，附上 `python3 scripts/doctor.py --json` 的输出和出错的命令。见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## 致谢

思路受 Rourke（GenHQ）的视频启发：https://www.youtube.com/watch?v=cDb-wPq0Iyk 。本项目与 Rourke、GenHQ 没有任何合作或官方关系，仓库里的文字和代码都是独立编写的。

## 许可

[MIT](LICENSE)。示例里的 Tallybird 名字和 logo 是虚构的，随仓库一起按 MIT 使用；`synth.py` 生成的声音同样可以商用。

---

如果它帮你做出了片子，点个 ⭐ 能让更多人找到它。

[![Star History Chart](https://api.star-history.com/svg?repos=risingjerry/motion-skill&type=Date)](https://star-history.com/#risingjerry/motion-skill&Date)
