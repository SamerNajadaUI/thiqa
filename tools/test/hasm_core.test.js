// فحص قواعد «ليلة الحسم»: node --test tools/test/hasm_core.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const G = path.join(__dirname, '../../docs/games/');
const C = require(G + 'hasm-content.js');
const K = require(G + 'hasm-core.js');
const career = K.prepCareer(JSON.parse(fs.readFileSync(G + 'career.json', 'utf8')));
const P = (n) => Array.from({ length: n }, (_, i) => ({ id: 'p' + i, name: 'لاعب' + i }));
const ATT = Object.keys(C.ATT), DEF = Object.keys(C.DEF);

// بيلعب موسم كامل: البشر بيختاروا عشوائي (أو ما بيجاوبوا أبداً إذا lazy)
function season(n, len, seed, opt = {}) {
  const g = K.newGame(P(n), { len }, seed), ctx = { career: opt.noCareer ? null : career };
  let r = seed * 7 + 1; const rr = (k) => { r = (r * 1103515245 + 12345) & 0x7fffffff; return r % k; };
  let guard = 0;
  while (g.S.phase !== 'final') {
    assert.ok(++guard < 400, 'اللعبة علقت');
    const ph = g.S.phase;
    if (opt.onPhase) opt.onPhase(g);
    if ((ph === 'prep' || ph === 'seg') && !opt.lazy) {
      for (const c of K.humans(g.S)) {
        if (ph === 'prep') K.apply(g, { t: 'prep', pid: c.id, ans: rr(4), bid: rr(Math.floor(c.budget / 5) + 1) * 5 }, ctx);
        else K.apply(g, { t: 'seg', pid: c.id, att: ATT[rr(3)], def: DEF[rr(3)], card: c.cards[0] || null }, ctx);
      }
      assert.notEqual(g.S.phase, ph, 'لازم تتسكّر المرحلة لما الكل يخلّص');
    } else assert.equal(K.apply(g, { t: 'go' }, ctx), true);
  }
  return g;
}

test('جدول المواجهات: كل نادي بيلعب مرة بكل جولة، والدورة الكاملة فيها كل المواجهات', () => {
  for (const n of [4, 6]) {
    const ids = Array.from({ length: n }, (_, i) => 'c' + i), fx = K.fixtures(ids, n - 1), seen = new Set();
    for (const round of fx) {
      assert.deepEqual(round.flat().sort(), ids);
      round.forEach(([a, b]) => seen.add([a, b].sort().join()));
    }
    assert.equal(seen.size, n * (n - 1) / 2);
  }
  const back = K.fixtures(['a', 'b', 'c', 'd'], 5);
  assert.deepEqual(back[3], back[0].map(([x, y]) => [y, x]));   // الإياب معكوس
});

test('جدول الهجمة ضد الدفاع مربع لاتيني: كل هجمة إلها هدف وميتة و50/50', () => {
  for (const a of ATT) assert.deepEqual(DEF.map((d) => C.MATRIX[a][d]).sort(), ['dead', 'fifty', 'goal']);
  for (const d of DEF) assert.deepEqual(ATT.map((a) => C.MATRIX[a][d]).sort(), ['dead', 'fifty', 'goal']);
});

test('عدد الأندية والجولات', () => {
  for (const [n, clubs] of [[1, 4], [2, 4], [4, 4], [5, 6], [6, 6]]) {
    const g = K.newGame(P(n), { len: 'quick' }, 5);
    assert.equal(g.S.clubs.length, clubs); assert.equal(K.humans(g.S).length, n); assert.equal(g.S.mds, 3);
    assert.equal(new Set(g.S.clubs.map((c) => c.id)).size, clubs);
  }
  assert.equal(K.newGame(P(3), { len: 'full' }, 5).S.mds, 5);
});

test('أول لاعبين بشر بيتواجهوا بآخر جولة', () => {
  for (let seed = 1; seed < 40; seed++) for (const len of ['quick', 'full']) {
    const { S } = K.newGame(P(2), { len }, seed);
    assert.ok(S.fx[S.mds - 1].some((m) => m.includes('p0') && m.includes('p1')));
  }
});

// بيجهّز لعبة لحد مرحلة الشوط، مع تحكم بالخبر
function atSeg(seed, news) {
  const g = K.newGame(P(2), { len: 'quick' }, seed), ctx = { career };
  K.apply(g, { t: 'go' }, ctx); K.apply(g, { t: 'go' }, ctx);
  K.apply(g, { t: 'prep', pid: 'p0', ans: -1, bid: 0 }, ctx); K.apply(g, { t: 'prep', pid: 'p1', ans: -1, bid: 0 }, ctx);
  K.apply(g, { t: 'go' }, ctx);
  assert.equal(g.S.phase, 'seg');
  g.S.news = news || 'sponsor'; g.S.cursed = null;
  g.S.clubs.forEach((c) => { c.stars = []; c.cards = []; });
  // خلّي p0 و p1 بنفس المباراة، p0 صاحب الأرض
  const m = g.S.matches.find((x) => x.h === 'p0' || x.a === 'p0'), other = g.S.matches.find((x) => x !== m);
  const rv = m.h === 'p0' ? m.a : m.h;
  if (rv !== 'p1') { if (other.h === 'p1') other.h = rv; else other.a = rv; }
  m.h = 'p0'; m.a = 'p1';
  return { g, ctx, m };
}
const play = (t, a0, d0, a1, d1, c0, c1) => {
  K.apply(t.g, { t: 'seg', pid: 'p0', att: a0, def: d0, card: c0 || null }, t.ctx);
  K.apply(t.g, { t: 'seg', pid: 'p1', att: a1, def: d1, card: c1 || null }, t.ctx);
  assert.equal(t.g.S.phase, 'segShow');
  return { h: t.m.plays.find((p) => p.side === 'h'), a: t.m.plays.find((p) => p.side === 'a') };
};
const starIdx = (role) => C.STARS.findIndex((s) => s[2] === role);

test('هدف أكيد وهجمة ميتة', () => {
  const t = atSeg(3), r = play(t, 'counter', 'trap', 'counter', 'press');
  assert.equal(r.h.out, 'goal'); assert.equal(r.a.out, 'dead');
  assert.equal(t.m.hg, 1); assert.equal(t.m.ag, 0);
  assert.equal(K.club(t.g.S, 'p0').st.blocks, 1);
});

test('نسب الـ50/50: هدّاف، صخرة، وأخبار', () => {
  const pOf = (news, setup, a0 = 'counter', d1 = 'bus') => { const t = atSeg(9, news); setup(t.g.S); return play(t, a0, 'bus', 'shot', d1).h.p; };
  assert.equal(pOf('sponsor', () => {}), 0.5);
  assert.equal(pOf('sponsor', (S) => K.club(S, 'p0').stars.push(starIdx('striker'))), 0.7);
  assert.equal(pOf('sponsor', (S) => K.club(S, 'p1').stars.push(starIdx('rock'))), 0.3);
  assert.equal(pOf('sponsor', (S) => { K.club(S, 'p0').stars.push(starIdx('striker')); K.club(S, 'p1').stars.push(starIdx('rock')); }), 0.5);
  assert.equal(pOf('crowd', () => {}), 0.6);
  assert.equal(pOf('mud', () => {}, 'tiki', 'press'), 0.35);
  assert.equal(pOf('wind', () => {}, 'shot', 'trap'), 0.35);
  // لعنة المتصدر بتعطّل نجومه
  assert.equal(pOf('curse', (S) => { K.club(S, 'p0').stars.push(starIdx('striker')); S.cursed = 'p0'; }), 0.5);
});

test('المايسترو: مرة وحدة بالمباراة', () => {
  const t = atSeg(4); K.club(t.g.S, 'p0').stars.push(starIdx('maestro'));
  const r = play(t, 'counter', 'bus', 'shot', 'trap');
  assert.ok(r.h.fl.includes('maestro')); assert.notEqual(r.h.out, 'dead');
  K.apply(t.g, { t: 'go' }, t.ctx);
  K.apply(t.g, { t: 'seg', pid: 'p0', att: 'counter', def: 'bus' }, t.ctx); K.apply(t.g, { t: 'seg', pid: 'p1', att: 'shot', def: 'trap' }, t.ctx);
  const second = t.m.plays.filter((p) => p.side === 'h')[1];
  assert.equal(second.out, 'dead'); assert.ok(!second.fl.includes('maestro'));
});

test('الكروت: تبديل ذهبي، كرت أحمر، راعي، وحكم متساهل', () => {
  let t = atSeg(5); K.club(t.g.S, 'p0').cards.push('gold');
  let r = play(t, 'counter', 'bus', 'shot', 'bus', 'gold');
  assert.equal(r.h.out, 'goal'); assert.ok(r.h.fl.includes('gold')); assert.deepEqual(K.club(t.g.S, 'p0').cards, []);

  t = atSeg(5); K.club(t.g.S, 'p0').stars.push(starIdx('striker')); K.club(t.g.S, 'p1').cards.push('red');
  r = play(t, 'counter', 'bus', 'shot', 'bus', null, 'red');
  assert.equal(r.h.p, 0.5);

  t = atSeg(5); K.club(t.g.S, 'p0').cards.push('sponsor'); const b = K.club(t.g.S, 'p0').budget;
  play(t, 'counter', 'bus', 'shot', 'bus', 'sponsor');
  assert.equal(K.club(t.g.S, 'p0').budget, b + 25);

  t = atSeg(5, 'lenient'); K.club(t.g.S, 'p0').stars.push(starIdx('striker')); K.club(t.g.S, 'p1').cards.push('red');
  r = play(t, 'counter', 'bus', 'shot', 'bus', null, 'red');
  assert.equal(r.h.p, 0.7); assert.deepEqual(K.club(t.g.S, 'p1').cards, ['red']);   // ما انلعب وما انحرق

  t = atSeg(5); r = play(t, 'counter', 'bus', 'shot', 'bus', 'var');                    // كرت مش معه
  assert.equal(t.g.S.show.cards.p0, undefined);
});

test('VAR: بيراجع أول هدف، وبيلغيه تقريباً نص المرات', () => {
  let no = 0, n = 0;
  for (let seed = 1; seed <= 200; seed++) {
    const t = atSeg(seed); K.club(t.g.S, 'p1').cards.push('var');
    const r = play(t, 'counter', 'trap', 'counter', 'press', null, 'var');
    assert.ok(r.h.fl.includes('var')); n++;
    if (r.h.out === 'varNo') { no++; assert.equal(t.m.hg, 0); } else { assert.equal(r.h.out, 'goal'); assert.equal(t.m.hg, 1); }
  }
  assert.ok(no > 70 && no < 130, 'VAR لغى ' + no + ' من ' + n);
});

test('المزاد: الأعلى بيدفع وبياخد النجم، والصفر ما بيشتري', () => {
  const g = K.newGame(P(2), { len: 'quick' }, 11), ctx = { career };
  K.apply(g, { t: 'go' }, ctx); K.apply(g, { t: 'go' }, ctx);
  g.S.news = 'derby';
  Object.keys(g.H.prep).forEach((id) => { g.H.prep[id].bid = 10; });
  const b0 = K.club(g.S, 'p0').budget;
  K.apply(g, { t: 'prep', pid: 'p0', ans: 0, bid: 63 }, ctx);   // بتتقرّب لـ65
  K.apply(g, { t: 'prep', pid: 'p1', ans: 0, bid: 9999 }, ctx); // بتنقص لحد الميزانية
  const sh = g.S.show, p1 = K.club(g.S, 'p1');
  assert.equal(g.S.phase, 'prepShow'); assert.equal(sh.win, 'p1'); assert.equal(sh.price, b0);
  assert.equal(p1.budget, 0); assert.deepEqual(p1.stars, [g.S.star]);
  assert.equal(sh.bids.find((b) => b.id === 'p0').bid, 65);
  assert.equal(K.club(g.S, 'p0').budget, b0);
});

test('المزاد: التعادل بيروح للأدنى بالجدول، وإذا الكل صفر النجم ما بينباع', () => {
  const g = K.newGame(P(2), { len: 'quick' }, 12), ctx = { career };
  K.apply(g, { t: 'go' }, ctx); K.apply(g, { t: 'go' }, ctx);
  Object.keys(g.H.prep).forEach((id) => { g.H.prep[id].bid = 0; });
  K.club(g.S, 'p0').pts = 6; K.club(g.S, 'p1').pts = 1;
  K.apply(g, { t: 'prep', pid: 'p0', ans: 0, bid: 40 }, ctx); K.apply(g, { t: 'prep', pid: 'p1', ans: 0, bid: 40 }, ctx);
  assert.equal(g.S.show.win, 'p1');
  const g2 = K.newGame(P(1), { len: 'quick' }, 13);
  K.apply(g2, { t: 'go' }, ctx); K.apply(g2, { t: 'go' }, ctx);
  Object.keys(g2.H.prep).forEach((id) => { g2.H.prep[id].bid = 0; });
  K.apply(g2, { t: 'prep', pid: 'p0', ans: 0, bid: 0 }, ctx);
  assert.equal(g2.S.show.win, null); assert.ok(g2.S.clubs.every((c) => c.stars.length === 0));
});

test('اللغز: الجواب الصح بيعطي كرت، والحد 3 كروت', () => {
  const g = K.newGame(P(2), { len: 'quick' }, 21), ctx = { career };
  K.apply(g, { t: 'go' }, ctx); K.apply(g, { t: 'go' }, ctx);
  assert.equal(g.S.puzzle.ans, null, 'الجواب ما بينكشف قبل الوقت');
  K.club(g.S, 'p1').cards = ['var', 'red', 'gold'];
  K.apply(g, { t: 'prep', pid: 'p0', ans: g.H.ans, bid: 0 }, ctx); K.apply(g, { t: 'prep', pid: 'p1', ans: g.H.ans, bid: 0 }, ctx);
  assert.equal(K.club(g.S, 'p0').cards.length, 1); assert.ok(C.CARDS[g.S.show.got.p0]);
  assert.equal(g.S.show.got.p1, 'full'); assert.equal(K.club(g.S, 'p1').cards.length, 3);
  assert.equal(g.S.puzzle.ans, g.H.ans);
});

test('مولّد الألغاز: 4 خيارات مختلفة وجواب صح واحد', () => {
  assert.ok(career, 'career.json لازم يتجهّز');
  const types = new Set();
  for (let seed = 1; seed <= 600; seed++) {
    const S = { rs: seed, emojiUsed: [] }, p = K.genPuzzle(S, career);
    types.add(p.type);
    assert.equal(p.opts.length, 4); assert.equal(new Set(p.opts).size, 4); assert.ok(p.ans >= 0 && p.ans < 4);
    if (p.type === 'common') {
      const three = p.items.map((n) => career.list.find((x) => x.n === n));
      const all = p.opts.filter((c) => three.every((x) => x.clubs.includes(c)));
      assert.deepEqual(all, [p.opts[p.ans]]);
    }
    if (p.type === 'odd') {
      const x = p.q.replace('مين الوحيد اللي ما لعب مع ', '').replace('؟', '');
      const outs = p.opts.filter((n) => !career.list.find((q) => q.n === n).clubs.includes(x));
      assert.deepEqual(outs, [p.opts[p.ans]]);
    }
    if (p.type === 'first') {
      const ys = p.opts.map((n) => career.list.find((q) => q.n === n).start);
      assert.equal(ys.indexOf(Math.min(...ys)), p.ans); assert.equal(ys.filter((y) => y === Math.min(...ys)).length, 1);
    }
  }
  assert.deepEqual([...types].sort(), ['common', 'emoji', 'first', 'odd']);
  assert.equal(K.genPuzzle({ rs: 1, emojiUsed: [] }, null).type, 'emoji');
});

test('الأخبار: لعنة المتصدر وهدية القدر ما بيطلعوا بأول جولة، وما في تكرار', () => {
  for (let seed = 1; seed <= 120; seed++) {
    const seen = [];
    season(2, 'full', seed, { onPhase: (g) => { if (g.S.phase === 'news') { seen.push(g.S.news); if (g.S.md === 0) assert.ok(C.NEWS[g.S.news].early); } } });
    assert.equal(seen.length, 5); assert.equal(new Set(seen).size, 5);
  }
});

test('الترتيب: نقاط ثم فرق أهداف ثم أهداف ثم مواجهة مباشرة ثم ميزانية', () => {
  const { S } = K.newGame(P(4), { len: 'quick' }, 2);
  const set = (id, o) => Object.assign(K.club(S, id), { pts: 0, gf: 0, ga: 0, budget: 100, tb: 0.5 }, o);
  set('p0', { pts: 6, gf: 3, ga: 1 }); set('p1', { pts: 6, gf: 4, ga: 2 }); set('p2', { pts: 6, gf: 4, ga: 2 }); set('p3', { pts: 7 });
  S.h2h['p2|p1'] = 3; S.h2h['p1|p2'] = 0;
  assert.deepEqual(K.standings(S).map((r) => r.id), ['p3', 'p2', 'p1', 'p0']);
  S.h2h = {}; K.club(S, 'p1').budget = 120;
  assert.deepEqual(K.standings(S).map((r) => r.id), ['p3', 'p1', 'p2', 'p0']);
  // الجدول الحي: نتيجة مؤقتة بترفع النادي
  const { S: T } = K.newGame(P(2), { len: 'quick' }, 2);
  T.matches = [{ h: 'p0', a: 'p1' }, { h: 'b0', a: 'b1' }];
  const live = K.standings(T, [{ hg: 0, ag: 2 }, { hg: 1, ag: 1 }]);
  assert.equal(live[0].id, 'p1'); assert.equal(live[0].pts, 3); assert.equal(live.find((r) => r.id === 'b0').pts, 1);
});

test('ديربي ناري: الفوز بـ4 نقاط', () => {
  const t = atSeg(3, 'derby');
  play(t, 'counter', 'trap', 'counter', 'press');
  K.apply(t.g, { t: 'go' }, t.ctx);
  K.apply(t.g, { t: 'seg', pid: 'p0', att: 'counter', def: 'trap' }, t.ctx); K.apply(t.g, { t: 'seg', pid: 'p1', att: 'counter', def: 'press' }, t.ctx);
  K.apply(t.g, { t: 'go' }, t.ctx);
  assert.equal(t.g.S.phase, 'table'); assert.equal(K.club(t.g.S, 'p0').pts, 4); assert.equal(K.club(t.g.S, 'p1').pts, 0);
});

test('حركات مرفوضة: مرتين، مرحلة غلط، لاعب مش موجود، كمبيوتر', () => {
  const g = K.newGame(P(2), { len: 'quick' }, 8), ctx = { career };
  assert.equal(K.apply(g, { t: 'prep', pid: 'p0', ans: 0, bid: 0 }, ctx), false);
  K.apply(g, { t: 'go' }, ctx); K.apply(g, { t: 'go' }, ctx);
  assert.equal(K.apply(g, { t: 'seg', pid: 'p0', att: 'counter', def: 'bus' }, ctx), false);
  assert.equal(K.apply(g, { t: 'prep', pid: 'zz', ans: 0, bid: 0 }, ctx), false);
  assert.equal(K.apply(g, { t: 'prep', pid: 'b0', ans: 0, bid: 0 }, ctx), false);
  assert.equal(K.apply(g, { t: 'prep', pid: 'p0', ans: 0, bid: 0 }, ctx), true);
  assert.equal(K.apply(g, { t: 'prep', pid: 'p0', ans: 1, bid: 50 }, ctx), false);
  K.apply(g, { t: 'prep', pid: 'p1', ans: 0, bid: 0 }, ctx); K.apply(g, { t: 'go' }, ctx);
  assert.equal(K.apply(g, { t: 'seg', pid: 'p0', att: 'nope', def: 'bus' }, ctx), false);
});

test('نفس البذرة = نفس الموسم', () => {
  const a = season(3, 'full', 77), b = season(3, 'full', 77);
  assert.deepEqual(a.S.fin, b.S.fin); assert.deepEqual(a.S.log, b.S.log);
});

test('الأسرار ما بتطلع بالحالة العامة قبل الكشف', () => {
  season(2, 'quick', 31, { onPhase: (g) => {
    const s = JSON.stringify(g.S);
    if (g.S.phase === 'prep' || g.S.phase === 'news') assert.equal(g.S.puzzle.ans, null);
    assert.ok(!s.includes('"prep":{') && !s.includes('"bid"') || g.S.phase !== 'prep');
    if (g.S.phase === 'seg') assert.equal(g.S.show, null);
  } });
});

test('300 موسم كامل بدون أخطاء، والأرقام متطابقة', () => {
  let goals = 0, matches = 0, champs = { human: 0, bot: 0 };
  for (let seed = 1; seed <= 300; seed++) {
    const n = 1 + (seed % 6), len = seed % 2 ? 'quick' : 'full';
    const { S } = season(n, len, seed, { lazy: seed % 5 === 0, noCareer: seed % 7 === 0 });
    assert.equal(S.md, S.mds); assert.equal(S.fin.order.length, S.clubs.length);
    const gf = S.clubs.reduce((s, c) => s + c.gf, 0), ga = S.clubs.reduce((s, c) => s + c.ga, 0);
    assert.equal(gf, ga);
    for (const c of S.clubs) {
      assert.equal(c.w + c.d + c.l, S.mds); assert.ok(c.budget >= 0); assert.ok(c.cards.length <= C.MAX_CARDS);
      assert.equal(new Set(c.stars).size, c.stars.length);
    }
    assert.equal(S.clubs.reduce((s, c) => s + c.stars.length, 0), S.log.filter((e) => e.k === 'buy').length);
    assert.equal(S.clubs.reduce((s, c) => s + c.w, 0), S.clubs.reduce((s, c) => s + c.l, 0));
    assert.ok(S.fin.story.length >= 2); assert.ok(S.fin.awards.length >= 2);
    if (n >= 2) { assert.ok(S.fin.loser && !K.club(S, S.fin.loser).bot && S.fin.dare); } else assert.equal(S.fin.loser, null);
    goals += gf; matches += S.clubs.length / 2 * S.mds;
    champs[K.club(S, S.fin.champ).bot ? 'bot' : 'human']++;
  }
  const avg = goals / matches;
  assert.ok(avg > 1.6 && avg < 3.4, 'معدل الأهداف بالمباراة ' + avg.toFixed(2));
  console.log(`    معدل الأهداف ${avg.toFixed(2)} · أبطال بشر ${champs.human} · كمبيوتر ${champs.bot}`);
});
