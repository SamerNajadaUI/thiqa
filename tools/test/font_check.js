// فحص الخط: بكل صفحة، رابط خطوط جوجل لازم يتحوّل لـmedia="all" بعد التحميل وبدون أخطاء JS.
// خطوط جوجل محجوبة بالجلسة السحابية، فبنرجّع CSS وهمي عشان onload يشتغل فعلاً.
// الاستعمال: (cd docs && python3 -m http.server 8765) ثم node tools/test/font_check.js
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const { adminInit } = require('./session.js');
const DOCS = path.join(__dirname, '../../docs');
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
const pages = walk(DOCS).filter((f) => f.endsWith('.html') && fs.readFileSync(f, 'utf8').includes('fonts.googleapis.com/css')).map((f) => path.relative(DOCS, f)).sort();
(async () => {
  const b = await chromium.launch();
  const c = await b.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
  await c.addInitScript(adminInit);
  await c.route(/fonts\.googleapis\.com/, (r) => r.fulfill({ status: 200, contentType: 'text/css', body: 'body{}' }));
  let bad = 0;
  for (const u of pages) {
    const p = await c.newPage(); const errs = []; p.on('pageerror', (e) => errs.push(e.message));
    await p.goto('http://localhost:8765/' + u); await p.waitForTimeout(500);
    const m = await p.evaluate(() => [...document.querySelectorAll('link[href*="fonts.googleapis.com/css"]')].map((l) => l.media));
    const ok = m.length && m.every((x) => x === 'all') && !errs.length;
    if (!ok) { bad++; console.log('✗', u, JSON.stringify(m), errs.join(' | ').slice(0, 160)); }
    await p.close();
  }
  console.log(bad ? `✗ ${bad} صفحة الخط فيها مش شغّال` : `✓ الخط شغّال بكل الصفحات (${pages.length})`);
  await b.close(); process.exit(bad ? 1 : 0);
})();
