// فحص ألعاب الكورة: تلفون واحد للآخر لكل لعبة، وغرفة من 3 تلفونات، وتحدي اللاعبين أونلاين.
// الاستعمال: node broker.js & ; cd docs && python3 -m http.server 8765 ; node kora_test.js
const { chromium } = require('playwright');
const fs = require('fs');
const { adminInit } = require('./session.js');
const MQ = fs.readFileSync(__dirname + '/node_modules/mqtt/dist/mqtt.min.js', 'utf8');
const U = 'http://localhost:8765/games/';
const SH = '/tmp/ks';
const GAMES = ['kworld', 'karab', 'kucl', 'kepl', 'kguess', 'kemoji', 'kkits', 'khair', 'ball'];
let bad = 0;
async function ctxNew(b) {
  const c = await b.newContext({ viewport: { width: 390, height: 844 } });
  await c.addInitScript(adminInit);
  await c.route('**/mqtt.min.js', (r) => r.fulfill({ contentType: 'application/javascript', body: MQ }));
  await c.route(/fonts\.(googleapis|gstatic)\.com|commons\.wikimedia|espncdn/, (r) => r.abort());
  return c;
}
function watch(p, tag) { p.on('pageerror', (e) => { bad++; console.log('✗', tag, e.message); }); }
(async () => {
  const b = await chromium.launch();
  // تلفون واحد
  for (const g of (process.env.ONLY_ROOM ? [] : GAMES)) {
    const c = await ctxNew(b); const p = await c.newPage(); watch(p, g);
    await p.goto(U + g + '.html');
    await p.click('#cnt [data-n="2"]'); await p.click('#qn [data-q="10"]'); await p.click('#go');
    for (let i = 0; i < 10; i++) {
      await p.waitForSelector('.kopt:not([disabled])', { timeout: 15000 });
      if (i === 0) await p.screenshot({ path: `${SH}/${g}-q.png` });
      await p.click(`.kopt >> nth=${i % 4}`);
      await p.waitForSelector('#nx');
      if (i === 0) await p.screenshot({ path: `${SH}/${g}-rev.png` });
      await p.click('#nx');
    }
    await p.waitForSelector('#again');
    await p.screenshot({ path: `${SH}/${g}-end.png` });
    console.log('✓ تلفون واحد', g);
    await c.close();
  }
  // غرفة: 3 تلفونات
  {
    const ps = [];
    for (let i = 0; i < 3; i++) { const c = await ctxNew(b); const p = await c.newPage(); watch(p, 'room' + i); ps.push(p); }
    const [h, a, z] = ps;
    await h.goto(U + 'kworld.html?broker=ws://localhost:8883');
    await h.click('#md [data-m="room"]'); await h.fill('#kn', 'سامر'); await h.click('#kh');
    await h.waitForSelector('.kcode b'); const code = (await h.textContent('.kcode b')).trim();
    for (const [p, n] of [[a, 'أحمد'], [z, 'زيد']]) { await p.goto(U + 'kworld.html?broker=ws://localhost:8883&room=' + code); await p.fill('#kn', n); await p.click('#kj'); }
    await h.waitForFunction(() => document.querySelectorAll('.klist li').length === 3, null, { timeout: 15000 });
    await h.screenshot({ path: `${SH}/room-lobby.png` });
    await h.click('#st');
    for (let i = 0; i < 10; i++) {
      for (const p of ps) { await p.waitForSelector('.kopt:not([disabled])', { timeout: 15000 }); }
      if (i === 0) await a.screenshot({ path: `${SH}/room-q.png` });
      for (const [k, p] of ps.entries()) await p.click(`.kopt >> nth=${k}`);
      await h.waitForSelector('#nx', { timeout: 15000 });
      if (i === 0) await z.screenshot({ path: `${SH}/room-rev.png` });
      await h.click('#nx');
    }
    for (const p of ps) await p.waitForSelector('.standings', { timeout: 15000 });
    await a.screenshot({ path: `${SH}/room-end.png` });
    console.log('✓ غرفة 3 تلفونات', code);
  }
  // تحدي اللاعبين أونلاين: 3 تلفونات بفريقين
  {
    const ps = [];
    for (let i = 0; i < 3; i++) { const c = await ctxNew(b); const p = await c.newPage(); watch(p, 'duel' + i); ps.push(p); }
    const [h, a, z] = ps;
    await h.goto(U + 'duel.html?broker=ws://localhost:8883');
    await h.click('#md [data-m="room"]'); await h.fill('#kn', 'سامر'); await h.click('#kh');
    await h.waitForSelector('.kcode b', { timeout: 20000 }); const code = (await h.textContent('.kcode b')).trim();
    for (const [p, n] of [[a, 'أحمد'], [z, 'زيد']]) { await p.goto(U + 'duel.html?broker=ws://localhost:8883&room=' + code); await p.fill('#kn', n); await p.click('#kj'); }
    await h.waitForSelector('#st:not([disabled])', { timeout: 15000 });
    await h.screenshot({ path: `${SH}/duel-lobby.png` });
    await h.click('#st');
    for (let r = 0; r < 6; r++) {
      // الممثل بيختار المستوى
      let actor = null;
      for (let t = 0; t < 40 && !actor; t++) { for (const p of ps) if (await p.$('[data-l]')) actor = p; if (!actor) await h.waitForTimeout(150); }
      await actor.click('[data-l="1"]');
      for (const p of ps) await p.waitForSelector('#tm');
      await h.waitForTimeout(300);
      const asker = []; for (const p of ps) if (await p.$('#gs')) asker.push(p);
      await asker[0].click('#ask');
      await actor.waitForSelector('#yes');
      if (r === 0) { await actor.screenshot({ path: `${SH}/duel-actor.png` }); await asker[0].screenshot({ path: `${SH}/duel-asker.png` }); }
      await actor.click('#yes');
      await asker[0].waitForSelector('.qlog');
      await asker[0].fill('#gn', 'مين ما كان'); await asker[0].click('#gs');
      await h.waitForSelector('#nx');
      if (r === 0) await a.screenshot({ path: `${SH}/duel-res.png` });
      await h.click('#nx');
    }
    for (const p of ps) await p.waitForSelector('.standings', { timeout: 15000 });
    console.log('✓ تحدي اللاعبين أونلاين');
  }
  await b.close();
  console.log(bad ? `✗ ${bad} أخطاء` : 'كلها تمام بدون أخطاء JS');
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.log('✗', e.message.split('\n')[0]); process.exit(1); });
