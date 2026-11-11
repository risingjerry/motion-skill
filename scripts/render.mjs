#!/usr/bin/env node
// 把一个按时间驱动的 HTML 动画页逐帧截图，交给 ffmpeg 编成 mp4（默认 4K）。
// 页面约定见 references/html-engine.md：window.MOTION = { duration, fps?, size?, beats?, seek(t) }。
//
//   node scripts/render.mjs info  <page.html>
//   node scripts/render.mjs still <page.html> <输出目录> --times 0.5,1.2,3
//   node scripts/render.mjs video <page.html> <输出.mp4> [--fps 30] [--scale 2] [--start 0] [--end 结束秒]
//   node scripts/render.mjs probe <page.html> <输出.json> [--step 0.1] [--scale 2]
//   node scripts/render.mjs board <分镜.json> <输出.png>
//   node scripts/render.mjs doctor
//
// 通用参数：--scale 页面像素到输出像素的倍数（1920x1080 的页面 --scale 2 = 3840x2160）
//           --chrome 浏览器路径（也可用环境变量 CHROME_PATH）  --gpu 打开 GPU（WebGL 页面用）
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const HELP = `用法：
  node scripts/render.mjs info  <page.html>
  node scripts/render.mjs still <page.html> <输出目录> --times 0.5,1.2,3 [--scale 2]
  node scripts/render.mjs video <page.html> <输出.mp4> [--fps 30] [--scale 2] [--start 秒] [--end 秒] [--crf 14]
  node scripts/render.mjs probe <page.html> <输出.json> [--step 0.1] [--scale 2]
  node scripts/render.mjs board <分镜.json> <输出.png>
  node scripts/render.mjs doctor
通用参数：--scale N  --chrome 浏览器路径  --gpu  --quiet`;

function parseArgs(argv) {
  const pos = [];
  const opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) opt[key] = true;
      else { opt[key] = next; i++; }
    } else pos.push(a);
  }
  return { pos, opt };
}

function die(msg, code = 2) {
  console.error(msg);
  process.exit(code);
}

async function loadPlaywright() {
  try {
    return await import('playwright-core');
  } catch {
    die('找不到 playwright-core。请在仓库根目录先运行：npm install');
  }
}

// 找浏览器：--chrome / CHROME_PATH → 本机 Google Chrome → Playwright 自带的 Chromium
async function launchBrowser(opt) {
  const { chromium } = await loadPlaywright();
  const args = ['--hide-scrollbars', '--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'];
  if (opt.gpu) args.push('--enable-gpu', '--ignore-gpu-blocklist', '--enable-gpu-rasterization');
  const tries = [];
  const exe = opt.chrome || process.env.CHROME_PATH;
  if (exe) tries.push({ label: exe, o: { executablePath: exe } });
  tries.push({ label: '本机 Google Chrome', o: { channel: 'chrome' } });
  tries.push({ label: 'Playwright Chromium', o: {} });
  const errors = [];
  for (const t of tries) {
    try {
      const browser = await chromium.launch({ headless: true, args, ...t.o });
      return { browser, label: t.label };
    } catch (e) {
      errors.push(`- ${t.label}: ${String(e.message).split('\n')[0]}`);
    }
  }
  die('启动不了浏览器。任选一种：\n  1) 安装 Google Chrome\n  2) 运行 npx playwright-core install chromium\n  3) 用 --chrome 或环境变量 CHROME_PATH 指定 Chrome/Chromium 路径\n' + errors.join('\n'));
}

function toUrl(p) {
  if (/^https?:\/\//.test(p) || p.startsWith('file:')) return p;
  const abs = path.resolve(p);
  if (!fs.existsSync(abs)) die(`找不到页面：${p}`);
  return pathToFileURL(abs).href;
}

// 打开页面，等 MOTION 就绪，返回页面信息
async function openPage(browser, url, opt, sizeHint) {
  let scale = Number(opt.scale ?? 2);
  if (!(scale >= 1)) scale = 1; // Chrome 截图不支持小于 1 的缩放；要小图请缩小页面尺寸或事后缩放
  const [w, h] = sizeHint ?? [1920, 1080];
  const context = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: scale });
  const page = await context.newPage();
  const logs = [];
  page.on('pageerror', (e) => logs.push(`页面报错：${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') logs.push(`console.error：${m.text()}`); });
  await page.goto(url, { waitUntil: 'load' });
  const ok = await page.waitForFunction(() => window.MOTION && typeof window.MOTION.seek === 'function', null, { timeout: 15000 }).then(() => true, () => false);
  if (!ok) die(`页面没有提供 window.MOTION.seek。约定见 references/html-engine.md\n${logs.join('\n')}`);
  const info = await page.evaluate(async () => {
    const M = window.MOTION;
    if (M.ready && typeof M.ready.then === 'function') await M.ready;
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    await Promise.all([...document.images].map((im) => (im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; }))));
    return { duration: Number(M.duration), fps: M.fps ?? null, size: M.size ?? null, beats: M.beats ?? {} };
  });
  if (!(info.duration > 0)) die('MOTION.duration 必须是正数（秒）');
  // 页面声明的尺寸和当前视口不同 → 重新开
  if (info.size && (info.size[0] !== w || info.size[1] !== h) && !sizeHint) {
    await context.close();
    return openPage(browser, url, opt, info.size);
  }
  const cdp = await context.newCDPSession(page);
  return { page, context, cdp, info, scale, logs, width: w, height: h };
}

// 定格到 t 秒：调页面的 seek，再把 CSS/Web Animations 也对到同一时刻
async function seek(page, t) {
  await page.evaluate(async (tt) => {
    const r = window.MOTION.seek(tt);
    if (r && typeof r.then === 'function') await r;
    if (document.getAnimations) {
      for (const a of document.getAnimations()) { a.pause(); a.currentTime = tt * 1000; }
    }
    await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
  }, t);
}

// 截一帧。必须带 clip 并把 scale 设成像素倍数：不带 clip 时 Chrome 只按 1 倍输出（4K 会变成 1080p）
async function grab(s) {
  const clip = { x: 0, y: 0, width: s.width, height: s.height, scale: s.scale };
  const { data } = await s.cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true, captureBeyondViewport: false, fromSurface: true, clip });
  return Buffer.from(data, 'base64');
}

function ffmpegBin() { return process.env.FFMPEG || 'ffmpeg'; }

function startEncoder(out, fps, crf) {
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  const args = [
    '-hide_banner', '-loglevel', 'error', '-y',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
    '-c:v', 'libx264', '-crf', String(crf), '-tune', 'animation', '-preset', 'slow',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
    '-movflags', '+faststart', out,
  ];
  const p = spawn(ffmpegBin(), args, { stdio: ['pipe', 'inherit', 'inherit'] });
  p.on('error', () => die('找不到 ffmpeg。macOS：brew install ffmpeg；Windows：winget install ffmpeg；Linux：apt install ffmpeg'));
  p.stdin.on('error', (e) => die(`ffmpeg 中途退出：${e.message}`));
  const done = new Promise((res, rej) => p.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg 退出码 ${c}`)))));
  return { p, done };
}

function writeChunk(stream, buf) {
  return new Promise((res) => {
    if (stream.write(buf)) res();
    else stream.once('drain', res);
  });
}

async function cmdInfo(file, opt) {
  const { browser } = await launchBrowser(opt);
  try {
    const s = await openPage(browser, toUrl(file), opt);
    console.log(JSON.stringify({ ...s.info, output: [s.width * s.scale, s.height * s.scale] }, null, 2));
  } finally { await browser.close(); }
}

async function cmdStill(file, outDir, opt) {
  if (!opt.times) die('still 需要 --times，例如 --times 0.5,1.2,3');
  const times = String(opt.times).split(',').map(Number);
  fs.mkdirSync(outDir, { recursive: true });
  const { browser } = await launchBrowser(opt);
  try {
    const s = await openPage(browser, toUrl(file), opt);
    for (const t of times) {
      await seek(s.page, t);
      const name = path.join(outDir, `t${t.toFixed(2).padStart(6, '0')}.png`);
      fs.writeFileSync(name, await grab(s));
      if (!opt.quiet) console.log(name);
    }
    if (s.logs.length) console.error(s.logs.join('\n'));
  } finally { await browser.close(); }
}

async function cmdVideo(file, out, opt) {
  const { browser, label } = await launchBrowser(opt);
  try {
    const s = await openPage(browser, toUrl(file), opt);
    const fps = Number(opt.fps ?? s.info.fps ?? 30);
    const start = Number(opt.start ?? 0);
    const end = Number(opt.end ?? s.info.duration);
    const n = Math.round((end - start) * fps);
    const crf = Number(opt.crf ?? 14);
    const W = s.width * s.scale; const H = s.height * s.scale;
    if (!opt.quiet) console.error(`渲染 ${n} 帧，${W}x${H}，${fps} fps，浏览器：${label}`);
    const enc = startEncoder(out, fps, crf);
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await seek(s.page, start + i / fps);
      await writeChunk(enc.p.stdin, await grab(s));
      if (!opt.quiet && (i % 30 === 0 || i === n - 1)) {
        const el = (Date.now() - t0) / 1000;
        process.stderr.write(`\r  ${i + 1}/${n} 帧  已用 ${el.toFixed(0)}s  预计还要 ${((el / (i + 1)) * (n - i - 1)).toFixed(0)}s   `);
      }
    }
    enc.p.stdin.end();
    await enc.done;
    if (!opt.quiet) console.error(`\n完成：${out}`);
    if (s.logs.length) console.error(s.logs.join('\n'));
    const beatsFile = out.replace(/\.mp4$/i, '') + '.beats.json';
    fs.writeFileSync(beatsFile, JSON.stringify({ duration: end - start, fps, start, beats: s.info.beats }, null, 2));
  } finally { await browser.close(); }
}

// 记下每个时刻所有 [data-qa] 元素在输出画面里的外框，给 layout_check.py 用
async function cmdProbe(file, out, opt) {
  const { browser } = await launchBrowser(opt);
  try {
    const s = await openPage(browser, toUrl(file), opt);
    const step = Number(opt.step ?? 0.1);
    const frames = [];
    for (let t = 0; t <= s.info.duration + 1e-9; t += step) {
      const tt = Math.round(t * 1000) / 1000;
      await seek(s.page, tt);
      const items = await s.page.evaluate((k) => {
        const res = [];
        for (const el of document.querySelectorAll('[data-qa]')) {
          let op = 1; let vis = true;
          for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
            const cs = getComputedStyle(e);
            if (cs.display === 'none' || cs.visibility === 'hidden') { vis = false; break; }
            op *= Number(cs.opacity);
          }
          const r = el.getBoundingClientRect();
          if (!vis || op < 0.05 || r.width < 1 || r.height < 1) continue;
          res.push({ name: el.dataset.qa, kind: el.dataset.qaKind || 'subject', opacity: +op.toFixed(3), box: [r.left * k, r.top * k, r.right * k, r.bottom * k].map((v) => +v.toFixed(1)) });
        }
        return res;
      }, s.scale);
      frames.push({ t: tt, items });
    }
    fs.writeFileSync(out, JSON.stringify({ output: [s.width * s.scale, s.height * s.scale], step, frames }, null, 1));
    if (!opt.quiet) console.log(out);
  } finally { await browser.close(); }
}

function esc(s) { return String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

// 分镜板：每格一个编号镜头。画面来自 page 在 at 秒的截图，或 image 指定的图，都没有就留草图框
async function cmdBoard(specFile, out, opt) {
  const spec = JSON.parse(fs.readFileSync(specFile, 'utf8'));
  const base = path.dirname(path.resolve(specFile));
  const { browser } = await launchBrowser(opt);
  try {
    const pics = {};
    if (spec.page) {
      const s = await openPage(browser, toUrl(path.resolve(base, spec.page)), { ...opt, scale: opt.scale ?? 1 });
      for (const shot of spec.shots) {
        if (shot.image || shot.at === undefined) continue;
        await seek(s.page, Number(shot.at));
        pics[shot.id] = 'data:image/png;base64,' + (await grab(s)).toString('base64');
      }
      await s.context.close();
    }
    for (const shot of spec.shots) {
      if (shot.image) pics[shot.id] = 'data:image/png;base64,' + fs.readFileSync(path.resolve(base, shot.image)).toString('base64');
    }
    const cols = Number(spec.columns ?? 3);
    const cells = spec.shots.map((s) => `
      <div class="cell">
        <div class="pic">${pics[s.id] ? `<img src="${pics[s.id]}">` : `<div class="sketch">${esc(s.picture)}</div>`}<span class="badge">${esc(s.id)}</span></div>
        <div class="meta"><b>${esc(s.from)}–${esc(s.to)} 秒</b>${s.line ? ` · 字：「${esc(s.line)}」` : ''}</div>
        <div class="row"><i>画面</i>${esc(s.picture)}</div>
        <div class="row"><i>动作</i>${esc(s.move)}</div>
        <div class="row"><i>变成下一镜</i>${esc(s.into_next)}</div>
      </div>`).join('');
    const html = `<!doctype html><meta charset="utf-8"><style>
      body{margin:0;background:#f4f2ee;font:15px/1.5 -apple-system,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;color:#222;padding:28px}
      h1{font-size:22px;margin:0 0 4px} .sub{color:#666;margin-bottom:18px}
      .grid{display:grid;grid-template-columns:repeat(${cols},1fr);gap:18px}
      .cell{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.12)}
      .pic{position:relative;aspect-ratio:16/9;background:#111} .pic img{width:100%;height:100%;object-fit:cover;display:block}
      .sketch{color:#bbb;padding:18px;font-size:14px}
      .badge{position:absolute;left:10px;top:8px;background:#ff5a36;color:#fff;font-weight:700;border-radius:14px;min-width:28px;text-align:center;padding:2px 8px}
      .meta{padding:8px 12px 2px} .row{padding:2px 12px;color:#444} .row:last-child{padding-bottom:10px}
      .row i{font-style:normal;color:#999;margin-right:8px}
    </style><h1>${esc(spec.title ?? '分镜')}</h1><div class="sub">${esc(spec.note ?? '按编号提意见，例如“4 变 5 不顺”')}</div><div class="grid">${cells}</div>`;
    const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.setContent(html, { waitUntil: 'load' });
    await page.screenshot({ path: out, fullPage: true });
    if (!opt.quiet) console.log(out);
  } finally { await browser.close(); }
}

async function cmdDoctor(opt) {
  const { browser, label } = await launchBrowser(opt);
  const v = browser.version();
  await browser.close();
  console.log(JSON.stringify({ ok: true, browser: label, version: v }));
}

async function main() {
  const { pos, opt } = parseArgs(process.argv.slice(2));
  const [cmd, a, b] = pos;
  if (!cmd || opt.help || cmd === 'help') { console.log(HELP); return; }
  if (cmd === 'doctor') return cmdDoctor(opt);
  if (!a) die(HELP);
  if (cmd === 'info') return cmdInfo(a, opt);
  if (!b) die(HELP);
  if (cmd === 'still') return cmdStill(a, b, opt);
  if (cmd === 'video') return cmdVideo(a, b, opt);
  if (cmd === 'probe') return cmdProbe(a, b, opt);
  if (cmd === 'board') return cmdBoard(a, b, opt);
  die(`不认识的命令：${cmd}\n${HELP}`);
}

main().catch((e) => { console.error(e?.stack || e); process.exit(1); });
