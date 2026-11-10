// فحص سيستم التصميم: (1) ما في hex خارج جدول البراند، (2) تباين WCAG للأزواج الأساسية بالفاتح والغامق.
// node ds_check.js
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const D = path.join(__dirname, '../../docs');
const css = fs.readFileSync(D + '/ds/ds.css', 'utf8');
const palBlock = css.slice(css.indexOf(':root {'), css.indexOf('}', css.indexOf(':root {')));
const PAL = {}; for (const m of palBlock.matchAll(/--c-([\w-]+):\s*(#[0-9A-Fa-f]{6})/g)) PAL[m[1]] = m[2].toUpperCase();
assert.equal(Object.keys(PAL).length, 16, 'الباليت 16 لون');
const allowed = new Set(Object.values(PAL));
let bad = [];
for (const f of ['ds/ds.css', 'ds/ui.css', 'ds/index.html', 'index.html', 'login.html', 'rewards.html', 'settings.html', 'app/ui.js']) {
  let t = fs.readFileSync(D + '/' + f, 'utf8');
  if (f === 'ds/ds.css') t = t.replace(palBlock, '');
  t = t.replace(/<meta name="theme-color"[^>]*>/g, '');           // meta بالـhead
  for (const m of t.matchAll(/#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b/g)) if (!allowed.has(m[0].toUpperCase())) bad.push(f + ' ' + m[0]);
}
assert.deepEqual(bad, [], 'ألوان خارج البراند: ' + bad.join(', '));
console.log('✓ ما في ألوان خارج جدول البراند');

const lum = (h) => { const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const mix = (a, b, pa) => '#' + [1, 3, 5].map((i) => Math.round(parseInt(a.slice(i, i + 2), 16) * pa + parseInt(b.slice(i, i + 2), 16) * (1 - pa)).toString(16).padStart(2, '0')).join('');
const cr = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const P = (k) => PAL[k];
const cardDark = mix(P('ink'), P('medium-ink'), 0.84), softLight = mix(P('light-stone'), P('light-orange'), 0.55);
const brandSoftLight = mix(P('soft-orange'), P('light-orange'), 0.32), brandSoftDark = mix(P('ink'), P('dark-orange'), 0.70);
const pairs = [   // [وصف، نص، خلفية، أدنى نسبة]
  ['فاتح: نص على خلفية', P('ink'), P('light-orange'), 7], ['فاتح: نص على كرت', P('ink'), P('white'), 7],
  ['فاتح: نص ثانوي على خلفية', P('medium-ink'), P('light-orange'), 4.5], ['فاتح: نص ثانوي على soft', P('medium-ink'), softLight, 4.5],
  ['زر أساسي: Ink على برتقالي', P('ink'), P('orange'), 4.5], ['زر قوي: أبيض على Dark Orange', P('white'), P('dark-orange'), 4.5],
  ['فاتح: نص برتقالي على brand-soft', P('dark-orange'), brandSoftLight, 4.5], ['فاتح: شارة على brand-soft', P('dark-orange'), brandSoftLight, 4.5],
  ['غامق: نص على خلفية', P('light-orange'), P('ink'), 7], ['غامق: نص على كرت', P('light-orange'), cardDark, 7],
  ['غامق: نص ثانوي على كرت', P('stone'), cardDark, 4.5], ['غامق: نص برتقالي فاتح على brand-soft', P('medium-orange'), brandSoftDark, 4.5],
  ['غامق: Ink على برتقالي (فعّال)', P('ink'), P('orange'), 4.5],
  ['شارة بلس فاتح', P('soft-orange'), P('ink'), 7], ['شارة بلس غامق', P('ink'), P('soft-orange'), 7],
];
let fail = 0;
for (const [n, fg, bg, min] of pairs) { const r = cr(fg, bg); const ok = r >= min; if (!ok) fail++; console.log(ok ? '✓' : '✗', n, r.toFixed(2) + ':1', '(≥' + min + ')'); }
console.log('ملاحظة: أبيض على البرتقالي', cr(P('white'), P('orange')).toFixed(2) + ':1 (لهيك نص الأزرار Ink)');
process.exit(fail ? 1 : 0);
