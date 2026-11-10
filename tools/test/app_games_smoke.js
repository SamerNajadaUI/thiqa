// يفتح كل صفحات الألعاب بحساب أدمن ويتأكد ما في أخطاء JS، ويصوّر كم لعبة قديمة للمقارنة البصرية.
// node app_games_smoke.js   (يلزمه سيرفر docs على 8765)
const { chromium } = require('playwright'); const fs = require('fs');
const B = 'http://localhost:8765/', SHOTS = __dirname + '/shots';
const games = fs.readdirSync(__dirname + '/../../docs/games').filter((f) => f.endsWith('.html') && f !== 'index.html');
(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com|cdn\.jsdelivr\.net/, (r) => r.abort());
  await ctx.addInitScript(() => { try { localStorage.setItem('app-users', JSON.stringify({ admin: { uid: 'admin', name: 'الأدمن', provider: 'admin', plan: 'admin', points: 0, dayKey: '', dayPlay: 0, lastDaily: '' } })); localStorage.setItem('app-session', '"admin"'); } catch {} });
  let bad = 0;
  for (const g of games) {
    const p = await ctx.newPage(); const errs = [];
    p.on('pageerror', (e) => errs.push(e.message));
    p.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|ERR_FAILED|net::/.test(m.text())) errs.push(m.text().slice(0, 160)); });
    await p.goto(B + 'games/' + g + '?fast', { waitUntil: 'load' }); await p.waitForTimeout(500);
    if (!/games\//.test(p.url())) errs.push('redirected to ' + p.url());
    if (['points.html', 'mafia.html', 'speed.html', 'sahra.html', 'wheel.html', 'tamaa.html'].includes(g)) await p.screenshot({ path: `${SHOTS}/old-${g.replace('.html', '')}.png` });
    console.log(errs.length ? '✗' : '✓', g, errs.join(' | ')); bad += errs.length ? 1 : 0; await p.close();
  }
  await browser.close(); process.exit(bad ? 1 : 0);
})();
