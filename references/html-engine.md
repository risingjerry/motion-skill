# HTML 动画页面和出片

## 页面约定

渲染脚本只认一件事：页面上有 `window.MOTION`，并且画面完全由时间决定。

```js
window.MOTION = {
  duration: 10,            // 总长（秒），必填
  fps: 30,                 // 建议帧率，可被 --fps 覆盖
  size: [1920, 1080],      // 页面逻辑尺寸（CSS 像素）；--scale 2 时输出 3840x2160
  beats: { flip: 1.4 },    // 关键时刻，声音按名字对齐；出片时写进 <片名>.beats.json
  seek(t) { /* 把所有元素摆到 t 秒该在的位置；可以返回 Promise */ },
  ready: Promise.resolve() // 可选：图片、字体、数据都准备好后 resolve
};
```

用 `templates/motion-kit.js` 的 `MotionKit.define({ duration, fps, size, beats, draw, stage })` 会自动建好这个对象。

**为什么必须“由时间决定”：** 渲染时每帧调用一次 `seek(t)` 再截图，跟真实时间无关。
所以不要用 `setTimeout`、`setInterval`、`requestAnimationFrame` 自己推进动画，也不要依赖 CSS transition。
CSS `@keyframes` 动画和 Web Animations 可以用：渲染脚本每帧会把它们暂停并拨到 t 秒。

## motion-kit.js 里有什么

| 函数 | 用途 |
|---|---|
| `track([[t, 值, 缓动], ...])` | 关键帧轨道，返回 `f(t)`；值可以是数字或数组 |
| `span(t, a, b)` | t 在 a–b 之间走了百分之几（0–1） |
| `ease.outCubic` 等 | 缓动曲线 |
| `reveal(el, t, 开始, 选项)` | 文字逐字从模糊浮上来变清楚；`out` 给出消失时间 |
| `mixColor(a, b, p)` | 两个颜色按比例混合 |

## 在浏览器里看

直接双击打开 HTML：
- `?play` 循环播放（看节奏用，可能掉帧，成片不会）
- `?at=3.2` 停在 3.2 秒

## 出片命令

```bash
node scripts/render.mjs info  page.html                       # 看时长、节拍、输出尺寸
node scripts/render.mjs still page.html out/ --times 1,2.5,4  # 抽静帧（PNG，按 --scale 的分辨率）
node scripts/render.mjs video page.html 片名-4K.mp4 --scale 2  # 4K 成片，另写 片名-4K.beats.json
node scripts/render.mjs probe page.html probe.json --step 0.1 # 记录 [data-qa] 元素每一刻的位置
node scripts/render.mjs board shots.json board.png            # 分镜板
```

- 编码：H.264、yuv420p、BT.709 色彩标记、crf 14。要更小的文件加 `--crf 18`。
- `--start` / `--end` 只渲一段，用来快速看某个转场。
- 浏览器：先找 `--chrome` / `CHROME_PATH`，再找本机 Google Chrome，最后用 Playwright 自带的 Chromium（`npx playwright-core install chromium`）。
- WebGL 页面加 `--gpu`。CSS 3D 模板不需要。
- `--scale` 不能小于 1（Chrome 截图的限制）；要快速试跑用 `--scale 1`（1080p）。

## 给检查脚本标记元素

在 HTML 上加属性：

```html
<div id="hero" data-qa="hero">…</div>                          <!-- 主体 -->
<div id="title" data-qa="title" data-qa-kind="text">…</div>    <!-- 文字 -->
```

`probe` 只记录看得见的元素（`display:none`、`visibility:hidden`、整体透明度 < 0.05 的都跳过）。
`reveal()` 在文字完全没出现时会自动把容器设成 `visibility:hidden`。

```bash
python3 scripts/layout_check.py probe probe.json --center hero
```

## 速度参考

10 秒、30 fps、3840x2160 的简单页面，大约 2–4 分钟（主要花在截图和 PNG 编码上）。
页面越复杂（大量模糊滤镜、阴影）越慢。一台电脑同时只跑一个 4K 渲染。
