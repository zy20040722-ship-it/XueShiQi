// 按 cut_plan.json 渲染粗剪成片
// 用法: node render_cut.mjs <源视频> <cut_plan.json 所在目录> <输出文件>
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';

const SRC = process.argv[2];
const DIR = process.argv[3];
const OUT = process.argv[4];
const FFMPEG = process.argv[5] || 'D:\\Software\\ffmpeg\\bin\\ffmpeg.exe';

const plan = JSON.parse(await fs.readFile(path.join(DIR, 'cut_plan.json'), 'utf8'));
const keeps = plan.keeps.filter((k) => k.end - k.start > 0.1);

console.log(`保留 ${keeps.length} 段, 目标时长 ${keeps.reduce((a, k) => a + k.end - k.start, 0).toFixed(1)} 秒`);

// ---- 组装 filter_complex (写进文件, 避免命令行长度限制) ----
const inputs = [];
const chains = [];
keeps.forEach((k, i) => {
  const dur = +(k.end - k.start).toFixed(3);
  inputs.push(['-ss', k.start.toFixed(3), '-t', dur.toFixed(3), '-i', SRC]);
  chains.push(`[${i}:v]trim=start=0:end=${dur},setpts=PTS-STARTPTS[v${i}]`);
  // 每个片段首尾各加 15 毫秒淡入淡出。
  // 大部分刀落在静音里本来就没声音, 但像「删掉重说的半个字」这种刀是切在人声上的,
  // 不做淡入淡出会有一声"啪"的爆音。
  const FADE = 0.015;
  const fadeOutAt = Math.max(0, dur - FADE).toFixed(3);
  chains.push(
    `[${i}:a]atrim=start=0:end=${dur},asetpts=PTS-STARTPTS,` +
      `afade=t=in:st=0:d=${FADE},afade=t=out:st=${fadeOutAt}:d=${FADE}[a${i}]`
  );
});
const concatIn = keeps.map((_, i) => `[v${i}][a${i}]`).join('');
chains.push(`${concatIn}concat=n=${keeps.length}:v=1:a=1[outv][outa]`);

const filterPath = path.join(DIR, 'filter_complex.txt');
await fs.writeFile(filterPath, chains.join(';\n'), 'utf8');

const args = [
  '-hide_banner', '-y',
  ...inputs.flat(),
  '-filter_complex_script', filterPath,
  '-map', '[outv]', '-map', '[outa]',
  '-c:v', 'h264_nvenc',
  '-preset', 'p5',
  '-rc', 'vbr', '-cq', '21', '-b:v', '0',
  '-maxrate', '20M', '-bufsize', '30M',
  '-profile:v', 'high', '-pix_fmt', 'yuv420p',
  '-r', '60',
  '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
  '-movflags', '+faststart',
  OUT,
];

console.log('开始渲染...');
const t0 = Date.now();
const ff = spawn(FFMPEG, args, { stdio: ['ignore', 'pipe', 'pipe'] });
let tail = '';
ff.stderr.on('data', (d) => {
  tail += d.toString();
  if (tail.length > 4000) tail = tail.slice(-2000);
});
ff.on('close', (code) => {
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  if (code === 0) {
    console.log(`渲染完成, 用时 ${secs} 秒 -> ${OUT}`);
  } else {
    console.error(`渲染失败, 退出码 ${code}\n${tail}`);
    process.exit(1);
  }
});
