// 粗剪版时间轴 <-> 原片时间轴 互转
// 用法: node map_time.mjs <分析目录> <时间1> <时间2> ...
import fs from 'node:fs/promises';
import path from 'node:path';

const DIR = process.argv[2];
const REV = process.argv.includes('--rev');
const times = process.argv.slice(3).filter((a) => a !== '--rev').map(Number);
const plan = JSON.parse(await fs.readFile(path.join(DIR, 'cut_plan.json'), 'utf8'));

// 累积出每段保留区间在成片里的起止
let acc = 0;
const map = plan.keeps.map((k) => {
  const rec = { cutStart: acc, cutEnd: acc + (k.end - k.start), origStart: k.start, origEnd: k.end };
  acc += k.end - k.start;
  return rec;
});

const toOrig = (t) => {
  for (const m of map) {
    if (t >= m.cutStart && t <= m.cutEnd) return m.origStart + (t - m.cutStart);
  }
  return null;
};
const toCut = (t) => {
  for (const m of map) {
    if (t >= m.origStart && t <= m.origEnd) return m.cutStart + (t - m.origStart);
  }
  return null;
};

console.log(`成片总长 ${acc.toFixed(2)} 秒, 共 ${map.length} 段`);
console.log('');
console.log(REV ? '原片时间  ->  成片时间' : '成片时间  ->  原片时间');
for (const t of times) {
  const o = REV ? toCut(t) : toOrig(t);
  const mm = (s) => `${Math.floor(s / 60)}:${(s % 60).toFixed(2).padStart(5, '0')}`;
  console.log(`  ${mm(t)} (${t.toFixed(2)}s)  ->  ${o === null ? (REV ? '这一段被删掉了' : '落在被删除的区间里') : mm(o) + ' (' + o.toFixed(2) + 's)'}`);
}

if (!REV) {
  console.log('');
  console.log('成片这几个位置对应的原片片段:');
  for (const t of times) {
    const o = toOrig(t);
    if (o === null) continue;
    const seg = map.find((m) => o >= m.origStart && o <= m.origEnd);
    console.log(`  成片 ${t.toFixed(2)}s -> 原片 ${seg.origStart.toFixed(2)}-${seg.origEnd.toFixed(2)} 区间内 (该段起点 ${seg.origStart.toFixed(2)}s)`);
  }
}
