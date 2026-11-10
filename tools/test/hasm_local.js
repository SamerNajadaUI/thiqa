// «ليلة الحسم» على تلفون واحد: موسم كامل آلياً مع ريفرش بالنص.
// node hasm_local.js [عدد اللاعبين=3] [quick|full] [slow]   (slow = بدون ?fast، لصور الأنيميشن)
const { chromium } = require('playwright');
const fs = require('fs');
const N = +(process.argv[2] || 3), LEN = process.argv[3] || 'quick', SLOW = process.argv[4] === 'slow';
const URL = 'http://localhost:8765/games/hasm.html' + (SLOW ? '' : '?fast');
const SHOTS = __dirname + '/shots';
const names = ['سامر', 'ليلى', 'خالد', 'نور', 'عمر', 'هبة'].slice(0, N);
(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com|cdn\.jsdelivr\.net/, (r) => r.abort());
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|ERR_FAILED/.test(m.text())) errs.push('console: ' + m.text()); });
  await p.goto(URL, { waitUntil: 'load' });
  await p.screenshot({ path: `${SHOTS}/hasm-home.png` });
  if (N === 1) { await p.fill('#name', names[0]); await p.click('[data-a=solo]'); }
  else {
    await p.click('[data-a=one]');
    for (let i = 2; i < N; i++) await p.click('[data-a=addp]');
    const ins = await p.$$('#nl input');
    for (let i = 0; i < N; i++) await ins[i].fill(names[i]);
  }
  await p.click(`[data-a=llen][data-v=${LEN}]`);
  await p.screenshot({ path: `${SHOTS}/hasm-setup${N === 1 ? '-solo' : ''}.png` });
  await p.click('[data-a=lgo]');
  await p.waitForFunction(() => S && S.clubs, null, { timeout: 15000 });
  const seen = new Set(); let reloaded = false, steps = 0; const t0 = Date.now();
  const shot = async (name, delay = 250) => { if (seen.has(name)) return; seen.add(name); await p.waitForTimeout(delay); await p.screenshot({ path: `${SHOTS}/hasm-${name}.png`, fullPage: true }); };
  while (Date.now() - t0 < (SLOW ? 900000 : 150000)) {
    steps++;
    const st = await p.evaluate(() => ({ phase: S.phase, md: S.md, seg: S.seg, key: lastKey, shown: !!shown[phaseKey()] }));
    if (st.phase === 'final') break;
    const tag = st.key.replace(/:l\d/g, '').replace(/[:\/]/g, '_').replace(/_\d+_\d+/, '');
    if (!reloaded && st.phase === 'seg' && st.md === 1) {       // ريفرش بنص الموسم
      reloaded = true;
      await p.reload({ waitUntil: 'load' });
      await p.click('[data-a=resume]');
      await p.waitForFunction(() => S && S.clubs && mode === 'local');
      console.log('reload ok at md', st.md + 1);
      continue;
    }
    if (await p.$('[data-a=hand]')) { await shot('pass'); await p.click('[data-a=hand]'); continue; }
    const opts = await p.$$('[data-a=pans]');
    if (opts.length) { await shot('puzzle-' + await p.evaluate(() => S.puzzle.type)); await opts[Math.floor(Math.random() * 4)].click(); continue; }
    if (await p.$('[data-a=psend]')) {
      const q = await p.$$('[data-a=bidset]'); await q[Math.floor(Math.random() * 4)].click();
      if (Math.random() < 0.5) await p.click('[data-a=bidstep][data-v="5"]');
      await shot('bid'); await p.click('[data-a=psend]'); continue;
    }
    if (await p.$('[data-a=ssend]')) {
      const a = await p.$$('[data-a=att]'), d = await p.$$('[data-a=def]'), c = await p.$$('[data-a=card]:not([disabled])');
      await a[Math.floor(Math.random() * 3)].click(); await d[Math.floor(Math.random() * 3)].click();
      if (c.length && Math.random() < 0.7) await c[0].click();
      await shot('seg' + st.seg + (c.length ? '-cards' : '')); await p.click('[data-a=ssend]'); continue;
    }
    if (st.phase === 'prepShow' || st.phase === 'segShow') {
      if (SLOW && st.phase === 'segShow' && !st.shown) {       // صور من نص الأنيميشن
        for (const sel of ['.duel .c.d.on', '.verdict.on', '.goalfx', '.varfx', '.bannerfx']) if (!seen.has('mid' + sel) && await p.$(sel)) { seen.add('mid' + sel); await p.waitForTimeout(350); await p.screenshot({ path: `${SHOTS}/hasm-mid${sel.replace(/[ .]+/g, '-')}.png` }); }
      }
      if (!st.shown) { await p.waitForTimeout(SLOW ? 200 : 60); continue; }
      await shot(st.phase + (st.phase === 'segShow' ? st.seg : ''));
    } else await shot(tag, st.phase === 'intro' ? 1500 : 450);
    const go = await p.$('[data-a=go]');
    if (go) { await go.click().catch(() => {}); continue; }
    await p.waitForTimeout(80);
  }
  await p.waitForSelector('.champ', { timeout: 5000 });
  await p.waitForTimeout(SLOW ? 4000 : 800);
  await p.screenshot({ path: `${SHOTS}/hasm-final.png`, fullPage: true });
  const fin = await p.evaluate(() => ({ champ: K.club(S, S.fin.champ).name, md: S.md, mds: S.mds, clubs: S.clubs.length, story: S.fin.story.length, awards: S.fin.awards.length, loser: S.fin.loser, saved: !!mem.get('local', null) }));
  // موسم جديد من شاشة النهاية
  await p.click('[data-a=again]');
  await p.waitForFunction(() => S && S.phase === 'intro' && S.md === -1, null, { timeout: 10000 });
  console.log(JSON.stringify({ n: N, len: LEN, steps, secs: Math.round((Date.now() - t0) / 1000), reloaded, fin, shots: seen.size, errs }));
  await browser.close();
  process.exit(errs.length || fin.md !== fin.mds ? 1 : 0);
})().catch((e) => { console.error('FAIL', e); process.exit(1); });
