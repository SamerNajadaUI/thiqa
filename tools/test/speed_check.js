// فحص السرعة: كل صفحة على نت 4G بطيء (150ms تأخير، 4 ميغابت). زيارة أولى (بدون كاش) وثانية (مع الكاش والـservice worker).
// بيقيس الوقت لحد ما الصفحة "تجهز" (يبين العنصر الأساسي)، وحجم اللي نزل.
// الاستعمال: cd docs && python3 -m http.server 8765 ; node speed_check.js
const { chromium } = require('playwright');
const { adminInit } = require('./session.js');
const B = 'http://localhost:8765/';
const PAGES = [['index.html', '.gcard'], ['home.html', '.gcard'], ['games/index.html', '.gcard'], ['games/points.html', '#one'], ['games/sahra.html', '[data-a=one]'],
  ['games/hasm.html', '#app button'], ['games/kworld.html', '#go'], ['games/duel.html', '#go'], ['games/party.html', '#app button'], ['games/career.html', '#app button'], ['games/numbers.html', '#app button'], ['rewards.html', '.apptabs'], ['settings.html', '.apptabs']];
(async () => {
  const b = await chromium.launch();
  const rows = [];
  for (const [pg, sel] of PAGES) {
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
    await ctx.addInitScript(adminInit);
    await ctx.route(/fonts\.(googleapis|gstatic)\.com|wikimedia|espncdn|flagcdn/, (r) => r.abort());
    const p = await ctx.newPage();
    const cdp = await ctx.newCDPSession(p);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: (4 * 1024 * 1024) / 8, uploadThroughput: (1024 * 1024) / 8 });
    let bytes = 0, n = 0; cdp.on('Network.loadingFinished', (e) => { n++; bytes += e.encodedDataLength || 0; });
    const errs = []; p.on('pageerror', (e) => errs.push(e.message));
    for (const visit of [1, 2]) {
      bytes = 0; n = 0;
      const t0 = Date.now();
      if (visit === 1) await p.goto(B + pg, { waitUntil: 'commit' }); else await p.reload({ waitUntil: 'commit' });
      let ready = -1;
      try { await p.waitForSelector(sel, { timeout: 20000 }); ready = Date.now() - t0; } catch {}
      await p.waitForTimeout(visit === 1 ? 2500 : 600);
      rows.push({ pg, visit, ready, n, kb: Math.round(bytes / 1024), errs: errs.length });
    }
    await ctx.close();
  }
  console.log('page'.padEnd(22), 'visit', 'ready(ms)'.padStart(10), 'reqs'.padStart(5), 'KB'.padStart(7), ' errs');
  for (const r of rows) console.log(r.pg.padEnd(22), String(r.visit).padStart(5), String(r.ready).padStart(10), String(r.n).padStart(5), String(r.kb).padStart(7), ' ', r.errs);
  await b.close();
})();
