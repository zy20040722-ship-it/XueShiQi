// 深度采集: 用 scrollIntoView 逼出抖音虚拟列表的全部作品, 并逐条读取点赞/标题
// 用法: node douyin_deep.mjs <输出目录> [--headed]

import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const SEC_UID =
  'MS4wLjABAAAAzgDkPWwgtkLeOAKp7WoN-07vflG4YJkBlPJVTuJKuwTO1WgjXekWDWeY6MmXDdTR';
const USER_URL = `https://www.douyin.com/user/${SEC_UID}`;
const OUTDIR = process.argv[2] || '.\\数据采集';
const HEADLESS = !process.argv.includes('--headed');
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

const listText = () =>
  // 从网格里逐条抠出: id / 标题 / 点赞数 / 是否置顶
  Array.from(document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')).map((a) => {
    const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
    const img = a.querySelector('img');
    const raw = (a.innerText || '').replace(/\s+/g, ' ').trim();
    // 网格里数字一般是 "1.8万" / "7064" 这种点赞量
    const num = raw.match(/(\d+(?:\.\d+)?)(万|w|W)?/);
    let likes = null;
    if (num) {
      likes = parseFloat(num[1]);
      if (num[2]) likes = Math.round(likes * 10000);
    }
    return {
      aweme_id: m ? m[1] : null,
      href: a.getAttribute('href') || '',
      raw,
      likes,
      is_top: /置顶/.test(raw),
      alt: (img?.getAttribute('alt') || '').replace(/\s+/g, ' ').trim(),
      img: img?.getAttribute('src') || '',
    };
  });

async function main() {
  await fs.mkdir(OUTDIR, { recursive: true });
  // 持久化用户目录: 反爬验证过一次之后就记住, 后续运行不再被拦
  const profileDir = path.join(__dirname, 'chrome-profile');
  await fs.mkdir(profileDir, { recursive: true });

  const ctx = await chromium.launchPersistentContext(profileDir, {
    channel: 'chrome',
    headless: HEADLESS,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    viewport: { width: 1600, height: 900 },
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    args: ['--disable-blink-features=AutomationControlled', '--lang=zh-CN'],
  });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });

  const page = ctx.pages()[0] || (await ctx.newPage());

  // 记录所有 aweme/post 请求的完整 URL, 供分析签名
  const apiUrls = [];
  page.on('request', (r) => {
    if (/aweme\/v1\/web\/aweme\/post/.test(r.url())) apiUrls.push(r.url());
  });

  log('打开主页...');
  await page.goto(USER_URL, { waitUntil: 'domcontentloaded', timeout: 90_000 });
  await page.waitForTimeout(10000);

  // 如果被拦, 等验证码跑完
  for (let i = 0; i < 20; i++) {
    const n = await page.evaluate(() => document.querySelectorAll('a[href*="/video/"]').length);
    if (n > 0) break;
    await page.waitForTimeout(1500);
    await page.mouse.move(700 + i * 7, 400 + (i % 5) * 20);
  }

  // 找到列表容器并报告
  const info = await page.evaluate(() => {
    const el = document.querySelector('a[href*="/video/"]');
    return {
      firstLinkText: el ? el.innerText.replace(/\s+/g, ' ').slice(0, 120) : null,
      totalLinks: document.querySelectorAll('a[href*="/video/"]').length,
      bodyScroll: document.body.scrollHeight,
      winInner: window.innerHeight,
      title: document.title,
      url: location.href,
    };
  });
  log('初始状态: ' + JSON.stringify(info));

  if (info.totalLinks === 0) {
    await page.screenshot({ path: path.join(OUTDIR, 'blocked.png'), fullPage: false });
    await fs.writeFile(path.join(OUTDIR, 'blocked.html'), await page.content(), 'utf8');
    log('!! 未加载出作品, 已保存 blocked.png / blocked.html');
  }

  // 用 scrollIntoView 逼虚拟列表加载
  log('深度滚动...');
  let stable = 0;
  let lastCount = 0;
  for (let i = 0; i < 200 && stable < 15; i++) {
    await page.evaluate(() => {
      const links = document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]');
      if (links.length) links[links.length - 1].scrollIntoView({ block: 'end' });
      window.scrollBy(0, 600);
    });
    await page.waitForTimeout(700);

    const n = await page.evaluate(() => {
      const s = new Set();
      for (const a of document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')) {
        const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
        if (m) s.add(m[1]);
      }
      return s.size;
    });

    if (n !== lastCount) {
      log(`  ${n} 个`);
      lastCount = n;
      stable = 0;
    } else stable++;
  }
  log(`滚动结束: ${lastCount} 个` + (stable >= 15 ? ' (已稳定)' : ' (达到迭代上限)'));

  const items = await page.evaluate(listText);
  const uniq = new Map();
  for (const it of items) if (it.aweme_id) uniq.set(it.aweme_id, it);
  const finalItems = [...uniq.values()];

  log(`抓到 ${finalItems.length} 条, 接口请求 ${apiUrls.length} 次`);
  await fs.writeFile(
    path.join(OUTDIR, 'grid_items.json'),
    JSON.stringify(finalItems, null, 2),
    'utf8'
  );
  await fs.writeFile(
    path.join(OUTDIR, 'api_urls.json'),
    JSON.stringify(apiUrls, null, 2),
    'utf8'
  );

  console.log('\n=== 网格条目 ===');
  for (const it of finalItems) {
    console.log(
      `${it.aweme_id}\t点赞:${it.likes}\t${it.is_top ? '置顶' : '    '}\t${(it.raw || '').slice(0, 50)}`
    );
  }

  await ctx.close();
}

main().catch((e) => {
  console.error('FAILED:', e?.stack || e);
  process.exit(1);
});
