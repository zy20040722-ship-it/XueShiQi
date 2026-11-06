// 抖音主页采集器
// 用法: node douyin_scrape.mjs [输出目录] [--headed]
// 作用: 打开指定抖音主页 -> 滚动加载全部作品 -> 截获接口数据 -> 落地为 JSON + 封面图

import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const USER_URL =
  'https://www.douyin.com/user/MS4wLjABAAAAzgDkPWwgtkLeOAKp7WoN-07vflG4YJkBlPJVTuJKuwTO1WgjXekWDWeY6MmXDdTR';

const OUTDIR = process.argv[2] || '.\\data';
const HEADLESS = !process.argv.includes('--headed');

const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

async function main() {
  const rawDir = path.join(OUTDIR, 'raw');
  const coverDir = path.join(OUTDIR, 'covers');
  await fs.mkdir(rawDir, { recursive: true });
  await fs.mkdir(coverDir, { recursive: true });

  log('启动 Chrome...');
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: HEADLESS,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process',
      '--lang=zh-CN',
    ],
  });

  const ctx = await browser.newContext({
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    viewport: { width: 1512, height: 950 },
    deviceScaleFactor: 1,
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  });

  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
  });

  const page = await ctx.newPage();
  const captured = [];
  let seq = 0;

  page.on('response', async (resp) => {
    const u = resp.url();
    if (!/aweme|user\/profile|user\/detail/i.test(u)) return;
    try {
      const ct = resp.headers()['content-type'] || '';
      if (!/json|text/i.test(ct)) return;
      const txt = await resp.text();
      if (!txt || txt.length < 50) return;
      const id = String(seq++).padStart(3, '0');
      const name = `${id}_${u.replace(/^https?:\/\//, '').replace(/[^\w.-]/g, '_').slice(0, 90)}.json`;
      await fs.writeFile(path.join(rawDir, name), txt, 'utf8');
      captured.push({ file: name, url: u, status: resp.status(), len: txt.length });
      log(`  截获 ${name}  (${txt.length} 字节)`);
    } catch {
      /* 忽略读不到 body 的响应 */
    }
  });

  log('打开主页...');
  await page.goto(USER_URL, { waitUntil: 'domcontentloaded', timeout: 90_000 });

  // 等反爬 JS 跑完、作品列表出现
  let appeared = false;
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000);
    const n = await page.evaluate(() => {
      const sels = [
        '[data-e2e="user-post-list"] li',
        '[data-e2e="user-post-item"]',
        'ul li a[href*="/video/"]',
        'a[href*="/video/"]',
      ];
      for (const s of sels) {
        const c = document.querySelectorAll(s).length;
        if (c > 0) return c;
      }
      return 0;
    });
    if (n > 0) {
      log(`作品列表出现, 当前 ${n} 个节点`);
      appeared = true;
      break;
    }
    if (i % 5 === 4) log(`  等待中... (${i + 1}s)`);
  }

  if (!appeared) {
    log('!! 未出现作品列表, 保存现场供排查');
    await page.screenshot({ path: path.join(OUTDIR, 'debug_page.png'), fullPage: false });
    await fs.writeFile(path.join(OUTDIR, 'debug_page.html'), await page.content(), 'utf8');
    log('   title = ' + (await page.title()));
  }

  // 滚动加载全部作品 —— 多策略组合，抖音的列表是虚拟滚动，只滚窗口往往不触发加载
  log('滚动加载...');
  await page.mouse.move(760, 520); // 把鼠标移到列表区域，wheel 才作用在列表上

  const countItems = () =>
    page.evaluate(() => {
      const s = new Set();
      for (const a of document.querySelectorAll('a[href*="/video/"], a[href*="/note/"]')) {
        const m = (a.getAttribute('href') || '').match(/\/(?:video|note)\/(\d+)/);
        if (m) s.add(m[1]);
      }
      return s.size;
    });

  let stable = 0;
  let last = 0;
  for (let i = 0; i < 140 && stable < 8; i++) {
    await page.mouse.wheel(0, 2500);
    await page.waitForTimeout(600);
    await page.keyboard.press('PageDown').catch(() => {});
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(600);

    // 兜底：直接滚动内部可滚动容器
    await page
      .evaluate(() => {
        const cand = [...document.querySelectorAll('div,main,section')]
          .filter((el) => el.scrollHeight > el.clientHeight + 200 && el.clientHeight > 300)
          .sort((a, b) => b.scrollHeight - a.scrollHeight)[0];
        if (cand) cand.scrollTop = cand.scrollHeight;
      })
      .catch(() => {});

    const n = await countItems();
    if (n === last) stable++;
    else {
      stable = 0;
      last = n;
      log(`  已加载 ${n} 个作品`);
    }
    if (n >= 30) {
      log(`  已达到 30 个, 继续多滚几轮确保全部接口都触发`);
    }
  }
  log(`滚动结束, 共 ${last} 个作品`);

  // 从页面 DOM 抓一份兜底数据
  const domItems = await page.evaluate(() => {
    const out = [];
    const seen = new Set();
    for (const a of document.querySelectorAll('a[href*="/video/"]')) {
      const href = a.getAttribute('href') || '';
      const m = href.match(/\/video\/(\d+)/);
      if (!m) continue;
      const id = m[1];
      if (seen.has(id)) continue;
      seen.add(id);
      const img = a.querySelector('img');
      out.push({
        aweme_id: id,
        href,
        text: (a.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 200),
        title: (a.getAttribute('title') || '').slice(0, 200),
        img: img ? img.getAttribute('src') : '',
        alt: img ? (img.getAttribute('alt') || '').slice(0, 200) : '',
      });
    }
    return out;
  });

  await fs.writeFile(
    path.join(OUTDIR, 'dom_items.json'),
    JSON.stringify(domItems, null, 2),
    'utf8'
  );
  await page.screenshot({ path: path.join(OUTDIR, 'page_full.png'), fullPage: true });

  // 下载封面
  log(`下载封面 (${domItems.length} 个)...`);
  let ok = 0;
  for (const it of domItems) {
    if (!it.img) continue;
    try {
      const resp = await ctx.request.get(it.img, { timeout: 20_000 });
      if (!resp.ok()) continue;
      const buf = await resp.body();
      await fs.writeFile(path.join(coverDir, `${it.aweme_id}.jpg`), buf);
      ok++;
    } catch {
      /* 封面下载失败不影响主流程 */
    }
  }

  await fs.writeFile(
    path.join(OUTDIR, 'captured_index.json'),
    JSON.stringify({ user_url: USER_URL, captured, dom_count: domItems.length, covers_ok: ok }, null, 2),
    'utf8'
  );

  log(`完成: 接口响应 ${captured.length} 个, DOM 作品 ${domItems.length} 个, 封面 ${ok} 张`);
  await browser.close();
}

main().catch(async (e) => {
  console.error('FAILED:', e && e.stack ? e.stack : e);
  process.exit(1);
});
