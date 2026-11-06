// 粗剪规划: 读转写与停顿数据, 算出「保留区间」, 并生成剪辑报告
// 用法: node make_cut.mjs <视频目录> <原视频时长秒>
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const DIR = process.argv[2] || '.\\分析\\IMG_3922';
const DURATION = parseFloat(process.argv[3] || '405.438');
const SRC_VIDEO = process.argv[4] || null;
const FFMPEG = 'D:\\Software\\ffmpeg\\bin\\ffmpeg.exe';
const SR = 16000;
const WIN = 0.02;
const QUIET_DB = -45;   // 低于这个电平算静音
const MIN_PIECE = 0.12; // 切开后小于这个长度的碎片直接丢掉

const transcript = JSON.parse(await fs.readFile(path.join(DIR, 'transcript.json'), 'utf8'));
const silences = JSON.parse(await fs.readFile(path.join(DIR, 'silences.json'), 'utf8'));

// ---- 停顿处理策略: 长空白按目标时长截短, 短停保留原样 ----
const SILENCE_RULES = [
  { max: 0.45, keep: null },  // 不到 0.45 秒的, 不动
  { max: 1.2,  keep: 0.35 },
  { max: 4.0,  keep: 0.5 },
  { max: Infinity, keep: 0.7 },
];

// ---- 人工判定的删除区间(重拍、说错、重复), 由转写逐词时间戳定位 ----
const MANUAL = [
  {
    start: 98.25, end: 103.58,
    reason: '明显停顿(1:22): "我的课就" 之后拖了 5.4 秒。中间夹着几声杂音, 静音被切成了两段, 所以上一版没剪干净。这次整段拿掉',
    quote: '我的课就 ……5.4秒…… 从原本的初中培优课',
  },
  {
    start: 209.76, end: 213.28,
    reason: '重复(2:11): 第一遍说到"有多少高中是学生上学第一"就停住重说, 删掉第一处, 保留第二遍完整的问句',
    quote: '有多少高中是学生上学第一 ‖(停顿)‖ 是学生上学第1学期',
  },
  {
    start: 324.10, end: 325.45,
    reason: '突兀片段(3:04): 上一版删"我会顺着"时, 在 325.1 秒留下 0.4 秒的残片',
    quote: '(半句"我会顺着"的残音)',
  },
  {
    start: 395.04, end: 395.90,
    reason: '重复(3:30): 原片是"你可以点·点·赞收藏", "点"说了两遍, 删掉第二遍, 让"点"直接接"赞"',
    quote: '你可以点点赞收藏这个视频',
  },
  {
    start: 196.85, end: 208.55,
    reason: '重拍: 先说"有多少学校是"没说完就改口, 后面"重新来"是明确的重录标记。第二次重说了完整版, 删掉第一次',
    quote: '有多少学校是 / 学生录取完之后就来学校… / 重新来',
  },
  {
    start: 222.48, end: 224.60,
    reason: '口吃重复: "甚至甚至又更早", 紧接的重说已包含这个意思',
    quote: '甚至甚至又更早',
  },
  {
    start: 277.40, end: 283.00,
    reason: '同义重复: 前半句已说"有前两个视频被下架了", 这句又重说一遍',
    quote: '因为我有我之前已经有两个相关这个话题被下架了',
  },
  {
    start: 339.24, end: 345.45,
    reason: '重拍: 说到一半卡住, 自己说了"重新来", 下一句才是正式版本',
    quote: '我得找到我的犀利的观点和我语言表达的……重新来',
  },
];

const fmt = (s) => {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toFixed(1).padStart(4, '0')}`;
};

// ---- 音频能量表: 用来给每一刀做体检 ----
// 光靠 ffmpeg 的 silencedetect 不够 —— 它偶尔会把夹在两段静音中间的一句短话
// 一起当成静音报出来(实测把"其实"和"谢谢大家"都吞掉了)。
// 所以这里自己解 PCM 算能量, 每一刀都必须落在真正的安静区里。
let PCM = null;
let DB = null;
if (SRC_VIDEO) {
  const r = spawnSync(
    FFMPEG,
    ['-hide_banner', '-loglevel', 'error', '-i', SRC_VIDEO, '-vn', '-ac', '1', '-ar', String(SR), '-f', 's16le', '-'],
    { maxBuffer: 1024 * 1024 * 256 }
  );
  if (r.stdout && r.stdout.length) {
    PCM = new Int16Array(r.stdout.buffer, r.stdout.byteOffset, Math.floor(r.stdout.length / 2));
    const n = Math.floor(PCM.length / (SR * WIN));
    DB = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      let sum = 0;
      const a = i * SR * WIN, b = a + SR * WIN;
      for (let j = a; j < b; j++) sum += PCM[j] * PCM[j];
      const rms = Math.sqrt(sum / (b - a)) / 32768;
      DB[i] = rms > 1e-9 ? 20 * Math.log10(rms) : -120;
    }
    console.log(`已载入音频能量表: ${n} 帧 (每帧 ${WIN * 1000} 毫秒)`);
  }
}

const isQuietAt = (t) => {
  if (!DB) return true;
  const i = Math.floor(t / WIN);
  return i >= 0 && i < DB.length && DB[i] < QUIET_DB;
};

/**
 * 把一刀裁成"只包含真正安静的部分"。
 * 返回若干段安静子区间; 如果整刀都不安静就返回空数组。
 */
function trimToQuiet(start, end) {
  if (!DB) return [[start, end]];
  const i0 = Math.max(0, Math.floor(start / WIN));
  const i1 = Math.min(DB.length - 1, Math.ceil(end / WIN));
  const pieces = [];
  let runStart = null;
  for (let i = i0; i <= i1; i++) {
    if (DB[i] < QUIET_DB) {
      if (runStart === null) runStart = i;
    } else if (runStart !== null) {
      pieces.push([runStart * WIN, i * WIN]);
      runStart = null;
    }
  }
  if (runStart !== null) pieces.push([runStart * WIN, (i1 + 1) * WIN]);

  // 把被极短杂音(小于 0.12 秒)打断的安静段接回去
  const merged = [];
  for (const p of pieces) {
    const last = merged[merged.length - 1];
    if (last && p[0] - last[1] < MIN_PIECE) last[1] = p[1];
    else merged.push([...p]);
  }
  return merged.filter((p) => p[1] - p[0] >= MIN_PIECE).map(([a, b]) => [Math.max(a, start), Math.min(b, end)]);
}

// ---- 1. 生成删除区间 ----
const cuts = [];
let silenceSaved = 0;

// 先把被「小杂音」隔断的静音合并回一个停顿。
// 不合并的话, 一个 5 秒的长停顿会被当成两三个短停顿分别处理,
// 每个都各自留 0.35 秒余量, 结果就是「剪了但还是很拖」——上一版 1:22 的问题就出在这。
const raw = silences.filter((s) => s.dur && s.end != null).sort((a, b) => a.start - b.start);
// 只把被极短杂音(0.25 秒以内)打断的静音接起来。
// 千万别放大 —— 0.5 秒已经够说一个完整的词, 会把夹在中间的短句一起吞掉。
const MERGE_GAP = 0.25;
const merged_sil = [];
for (const s of raw) {
  const last = merged_sil[merged_sil.length - 1];
  if (last && s.start - last.end < MERGE_GAP) {
    last.end = Math.max(last.end, s.end);
    last.dur = last.end - last.start;
  } else {
    merged_sil.push({ start: s.start, end: s.end, dur: s.dur });
  }
}

for (const s of merged_sil) {
  const rule = SILENCE_RULES.find((r) => s.dur < r.max);
  if (!rule || rule.keep === null) continue;
  const keepHalf = rule.keep / 2;
  const cs = +(s.start + keepHalf).toFixed(3);
  const ce = +(s.end - keepHalf).toFixed(3);
  if (ce - cs <= 0.05) continue;
  // 体检: 这一刀必须整个落在真正安静的区域里, 否则裁成只包含安静部分的几小刀
  for (const [as, ae] of trimToQuiet(cs, ce)) {
    const a = +as.toFixed(3), b = +ae.toFixed(3);
    if (b - a < MIN_PIECE) continue;
    cuts.push({ start: a, end: b, reason: `停顿 ${s.dur.toFixed(2)} 秒 → 保留 ${rule.keep} 秒`, type: 'silence' });
    silenceSaved += b - a;
  }
}

const manualSaved = MANUAL.reduce((a, m) => a + (m.end - m.start), 0);
for (const m of MANUAL) cuts.push({ ...m, type: 'manual' });

cuts.sort((a, b) => a.start - b.start);

// ---- 2. 合并重叠 ----
const merged = [];
for (const c of cuts) {
  const last = merged[merged.length - 1];
  if (last && c.start <= last.end) {
    last.end = Math.max(last.end, c.end);
    if (!last.reasons) last.reasons = [last.reason];
    last.reasons.push(c.reason);
    // 只要这一段里含人工判定, 整段就算人工删除(里面的停顿修剪也是有意为之)
    if (c.type === 'manual') last.type = 'manual';
  } else {
    merged.push({ ...c, type: c.type || 'silence' });
  }
}

// ---- 3. 取补集 = 保留区间 ----
const keeps = [];
let cursor = 0;
for (const c of merged) {
  const s = Math.max(0, c.start);
  if (s - cursor > 0.08) keeps.push({ start: +cursor.toFixed(3), end: +s.toFixed(3) });
  cursor = Math.max(cursor, c.end);
}
if (DURATION - cursor > 0.08) keeps.push({ start: +cursor.toFixed(3), end: +DURATION.toFixed(3) });

const totalKeep = keeps.reduce((a, k) => a + (k.end - k.start), 0);
const totalCut = DURATION - totalKeep;

// ---- 4. 报告 ----
const lines = [];
lines.push('# 粗剪方案报告');
lines.push('');
lines.push(`原片时长：**${fmt(DURATION)}**（${DURATION.toFixed(1)} 秒）`);
lines.push(`粗剪后时长：**${fmt(totalKeep)}**（${totalKeep.toFixed(1)} 秒）`);
lines.push(`共删除：**${totalCut.toFixed(1)} 秒**，占原片 **${((totalCut / DURATION) * 100).toFixed(0)}%**`);
lines.push('');
lines.push('## 两类删除');
lines.push('');
lines.push(`- **停顿压缩**：删除 ${(silenceSaved / totalCut * 100).toFixed(0)}%（原片停顿共 ${silences.filter((s) => s.dur).reduce((a, s) => a + s.dur, 0).toFixed(0)} 秒，是全片最大的一块赘肉）`);
lines.push(`- **重拍与重复**：删除 ${(manualSaved / totalCut * 100).toFixed(0)}%，共 ${MANUAL.length} 处，逐条列在下面`);
lines.push('');
lines.push('## 重拍与重复清单（请重点核对）');
lines.push('');
lines.push('| 时间 | 内容 | 为什么删 |');
lines.push('|---|---|---|');
for (const m of MANUAL) {
  lines.push(`| ${fmt(m.start)}–${fmt(m.end)} | ${m.quote} | ${m.reason} |`);
}
lines.push('');
lines.push('## 最长的 10 处停顿');
lines.push('');
lines.push('| 时间 | 时长 | 处理 |');
lines.push('|---|---|---|');
silences
  .filter((s) => s.dur)
  .sort((a, b) => b.dur - a.dur)
  .slice(0, 10)
  .forEach((s) => {
    const rule = SILENCE_RULES.find((r) => s.dur < r.max);
    lines.push(`| ${fmt(s.start)}–${fmt(s.end)} | ${s.dur.toFixed(1)} 秒 | 保留 ${rule.keep} 秒 |`);
  });
lines.push('');
lines.push(`## 保留区间（共 ${keeps.length} 段）`);
lines.push('');
lines.push('```');
keeps.forEach((k, i) => lines.push(`${String(i + 1).padStart(3)}  ${k.start.toFixed(3)} -> ${k.end.toFixed(3)}   (${(k.end - k.start).toFixed(2)} 秒)`));
lines.push('```');

await fs.writeFile(path.join(DIR, 'cut_plan.json'), JSON.stringify({ duration: DURATION, keeps, cuts: merged, stats: { totalKeep, totalCut, silenceSaved, manualSaved } }, null, 2), 'utf8');
await fs.writeFile(path.join(DIR, '粗剪报告.md'), lines.join('\n'), 'utf8');

console.log(`原片 ${DURATION.toFixed(1)} 秒 -> 粗剪后 ${totalKeep.toFixed(1)} 秒 (删掉 ${totalCut.toFixed(1)} 秒, ${((totalCut / DURATION) * 100).toFixed(0)}%)`);
console.log(`保留区间 ${keeps.length} 段`);
console.log(`其中: 停顿压缩 ${silenceSaved.toFixed(1)} 秒, 重拍重复 ${manualSaved.toFixed(1)} 秒`);
console.log(`报告: ${path.join(DIR, '粗剪报告.md')}`);
