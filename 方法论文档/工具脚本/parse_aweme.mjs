// 解析抖音采集到的接口数据 -> 作品清单表
import fs from 'node:fs/promises';
import path from 'node:path';

const ROOT = process.argv[2] || '.\\数据采集';
const rawDir = path.join(ROOT, 'raw');

const files = await fs.readdir(rawDir).catch(() => []);
const postFile = files.find((f) => f.includes('aweme_post'));
const profileFile = files.find((f) => f.includes('user_profile_other'));

if (!postFile) {
  console.error('找不到 aweme_post 数据文件, 现有: ' + files.join(', '));
  process.exit(1);
}

const raw = JSON.parse(await fs.readFile(path.join(rawDir, postFile), 'utf8'));

console.log('=== 顶层结构 ===');
console.log(Object.keys(raw).join(', '));
if (Array.isArray(raw.aweme_list)) {
  console.log(`aweme_list 条数 = ${raw.aweme_list.length}`);
  console.log('第一条的字段 = ' + Object.keys(raw.aweme_list[0]).join(', '));
}
console.log('has_more = ' + raw.has_more + ', max_cursor = ' + raw.max_cursor);

// 用户资料
if (profileFile) {
  const prof = JSON.parse(await fs.readFile(path.join(rawDir, profileFile), 'utf8'));
  const u = prof.user || prof.data?.user || {};
  console.log('\n=== 账号信息 ===');
  console.log('昵称: ' + u.nickname);
  console.log('签名: ' + (u.signature || '').replace(/\n/g, ' / '));
  console.log('粉丝: ' + u.follower_count + '  关注: ' + u.following_count + '  获赞: ' + u.total_favorited);
  console.log('作品数(接口): ' + u.aweme_count);
  console.log('抖音号: ' + (u.unique_id || u.short_id));
  await fs.writeFile(path.join(ROOT, 'account.json'), JSON.stringify(u, null, 2), 'utf8');
}

const items = (raw.aweme_list || []).map((a) => {
  const s = a.statistics || {};
  return {
    aweme_id: a.aweme_id,
    desc: (a.desc || '').replace(/\s+/g, ' ').trim(),
    create_time: a.create_time,
    date: new Date((a.create_time || 0) * 1000).toISOString().slice(0, 19).replace('T', ' '),
    duration_sec: a.video?.duration ? +(a.video.duration / 1000).toFixed(2) : null,
    digg: s.digg_count ?? 0,
    comment: s.comment_count ?? 0,
    share: s.share_count ?? 0,
    collect: s.collect_count ?? 0,
    play: s.play_count ?? 0,
    cover: a.video?.cover?.url_list?.[0] || a.video?.origin_cover?.url_list?.[0] || '',
    play_url: a.video?.play_addr?.url_list?.[0] || '',
    is_top: a.is_top || 0,
    text_extra: (a.text_extra || []).map((t) => t.hashtag_name).filter(Boolean).join(','),
    music: a.music?.title || '',
    ratio: a.video?.ratio || '',
  };
});

console.log(`\n=== 作品清单 (${items.length} 条) ===`);
console.log(
  ['#', '日期', '时长', '点赞', '评论', '分享', '收藏', '文案'].join('\t')
);
items
  .slice()
  .sort((a, b) => b.digg - a.digg)
  .forEach((it, i) => {
    console.log(
      [i + 1, it.date, it.duration_sec, it.digg, it.comment, it.share, it.collect, it.desc.slice(0, 40)].join('\t')
    );
  });

await fs.writeFile(path.join(ROOT, 'works.json'), JSON.stringify(items, null, 2), 'utf8');

const csv = [
  'aweme_id,date,duration_sec,digg,comment,share,collect,is_top,hashtags,desc',
  ...items.map((it) =>
    [
      it.aweme_id,
      it.date,
      it.duration_sec,
      it.digg,
      it.comment,
      it.share,
      it.collect,
      it.is_top,
      '"' + (it.text_extra || '').replace(/"/g, "'") + '"',
      '"' + (it.desc || '').replace(/"/g, "'") + '"',
    ].join(',')
  ),
].join('\n');
await fs.writeFile(path.join(ROOT, 'works.csv'), '\uFEFF' + csv, 'utf8');
console.log('\n已写出 works.json 与 works.csv');
