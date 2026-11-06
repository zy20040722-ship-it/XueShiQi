// 备用方案: 试老版接口 + 拟人化慢速滚动
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUTDIR = process.argv[2] || '.\\数据采集';
const SEC_UID =
  'MS4wLjABAAAAzgDkPWwgtkLeOAKp7WoN-07vflG4YJkBlPJVTuJKuwTO1WgjXekWDWeY6MmXDdTR';
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

const ctx = await chromium.launchPersistentContext(path.join(__dirname, 'chrome-profile'), {
  channel: 'chrome',
  headless: true,
  locale: 'zh-CN',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1600, height: 900 },
  userAgent:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  args: ['--disable-blink-features=AutomationControlled', '--lang=zh-CN'],
});

const page = ctx.pages()[0] || (await ctx.newPage());
const seenApi = [];
page.on('request', (r) => {
  if (/aweme\/v1\/web\/aweme\/post|\/web\/api\/v2\/aweme\/post/.test(r.url())) seenApi.push(r.url());
});

log('打开主页...');
await page.goto(`https://www.douyin.com/user/${SEC_UID}`, {
  waitUntil: 'domcontentloaded',
  timeout: 90_000,
});
await page.waitForTimeout(9000);

// --- 方案 A: 老版接口 ---
log('--- 方案A: 老版接口 ---');
const legacy = [
  `https://www.iesdouyin.com/web/api/v2/aweme/post/?sec_uid=${SEC_UID}&count=21&max_cursor=0&aid=1128`,
  `https://www.iesdouyin.com/web/api/v2/aweme/post/?sec_uid=${SEC_UID}&count=21&max_cursor=0`,
];
for (const u of legacy) {
  try {
    const r = await ctx.request.get(u, { timeout: 25_000, headers: { Referer: 'https://www.douyin.com/' } });
    const t = await r.text();
    let n = 0;
    try {
      n = JSON.parse(t)?.aweme_list?.length || 0;
    } catch {}
    log(`  ${r.status()} 长度=${t.length} 条数=${n}  ${t.slice(0, 120).replace(/\n/g, ' ')}`);
  } catch (e) {
    log('  失败: ' + e.message);
  }
}

// --- 方案 B: 拟人化慢速滚动 ---
log('--- 方案B: 拟人化慢速滚动 ---');
const box = await page.evaluate(() => {
  const el = document.querySelector('a[href*="/video/"]');
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
});
if (box) await page.mouse.move(box.x, box.y);

let last = 0;
let stable = 0;
for (let i = 0; i < 90 && stable < 12; i++) {
  await page.mouse.wheel(0, 300 + Math.random() * 200);
  await page.waitForTimeout(500 + Math.random() * 500);
  const n = await page.evaluate(() => {
    const s = new Set();
    for (const a of document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')) {
      const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
      if (m) s.add(m[1]);
    }
    return s.size;
  });
  if (n !== last) {
    log(`  ${n} 个`);
    last = n;
    stable = 0;
  } else stable++;
}
log(`滚动结束: ${last} 个, 接口被调用 ${seenApi.length} 次`);

// 判断哪些是本人作品: alt 前缀是账号名
const items = await page.evaluate(() => {
  const out = [];
  for (const a of document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')) {
    const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
    if (!m) continue;
    const img = a.querySelector('img');
    out.push({
      aweme_id: m[1],
      alt: (img?.getAttribute('alt') || '').replace(/\s+/g, ' ').trim(),
      raw: (a.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 100),
    });
  }
  return out;
});
const uniq = new Map(items.map((i) => [i.aweme_id, i]));
const own = [...uniq.values()].filter((i) => i.alt.startsWith('薛世奇说物理'));
log(`页面共 ${uniq.size} 个链接, 其中本人作品 ${own.length} 条`);
await fs.writeFile(path.join(OUTDIR, 'alt_result.json'), JSON.stringify([...uniq.values()], null, 2), 'utf8');
await fs.writeFile(path.join(OUTDIR, 'api_calls.json'), JSON.stringify(seenApi, null, 2), 'utf8');

await ctx.close();
