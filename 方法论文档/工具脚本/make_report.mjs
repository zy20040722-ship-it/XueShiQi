// 把采集到的作品数据整理成一份便于阅读的 Markdown 清单
import fs from 'node:fs/promises';
import path from 'node:path';

const ROOT = process.argv[2] || '.\\数据采集';
const works = JSON.parse(await fs.readFile(path.join(ROOT, 'works.json'), 'utf8'));
let account = null;
try {
  account = JSON.parse(await fs.readFile(path.join(ROOT, 'account.json'), 'utf8'));
} catch {
  account = null;
}

const ranked = [...works].sort((a, b) => b.digg - a.digg);
const fmt = (n) => (n >= 10000 ? (n / 10000).toFixed(1) + '万' : String(n));
const mmss = (s) => (s ? Math.floor(s / 60) + '分' + String(Math.round(s % 60)).padStart(2, '0') + '秒' : '-');

const totalDigg = works.reduce((a, b) => a + b.digg, 0);
const avgDigg = Math.round(totalDigg / works.length);
const durations = works.map((w) => w.duration_sec).filter(Boolean).sort((a, b) => a - b);
const medianDur = durations[Math.floor(durations.length / 2)];

const lines = [];
lines.push('# 薛世奇说物理 — 作品数据清单');
lines.push('');
lines.push(`采集时间：${new Date().toISOString().slice(0, 16).replace('T', ' ')}`);
lines.push('');
lines.push('## 账号概况');
lines.push('');
lines.push(`- 昵称：${account?.nickname || '薛世奇说物理'}`);
lines.push(`- 抖音号：${account?.unique_id || '87939827220'}`);
lines.push(`- 粉丝：${fmt(account?.follower_count || 0)}　总获赞：${fmt(account?.total_favorited || 0)}`);
lines.push(`- 平台标注作品总数：${account?.aweme_count || 30}`);
lines.push(`- 本次抓到公开作品：${works.length} 条（网页端仅暴露这些，其余需登录作者后台才能看到）`);
lines.push('');
lines.push('## 规律速览');
lines.push('');
lines.push(`- 平均点赞：${fmt(avgDigg)}　中位数时长：${mmss(medianDur)}`);
lines.push(`- 点赞最高：${fmt(ranked[0].digg)}　最低：${fmt(ranked[ranked.length - 1].digg)}　差距 ${(ranked[0].digg / Math.max(1, ranked[ranked.length - 1].digg)).toFixed(1)} 倍`);
lines.push('');
lines.push('## 作品一览（按点赞排序）');
lines.push('');
lines.push('| # | 发布日期 | 时长 | 点赞 | 评论 | 分享 | 收藏 | 文案标题 |');
lines.push('|---|---|---|---|---|---|---|---|');
ranked.forEach((w, i) => {
  const d = w.date.slice(0, 10);
  const desc = (w.desc || '').replace(/\|/g, '｜').slice(0, 42);
  lines.push(
    `| ${i + 1} | ${d} | ${mmss(w.duration_sec)} | ${fmt(w.digg)} | ${fmt(w.comment)} | ${fmt(w.share)} | ${fmt(
      w.collect
    )} | ${desc} ${w.is_top ? '📌' : ''} |`
  );
});
lines.push('');
lines.push('> 📌 = 置顶作品。播放量抖音网页端不公开，仅作者后台可见，故此处用点赞/评论作为对标指标。');
lines.push('');
lines.push('## 完整文案');
lines.push('');
ranked.forEach((w, i) => {
  lines.push(`### ${i + 1}. ${w.desc.slice(0, 30)}…`);
  lines.push('');
  lines.push(`- 发布：${w.date.slice(0, 10)}　时长：${mmss(w.duration_sec)}　点赞 ${fmt(w.digg)}　评论 ${fmt(w.comment)}`);
  lines.push(`- 话题：${w.text_extra || '（无）'}`);
  lines.push('');
  lines.push('```');
  lines.push(w.desc);
  lines.push('```');
  lines.push('');
});

await fs.writeFile(path.join(ROOT, '作品清单.md'), lines.join('\n'), 'utf8');
console.log(`已生成 作品清单.md，共 ${works.length} 条作品`);
console.log(`平均点赞 ${avgDigg}，中位时长 ${Math.round(medianDur)} 秒`);
