const { chromium } = require('playwright');
const len = process.argv[2] || 'full';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/Failed to load|ERR_/.test(m.text())) errs.push(m.text()); });
  await page.goto('http://localhost:8765/games/sahra.html?fast', { waitUntil: 'load' });
  await page.screenshot({ path: __dirname + '/shots/sahra-intro.png' });
  await page.click('[data-a=one]');
  await page.click(`[data-a=lcfg][data-v="len:${len}"]`); await page.click(`[data-a=lcfg][data-v="vibe:${process.argv[3]||'mix'}"]`);
  await page.click('[data-a=lgo]');
  const seen = new Set(); const shots = new Set(); let steps = 0;
  const t0 = Date.now();
  while (Date.now() - t0 < 100000) {
    if (await page.$('.king')) break;
    const hs = await page.$eval('.hud .hs', e => e.textContent).catch(() => null);
    const kind = await page.evaluate(() => S && (S.phase + ':' + (S.cur ? S.cur.kind + (S.cur.st ? '/' + S.cur.st : '') : '')));
    if (kind && !shots.has(kind)) { shots.add(kind); await page.screenshot({ path: __dirname + `/shots/sahra-${len}-${kind.replace(/[:\/]/g, '_')}.png` }); }
    if (hs) seen.add(hs);
    const order = ['hand', 'cgo', 'bgo'];
    let done = false;
    for (const a of order) { const b = await page.$(`[data-a=${a}]`); if (b) { await b.click(); done = true; break; } }
    if (!done) {
      const txt = await page.$('#txt');
      if (txt) { await txt.fill(['بطيخ', 'جدّي', 'عمّان', 'سمكة', 'كنافة'][steps % 5] + (Math.random() < .5 ? '' : ' ' + steps)); await page.click('[data-a=text]'); done = true; }
    }
    if (!done && await page.$('[data-a=num]')) { await page.$eval('#rng', (r) => { r.value = String(Math.floor(Math.random() * (+r.max + 1))); r.dispatchEvent(new Event('input')); }); await page.click('[data-a=num]'); done = true; }
    if (!done) { const o = await page.$$('[data-a=career]'); if (o.length) { await page.waitForTimeout(Math.random()*4000); await o[Math.floor(Math.random() * o.length)].click(); done = true; } }
    if (!done) { const o = await page.$$('[data-a=ans]:not([disabled])'); if (o.length) { await o[Math.floor(Math.random() * o.length)].click(); done = true; } }
    if (!done) { const o = await page.$$('[data-a=cok]'); if (o.length) { await o[Math.floor(Math.random() * o.length)].click(); done = true; await page.waitForTimeout(500); } }
    if (!done) { const b = await page.$('[data-a=bpass]'); if (b) { await b.click(); done = true; await page.waitForTimeout(950); } }
    if (!done && Math.random() < .5) { const j = await page.$$('[data-a=joker]:not([disabled])'); if (j.length && Math.random() < .4) await j[0].click(); }
    if (!done) { const b = await page.$('[data-a=go]'); if (b) { await b.click(); done = true; } }
    steps++;
    await page.waitForTimeout(done ? 40 : 200);
  }
  const fin = await page.$('.king');
  await page.waitForTimeout(800);
  await page.screenshot({ path: __dirname + `/shots/sahra-${len}-final.png`, fullPage: true });
  const scores = await page.evaluate(() => S.players.map(p => p.name + ':' + p.score).join(' ') + ' | awards ' + S.awards.map(a => a.title).join(','));
  console.log(len, 'finished:', !!fin, 'steps', steps, 'secs', Math.round((Date.now() - t0) / 1000));
  console.log('stages:', [...seen].join(' | '));
  console.log('kinds:', [...shots].join(' '));
  console.log(scores);
  console.log('errors:', errs.length ? [...new Set(errs)].join(' ; ') : 'none');
  await browser.close();
})();
