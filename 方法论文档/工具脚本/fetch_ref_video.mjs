// 精确抓取指定作品的画面: 拦截详情接口, 只认这个 aweme_id 的播放地址
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WS = path.resolve(__dirname, '..');
const OUT = path.join(WS, '参考视频');
const AWEME = '7689437605540220200';
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

await fs.mkdir(OUT, { recursive: true });
const ctx = await chromium.launchPersistentContext(path.join(__dirname, 'chrome-profile'), {
  channel: 'chrome',
  headless: true,
  locale: 'zh-CN',
  viewport: { width: 1400, height: 980 },
  userAgent:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  args: ['--disable-blink-features=AutomationControlled', '--lang=zh-CN', '--autoplay-policy=no-user-gesture-required'],
});
const page = ctx.pages()[0] || (await ctx.newPage());

// 拦详情接口, 拿到这个作品自己的播放地址
let playUrls = null;
let meta = null;
page.on('response', async (r) => {
  const u = r.url();
  if (!/aweme\/v1\/web\/aweme\/detail/.test(u)) return;
  try {
    const j = JSON.parse(await r.text());
    const a = j.aweme_detail || (j.aweme_list || [])[0];
    if (!a || String(a.aweme_id) !== AWEME) return;
    meta = {
      desc: (a.desc || '').replace(/\s+/g, ' ').slice(0, 200),
      duration: a.video?.duration,
      w: a.video?.width,
      h: a.video?.height,
      digg: a.statistics?.digg_count,
    };
    playUrls = a.video?.play_addr_h264?.url_list || a.video?.play_addr?.url_list || [];
    log(`拿到作品详情: ${meta.duration}ms  ${meta.w}x${meta.h}  播放地址 ${playUrls.length} 个`);
  } catch {
    /* 忽略解析失败的响应 */
  }
});

log('打开作品页...');
await page.goto(`https://www.douyin.com/video/${AWEME}`, { waitUntil: 'domcontentloaded', timeout: 90_000 });
for (let i = 0; i < 25 && !playUrls; i++) await page.waitForTimeout(1000);

// 关弹窗
for (let i = 0; i < 5; i++) {
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(300);
}
await page.waitForTimeout(1500);

const st = await page.evaluate(() => {
  const v = document.querySelector('video');
  return v ? { d: v.duration, w: v.videoWidth, h: v.videoHeight } : null;
});
log('播放器状态: ' + JSON.stringify(st));

// 截视频画面
if (st && st.d) {
  await page.evaluate(() => {
    const v = document.querySelector('video');
    v.muted = true;
    v.play().catch(() => {});
  });
  const vid = page.locator('video').first();
  for (const t of [2, 12, 30, 55, 80, 110, 150, 172]) {
    if (t >= st.d) continue;
    await page.evaluate((tt) => {
      document.querySelector('video').currentTime = tt;
    }, t);
    await page.waitForTimeout(1400);
    await vid.screenshot({ path: path.join(OUT, `ref_${String(t).padStart(3, '0')}s.png`) });
    log(`  截图 ${t}s`);
  }
}

await fs.writeFile(path.join(OUT, 'ref_meta.json'),
  JSON.stringify({ aweme: AWEME, meta, playUrls }, null, 2), 'utf8');

// 下载这个作品自己的视频
if (playUrls && playUrls.length) {
  log('下载作品视频...');
  const r = await ctx.request.get(playUrls[0], { timeout: 180_000 });
  if (r.ok()) {
    const buf = await r.body();
    await fs.writeFile(path.join(OUT, '参考视频.mp4'), buf);
    log(`  参考视频.mp4  ${(buf.length / 1024 / 1024).toFixed(1)} MB`);
  } else {
    log(`  下载失败 HTTP ${r.status()}`);
  }
}
await ctx.close();
log('完成');
