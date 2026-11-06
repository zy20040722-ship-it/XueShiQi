// 测试: 能否通过重放接口请求拿到第二页作品
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
let capturedUrl = null;
page.on('request', (r) => {
  if (/aweme\/v1\/web\/aweme\/post/.test(r.url())) capturedUrl = r.url();
});

log('打开主页...');
await page.goto(`https://www.douyin.com/user/${SEC_UID}`, {
  waitUntil: 'domcontentloaded',
  timeout: 90_000,
});
for (let i = 0; i < 25 && !capturedUrl; i++) await page.waitForTimeout(1000);

if (!capturedUrl) {
  log('没截到接口请求, 退出');
  await ctx.close();
  process.exit(1);
}
log('已截到接口 URL, 长度 ' + capturedUrl.length);

const all = [];
const tryFetch = async (cursor, tag, keepSig, count) => {
  const res = await page.evaluate(
    async ([u, cur, keep, cnt]) => {
      const url = new URL(u);
      url.searchParams.set('max_cursor', String(cur));
      if (cnt) url.searchParams.set('count', String(cnt));
      if (!keep) {
        url.searchParams.delete('a_bogus');
        url.searchParams.delete('x-secsdk-web-signature');
      }
      try {
        const r = await fetch(url.toString(), { credentials: 'include' });
        const t = await r.text();
        return { status: r.status, len: t.length, body: t.slice(0, 300), text: t };
      } catch (e) {
        return { error: String(e) };
      }
    },
    [capturedUrl, cursor, keepSig, count]
  );
  let parsed = null;
  try {
    parsed = JSON.parse(res.text || '{}');
  } catch {}
  const n = parsed?.aweme_list?.length ?? 0;
  log(
    `${tag}: http=${res.status ?? res.error} 长度=${res.len ?? 0} aweme_list=${n} has_more=${
      parsed?.has_more
    } status_code=${parsed?.status_code} ${n === 0 ? '| body=' + (res.body || '').slice(0, 160) : ''}`
  );
  if (n) all.push(...parsed.aweme_list);
  return parsed;
};

// 原样重放: 参数一个都不改(连 count 都不改), 验证签名可复用
const first = await tryFetch(0, '第1页原样重放', true, null);
const cursor2 = first?.max_cursor;
log('第一页 max_cursor = ' + cursor2 + ', has_more = ' + first?.has_more);

if (cursor2) {
  await tryFetch(cursor2, '第2页(改游标+保留签名)', true, null);
  await tryFetch(cursor2, '第2页(改游标+去签名)', false, null);
}

if (all.length) {
  const uniq = new Map(all.map((a) => [a.aweme_id, a]));
  await fs.writeFile(
    path.join(OUTDIR, 'aweme_pages.json'),
    JSON.stringify([...uniq.values()], null, 2),
    'utf8'
  );
  log(`已保存 ${uniq.size} 条作品原始数据`);
}

await ctx.close();
