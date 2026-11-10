const { chromium } = require('playwright');
const fs = require('fs');
const MQ = fs.readFileSync(require.resolve('mqtt/dist/mqtt.min.js'), 'utf8');
const URL = 'http://localhost:8765/games/sahra.html?fast&broker=' + encodeURIComponent('ws://localhost:8883');
const names = ['سامر', 'ليلى', 'خالد', 'نور'];
(async () => {
  const browser = await chromium.launch();
  const errs = [];
  const pages = [];
  for (const n of names) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await ctx.route('**/mqtt.min.js', r => r.fulfill({ contentType: 'application/javascript', body: MQ }));
    await ctx.addInitScript(require('./session').adminInit);
    const p = await ctx.newPage();
    p.on('pageerror', e => errs.push(n + ': ' + e.message));
    await p.goto(URL, { waitUntil: 'load' });
    await p.fill('#name', n);
    pages.push(p);
  }
  await pages[0].click('[data-a=create]');
  await pages[0].waitForSelector('.roomcode b');
  const code = await pages[0].$eval('.roomcode b', e => e.textContent);
  for (const p of pages.slice(1)) { await p.fill('#code', code); await p.click('[data-a=join]'); }
  await pages[0].waitForFunction(() => S && S.players.length === 4, null, { timeout: 15000 });
  await pages[1].waitForFunction(() => S && S.players.length === 4, null, { timeout: 15000 });
  await pages[1].screenshot({ path: __dirname + '/shots/on-lobby-guest.png' });
  await pages[0].screenshot({ path: __dirname + '/shots/on-lobby-host.png' });
  await pages[0].click('[data-a=start]');
  const shots = new Set(); let steps = 0; const t0 = Date.now(); let reloaded = false;
  const stepPage = async (p, i) => {
    if (await p.$('.king')) return;
    const kind = await p.evaluate(() => S && (S.phase + ':' + (S.cur ? S.cur.kind + (S.cur.st ? '/' + S.cur.st : '') : ''))).catch(() => null);
    if (i === 1 && kind && !shots.has(kind)) { shots.add(kind); await p.waitForTimeout(kind.startsWith('show') ? 1900 : kind === 'ask:career' ? 7600 : 450); await p.screenshot({ path: __dirname + `/shots/on-${kind.replace(/[:\/]/g, '_')}.png` }); }
    for (const a of ['cgo', 'bgo']) { const b = await p.$(`[data-a=${a}]`); if (b) return b.click(); }
    const txt = await p.$('#txt');
    if (txt) { await txt.fill(['بطيخ', 'جدّي بالمطبخ', 'عمّان', 'سمكة طايرة'][i] + (steps % 3 ? '' : ' ' + steps)); return p.click('[data-a=text]'); }
    if (await p.$('[data-a=num]')) { await p.$eval('#rng', (r) => { r.value = String(Math.floor(Math.random() * (+r.max + 1))); }); return p.click('[data-a=num]'); }
    let o = await p.$$('[data-a=career]'); if (o.length) return o[Math.floor(Math.random() * o.length)].click();
    o = await p.$$('[data-a=ans]:not([disabled])'); if (o.length) return o[Math.floor(Math.random() * o.length)].click();
    o = await p.$$('[data-a=cok]'); if (o.length) return o[Math.floor(Math.random() * o.length)].click();
    const bp = await p.$('[data-a=bpass]'); if (bp) { await p.waitForTimeout(950); return bp.click().catch(() => {}); }
    const j = await p.$('[data-a=joker][aria-pressed=false]'); if (j && Math.random() < .15) return j.click();
    const go = await p.$('[data-a=go]'); if (go) { await p.waitForTimeout(150); return go.click().catch(() => {}); }
  };
  while (Date.now() - t0 < 110000) {
    const kings = await Promise.all(pages.map(p => p.$('.king')));
    if (kings.every(Boolean)) break;
    for (let i = 0; i < pages.length; i++) await stepPage(pages[i], i).catch(() => {});
    steps++;
    // فحص: صاحب الغرفة بيعمل ريفرش بنص اللعبة وبيرجع
    if (!reloaded && await pages[0].evaluate(() => S && S.si === 2).catch(() => false)) {
      reloaded = true;
      await pages[0].reload({ waitUntil: 'load' });
      await pages[0].click('[data-a=back2room]');
      await pages[0].waitForFunction(() => S && S.phase !== 'lobby' && mode === 'host', null, { timeout: 15000 });
      // وضيف كمان بيعمل ريفرش
      await pages[2].reload({ waitUntil: 'load' });
      await pages[2].click('[data-a=back2room]');
      await pages[2].waitForFunction(() => S && S.players && mode === 'guest', null, { timeout: 15000 });
      console.log('reload host+guest ok at stage', await pages[0].evaluate(() => S.si + 1));
    }
    await pages[0].waitForTimeout(60);
  }
  await pages[0].waitForTimeout(700);
  const res = await Promise.all(pages.map(p => p.evaluate(() => S.phase + ' ' + S.players.map(x => x.name + ':' + x.score).join(' '))));
  console.log('secs', Math.round((Date.now() - t0) / 1000), 'steps', steps, 'reloaded', reloaded);
  res.forEach((r, i) => console.log(names[i], '=>', r));
  console.log('all same:', new Set(res).size === 1);
  console.log('guest kinds:', [...shots].join(' '));
  await pages[1].screenshot({ path: __dirname + '/shots/on-final-guest.png', fullPage: true });
  console.log('errors:', errs.length ? [...new Set(errs)].join(' ; ') : 'none');
  await browser.close();
})();
