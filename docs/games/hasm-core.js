// قواعد «ليلة الحسم» بدون أي واجهة. نفس الملف بيشتغل بالمتصفح وبـNode (للفحص).
// G = { S, H }: S الحالة العامة (بتنبعث للكل)، H الأسرار (عروض واختيارات قبل الكشف، بتضل عند صاحب الغرفة).
"use strict";
(function (root) {
  const C = typeof HASM !== "undefined" ? HASM : require("./hasm-content.js");

  // ---------- عشوائية ببذرة محفوظة بالحالة (ريفرش وفحص بيعطوا نفس النتيجة) ----------
  function rnd(S) {
    let t = (S.rs = (S.rs + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  const ri = (S, n) => Math.floor(rnd(S) * n);
  const rpick = (S, a) => a[ri(S, a.length)];
  const rshuffle = (S, a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = ri(S, i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  const club = (S, id) => S.clubs.find((c) => c.id === id);
  const humans = (S) => S.clubs.filter((c) => !c.bot);
  const starOf = (i) => { const s = C.STARS[i]; return { i, name: s[0], flag: s[1], role: s[2], tag: s[3], tier: s[4] }; };
  const roles = (c) => [...new Set(c.stars.map((i) => C.STARS[i][2]))];
  const matchOf = (S, id) => S.matches.find((m) => m.h === id || m.a === id);
  const rival = (S, id) => { const m = matchOf(S, id); return m ? (m.h === id ? m.a : m.h) : null; };

  // ---------- جدول المواجهات (round-robin بطريقة الدائرة) ----------
  function fixtures(ids, mds) {
    const n = ids.length, arr = ids.slice(), rounds = [];
    for (let r = 0; r < n - 1; r++) {
      const ps = [];
      for (let i = 0; i < n / 2; i++) { const a = arr[i], b = arr[n - 1 - i]; ps.push((r + i) % 2 ? [b, a] : [a, b]); }
      rounds.push(ps);
      arr.splice(1, 0, arr.pop());
    }
    return Array.from({ length: mds }, (_, k) => {
      const base = rounds[k % (n - 1)];
      return Math.floor(k / (n - 1)) % 2 ? base.map(([a, b]) => [b, a]) : base;
    });
  }

  // ---------- الترتيب ----------
  // live: نتائج مؤقتة للمباريات الشغالة [{hg, ag}] بنفس ترتيب S.matches
  function standings(S, live) {
    const rows = S.clubs.map((c) => ({ id: c.id, pl: c.w + c.d + c.l, w: c.w, d: c.d, l: c.l, gf: c.gf, ga: c.ga, pts: c.pts, budget: c.budget, tb: c.tb }));
    const R = (id) => rows.find((r) => r.id === id);
    if (live) S.matches.forEach((m, i) => {
      const sc = live[i]; if (!sc) return;
      const h = R(m.h), a = R(m.a), win = winPts(S);
      h.pl++; a.pl++; h.gf += sc.hg; h.ga += sc.ag; a.gf += sc.ag; a.ga += sc.hg;
      if (sc.hg > sc.ag) { h.pts += win; h.w++; a.l++; } else if (sc.hg < sc.ag) { a.pts += win; a.w++; h.l++; } else { h.pts++; a.pts++; h.d++; a.d++; }
    });
    const h2h = (x, y) => (S.h2h[x + "|" + y] || 0) - (S.h2h[y + "|" + x] || 0);
    rows.forEach((r) => { r.gd = r.gf - r.ga; });
    return rows.sort((x, y) => y.pts - x.pts || y.gd - x.gd || y.gf - x.gf || h2h(y.id, x.id) || y.budget - x.budget || y.tb - x.tb);
  }
  const winPts = (S) => (S.news === "derby" ? 4 : 3);

  // ---------- بداية موسم ----------
  // players: [{id, name}] البشر بالترتيب. cfg: {len: "quick"|"full"}
  function newGame(players, cfg, seed) {
    const S = { v: 0, phase: "intro", cfg: { len: cfg && cfg.len === "quick" ? "quick" : "full" }, rs: seed | 0, clubs: [], md: -1, h2h: {}, log: [], hist: [],
      newsUsed: [], starsUsed: [], emojiUsed: [], news: null, star: null, puzzle: null, done: [], seg: 0, segs: 2, matches: [], show: null, cursed: null, fin: null };
    const n = players.length <= 4 ? 4 : 6;
    const mk = (o) => Object.assign({ budget: C.BUDGET, stars: [], cards: [], pts: 0, gf: 0, ga: 0, w: 0, d: 0, l: 0, tb: rnd(S), st: { spent: 0, puz: 0, blocks: 0, top: 0 } }, o);
    players.slice(0, C.MAX_P).forEach((p, i) => S.clubs.push(mk({ id: p.id, name: p.name, bot: false, crest: C.CRESTS[i], hue: C.HUES[i] })));
    rshuffle(S, C.BOTS.map((b, i) => [b, i])).slice(0, n - S.clubs.length).forEach(([b, i], k) =>
      S.clubs.push(mk({ id: "b" + k, name: b[0], crest: b[1], pers: b[2], boss: b[3], bot: true, hue: C.BOT_HUES[i] })));
    S.mds = S.cfg.len === "quick" ? 3 : 5;
    // ترتيب عشوائي للجدول، بس أول لاعبين بشر بيتواجهوا بآخر جولة (ليلة الحسم) إذا ممكن
    const fx = fixtures(rshuffle(S, S.clubs.map((c) => c.id)), S.mds), hs = humans(S);
    if (hs.length >= 2) {
      const meet = (r) => r.some(([a, b]) => (a === hs[0].id && b === hs[1].id) || (a === hs[1].id && b === hs[0].id));
      const k = fx.findIndex(meet);
      if (k >= 0 && !meet(fx[S.mds - 1])) [fx[k], fx[S.mds - 1]] = [fx[S.mds - 1], fx[k]];
    }
    S.fx = fx;
    return { S, H: { ans: null, prep: {}, seg: {} } };
  }

  // ---------- الألغاز ----------
  // بنجهّز career.json مرة: أشهر اللاعبين بس، وأسماء أنديتهم وسنة بدايتهم
  function prepCareer(raw) {
    const list = ((raw && raw.players) || []).slice(0, 170).map((p) => {
      const cs = (p.c || []).filter((x) => x && x[0]);
      const ys = cs.map((x) => x[1]).filter((y) => typeof y === "number");
      return { n: p.a, clubs: [...new Set(cs.map((x) => String(x[0]).replace(/^نادي /, "")))], start: ys.length === cs.length && ys.length ? Math.min(...ys) : null };
    }).filter((p) => p.n && p.clubs.length);
    const count = {};
    list.forEach((p) => p.clubs.forEach((c) => { count[c] = (count[c] || 0) + 1; }));
    const big = Object.keys(count).filter((c) => count[c] >= 8);
    return list.length >= 40 && big.length >= 6 ? { list, big } : null;
  }
  function genPuzzle(S, career) {
    const kinds = career ? rshuffle(S, ["emoji", "common", "odd", "first"]) : ["emoji"];
    for (const k of kinds) { const p = PUZ[k](S, career); if (p) return p; }
    return PUZ.emoji(S);
  }
  const withOpts = (S, right, wrong, extra) => {
    const opts = rshuffle(S, [right, ...wrong]);
    return Object.assign({ opts, ans: opts.indexOf(right) }, extra);
  };
  const PUZ = {
    emoji(S) {
      let free = C.EMOJI.map((_, i) => i).filter((i) => !S.emojiUsed.includes(i));
      if (!free.length) { S.emojiUsed = []; free = C.EMOJI.map((_, i) => i); }
      const i = rpick(S, free), e = C.EMOJI[i];
      S.emojiUsed.push(i);
      return withOpts(S, e[1], e.slice(2), { type: "emoji", title: "شيفرة الإيموجي", q: "مين المقصود؟", big: e[0] });
    },
    common(S, cr) {
      for (let t = 0; t < 30; t++) {
        const x = rpick(S, cr.big), three = rshuffle(S, cr.list.filter((p) => p.clubs.includes(x))).slice(0, 3);
        if (three.length < 3) continue;
        const wrong = rshuffle(S, cr.big.filter((c) => c !== x && !three.every((p) => p.clubs.includes(c)))).slice(0, 3);
        if (wrong.length < 3) continue;
        return withOpts(S, x, wrong, { type: "common", title: "القاسم المشترك", q: "أي نادي لعبوا فيه الثلاثة؟", items: three.map((p) => p.n) });
      }
      return null;
    },
    odd(S, cr) {
      for (let t = 0; t < 30; t++) {
        const x = rpick(S, cr.big), ins = rshuffle(S, cr.list.filter((p) => p.clubs.includes(x))).slice(0, 3);
        const outs = cr.list.filter((p) => !p.clubs.includes(x));
        if (ins.length < 3 || !outs.length) continue;
        return withOpts(S, rpick(S, outs).n, ins.map((p) => p.n), { type: "odd", title: "مين الدخيل؟", q: `مين الوحيد اللي ما لعب مع ${x}؟` });
      }
      return null;
    },
    first(S, cr) {
      const pool = cr.list.filter((p) => p.start);
      for (let t = 0; t < 40; t++) {
        const four = rshuffle(S, pool).slice(0, 4).sort((a, b) => a.start - b.start);
        if (four.length < 4 || four[1].start - four[0].start < 3) continue;
        return withOpts(S, four[0].n, four.slice(1).map((p) => p.n), { type: "first", title: "الأقدم", q: "مين بلّش مسيرته الاحترافية أول؟", note: `بلّش سنة ${four[0].start}` });
      }
      return null;
    },
  };

  // ---------- الكمبيوتر ----------
  function botPrep(S, H, c) {
    const right = rnd(S) < 0.55;
    const ans = right ? H.ans : (H.ans + 1 + ri(S, 3)) % 4;
    const st = starOf(S.star), has = roles(c).includes(st.role);
    let v = (14 + st.tier * 9) * (has ? 0.35 : 1.25) * ({ stingy: 0.55, crazy: 1.6 }[c.pers] || 1) * (0.7 + rnd(S) * 0.6);
    if (rnd(S) < 0.12) v = 0;
    const left = S.mds - S.md - 1;                       // لا يصرف كل إشي بدري
    const cap = left > 0 ? c.budget * (c.pers === "crazy" ? 0.8 : 0.6) : c.budget;
    return { ans, bid: clamp(Math.round(Math.min(v, cap) / C.STEP) * C.STEP, 0, c.budget) };
  }
  function weighted(S, w) {
    const ks = Object.keys(w), tot = ks.reduce((s, k) => s + w[k], 0);
    let r = rnd(S) * tot;
    for (const k of ks) { r -= w[k]; if (r <= 0) return k; }
    return ks[ks.length - 1];
  }
  function botSeg(S, c) {
    const att = weighted(S, { counter: c.pers === "att" ? 2 : 1, shot: 1, tiki: 1 });
    const def = weighted(S, { press: 1, bus: c.pers === "def" ? 2 : 1, trap: 1 });
    const ok = c.cards.filter((k) => cardAllowed(S, k));
    const card = ok.length && rnd(S) < 0.5 ? (ok.includes("sponsor") ? "sponsor" : rpick(S, ok)) : null;
    return { att, def, card };
  }
  const cardAllowed = (S, k) => !!C.CARDS[k] && !(S.news === "lenient" && C.CARDS[k].ref);
  const giveCard = (S, c) => { if (c.cards.length >= C.MAX_CARDS) return null; const k = rpick(S, C.CARD_POOL); c.cards.push(k); return k; };

  // ---------- مراحل الجولة ----------
  function nextMd(G, ctx) {
    const { S, H } = G;
    S.md++;
    if (S.md >= S.mds) return finale(S);
    S.segs = S.md === S.mds - 1 ? 3 : 2;
    const order = standings(S);
    const free = Object.keys(C.NEWS).filter((k) => !S.newsUsed.includes(k) && (S.md > 0 || C.NEWS[k].early));
    S.news = rpick(S, free); S.newsUsed.push(S.news);
    S.cursed = null; S.newsFx = null;
    if (S.news === "sponsor") S.clubs.forEach((c) => { c.budget += 20; });
    if (S.news === "curse") S.cursed = order[0].id;
    if (S.news === "gift") { const last = club(S, order[order.length - 1].id); S.newsFx = { club: last.id, card: giveCard(S, last) }; }
    if (S.news === "curse") S.newsFx = { club: S.cursed };
    S.star = rpick(S, C.STARS.map((_, i) => i).filter((i) => !S.starsUsed.includes(i))); S.starsUsed.push(S.star);
    const p = genPuzzle(S, ctx && ctx.career);
    H.ans = p.ans; H.note = p.note || null;
    S.puzzle = { type: p.type, title: p.title, q: p.q, big: p.big || null, items: p.items || null, opts: p.opts, ans: null, note: null };
    S.matches = S.fx[S.md].map(([h, a]) => ({ h, a, hg: 0, ag: 0, mu: {}, plays: [] }));
    S.show = null; S.done = []; S.seg = 0; S.phase = "news";
  }
  function openPrep(G) {
    const { S, H } = G;
    S.phase = "prep"; S.done = []; H.prep = {}; S.show = null;
    S.clubs.filter((c) => c.bot).forEach((c) => { H.prep[c.id] = botPrep(S, H, c); });
  }
  function closePrep(G) {
    const { S, H } = G;
    humans(S).forEach((c) => { if (!H.prep[c.id]) H.prep[c.id] = { ans: -1, bid: 0 }; });
    const order = standings(S).map((r) => r.id);
    const picks = {}, got = {};
    S.clubs.forEach((c) => {
      const a = H.prep[c.id].ans; picks[c.id] = a;
      if (a === H.ans) { c.st.puz++; got[c.id] = giveCard(S, c) || "full"; }
    });
    const bids = S.clubs.map((c) => ({ id: c.id, bid: H.prep[c.id].bid })).sort((x, y) => x.bid - y.bid || order.indexOf(x.id) - order.indexOf(y.id));
    const max = bids[bids.length - 1].bid;
    let win = null;
    if (max > 0) {
      // التعادل: الأدنى بالجدول، وبعدها القرعة (tb)
      const tied = bids.filter((b) => b.bid === max).map((b) => club(S, b.id));
      const pos = (c) => { const r = standings(S).find((x) => x.id === c.id); return [r.pts, r.gd, r.gf]; };
      tied.sort((a, b) => { const x = pos(a), y = pos(b); return x[0] - y[0] || x[1] - y[1] || x[2] - y[2] || a.tb - b.tb; });
      const w = tied[0];
      w.budget -= max; w.st.spent += max; w.stars.push(S.star); win = w.id;
      if (max > w.st.top) w.st.top = max;
      S.log.push({ k: "buy", md: S.md, club: w.id, star: S.star, price: max });
    }
    S.puzzle.ans = H.ans; S.puzzle.note = H.note;
    S.show = { k: "prep", picks, got, bids, win, price: max };
    S.phase = "prepShow"; S.done = [];
  }
  function openSeg(G, k) {
    const { S, H } = G;
    S.seg = k; S.phase = "seg"; S.done = []; H.seg = {}; S.show = null;
    S.clubs.filter((c) => c.bot).forEach((c) => { H.seg[c.id] = botSeg(S, c); });
  }
  const MIN_RANGE = [[4, 44], [47, 89], [91, 96]];
  function closeSeg(G) {
    const { S, H } = G;
    const AK = Object.keys(C.ATT), DK = Object.keys(C.DEF);
    humans(S).forEach((c) => { if (!H.seg[c.id]) H.seg[c.id] = { att: rpick(S, AK), def: rpick(S, DK), card: null, auto: true }; });
    const played = {};
    S.clubs.forEach((c) => {
      const ch = H.seg[c.id], i = ch.card ? c.cards.indexOf(ch.card) : -1;
      if (i < 0 || !cardAllowed(S, ch.card)) { ch.card = null; return; }
      c.cards.splice(i, 1); played[c.id] = ch.card;
      if (ch.card === "sponsor") c.budget += 25;
    });
    const [lo, hi] = MIN_RANGE[S.seg];
    S.matches.forEach((m) => {
      const m1 = lo + ri(S, hi - lo + 1); let m2 = lo + ri(S, hi - lo + 1); if (m2 === m1) m2 = m1 < hi ? m1 + 1 : m1 - 1;
      const first = rnd(S) < 0.5 ? "h" : "a";
      const mins = { [first]: Math.min(m1, m2), [first === "h" ? "a" : "h"]: Math.max(m1, m2) };
      const ps = ["h", "a"].map((side) => resolvePlay(S, m, side, H.seg, played, mins[side])).sort((x, y) => x.min - y.min);
      ps.forEach((p) => { p.seg = S.seg; m.plays.push(p); });
    });
    S.show = { k: "seg", seg: S.seg, cards: played, auto: humans(S).filter((c) => H.seg[c.id].auto).map((c) => c.id) };
    S.phase = "segShow"; S.done = [];
  }
  // هجمة وحدة. الترتيب: كرت أحمر ← الجدول ← مايسترو ← تبديل ذهبي ← النرد ← VAR
  function resolvePlay(S, m, side, picks, played, min) {
    const A = club(S, side === "h" ? m.h : m.a), D = club(S, side === "h" ? m.a : m.h);
    const off = (c, opp) => played[opp.id] === "red" || S.cursed === c.id;
    const rA = off(A, D) ? [] : roles(A), rD = off(D, A) ? [] : roles(D);
    const att = picks[A.id].att, def = picks[D.id].def;
    let base = C.MATRIX[att][def];
    const p = { side, att, def, base, min, fl: [], out: null, p: null };
    if (base === "dead" && rA.includes("maestro") && !m.mu[A.id]) { m.mu[A.id] = 1; base = "fifty"; p.fl.push("maestro"); }
    if (base === "goal") p.out = "goal";
    else if (base === "dead") { p.out = "dead"; D.st.blocks++; }
    else if (played[A.id] === "gold") { p.fl.push("gold"); p.out = "goal"; }
    else {
      let pr = 0.5;
      if (rA.includes("striker")) pr += 0.2;
      if (rD.includes("rock")) pr -= 0.2;
      if (S.news === "mud" && att === "tiki") pr -= 0.15;
      if (S.news === "wind" && att === "shot") pr -= 0.15;
      if (S.news === "crowd" && side === "h") pr += 0.1;
      p.p = clamp(Math.round(pr * 100) / 100, 0.1, 0.9);
      p.out = rnd(S) < p.p ? "goal" : rnd(S) < 0.35 ? "post" : "save";
    }
    if (p.out === "goal" && played[D.id] === "var" && !m.mu["var" + D.id + S.seg]) {
      m.mu["var" + D.id + S.seg] = 1; p.fl.push("var");
      if (rnd(S) < 0.5) { p.out = "varNo"; S.log.push({ k: "var", md: S.md, club: D.id }); }
    }
    if (p.out === "goal") {
      if (side === "h") m.hg++; else m.ag++;
      if (min >= 85) S.log.push({ k: "late", md: S.md, club: A.id });
    }
    return p;
  }
  function endMd(G) {
    const { S } = G;
    const prev = standings(S).map((r) => r.id), win = winPts(S);
    S.matches.forEach((m) => {
      const h = club(S, m.h), a = club(S, m.a);
      h.gf += m.hg; h.ga += m.ag; a.gf += m.ag; a.ga += m.hg;
      let hp = 1, ap = 1;
      if (m.hg > m.ag) { hp = win; ap = 0; h.w++; a.l++; } else if (m.hg < m.ag) { hp = 0; ap = win; a.w++; h.l++; } else { h.d++; a.d++; }
      h.pts += hp; a.pts += ap;
      S.h2h[m.h + "|" + m.a] = (S.h2h[m.h + "|" + m.a] || 0) + hp;
      S.h2h[m.a + "|" + m.h] = (S.h2h[m.a + "|" + m.h] || 0) + ap;
      S.log.push({ k: "res", md: S.md, h: m.h, a: m.a, hg: m.hg, ag: m.ag });
    });
    const now = standings(S).map((r) => r.id);
    S.hist.push(now);
    S.show = { k: "table", prev };
    S.phase = "table"; S.done = [];
  }

  // ---------- النهاية: البطل، الألقاب، قصة الموسم، وحكم الأخير ----------
  function finale(S) {
    const rows = standings(S), order = rows.map((r) => r.id), nm = (id) => club(S, id).name;
    const champ = order[0], last = order[order.length - 1];
    const best = (val, min) => { let b = null; rows.forEach((r) => { const v = val(club(S, r.id)); if (v >= (min === undefined ? -Infinity : min) && (b === null || v > b.v)) b = { id: r.id, v }; }); return b; };
    const aw = [];
    const add = (k, b, v) => { if (b) aw.push({ k, id: b.id, v: v === undefined ? b.v : v }); };
    add("boot", best((c) => c.gf, 1));
    const wall = best((c) => -c.ga); add("wall", wall, wall && -wall.v);
    add("spend", best((c) => c.st.spent, 5));
    add("save", best((c) => c.budget, 5));
    add("brain", best((c) => c.st.puz, 1));
    add("read", best((c) => c.st.blocks, 1));
    const story = [`${club(S, champ).crest} ${nm(champ)} بطل الدوري بـ${rows[0].pts} نقطة.`];
    const before = S.hist.length >= 2 ? S.hist[S.hist.length - 2][0] : null;
    if (before && before !== champ) story.push(`لحد آخر جولة كان ${nm(before)} هو المتصدر، بس ليلة الحسم قلبت كل إشي.`);
    else if (S.hist.length >= 2 && S.hist.every((h) => h[0] === champ)) story.push("تصدّر من أول جولة لآخر جولة، وما حدا قدر ينزله عن العرش.");
    if (rows.length > 1 && rows[0].pts === rows[1].pts) story.push(`البطولة انحسمت بالتفاصيل: نفس نقاط ${nm(order[1])} بالزبط!`);
    const buys = S.log.filter((e) => e.k === "buy").sort((a, b) => b.price - a.price);
    if (buys[0]) story.push(`أغلى صفقة بالموسم: ${nm(buys[0].club)} دفع ${buys[0].price} مليون على ${C.STARS[buys[0].star][0]}.`);
    const res = S.log.filter((e) => e.k === "res").sort((a, b) => Math.abs(b.hg - b.ag) - Math.abs(a.hg - a.ag) || (b.hg + b.ag) - (a.hg + a.ag));
    if (res[0] && res[0].hg !== res[0].ag) story.push(`أكبر نتيجة: ${nm(res[0].h)} ${res[0].hg}-${res[0].ag} ${nm(res[0].a)} بالجولة ${res[0].md + 1}.`);
    const vars = S.log.filter((e) => e.k === "var").length, late = S.log.filter((e) => e.k === "late").length;
    if (vars) story.push(`الـVAR لغى ${vars === 1 ? "هدف واحد" : vars + " أهداف"} هالموسم، وأصحابهم لسا زعلانين.`);
    if (late) story.push(`و${late === 1 ? "هدف واحد" : late + " أهداف"} إجوا بالوقت القاتل.`);
    story.push(`وبآخر الجدول ${nm(last)}... الموسم الجاي أحسن إن شاء الله.`);
    const hs = order.filter((id) => !club(S, id).bot);
    const loser = hs.length >= 2 ? hs[hs.length - 1] : null;
    S.fin = { order, champ, awards: aw, story, loser, dare: loser ? rpick(S, C.DARES) : null };
    S.phase = "final"; S.show = null; S.done = [];
  }

  // ---------- الحركات ----------
  // ctx: { career } (بيانات الألغاز المجهّزة، أو null). بترجع true إذا تغيّرت الحالة.
  function apply(G, a, ctx) {
    const { S, H } = G;
    if (!a || !S) return false;
    if (a.t === "go") {
      if (S.phase === "intro" || S.phase === "table") nextMd(G, ctx);
      else if (S.phase === "news") openPrep(G);
      else if (S.phase === "prep") closePrep(G);
      else if (S.phase === "prepShow") openSeg(G, 0);
      else if (S.phase === "seg") closeSeg(G);
      else if (S.phase === "segShow") { if (S.seg + 1 < S.segs) openSeg(G, S.seg + 1); else endMd(G); }
      else return false;
      autoClose(G);
      return true;
    }
    const c = club(S, a.pid);
    if (!c || c.bot || S.done.includes(c.id)) return false;
    if (a.t === "prep" && S.phase === "prep") {
      const bid = clamp(Math.round((+a.bid || 0) / C.STEP) * C.STEP, 0, c.budget);
      H.prep[c.id] = { ans: [0, 1, 2, 3].includes(a.ans) ? a.ans : -1, bid };
      S.done.push(c.id); autoClose(G);
      return true;
    }
    if (a.t === "seg" && S.phase === "seg") {
      if (!C.ATT[a.att] || !C.DEF[a.def]) return false;
      const card = a.card && c.cards.includes(a.card) && cardAllowed(S, a.card) ? a.card : null;
      H.seg[c.id] = { att: a.att, def: a.def, card };
      S.done.push(c.id); autoClose(G);
      return true;
    }
    return false;
  }
  // إذا كل البشر خلّصوا، بنسكّر المرحلة لحالنا
  function autoClose(G) {
    const { S } = G;
    if (S.phase !== "prep" && S.phase !== "seg") return;
    if (!humans(S).every((c) => S.done.includes(c.id))) return;
    if (S.phase === "prep") closePrep(G); else closeSeg(G);
  }

  const api = { newGame, apply, standings, fixtures, prepCareer, genPuzzle, humans, club, roles, starOf, rival, matchOf, cardAllowed, winPts, rnd };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.HasmCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
