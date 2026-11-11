// فحص سيستم التصميم: (1) ما في hex خارج جدول البراند، (2) تباين WCAG للأزواج الأساسية بالفاتح والغامق.
// node ds_check.js
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const D = path.join(__dirname, '../../docs');
const css = fs.readFileSync(D + '/ds/ds.css', 'utf8');
const palBlock = css.slice(css.indexOf(':root {'), css.indexOf('}', css.indexOf(':root {')));
const PAL = {}; for (const m of palBlock.matchAll(/--c-([\w-]+):\s*(#[0-9A-Fa-f]{6})/g)) PAL[m[1]] = m[2].toUpperCase();
assert.equal(Object.keys(PAL).length, 27, 'الباليت 27 لون');
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
const pairs = [   // [وصف، نص، خلفية، أدنى نسبة]
  ['فاتح: حبر على ورق', P('layl'), P('waraq'), 7], ['فاتح: حبر على كرت', P('layl'), P('white'), 7], ['فاتح: حبر على soft', P('layl'), P('waraq-2'), 7],
  ['فاتح: ثانوي على ورق', P('muted'), P('waraq'), 4.5], ['فاتح: ثانوي على كرت', P('muted'), P('white'), 4.5], ['فاتح: ثانوي على soft', P('muted'), P('waraq-2'), 4.5],
  ['فاتح: نص لمبة على كرت', P('lamba-text'), P('white'), 4.5], ['فاتح: نص لمبة على soft', P('lamba-text'), P('waraq-2'), 4.5],
  ['فاتح: نص جمر على ورق', P('jamr-text'), P('waraq'), 4.5], ['فاتح: نص نعنع على ورق', P('nanaa-text'), P('waraq'), 4.5], ['فاتح: نص توت على ورق', P('toot-text'), P('waraq'), 4.5],
  ['فاتح: حدود التحكم على ورق', P('control'), P('waraq'), 3], ['فاتح: التركيز على كرت', P('toot-text'), P('white'), 3],
  ['غامق: ورق على ليل', P('waraq'), P('layl'), 7], ['غامق: ورق على كرت', P('waraq'), P('layl-2'), 7], ['غامق: ورق على soft', P('waraq'), P('layl-3'), 7],
  ['غامق: ثانوي على ليل', P('muted-night'), P('layl'), 4.5], ['غامق: ثانوي على كرت', P('muted-night'), P('layl-2'), 4.5], ['غامق: ثانوي على soft', P('muted-night'), P('layl-3'), 4.5],
  ['غامق: لمبة على كرت', P('lamba'), P('layl-2'), 4.5], ['غامق: جمر على كرت', P('jamr-night'), P('layl-2'), 4.5], ['غامق: نعنع على كرت', P('nanaa-night'), P('layl-2'), 4.5], ['غامق: توت على كرت', P('toot-night'), P('layl-2'), 4.5],
  ['غامق: حدود التحكم على ليل', P('control-night'), P('layl'), 3],
  ['زر أساسي: ليل على لمبة', P('layl'), P('lamba'), 7], ['زر جمر: ليل على جمر', P('layl'), P('jamr'), 4.5], ['نعنع: ليل على نعنع', P('layl'), P('nanaa'), 4.5], ['بلس: أبيض على توت', P('white'), P('toot'), 4.5],
  ['شارة جديد: ورق على ليل', P('waraq'), P('layl'), 7],
];
let fail = 0;
for (const [n, fg, bg, min] of pairs) { const r = cr(fg, bg); const ok = r >= min; if (!ok) fail++; console.log(ok ? '✓' : '✗', n, r.toFixed(2) + ':1', '(≥' + min + ')'); }
console.log('ملاحظة: أبيض على اللمبة', cr(P('white'), P('lamba')).toFixed(2) + ':1 (لهيك نص الأزرار ليل)');
process.exit(fail ? 1 : 0);
