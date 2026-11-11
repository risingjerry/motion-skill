// motion-kit.js —— 模板和示例共用的小工具（无依赖）。
// 核心想法：画面只由时间 t 决定。draw(t) 把每个元素摆到 t 时刻该在的位置，
// 渲染脚本逐帧调用 MOTION.seek(t) 截图，所以预览和成片永远一致。
(function (root) {
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;

  // 常用缓动。动作要“快起、慢收、收得久一点”，默认用 outCubic / inOutCubic
  const ease = {
    linear: (p) => p,
    inCubic: (p) => p * p * p,
    outCubic: (p) => 1 - Math.pow(1 - p, 3),
    inOutCubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    outQuint: (p) => 1 - Math.pow(1 - p, 5),
    inOutSine: (p) => -(Math.cos(Math.PI * p) - 1) / 2,
    smooth: (p) => p * p * (3 - 2 * p),
  };

  // t 在 [a, b] 之间走到了百分之几（夹在 0..1）
  const span = (t, a, b) => clamp((t - a) / (b - a));

  // 把十六进制颜色混合：mixColor('#ff0000', '#0000ff', 0.5)
  function hex(c) {
    const s = c.replace('#', '');
    const v = s.length === 3 ? s.split('').map((x) => x + x).join('') : s;
    return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16));
  }
  function mixColor(a, b, p) {
    const A = hex(a), B = hex(b);
    return `rgb(${A.map((x, i) => Math.round(lerp(x, B[i], p))).join(',')})`;
  }

  // 关键帧轨道：track([[0, 0], [1.2, 100, 'outCubic'], [3, 40]])(t)
  // 每个关键帧 [时间, 值, 进入这一段用的缓动]；值可以是数字或等长数组
  function track(keys, defaultEase = 'inOutCubic') {
    return function (t) {
      if (t <= keys[0][0]) return keys[0][1];
      for (let i = 1; i < keys.length; i++) {
        const [t1, v1, e] = keys[i];
        const [t0, v0] = keys[i - 1];
        if (t <= t1) {
          const p = (ease[e || defaultEase] || ease.inOutCubic)(span(t, t0, t1));
          return Array.isArray(v0) ? v0.map((x, j) => lerp(x, v1[j], p)) : lerp(v0, v1, p);
        }
      }
      return keys[keys.length - 1][1];
    };
  }

  // 把文字拆成逐字/逐词的 span，配合 reveal 做“从模糊浮上来变清楚”
  function splitText(el, by = 'char') {
    if (el.dataset.split) return [...el.querySelectorAll('.mk-piece')];
    const text = el.textContent;
    const parts = by === 'word' ? text.split(/(\s+)/) : [...text];
    el.textContent = '';
    for (const part of parts) {
      const s = document.createElement('span');
      s.className = 'mk-piece';
      s.style.display = 'inline-block';
      s.style.whiteSpace = 'pre';
      s.textContent = part;
      el.appendChild(s);
    }
    el.dataset.split = by;
    return [...el.querySelectorAll('.mk-piece')];
  }

  // 文字出现：每一块晚 stagger 秒开始，dur 秒内从模糊、略低、透明变成清楚、到位、不透明。
  // out 给出消失开始时间（可选），消失是反过来走一遍但更快
  function reveal(el, t, start, { stagger = 0.04, dur = 0.6, rise = 18, blur = 12, out = null, outDur = 0.35, by = 'char' } = {}) {
    const pieces = splitText(el, by);
    let shown = 0;
    pieces.forEach((s, i) => {
      const t0 = start + stagger * i;
      let p = ease.outCubic(span(t, t0, t0 + dur));
      if (out !== null) p *= 1 - ease.inCubic(span(t, out + i * stagger * 0.5, out + i * stagger * 0.5 + outDur));
      s.style.opacity = p.toFixed(3);
      s.style.filter = p >= 0.999 ? 'none' : `blur(${((1 - p) * blur).toFixed(2)}px)`;
      s.style.transform = `translateY(${((1 - p) * rise).toFixed(2)}px)`;
      shown = Math.max(shown, p);
    });
    // 整行完全没出现时把容器也藏起来，这样 probe / layout_check 不会把看不见的字算进去
    el.style.visibility = shown > 0.001 ? 'visible' : 'hidden';
  }

  // 注册动画：define({ duration, fps, size, beats, draw })
  // 浏览器里直接打开时：?at=3.2 看某一刻；?play 循环播放；什么都不加停在第 0 秒
  function define(spec) {
    const M = {
      duration: spec.duration,
      fps: spec.fps || 30,
      size: spec.size || [1920, 1080],
      beats: spec.beats || {},
      seek(t) { return spec.draw(clamp(t, 0, spec.duration)); },
      ready: spec.ready || Promise.resolve(),
    };
    root.MOTION = M;
    // 在普通浏览器窗口里预览时，把固定尺寸的舞台缩放到窗口大小；渲染时视口正好等于 size，缩放为 1
    const stage = spec.stage && document.querySelector(spec.stage);
    if (stage) {
      const fit = () => {
        const k = Math.min(innerWidth / M.size[0], innerHeight / M.size[1]);
        stage.style.transformOrigin = '0 0';
        stage.style.transform = Math.abs(k - 1) < 1e-6 ? 'none' : `scale(${k})`;
      };
      fit();
      addEventListener('resize', fit);
    }
    const q = new URLSearchParams(location.search);
    const startPreview = () => {
      if (q.get('play') !== null) {
        const t0 = performance.now();
        const loop = () => { M.seek(((performance.now() - t0) / 1000) % M.duration); requestAnimationFrame(loop); };
        requestAnimationFrame(loop);
      } else {
        M.seek(Number(q.get('at') || 0));
      }
    };
    M.ready.then(startPreview);
    return M;
  }

  root.MotionKit = { clamp, lerp, ease, span, mixColor, track, splitText, reveal, define };
})(window);
