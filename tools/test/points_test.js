// فحص «جمع نقاط» 2: لعبة كاملة على تلفون واحد (2 و3 فرق، مع جولة السرعة والرهان الأخير)، وغرفة من 3 تلفونات.
// الاستعمال: node broker.js & ; cd docs && python3 -m http.server 8765 ; node points_test.js [local|room|all]
const { chromium } = require('playwright');
const fs = require('fs');
const { adminInit } = require('./session.js');
const MQ = fs.readFileSync(__dirname + '/node_modules/mqtt/dist/mqtt.min.js', 'utf8');
const U = 'http://localhost:8765/games/points.html';
const SH = process.env.SHOTS || '/tmp/pts';
fs.mkdirSync(SH, { recursive: true });
const which = process.argv[2] || 'all';
let bad = 0;
async function ctxNew(b) {
  const c = await b.newContext({ viewport: { width: 390, height: 844 } });
  await c.addInitScript(adminInit);
  await c.route('**/mqtt.min.js', (r) => r.fulfill({ contentType: 'application/javascript', body: MQ }));
  await c.route(/fonts\.(googleapis|gstatic)\.com|wikimedia|espncdn|flagcdn|wikipedia/, (r) => r.abort());
  return c;
}
const watch = (p, tag) => p.on('pageerror', (e) => { bad++; console.log('✗', tag, e.message); });
const phase = (p) => p.evaluate(() => (typeof S !== 'undefined' && S ? S.phase + ':' + (S.rush ? S.rush.st : S.fin ? S.fin.st : '') : 'none'));
async function clickAny(p, sels) { for (const s of sels) { const el = await p.$(s); if (el) { try { await el.click({ timeout: 1500 }); return s; } catch {} } } return null; }

async function localGame(b, nTeams, cats, tag) {
  const c = await ctxNew(b); const p = await c.newPage(); watch(p, tag);
  await p.goto(U); await p.waitForSelector('#one');
  await p.screenshot({ path: `${SH}/${tag}-intro.png` });
  await p.click('#one'); await p.click(`[data-n="${nTeams}"]`); await p.click('#go');
  await p.waitForSelector('[data-c]');
  await p.click('#sett'); await p.click('[data-aid="dbl"]'); await p.click('[data-secs="20"]');
  await p.click(`[data-cn="${cats.length}"]`);
  for (const id of cats) await p.click(`[data-c="${id}"]`);
  await p.screenshot({ path: `${SH}/${tag}-cats.png`, fullPage: false });
  await p.click('#go');
  await p.waitForSelector('.board', { timeout: 20000 });
  await p.waitForTimeout(400);
  await p.screenshot({ path: `${SH}/${tag}-board.png` });
  const seen = new Set(); let steps = 0; const t0 = Date.now();
  while (Date.now() - t0 < 600000) {
    steps++;
    const ph = await phase(p);
    if (!seen.has(ph)) { seen.add(ph); await p.waitForTimeout(ph.startsWith('rush') || ph.startsWith('final') ? 900 : 300); await p.screenshot({ path: `${SH}/${tag}-${ph.replace(/:/g, '_')}.png` }); }
    if (ph.startsWith('over')) break;
    if (ph.startsWith('board')) { const cells = await p.$$('.lv:not(.done)'); if (cells.length) await cells[Math.floor(Math.random() * cells.length)].click().catch(() => {}); }
    else if (ph.startsWith('q')) {
      if (Math.random() < 0.15) { const h = await p.$$('[data-h]:not([disabled])'); if (h.length) { p.once('dialog', (d) => d.accept()); await h[0].click().catch(() => {}); continue; } }
      if (!(await clickAny(p, ['[data-card]']))) { const o = await p.$$('.opt:not([disabled])'); if (o.length) await o[Math.floor(Math.random() * o.length)].click().catch(() => {}); }
    }
    else if (ph.startsWith('res')) await clickAny(p, ['#next']);
    else if (ph.startsWith('rush')) { if (!(await clickAny(p, ['[data-rb]:not([disabled])']))) { const o = await p.$$('.opt:not([disabled])'); if (o.length) await o[Math.floor(Math.random() * o.length)].click().catch(() => {}); else await clickAny(p, ['#next']); } }
    else if (ph.startsWith('final')) { if (!(await clickAny(p, ['#ready', '[data-bet]']))) { const o = await p.$$('.opt:not([disabled])'); if (o.length) await o[Math.floor(Math.random() * o.length)].click().catch(() => {}); else await clickAny(p, ['#next']); } }
    await p.waitForTimeout(120);
  }
  await p.waitForTimeout(800);
  await p.screenshot({ path: `${SH}/${tag}-over.png`, fullPage: true });
  const res = await p.evaluate(() => ({ phase: S.phase, scores: S.teams.map((t) => t.name + ':' + t.score), done: S.done + '/' + S.total, awards: (S.awards || []).map((a) => a.title) }));
  console.log(res.phase === 'over' ? '✓' : '✗', tag, 'steps', steps, 'secs', Math.round((Date.now() - t0) / 1000), JSON.stringify(res), [...seen].join(' '));
  if (res.phase !== 'over') bad++;
  await c.close();
}

async function roomGame(b) {
  const ps = [];
  for (let i = 0; i < 3; i++) { const c = await ctxNew(b); const p = await c.newPage(); watch(p, 'room' + i); ps.push(p); }
  const [h, a, z] = ps;
  await h.goto(U + '?broker=ws://localhost:8883'); await h.fill('#tname', 'الصقور'); await h.click('#create');
  await h.waitForSelector('.code'); const code = (await h.textContent('.code')).trim();
  for (const [p, n] of [[a, 'النمور'], [z, 'الأسود']]) { await p.goto(U + '?broker=ws://localhost:8883&room=' + code); await p.fill('#tname', n); await p.click('#join'); }
  await h.waitForFunction(() => S && S.teams.length === 3, null, { timeout: 15000 });
  await h.screenshot({ path: `${SH}/room-lobby.png` });
  await h.click('#begin'); await h.waitForSelector('[data-c]');
  await h.click('[data-cn="2"]');
  for (const id of ['g_math', 'general']) await h.click(`[data-c="${id}"]`);
  await h.click('#go');
  const t0 = Date.now(); let steps = 0; const seen = new Set();
  while (Date.now() - t0 < 600000) {
    steps++;
    const ph = await phase(h);
    if (!seen.has(ph)) { seen.add(ph); await a.waitForTimeout(500); await a.screenshot({ path: `${SH}/room-${ph.replace(/:/g, '_')}.png` }); }
    if (ph.startsWith('over')) break;
    for (const p of ps) {
      if (ph.startsWith('board')) { const cells = await p.$$('.board:not(.wait) .lv:not(.done)'); if (cells.length) { await cells[Math.floor(Math.random() * cells.length)].click().catch(() => {}); break; } }
      else if (ph.startsWith('final')) { await clickAny(p, ['[data-bet]']) || (await (async () => { const o = await p.$$('.opt:not([disabled])'); if (o.length) await o[Math.floor(Math.random() * o.length)].click().catch(() => {}); })()); }
      else { if (await clickAny(p, ['[data-card]'])) continue; const o = await p.$$('.opt:not([disabled])'); if (o.length) await o[Math.floor(Math.random() * o.length)].click().catch(() => {}); }
    }
    if (ph.startsWith('res') || ph.endsWith(':res') || ph.endsWith(':intro') || ph.endsWith(':rev')) await clickAny(h, ['#next']);
    await h.waitForTimeout(150);
  }
  await a.waitForTimeout(1200);
  const fin = await Promise.all(ps.map((p) => p.evaluate(() => S && S.phase + ' ' + S.teams.map((t) => t.score).join(','))));
  console.log(fin.every((x) => x === fin[0] && x.startsWith('over')) ? '✓' : '✗', 'room 3 phones', 'steps', steps, 'secs', Math.round((Date.now() - t0) / 1000), fin.join(' | '), [...seen].join(' '));
  if (!fin.every((x) => x === fin[0] && x.startsWith('over'))) bad++;
  await z.screenshot({ path: `${SH}/room-over.png`, fullPage: true });
}

(async () => {
  const b = await chromium.launch();
  if (which !== 'room') {
    await localGame(b, 2, process.env.QUICK ? ['g_math', 'general'] : ['g_math', 'general', 'islamic'], 'l2');
    await localGame(b, 3, ['g_club', 'g_old'], 'l3');
    if (which === 'all') await localGame(b, 5, ['g_nat', 'g_face'], 'l5');
  }
  if (which !== 'local') await roomGame(b);
  await b.close();
  console.log(bad ? `✗ ${bad} مشاكل` : 'كله تمام بدون أخطاء JS');
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.log('✗', e.message.split('\n')[0]); process.exit(1); });
