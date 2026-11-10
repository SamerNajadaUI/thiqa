// «ليلة الحسم» بغرفة: 3 تلفونات + كمبيوتر على بروكر محلي، مع ريفرش لصاحب الغرفة ولضيف،
// وضيف ما بيختار (صاحب الغرفة بيكمّل بدونه)، وفحص إنه الأسرار ما بتنبعث قبل الكشف.
// قبلها: node broker.js &   و   (cd ../../docs && python3 -m http.server 8765 &)
const { chromium } = require('playwright');
const fs = require('fs');
const mqtt = require('mqtt');
const MQ = fs.readFileSync(__dirname + '/node_modules/mqtt/dist/mqtt.min.js', 'utf8');
const BROKER = 'ws://localhost:8883';
const URL = 'http://localhost:8765/games/hasm.html?fast&broker=' + encodeURIComponent(BROKER);
const SHOTS = __dirname + '/shots';
const names = ['سامر', 'ليلى', 'خالد'];
(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const errs = [], pages = [], leaks = [];
  for (const n of names) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    await ctx.route('**/mqtt.min.js', (r) => r.fulfill({ contentType: 'application/javascript', body: MQ }));
    await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errs.push(n + ': ' + e.message));
    p.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|ERR_FAILED/.test(m.text())) errs.push(n + ' console: ' + m.text()); });
    await p.goto(URL, { waitUntil: 'load' });
    await p.fill('#name', n);
    pages.push(p);
  }
  await pages[0].click('[data-a=create]');
  await pages[0].waitForSelector('.roomcode b');
  const code = await pages[0].$eval('.roomcode b', (e) => e.textContent);
  // جاسوس على البروكر: بيقرا كل حالة منشورة وبيتأكد ما فيها أسرار
  const spy = mqtt.connect(BROKER);
  spy.on('connect', () => spy.subscribe(`abuodeh-hasm-v1/${code}/s`));
  spy.on('message', (_, buf) => {
    const txt = buf.toString(); if (!txt) return;
    const s = JSON.parse(txt);
    if (s.rs) leaks.push('rs');
    if (s.H || /"bid":\d+,"ans"|"prep":\{/.test(txt)) leaks.push('H');
    if (s.clubs && (s.phase === 'prep' || s.phase === 'news') && s.puzzle.ans !== null) leaks.push('puzzle.ans@' + s.phase);
    if (s.clubs && s.phase === 'prep' && s.show) leaks.push('show@prep');
    if (s.clubs && s.phase === 'seg' && (s.show || s.matches.some((m) => m.plays.some((p) => p.seg === s.seg)))) leaks.push('plays@seg');
  });
  for (const p of pages.slice(1)) { await p.fill('#code', code); await p.click('[data-a=join]'); }
  for (const p of pages) await p.waitForFunction(() => S && S.players && S.players.length === 3, null, { timeout: 15000 });
  await pages[1].screenshot({ path: `${SHOTS}/hasm-on-lobby-guest.png` });
  await pages[0].screenshot({ path: `${SHOTS}/hasm-on-lobby-host.png` });
  await pages[0].click('[data-a=cfg][data-v=quick]');
  await pages[0].click('[data-a=start]');
  for (const p of pages) await p.waitForFunction(() => S && S.clubs, null, { timeout: 15000 });
  const seen = new Set(); let reloaded = false, forced = false, autoSeen = false; const t0 = Date.now();
  const stepPage = async (p, i) => {
    const st = await p.evaluate(() => (S && S.clubs ? { phase: S.phase, md: S.md, seg: S.seg, shown: !!shown[phaseKey()], done: S.done.length, me: S.done.includes(me.id) } : null)).catch(() => null);
    if (!st || st.phase === 'final') return;
    const name = `${st.phase}${st.phase.startsWith('seg') ? st.seg : ''}`;
    if (i === 1 && !seen.has(name) && (st.shown || !/Show/.test(st.phase))) { seen.add(name); await p.waitForTimeout(300); await p.screenshot({ path: `${SHOTS}/hasm-on-${name}.png`, fullPage: true }); }
    const lazy = i === 2 && st.md === 0 && st.phase === 'seg' && st.seg === 0;   // خالد ما بيختار بأول شوط
    const opts = await p.$$('[data-a=pans]');
    if (opts.length) return opts[Math.floor(Math.random() * 4)].click();
    if (await p.$('[data-a=psend]')) { const q = await p.$$('[data-a=bidset]'); await q[1 + Math.floor(Math.random() * 3)].click(); return p.click('[data-a=psend]'); }
    if (await p.$('[data-a=ssend]') && !lazy) {
      const a = await p.$$('[data-a=att]'), d = await p.$$('[data-a=def]'), c = await p.$$('[data-a=card]:not([disabled])');
      await a[Math.floor(Math.random() * 3)].click(); await d[Math.floor(Math.random() * 3)].click();
      if (c.length && Math.random() < 0.7) await c[0].click();
      return p.click('[data-a=ssend]');
    }
    if (i !== 0) return;
    if (st.phase === 'prep' || st.phase === 'seg') {
      if (lazy || !(st.md === 0 && st.phase === 'seg' && st.seg === 0) || st.done < 2) return;
      forced = true; return p.click('[data-a=go]');                                // «كمّل بدون الباقي»
    }
    if (/Show/.test(st.phase) && !st.shown) return;
    const go = await p.$('.btn[data-a=go]'); if (go) return go.click().catch(() => {});
  };
  while (Date.now() - t0 < 150000) {
    if ((await Promise.all(pages.map((p) => p.$('.champ')))).every(Boolean)) break;
    for (let i = 0; i < pages.length; i++) await stepPage(pages[i], i).catch(() => {});
    if (!autoSeen) autoSeen = await pages[1].evaluate(() => !!(S && S.show && S.show.auto && S.show.auto.length === 1)).catch(() => false);
    if (!reloaded && await pages[0].evaluate(() => S && S.clubs && S.md === 1 && S.phase === 'seg').catch(() => false)) {
      reloaded = true;                                                             // ريفرش لصاحب الغرفة ولضيف بنص الموسم
      await pages[0].reload({ waitUntil: 'load' }); await pages[0].click('[data-a=back2room]');
      await pages[0].waitForFunction(() => S && S.clubs && mode === 'host' && H && H.seg, null, { timeout: 15000 });
      await pages[2].reload({ waitUntil: 'load' }); await pages[2].click('[data-a=back2room]');
      await pages[2].waitForFunction(() => S && S.clubs && mode === 'guest', null, { timeout: 15000 });
      console.log('reload host+guest ok at md', await pages[0].evaluate(() => S.md + 1));
    }
    await pages[0].waitForTimeout(60);
  }
  for (const p of pages) await p.waitForSelector('.champ', { timeout: 5000 });
  await pages[1].waitForTimeout(700);
  await pages[1].screenshot({ path: `${SHOTS}/hasm-on-final-guest.png`, fullPage: true });
  const fins = await Promise.all(pages.map((p) => p.evaluate(() => JSON.stringify([S.fin.order, S.clubs.map((c) => [c.pts, c.gf, c.ga, c.budget])]))));
  const same = fins.every((f) => f === fins[0]);
  const guestH = await pages[1].evaluate(() => H === null && S.rs === 0);
  // موسم جديد: صاحب الغرفة بيضغط، والضيوف بيلحقوه
  await pages[0].click('[data-a=again]');
  for (const p of pages) await p.waitForFunction(() => S && S.phase === 'intro' && S.md === -1, null, { timeout: 15000 });
  spy.end(true);
  const out = { secs: Math.round((Date.now() - t0) / 1000), reloaded, forced, autoSeen, same, guestH, leaks: [...new Set(leaks)], shots: seen.size, errs };
  console.log(JSON.stringify(out));
  await browser.close();
  process.exit(errs.length || leaks.length || !same || !reloaded || !forced || !autoSeen || !guestH ? 1 : 0);
})().catch((e) => { console.error('FAIL', e); process.exit(1); });
