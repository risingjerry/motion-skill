// render.mjs 的端到端测试：需要能启动 Chrome/Chromium，否则跳过。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RENDER = path.join(ROOT, 'scripts', 'render.mjs');
const PAGE = path.join(ROOT, 'tests', 'fixtures', 'tiny.html');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'motion-ad-test-'));
const hasBrowser = spawnSync('node', [RENDER, 'doctor'], { encoding: 'utf8' }).status === 0;
const opts = { skip: hasBrowser ? false : '没有可用的 Chrome/Chromium' };

function run(...args) {
  return execFileSync('node', [RENDER, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

test('info 读到时长、节拍和输出尺寸', opts, () => {
  const info = JSON.parse(run('info', PAGE, '--scale', '2'));
  assert.equal(info.duration, 1);
  assert.deepEqual(info.beats, { go: 0, half: 0.5 });
  assert.deepEqual(info.output, [640, 360]);
});

test('still 按 --scale 输出对应分辨率的 PNG，画面随时间变化', opts, () => {
  const dir = path.join(tmp, 'stills');
  run('still', PAGE, dir, '--times', '0,0.9', '--scale', '2', '--quiet');
  const files = fs.readdirSync(dir).sort();
  assert.equal(files.length, 2);
  const a = fs.readFileSync(path.join(dir, files[0]));
  const b = fs.readFileSync(path.join(dir, files[1]));
  assert.equal(a.readUInt32BE(16), 640); // PNG IHDR 宽
  assert.equal(a.readUInt32BE(20), 360);
  assert.notDeepEqual(a, b);
});

test('video 按 --scale 出高分辨率 mp4（不是放大的低清），帧数对，并写节拍表', opts, () => {
  const out = path.join(tmp, 'v.mp4');
  run('video', PAGE, out, '--scale', '2', '--fps', '10', '--quiet');
  const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-count_frames', '-show_entries', 'stream=width,height,nb_read_frames,pix_fmt,color_space', '-of', 'json', out], { encoding: 'utf8' }));
  const s = probe.streams[0];
  assert.equal(s.width, 640);
  assert.equal(s.height, 360);
  assert.equal(Number(s.nb_read_frames), 10);
  assert.equal(s.pix_fmt, 'yuv420p');
  assert.equal(s.color_space, 'bt709');
  const beats = JSON.parse(fs.readFileSync(path.join(tmp, 'v.beats.json'), 'utf8'));
  assert.equal(beats.beats.half, 0.5);
});

test('probe 只记录看得见的元素，坐标按 scale 放大', opts, () => {
  const out = path.join(tmp, 'p.json');
  run('probe', PAGE, out, '--step', '0.5', '--scale', '2', '--quiet');
  const d = JSON.parse(fs.readFileSync(out, 'utf8'));
  assert.deepEqual(d.output, [640, 360]);
  assert.equal(d.frames.length, 3);
  assert.deepEqual(d.frames[0].items.map((i) => i.name), ['box']);
  assert.deepEqual(d.frames[1].items.map((i) => i.name).sort(), ['box', 'label']);
  const box = d.frames[2].items.find((i) => i.name === 'box').box;
  assert.deepEqual(box, [520, 120, 640, 240]);
});

test('board 出分镜板 PNG', opts, () => {
  const spec = path.join(tmp, 'shots.json');
  fs.writeFileSync(spec, JSON.stringify({ title: 't', page: PAGE, shots: [{ id: 1, from: 0, to: 1, at: 0.5, picture: 'p', move: 'm', into_next: 'n' }, { id: 2, from: 1, to: 2, picture: '草图', move: 'm', into_next: 'n' }] }));
  const out = path.join(tmp, 'board.png');
  run('board', spec, out, '--quiet');
  assert.ok(fs.statSync(out).size > 1000);
});

test('页面没有 MOTION 时给出明确报错', opts, () => {
  const bad = path.join(tmp, 'bad.html');
  fs.writeFileSync(bad, '<!doctype html><p>no motion</p>');
  const r = spawnSync('node', [RENDER, 'info', bad], { encoding: 'utf8' });
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /MOTION/);
});
