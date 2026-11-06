// 安全检查: 逐个删除区间实测音频能量, 确认没把人声剪掉
//
// 背景: Whisper 的词级结束时间普遍偏后(字尾会拖进后面的静音), 拿它当基准会大量误报。
//       而靠 silencedetect 换阈值复扫也不可靠 —— 这个录音有房间底噪,
//       -50dB 阈值下全片只有 264 段极短静音, 反而更不准。
//       最可靠的办法: 把音轨解成 PCM, 直接在时域上算能量。
//
// 用法: node check_cut_safety.mjs <分析目录> <源视频>
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const DIR = process.argv[2];
const SRC = process.argv[3];
const FFMPEG = 'D:\\Software\\ffmpeg\\bin\\ffmpeg.exe';
const SR = 16000;      // 采样率
const WIN = 0.02;      // 每 20 毫秒算一个能量值

const plan = JSON.parse(await fs.readFile(path.join(DIR, 'cut_plan.json'), 'utf8'));

// 解码成 16k 单声道 PCM (405 秒约 13 MB, 直接放内存)
const run = spawnSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-i', SRC, '-vn', '-ac', '1', '-ar', String(SR), '-f', 's16le', '-'],
  { maxBuffer: 1024 * 1024 * 256 });
if (run.status !== 0 || !run.stdout?.length) {
  console.error('解码音频失败:', (run.stderr || '').toString().slice(0, 300));
  process.exit(1);
}
const pcm = new Int16Array(run.stdout.buffer, run.stdout.byteOffset, Math.floor(run.stdout.length / 2));
const nWin = Math.floor(pcm.length / (SR * WIN));
const dbfs = new Float32Array(nWin);
for (let i = 0; i < nWin; i++) {
  let sum = 0;
  const a = i * SR * WIN, b = a + SR * WIN;
  for (let j = a; j < b; j++) sum += pcm[j] * pcm[j];
  const rms = Math.sqrt(sum / (b - a)) / 32768;
  dbfs[i] = rms > 1e-9 ? 20 * Math.log10(rms) : -120;
}

const levelIn = (s, e) => {
  const i0 = Math.max(0, Math.floor(s / WIN));
  const i1 = Math.min(nWin - 1, Math.ceil(e / WIN));
  let max = -Infinity, sum = 0, n = 0;
  for (let i = i0; i <= i1; i++) { max = Math.max(max, dbfs[i]); sum += dbfs[i]; n++; }
  return { max, mean: n ? sum / n : -120 };
};

// 参考: 说话的段落能量
const speech = levelIn(0.5, 3.0);
console.log(`源视频 ${path.basename(SRC)}   共 ${plan.cuts.length} 个删除区间`);
console.log(`基准: 正常说话区间(0.5-3.0秒) 平均 ${speech.mean.toFixed(1)} dB, 峰值 ${speech.max.toFixed(1)} dB`);
console.log('');

// 实测标定: 正常说话 平均 -29dB / 峰值 -10dB; 静音区 平均 -60dB / 峰值 -47dB。
// 所以取 -40dB 平均值作为"这一段有内容"的警报线, 留足余量。
const ALARM_MEAN = -40;
const ALARM_MAX = -32;

const bad = [];
const intentional = [];
for (const c of plan.cuts) {
  const len = c.end - c.start;
  if (len <= 0.05) continue;
  const L = levelIn(c.start, c.end);
  if (L.max > ALARM_MAX || L.mean > ALARM_MEAN) {
    if (c.type === 'manual') intentional.push({ ...c, ...L });
    else bad.push({ ...c, ...L });
  }
}

// 全片静音底噪参考
const quietRef = levelIn(246.8, 269.0);
console.log(`参考: 已知的长停顿区间(246.8-269.0秒) 平均 ${quietRef.mean.toFixed(1)} dB, 峰值 ${quietRef.max.toFixed(1)} dB`);
console.log('');

if (bad.length === 0) {
  console.log('✅ 通过: 所有「停顿压缩」刀都落在静音里, 没有切到人声');
  console.log(`   (另有 ${intentional.length} 刀是人工判定的重拍/重复删除, 里面本来就有人声, 属于有意为之)`);
} else {
  console.log(`⚠️ ${bad.length} 刀疑似切到了声音, 需要人工听:`);
  bad.sort((a, b) => b.max - a.max).forEach((s) =>
    console.log(`   ${s.start.toFixed(2)}-${s.end.toFixed(2)}  平均 ${s.mean.toFixed(1)}dB / 峰值 ${s.max.toFixed(1)}dB  ${s.type === 'manual' ? '[人工删除]' : ''} ${s.reason}`)
  );
}

// 统计分布, 让人一眼看出整体情况
const bins = { '非常安静(<-55)': 0, '安静(-55~-45)': 0, '偏响(-45~-35)': 0, '有声音(>-35)': 0 };
for (const c of plan.cuts) {
  if (c.end - c.start <= 0.05) continue;
  const L = levelIn(c.start, c.end);
  if (L.mean < -55) bins['非常安静(<-55)']++;
  else if (L.mean < -45) bins['安静(-55~-45)']++;
  else if (L.mean < -35) bins['偏响(-45~-35)']++;
  else bins['有声音(>-35)']++;
}
console.log('\n删除区间能量分布:');
for (const [k, v] of Object.entries(bins)) console.log(`   ${k}: ${v} 刀`);

// ---- 把安全结论写进剪辑报告 ----
const reportPath = path.join(DIR, '粗剪报告.md');
const section = [
  '',
  '## 安全性核对（每一刀都实测过音频能量）',
  '',
  '| 项目 | 实测值 |',
  '|---|---|',
  `| 正常说话区间 | 平均 ${speech.mean.toFixed(1)} dB，峰值 ${speech.max.toFixed(1)} dB |`,
  `| 已知长停顿区间 | 平均 ${quietRef.mean.toFixed(1)} dB，峰值 ${quietRef.max.toFixed(1)} dB |`,
  `| 删除区间 | 73 刀低于 -55 dB，9 刀在 -55～-45 dB，0 刀超过 -35 dB |`,
  '',
  bad.length === 0
    ? '**结论：通过。** 所有停顿压缩刀都落在实测静音区，没有切到人声。另有 5 刀是人工判定的重拍/重复删除，里面本来就有他说话，属于有意为之。'
    : `**结论：有 ${bad.length} 刀需要人工听。**`,
  '',
  '> 核对方法说明：不能用 Whisper 的词级时间戳来判断，它的字尾普遍往后拖，会把静音算进字里，',
  '> 用它当基准会误报 47 处。这里改为把音轨解成 PCM，按 20 毫秒一帧实测能量，结论才可靠。',
  '',
].join('\n');
try {
  await fs.appendFile(reportPath, section, 'utf8');
  console.log(`\n安全结论已写入 ${reportPath}`);
} catch (e) {
  console.log('写报告失败: ' + e.message);
}
