// فحص السرعة: كل صفحة على نت 4G بطيء (CDP)، أول زيارة وزيارة ثانية (مع الكاش والـservice worker).
// بيطبع: وقت أول رسم، وقت التحميل، عدد الطلبات، والحجم. الاستعمال: cd docs && python3 -m http.server 8765 ; node speed_check.js
const { chromium } = require('playwright');
const { adminInit } = require('./session.js');
const B = 'http://localhost:8765/';
const PAGES = ['index.html', 'home.html', 'games/index.html', 'games/points.html', 'games/sahra.html', 'games/hasm.html', 'games/kworld.html', 'games/party.html', 'games/career.html', 'rewards.html', 'settings.html'];
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.addInitScript(adminInit);
  await ctx.route(/fonts\.(googleapis|gstatic)\.com|wikimedia|espncdn|flagcdn|jsdelivr/, (r) => r.abort());
  const rows = [];
  for (const pg of PAGES) {
    for (const visit of [1, 2]) {
      const p = await ctx.newPage();
      const cdp = await ctx.newCDPSession(p);
      await cdp.send('Network.enable');
      await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: (4 * 1024 * 1024) / 8, uploadThroughput: (1 * 1024 * 1024) / 8 });
      let n = 0, bytes = 0; const errs = [];
      cdp.on('Network.loadingFinished', (e) => { n++; bytes += e.encodedDataLength || 0; });
      p.on('pageerror', (e) => errs.push(e.message));
      const t0 = Date.now();
      await p.goto(B + pg, { waitUntil: 'load' });
      const load = Date.now() - t0;
      await p.waitForTimeout(1500);
      const m = await p.evaluate(() => { const pe = performance.getEntriesByType('paint').find((x) => x.name === 'first-contentful-paint'); const nav = performance.getEntriesByType('navigation')[0]; return { fcp: pe ? Math.round(pe.startTime) : -1, dcl: nav ? Math.round(nav.domContentLoadedEventEnd) : -1, url: location.pathname.split('/').slice(-2).join('/') }; });
      rows.push({ page: pg, visit, fcp: m.fcp, dcl: m.dcl, load, reqs: n, kb: Math.round(bytes / 1024), at: m.url, errs: errs.length });
      await p.close();
    }
  }
  console.log('page'.padEnd(22), 'v', 'FCP'.padStart(6), 'DCL'.padStart(6), 'load'.padStart(6), 'reqs'.padStart(5), 'KB'.padStart(7), ' errs  →');
  for (const r of rows) console.log(r.page.padEnd(22), r.visit, String(r.fcp).padStart(6), String(r.dcl).padStart(6), String(r.load).padStart(6), String(r.reqs).padStart(5), String(r.kb).padStart(7), ' ', r.errs, ' ', r.at);
  await b.close();
})();
