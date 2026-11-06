// 细看某几段音频的能量结构, 用来定位停顿/重复/异常
// 用法: node probe_audio.mjs <视频> <起始秒> <结束秒> [步长秒]
import { spawnSync } from 'node:child_process';

const SRC = process.argv[2];
const A = parseFloat(process.argv[3]);
const B = parseFloat(process.argv[4]);
const STEP = parseFloat(process.argv[5] || '0.05');
const FFMPEG = 'D:\\Software\\ffmpeg\\bin\\ffmpeg.exe';
const SR = 16000;

const run = spawnSync(
  FFMPEG,
  ['-hide_banner', '-loglevel', 'error', '-ss', String(A), '-t', String(B - A), '-i', SRC,
   '-vn', '-ac', '1', '-ar', String(SR), '-f', 's16le', '-'],
  { maxBuffer: 1024 * 1024 * 128 }
);
const pcm = new Int16Array(run.stdout.buffer, run.stdout.byteOffset, Math.floor(run.stdout.length / 2));
const win = Math.round(SR * STEP);
console.log(`区间 ${A}s - ${B}s, 每格 ${(STEP * 1000).toFixed(0)} 毫秒    ▁=静音 ▂▃▄▅▆▇█=越响`);
let line = '';
for (let i = 0; i * win < pcm.length; i++) {
  let sum = 0;
  const s = i * win, e = Math.min(s + win, pcm.length);
  for (let j = s; j < e; j++) sum += pcm[j] * pcm[j];
  const db = 20 * Math.log10(Math.max(1e-9, Math.sqrt(sum / (e - s)) / 32768));
  const marks = '▁▂▃▄▅▆▇█';
  const k = db < -55 ? 0 : db < -48 ? 1 : db < -42 ? 2 : db < -36 ? 3 : db < -30 ? 4 : db < -24 ? 5 : db < -18 ? 6 : 7;
  line += marks[k];
  if (line.length === 100) {
    console.log(`  ${(A + i * STEP - 99 * STEP).toFixed(2)}s  ${line}`);
    line = '';
  }
}
if (line) console.log(`  ${(A + (Math.floor(pcm.length / win) - line.length) * STEP).toFixed(2)}s  ${line}`);
