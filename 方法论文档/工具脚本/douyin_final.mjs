// 最后一次尝试: 找到真正承载作品的滚动容器, 用键盘/分段滚动逼出全部作品
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SEC_UID =
  'MS4wLjABAAAAzgDkPWwgtkLeOAKp7WoN-07vflG4YJkBlPJVTuJKuwTO1WgjXekWDWeY6MmXDdTR';
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

const ctx = await chromium.launchPersistentContext(path.join(__dirname, 'chrome-profile'), {
  channel: 'chrome',
  headless: true,
  locale: 'zh-CN',
  viewport: { width: 1600, height: 900 },
  userAgent:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  args: ['--disable-blink-features=AutomationControlled', '--lang=zh-CN'],
});
const page = ctx.pages()[0] || (await ctx.newPage());
const apiCalls = [];
page.on('request', (r) => {
  if (/aweme\/v1\/web\/aweme\/post/.test(r.url())) apiCalls.push(r.url());
});

await page.goto(`https://www.douyin.com/user/${SEC_UID}`, { waitUntil: 'domcontentloaded', timeout: 90_000 });
await page.waitForTimeout(10000);

// 页签栏文字 —— 看官方显示的「作品」数量
const tabs = await page.evaluate(() => {
  const out = [];
  for (const el of document.querySelectorAll('div,span,a')) {
    const t = (el.textContent || '').trim();
    if (/^(作品|喜欢|收藏)\s*\d*$/.test(t) && t.length < 20) out.push(t);
  }
  return [...new Set(out)].slice(0, 12);
});
log('页签栏: ' + JSON.stringify(tabs));

const containers = await page.evaluate(() => {
  return [...document.querySelectorAll('div,main,section')]
    .filter((el) => el.scrollHeight > el.clientHeight + 150 && el.clientHeight > 200)
    .slice(0, 8)
    .map((el) => ({
      cls: (el.className || '').toString().slice(0, 60),
      sh: el.scrollHeight,
      ch: el.clientHeight,
      containsGrid: !!el.querySelector('a[href*="/video/"]'),
    }));
});
log('可滚动容器: ' + JSON.stringify(containers, null, 1));

const count = () =>
  page.evaluate(() => {
    const s = new Set();
    for (const a of document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')) {
      const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
      if (m) s.add(m[1]);
    }
    return s.size;
  });

log('start: ' + (await count()));
// 点一下网格再反复按 End
const box = await page.evaluate(() => {
  const el = document.querySelector('a[href*="/video/"]');
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
});
if (box) await page.mouse.click(box.x, box.y).catch(() => {});
await page.keyboard.press('Escape').catch(() => {});

let last = 0;
let stable = 0;
for (let i = 0; i < 120 && stable < 20; i++) {
  await page.keyboard.press('End').catch(() => {});
  await page.mouse.wheel(0, 900);
  await page.waitForTimeout(800);
  // 分段滚动内部容器
  await page.evaluate(() => {
    for (const el of document.querySelectorAll('div,main,section')) {
      if (el.scrollHeight > el.clientHeight + 150 && el.clientHeight > 200 && el.querySelector('a[href*="/video/"]')) {
        el.scrollTop = el.scrollTop + 800;
      }
    }
  });
  const n = await count();
  if (n !== last) {
    log(`  ${n}`);
    last = n;
    stable = 0;
  } else stable++;
}
log(`结束: ${last} 个, 接口调用 ${apiCalls.length} 次`);

const own = await page.evaluate(() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')) {
    const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
    const img = a.querySelector('img');
    const alt = (img?.getAttribute('alt') || '').replace(/\s+/g, ' ').trim();
    if (!m || seen.has(m[1])) continue;
    seen.add(m[1]);
    out.push({ aweme_id: m[1], alt, raw: (a.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 80) });
  }
  return out;
});
const mine = own.filter((o) => o.alt.startsWith('薛世奇说物理'));
log(`本人作品 ${mine.length} 条`);
await fs.writeFile(path.join(__dirname, '..', '数据采集', 'final_grid.json'), JSON.stringify(own, null, 2), 'utf8');
await ctx.close();
