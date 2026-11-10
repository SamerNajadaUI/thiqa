// تدفق التطبيق كامل بعرض 390px: سبلاش ← دخول ← رئيسية ← ألعاب ← قفل ← مكافآت ← إعدادات ← أدمن.
// node app_flow.js   (يلزمه: cd docs && python3 -m http.server 8765)
const { chromium } = require('playwright');
const fs = require('fs'), assert = require('node:assert/strict');
const B = 'http://localhost:8765/', SHOTS = __dirname + '/shots';
(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com|cdn\.jsdelivr\.net/, (r) => r.abort());
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', (e) => errs.push(p.url() + ' :: ' + e.message));
  p.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|ERR_FAILED|net::/.test(m.text())) errs.push('console: ' + m.text().slice(0, 200)); });
  const shot = (n) => p.screenshot({ path: `${SHOTS}/app-${n}.png` });
  const ok = (m) => console.log('✓', m);
  const pts = () => p.evaluate(() => Auth.user().points);

  // 1) سبلاش ثم دخول
  await p.goto(B + 'index.html'); await p.waitForTimeout(500); await shot('1-splash');
  await p.waitForURL(/login\.html/, { timeout: 5000 }); ok('السبلاش بيودي على الدخول');
  await shot('2-login');

  // 2) دخول برقم: رقم غلط، كود غلط، ثم صح
  await p.fill('#phone', '0691234567'); await p.click('#b-send');
  await p.waitForSelector('#err:not([hidden])'); ok('رقم غلط بيطلع خطأ');
  await p.fill('#phone', '079 123 4567'); await p.click('#b-send');
  await p.waitForSelector('#f-code:not([hidden])'); await shot('3-code');
  await p.fill('#code', '000000'); await p.click('#b-code');
  await p.waitForSelector('#err:not([hidden])'); ok('كود غلط بيطلع خطأ');
  await p.fill('#code', '123456'); await p.click('#b-code');
  await p.waitForURL(/home\.html/); ok('دخول بالرقم ← الرئيسية');
  await p.waitForSelector('#pts-card .points-big'); await shot('4-home');
  assert.equal(await pts(), 10, 'بونص يومي 10'); ok('بونص يومي +10');
  assert.equal(await p.locator('#games .gcard').count(), 4); ok('4 ألعاب مميزة');
  assert.equal(await p.locator('.apptabs a').count(), 4); ok('شريط تبويب 4');

  // 3) الألعاب: شرائح وترتيب
  await p.click('.apptabs a[href$="games/"]'); await p.waitForURL(/games\/$/);
  await p.waitForSelector('#gres .gcard'); const all = await p.locator('#gres .gcard').count();
  await p.click('[data-f=sec][data-v=fast]'); const fast = await p.locator('#gres .gcard').count();
  assert.ok(fast > 0 && fast < all); ok(`فلتر قسم (${all} ← ${fast})`);
  await p.click('[data-f=sec][data-v=all]'); await p.click('[data-f=sort][data-v=group]');
  assert.ok(await p.locator('#gres .gcard').count() > 0); ok('ترتيب جماعي');
  await p.click('[data-f=sort][data-v=pop]'); await p.click('[data-f=sec][data-v=strat]');
  assert.ok(await p.locator('#gres .gcard.locked').count() >= 2); await shot('5-games'); ok('كروت مقفولة ظاهرة');

  // 4) لعبة مقفولة ← مكافآت
  await p.goto(B + 'games/auction.html'); await p.waitForURL(/rewards\.html\?locked=auction/); ok('المزاد مقفول للمجاني');
  await p.waitForSelector('#plans [data-plan=plus_m]'); await shot('6-rewards-locked');
  await p.click('[data-plan=plus_m]'); await p.waitForSelector('.badge.plus');
  await p.goto(B + 'games/auction.html'); await p.waitForTimeout(600);
  assert.ok(/games\/auction\.html/.test(p.url())); ok('بعد بلس بيفتح المزاد');
  assert.equal(await p.evaluate(() => Rewards.multiplier(Auth.user().plan)), 2);
  const before = await pts(); const add = await p.evaluate(() => Rewards.finish('auction', 20));
  assert.equal(add, 40); assert.equal(await pts(), before + 40); ok('نقاط ×2 (+40)');

  // 5) إعدادات: اسم + غامق
  await p.goto(B + 'settings.html'); await p.fill('#nm', 'سامر'); await p.click('#save');
  assert.equal(await p.evaluate(() => Auth.user().name), 'سامر'); ok('تغيير الاسم');
  await p.click('[data-theme-set=dark]'); await p.waitForTimeout(300); await shot('7-settings-dark');
  await p.goto(B + 'home.html'); await p.waitForSelector('#pts-card .points-big'); await shot('8-home-dark');
  await p.goto(B + 'rewards.html'); await p.waitForSelector('.points-big'); await shot('9-rewards-dark');
  await p.click('[data-theme-set=light]').catch(() => {});

  // 6) خروج، رابط مباشر للعبة بدون دخول يرجّع للعبة بعد الدخول
  await p.goto(B + 'settings.html'); await p.click('#out'); await p.waitForURL(/login\.html/); ok('خروج');
  await p.goto(B + 'games/speed.html'); await p.waitForURL(/login\.html\?next=/);
  await p.click('#b-admin-open'); await p.fill('#au', 'admin'); await p.fill('#ap', 'wrong'); await p.click('#f-admin button[type=submit]');
  await p.waitForSelector('#err:not([hidden])'); ok('باسورد أدمن غلط ممنوع');
  await p.fill('#ap', 'admin'); await p.click('#f-admin button[type=submit]');
  await p.waitForURL(/games\/speed\.html/); ok('أدمن ← رجع للعبة المطلوبة (next)');
  assert.equal(await p.evaluate(() => Auth.user().plan), 'admin');
  await p.goto(B + 'games/wheel.html'); await p.waitForTimeout(500); assert.ok(/wheel\.html/.test(p.url())); ok('الأدمن يفتح المقفولة');
  const big = await p.evaluate(() => { let t = 0; for (let i = 0; i < 40; i++) t += Rewards.add(20); return t; });
  assert.equal(big, 1600); ok('الأدمن بدون سقف يومي');

  // 7) ثغرة next: رابط خارجي ما بيتبع
  await p.evaluate(() => Auth.signOut());
  await p.goto(B + 'login.html?next=' + encodeURIComponent('https://evil.example/x'));
  await p.click('#b-google'); await p.waitForURL(/home\.html/); ok('next خارجي بيتجاهل');

  // 8) صفحة سيستم التصميم + لعبة قديمة شغّالة
  await p.goto(B + 'ds/index.html'); await p.waitForSelector('.sws'); await shot('10-ds');
  await p.goto(B + 'games/hasm.html?fast'); await p.waitForTimeout(800); await shot('11-hasm');
  await browser.close();
  if (errs.length) { console.log('أخطاء JS:\n' + errs.join('\n')); process.exit(1); }
  console.log('كل التدفق تمام، وما في أخطاء JS');
})().catch((e) => { console.error('FAIL', e.message); process.exit(1); });
