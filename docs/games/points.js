// «جمع نقاط» النسخة 2: لوحة أسئلة بين فرق (2-5)، كل فريق إله سؤال من كل مستوى بكل قسم.
// المراحل: اللوحة ← جولة السرعة (بالنص) ← اللوحة ← الرهان الأخير ← التتويج.
// المحرك عند صاحب الغرفة (أو على التلفون الواحد)، والضيوف بيرسموا الحالة اللي بتوصلهم.
/* global mqtt, Sound, FXL, howto, Rewards */
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const store = { get(k, d) { try { const v = localStorage.getItem("points-" + k); return v ? JSON.parse(v) : d; } catch { return d; } }, set(k, v) { try { localStorage.setItem("points-" + k, JSON.stringify(v)); } catch {} } };
function render(html) { $("app").innerHTML = html; }
function bind(map) { for (const [id, fn] of Object.entries(map)) { const el = $(id); if (el) el.onclick = fn; } }
const sfx = (k, d, a) => { try { Sound.fx(k, d || 0, a); } catch {} };

// ---------- القواعد ----------
const LEVELS = [null, { name: "سهل", pts: 100 }, { name: "متوسط", pts: 200 }, { name: "صعب", pts: 300 }, { name: "صعب جداً", pts: 500 }];
const LV = [1, 2, 3, 4];
const MAX_TEAMS = 5;
const CATS_N = [2, 3, 4, 5, 6];
const SECS = [20, 30, 45, 60];
const STEAL_MS = 15000, OFFER_MS = 7000, NEXT_MS = 4600;
const RUSH_N = 5, RUSH_PTS = 150, RUSH_MS = 15000, BUZZ_MS = 8000;
const FIN_BET_MS = 30000, FIN_Q_MS = 40000;
const CARDS = 3, FIRE_AT = 3, FIRE_BONUS = 50;
const AIDS = {
  cut: { icon: "✂️", name: "احذف ثنتين", tip: "بيشيل جوابين غلط" },
  two: { icon: "✌️", name: "جاوب جوابين", tip: "إلكم محاولتين بنفس السؤال" },
  pit: { icon: "🕳️", name: "الحفرة", tip: "إذا جاوبتوا صح، المتصدّر بيخسر نفس النقاط" },
  dbl: { icon: "🎯", name: "دبّلها", tip: "نقاط السؤال ×2 إذا جاوبتوا صح" },
  time: { icon: "⏱️", name: "وقت زيادة", tip: "+20 ثانية على العدّاد" },
  swap: { icon: "🔄", name: "سؤال ثاني", tip: "بيبدّل السؤال بغيره من نفس المستوى" },
};
const AID_DEFAULT = ["cut", "two", "pit"];
const minutes = (cats, teams) => Math.round(cats * 4 * teams * 0.75 + 4);
let DATA, CAT;

// ---------- ذاكرة ضد التكرار: لكل قسم، الأسئلة اللي انسألت على هالجهاز ----------
const qkey = (q) => q[1] + "|" + (q[3] || "") + "|" + q[2][0];
const SEEN = store.get("seen2", null) || {};
try { localStorage.removeItem("points-used"); } catch {}   // الذاكرة القديمة (قبل النسخة 2)
const seenOf = (cid) => new Set(SEEN[cid] || []);
function markSeen(cid, q) { const k = qkey(q); const l = SEEN[cid] || (SEEN[cid] = []); if (!l.includes(k)) l.push(k); if (l.length > 1500) l.splice(0, l.length - 1500); store.set("seen2", SEEN); }

// ---------- أقسام بتتولّد من البيانات (أسئلة ما بتخلص) ----------
let PL = null;   // اللاعبين
async function loadPlayers() {
  if (PL) return PL;
  const j = await (await fetch("players.json?t=" + Math.floor(Date.now() / 3.6e6))).json();
  const NATFIX = { "مملكة هولندا": "هولندا", "ألمانيا الغربية": "ألمانيا", "يوغوسلافيا": "صربيا" };
  // اللاعبين المغمورين من الدوري الياباني كثار بالبيانات، فبنخلي بس المشاهير منهم
  const all = j.players.filter((p) => p.a && !/[A-Za-z]/.test(p.a) && (p.nat || []).length && !(p.lv >= 3 && p.nat[0] === "اليابان"));
  all.forEach((p) => { p.nat = p.nat.map((n) => NATFIX[n] || n); });
  const by = { 1: [], 2: [], 3: [], 4: [] };
  all.forEach((p) => by[p.lv] && by[p.lv].push(p));
  const clubCount = new Map();
  for (const p of all) for (const n of new Set((p.c || []).map((c) => club(c[0])))) clubCount.set(n, (clubCount.get(n) || 0) + (p.lv <= 2 ? 3 : 1));
  const bigClubs = [...clubCount].filter(([, n]) => n >= 12).sort((a, b) => b[1] - a[1]).map(([n]) => n);
  const clubPl = new Map();
  for (const p of all) if (p.lv <= 3) for (const n of new Set((p.c || []).map((c) => club(c[0])))) { if (!clubPl.has(n)) clubPl.set(n, []); clubPl.get(n).push(p); }
  const natN = new Map();
  all.forEach((p) => { if (p.lv <= 3) natN.set(p.nat[0], (natN.get(p.nat[0]) || 0) + 1); });
  const nats = [...natN].filter(([n, k]) => k >= 3 && !/[A-Za-z]|رابطة|الاتحاد السوفيتي/.test(n)).map(([n]) => n).concat(["مصر", "المغرب", "الجزائر", "السعودية", "تونس", "السنغال", "كوريا الجنوبية"]);
  PL = { all, by, bigClubs, clubPl, nats: [...new Set(nats)] };
  return PL;
}
const club = (n) => String(n).replace(/^نادي\s+/, "").replace(/\s+لكرة القدم$/, "").trim();
const lvFor = (d) => ({ 1: [1], 2: [1, 2], 3: [2, 3], 4: [3] }[d]);
const pickP = (d, f = () => true) => { for (let i = 0; i < 80; i++) { const p = pick(PL.by[pick(lvFor(d))]); if (p && f(p)) return p; } return null; };
function decoyNames(p, n = 3, f = () => true) {
  const out = [], pos = (p.pos || [])[0];
  const pools = [PL.by[p.lv].filter((x) => (x.pos || [])[0] === pos), PL.by[p.lv], PL.by[Math.max(1, p.lv - 1)]];
  for (const pool of pools) for (const x of shuffle(pool).slice(0, 40)) { if (x.a !== p.a && !out.includes(x.a) && f(x)) out.push(x.a); if (out.length === n) return out; }
  return out;
}
const fmt = (n) => n.toLocaleString("en-US");
const GEN = {
  g_nat: { name: "من وين اللاعب؟", icon: "🌍", g: "كورة", make(d) {
    const p = pickP(d, (x) => PL.nats.includes(x.nat[0])); if (!p) return null;
    const nat = p.nat[0], dec = shuffle(PL.nats.filter((x) => !p.nat.includes(x))).slice(0, 3);
    return [d, `من أي بلد اللاعب ${p.a}؟`, [nat, ...dec]];
  } },
  g_club: { name: "وين لعب؟", icon: "🏟️", g: "كورة", make(d) {
    if (d === 4) {
      const p = pickP(4, (x) => new Set((x.c || []).map((c) => club(c[0]))).size >= 4); if (!p) return null;
      const cl = [...new Set(p.c.map((c) => club(c[0])))];
      return [d, `أول نادي لعب فيه ${p.a}؟`, [cl[0], ...shuffle(cl.slice(1)).slice(0, 3)]];
    }
    const p = pickP(d, (x) => (x.c || []).length >= 1); if (!p) return null;
    const mine = new Set(p.c.map((c) => club(c[0])));
    const right = pick([...mine].filter((c) => PL.bigClubs.includes(c)).concat(d === 3 ? [...mine] : [])) || pick([...mine]);
    const dec = shuffle(PL.bigClubs.slice(0, d === 1 ? 30 : 70).filter((c) => !mine.has(c))).slice(0, 3);
    return [d, `بأي نادي من هدول لعب ${p.a}؟`, [right, ...dec]];
  } },
  g_face: { name: "مين بالصورة؟", icon: "📸", g: "كورة", img: true, make(d) {
    const p = pickP(Math.min(d, 3), (x) => x.img); if (!p) return null;
    const dec = decoyNames(p); if (dec.length < 3) return null;
    return [d, "مين هاللاعب؟", [p.a, ...dec], (d === 4 ? "blur:" : "") + p.img];
  } },
  g_team: { name: "زميل بالنادي", icon: "🤝", g: "كورة", make(d) {
    const pool = PL.bigClubs.slice(0, d <= 2 ? 25 : 60);
    for (let i = 0; i < 40; i++) {
      const cl = pick(pool), list = (PL.clubPl.get(cl) || []).filter((p) => lvFor(d).includes(p.lv) || (d === 4 && p.lv === 2));
      if (!list.length) continue;
      const p = pick(list), dec = decoyNames(p, 3, (x) => !(x.c || []).some((c) => club(c[0]) === cl));
      if (dec.length === 3) return [d, `مين من هدول لعب بـ${cl}؟`, [p.a, ...dec]];
    }
    return null;
  } },
  g_old: { name: "مين الأكبر؟", icon: "🎂", g: "كورة", make(d) {
    const gap = { 1: 5, 2: 3, 3: 2, 4: 1 }[d];
    for (let i = 0; i < 60; i++) {
      const four = [pickP(d), pickP(d), pickP(d), pickP(d)];
      if (four.some((p) => !p || !p.by)) continue;
      const ys = four.map((p) => p.by).sort((a, b) => a - b);
      if (new Set(four.map((p) => p.a)).size < 4 || ys.some((y, k) => k && y - ys[k - 1] < gap)) continue;
      const old = four.reduce((a, b) => (a.by < b.by ? a : b));
      return [d, "مين الأكبر بالعمر؟", [old.a, ...four.filter((p) => p !== old).map((p) => p.a)]];
    }
    return null;
  } },
  g_math: { name: "حساب سريع", icon: "🧮", g: "ألعاب ممتعة", local: true, make(d) {
    const r = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
    let q, v;
    if (d === 1) { const a = r(12, 89), b = r(11, 79); q = `كم ${a} + ${b}؟`; v = a + b; }
    else if (d === 2) { const a = r(12, 49), b = r(3, 9); q = `كم ${a} × ${b}؟`; v = a * b; }
    else if (d === 3) { if (Math.random() < 0.5) { const a = r(11, 25), b = r(11, 19); q = `كم ${a} × ${b}؟`; v = a * b; } else { const a = r(301, 999), b = r(102, 299); q = `كم ${a} − ${b}؟`; v = a - b; } }
    else { const t = r(0, 2); if (t === 0) { const p = pick([5, 10, 15, 20, 25, 30, 40, 75]), b = r(2, 30) * 20; q = `كم ${p}% من ${b}؟`; v = (p * b) / 100; } else if (t === 1) { const a = r(13, 31); q = `كم ${a} × ${a}؟`; v = a * a; } else { const a = r(4, 12), b = r(3, 9), c = r(10, 60); q = `كم ${a} × ${b} + ${c}؟`; v = a * b + c; } }
    if (!Number.isInteger(v)) return null;
    const near = new Set([v]);
    const steps = d <= 2 ? [1, 2, 10, -1, -2, -10, 3, 11, -9] : [10, -10, 1, -1, 20, 2, -2, 100, -100];
    for (const s of shuffle(steps)) { if (near.size >= 4) break; if (v + s > 0) near.add(v + s); }
    return [d, q, [...near].map(fmt)];
  } },
};
const GEN_IDS = Object.keys(GEN);
const isGen = (cid) => !!GEN[cid];
const needsPlayers = (cats) => cats.some((c) => isGen(c) && !GEN[c].local);

// سحب سؤال لقسم ومستوى: أولاً اللي ما انسأل على هالجهاز، وإذا خلصوا بنفرّغ ذاكرة القسم
function takeQ(cid, d, avoid) {
  const sn = seenOf(cid);
  if (isGen(cid)) {
    let last = null;
    for (let i = 0; i < 50; i++) { const q = GEN[cid].make(d) || GEN[cid].make(Math.max(1, d - 1)); if (!q || q[2].length !== 4 || new Set(q[2]).size !== 4) continue; last = q; const k = qkey(q); if (!avoid.has(k) && !sn.has(k)) return q; }
    return last;
  }
  const all = CAT.get(cid).qs;
  let lvl = all.filter((q) => q[0] === d && !avoid.has(qkey(q)));
  if (!lvl.length) lvl = all.filter((q) => Math.abs(q[0] - d) === 1 && !avoid.has(qkey(q)));
  if (!lvl.length) lvl = all.filter((q) => !avoid.has(qkey(q)));
  if (!lvl.length) lvl = all;
  let fresh = lvl.filter((q) => !sn.has(qkey(q)));
  if (!fresh.length) { const drop = new Set(lvl.map(qkey)); SEEN[cid] = (SEEN[cid] || []).filter((k) => !drop.has(k)); fresh = lvl; }
  return pick(fresh);
}

// ---------- المحرك ----------
let S = null, SECRET = null, mode = null, timer = null;
const nT = () => S.teams.length;
const T = (i) => S.teams[i];
const newHelp = () => Object.fromEntries(((S && S.cfg && S.cfg.aids) || AID_DEFAULT).map((k) => [k, true]));
const newStats = () => ({ right: 0, wrong: 0, steal: 0, streak: 0, best: 0, pit: 0, rush: 0 });
function defCfg() {
  const c = Object.assign({ secs: 30, aids: AID_DEFAULT.slice(), rush: true, final: true }, store.get("cfg", {}));
  if (!SECS.includes(c.secs)) c.secs = 30;
  if (!Array.isArray(c.aids) || c.aids.length !== 3 || !c.aids.every((k) => AIDS[k])) c.aids = AID_DEFAULT.slice();
  return c;
}
const newTeam = (pid, name) => ({ pid, name, score: 0, help: newHelp(), cards: CARDS, st: newStats() });
function fx(kind, extra) { S.fxId = Object.assign({ id: Date.now() + Math.random(), at: Date.now(), kind }, extra || {}); }
function armAt(ms, fn) { clearTimeout(timer); const v = S.v; timer = setTimeout(() => { if (S) { fn(); commit(); } }, Math.max(0, ms - Date.now()) + 200); return v; }

function newGame(cats) {
  SECRET = { pre: {}, taken: [], dbl: [] };
  const taken = new Set();
  S.cats = cats; S.board = {};
  for (const cid of cats) {
    S.board[cid] = LV.map(() => S.teams.map(() => null));
    SECRET.pre[cid] = LV.map((d) => S.teams.map(() => { const q = takeQ(cid, d, taken); taken.add(qkey(q)); return q; }));
  }
  SECRET.taken = [...taken];
  // سؤال دبل مخفي لكل فريق (عشان العدل)
  S.teams.forEach((t, ti) => { const cid = pick(cats), li = Math.floor(Math.random() * 4); SECRET.dbl.push(`${cid}:${li}:${ti}`); });
  S.teams.forEach((t) => { t.score = 0; t.help = newHelp(); t.cards = CARDS; t.st = newStats(); });
  S.turn = Math.floor(Math.random() * nT());
  S.total = cats.length * 4 * nT(); S.done = 0; S.rushDone = !S.cfg.rush || nT() < 2; S.rush = null; S.fin = null; S.awards = null;
  S.phase = "board"; S.cur = null; S.res = null;
  fx("start");
  for (const cid of cats) for (const row of SECRET.pre[cid]) for (const q of row) if (q[3]) { const im = new Image(); im.referrerPolicy = "no-referrer"; im.src = imgUrl(q[3].replace(/^(zoom|blur):/, "")); }
}
const openLeft = (ti) => S.cats.reduce((n, cid) => n + S.board[cid].filter((row) => row[ti] === null).length, 0);
function nextTurn(from) { for (let k = 1; k <= nT(); k++) { const t = (from + k) % nT(); if (openLeft(t)) return t; } return from; }
function openCell(team, cid, li) {
  const row = S.board[cid] && S.board[cid][li];
  if (!row || row[team] !== null || S.phase !== "board" || team !== S.turn) return false;
  S.cur = { owner: team, dbl: SECRET.dbl.includes(`${cid}:${li}:${team}`) };
  setQuestion(SECRET.pre[cid][li][team], cid, li, team);
  if (S.cur.dbl) fx("dbl", { team });
  return true;
}
function setQuestion(q, cid, li, team) {
  const order = shuffle([0, 1, 2, 3]);
  SECRET.right = order.indexOf(0); SECRET.q = q;
  Object.assign(S.cur, { cid, li, d: q[0] || LV[li], lvl: LV[li], text: q[1], img: q[3] || null, opts: order.map((k) => q[2][k]),
    team, gone: [], wrong: [], tries: 1, steal: null, pit: false, x2: false,
    deadline: Date.now() + S.cfg.secs * 1000 + (LV[li] === 4 ? 10000 : 0) + (S.cur.dbl ? 2500 : 0) });
  S.cur.total = S.cur.deadline - Date.now();
  S.phase = "q";
  markSeen(cid, q);
  armQ();
}
function armQ() { const d = S.cur.deadline; armAt(d, () => { if (S.phase === "q" && S.cur.deadline === d) timeUp(); }); }
const leftOpts = (c) => [0, 1, 2, 3].filter((k) => !c.gone.includes(k) && !c.wrong.includes(k)).length;
// غلط أو خلص الوقت: الفرق الثانية بتقدر تسرق بكرت (الأسرع بياخذها). الصح بكامل النقاط، والغلط بينخصم نصها
function openSteal() {
  const c = S.cur;
  c.lastWrong = c.team;
  const able = S.teams.map((_, k) => k).filter((k) => k !== c.owner && T(k).cards > 0);
  if (leftOpts(c) < 2 || !able.length) return finish(null, null);
  c.steal = "offer"; c.offer = able; c.declined = []; c.team = null; c.deadline = Date.now() + OFFER_MS; c.total = OFFER_MS;
  fx("steal");
  armQ();
}
function timeUp() {
  const c = S.cur;
  if (!c.steal) { T(c.owner).st.wrong++; openSteal(); }
  else if (c.steal === "offer") finish(null, null);
  else finish(null, null, c.team);
}
function useCard(team) {
  const c = S.cur;
  if (S.phase !== "q" || c.steal !== "offer" || !c.offer.includes(team) || c.declined.includes(team) || T(team).cards <= 0) return false;
  T(team).cards--;
  c.steal = "answer"; c.team = team; c.deadline = Date.now() + STEAL_MS; c.total = STEAL_MS;
  fx("buzz", { team });
  armQ();
  return true;
}
function decline(team) {
  const c = S.cur;
  if (S.phase !== "q" || c.steal !== "offer") return false;
  if (team === "all") { finish(null, null); return true; }
  if (!c.offer.includes(team) || c.declined.includes(team)) return false;
  c.declined.push(team);
  if (c.offer.every((k) => c.declined.includes(k))) finish(null, null);
  return true;
}
const basePts = (c) => LEVELS[c.lvl].pts;
const cellPoints = (c) => basePts(c) * (c.dbl ? 2 : 1) * (c.x2 ? 2 : 1);
const leaderExcept = (ti) => { let best = -1; S.teams.forEach((t, k) => { if (k !== ti && (best < 0 || t.score > T(best).score)) best = k; }); return best; };
function finish(winner, pickK, thief = null) {
  clearTimeout(timer);
  const c = S.cur;
  let pts = 0, minus = 0, bonus = 0, pitOn = null, fireNew = false;
  if (winner !== null) {
    const t = T(winner);
    pts = cellPoints(c); t.st.right++;
    if (c.steal) t.st.steal++;
    if (winner === c.owner) { t.st.streak++; t.st.best = Math.max(t.st.best, t.st.streak); if (t.st.streak >= FIRE_AT) { bonus = FIRE_BONUS; fireNew = t.st.streak === FIRE_AT; } }
    t.score += pts + bonus;
    if (c.pit && winner === c.owner) { pitOn = leaderExcept(winner); if (pitOn >= 0 && T(pitOn).score > 0) { T(pitOn).score -= pts; t.st.pit += pts; } else pitOn = null; }
  } else if (thief !== null) { minus = Math.round(cellPoints(c) / 2); T(thief).score -= minus; }
  if (winner !== c.owner) T(c.owner).st.streak = 0;
  S.board[c.cid][c.li][c.owner] = winner === null ? -1 : winner;
  S.done++;
  S.res = { winner, pts, minus, thief, bonus, pitOn, right: SECRET.right, pick: pickK, steal: c.steal === "answer", dbl: c.dbl, until: Date.now() + NEXT_MS + (pitOn !== null ? 1200 : 0) };
  c.right = SECRET.right;
  S.phase = "res";
  fx(winner === null ? "none" : pitOn !== null ? "pit" : "good", { team: winner, fire: fireNew, pitOn, pts });
  S.turn = nextTurn(c.owner);
  armAt(S.res.until, () => { if (S.phase === "res") afterRes(); });
}
function answer(team, k) {
  const c = S.cur;
  if (S.phase !== "q" || c.steal === "offer" || team !== c.team || c.gone.includes(k) || c.wrong.includes(k)) return;
  if (k === SECRET.right) return finish(team, k);
  fx("bad", { team });
  c.wrong.push(k);
  if (!c.steal && c.tries > 1) { c.tries--; return; }
  if (!c.steal) { T(c.owner).st.wrong++; openSteal(); } else finish(null, k, team);
}
function useHelp(team, h) {
  const c = S.cur, t = T(team);
  if (S.phase !== "q" || team !== c.team || c.steal || !t.help[h]) return;
  if (h === "cut") {
    const wrongs = [0, 1, 2, 3].filter((k) => k !== SECRET.right && !c.gone.includes(k) && !c.wrong.includes(k));
    if (wrongs.length < 2) return;
    c.gone.push(...shuffle(wrongs).slice(0, 2));
  } else if (h === "two") c.tries = 2;
  else if (h === "pit") c.pit = true;
  else if (h === "dbl") c.x2 = true;
  else if (h === "time") { c.deadline += 20000; c.total += 20000; armQ(); }
  else if (h === "swap") {
    const avoid = new Set([...SECRET.taken, qkey(SECRET.q)]);
    const q = takeQ(c.cid, c.lvl, avoid);
    if (!q) return;
    SECRET.taken.push(qkey(q));
    t.help[h] = false;
    setQuestion(q, c.cid, c.li, team);
    return;
  }
  t.help[h] = false;
  fx("aid", { team, h });
}
function afterRes() {
  if (S.phase !== "res") return;
  S.cur = null;
  const left = S.cats.some((cid) => S.board[cid].some((row) => row.some((x) => x === null)));
  if (left && !S.rushDone && S.done >= Math.ceil(S.total / 2) && S.total >= 8) return startRush();
  if (left) { S.phase = "board"; return; }
  if (S.cfg.final && nT() >= 2) return startFinal();
  gameOver();
}

// ---------- جولة السرعة: 5 أسئلة، الأسرع بالجواب الصح بياخذ 150 ----------
function startRush() {
  S.rushDone = true;
  const avoid = new Set(SECRET.taken);
  SECRET.rush = Array.from({ length: RUSH_N }, (_, i) => { const cid = S.cats[i % S.cats.length]; const q = takeQ(cid, i < 3 ? 1 : 2, avoid); avoid.add(qkey(q)); return { cid, q }; });
  S.rush = { i: -1, n: RUSH_N, st: "intro", wins: S.teams.map(() => 0), until: Date.now() + 4200 };
  S.phase = "rush";
  fx("rush");
  armAt(S.rush.until, () => { if (S.phase === "rush" && S.rush.st === "intro") rushNext(); });
}
function rushNext() {
  const r = S.rush;
  r.i++;
  if (r.i >= r.n) { S.rush = null; S.phase = "board"; fx("rushend"); return; }
  const { cid, q } = SECRET.rush[r.i];
  const order = shuffle([0, 1, 2, 3]);
  SECRET.right = order.indexOf(0);
  markSeen(cid, q);
  Object.assign(r, { st: "q", cid, text: q[1], img: q[3] || null, opts: order.map((k) => q[2][k]), locked: [], buzz: null, win: null, right: null, picks: {}, deadline: Date.now() + RUSH_MS, bdl: 0 });
  armRush();
}
function armRush() {
  const r = S.rush, d = r.buzz !== null ? r.bdl : r.deadline, key = r.i + ":" + r.buzz + ":" + d;
  armAt(d, () => { const x = S.rush; if (!x || S.phase !== "rush" || x.i + ":" + x.buzz + ":" + (x.buzz !== null ? x.bdl : x.deadline) !== key) return; if (x.buzz !== null) rushAnswer(x.buzz, -1); else rushEnd(null); });
}
function rushBuzz(team) {
  const r = S.rush;
  if (mode !== "local" || S.phase !== "rush" || r.st !== "q" || r.buzz !== null || r.locked.includes(team)) return false;
  r.buzz = team; r.bdl = Math.min(r.deadline + BUZZ_MS, Date.now() + BUZZ_MS);
  fx("buzz", { team });
  armRush();
  return true;
}
function rushAnswer(team, k) {
  const r = S.rush;
  if (S.phase !== "rush" || r.st !== "q" || r.locked.includes(team)) return;
  if (mode === "local" && r.buzz !== team) return;
  r.picks[team] = k;
  if (k === SECRET.right) { r.win = team; r.wins[team]++; T(team).score += RUSH_PTS; T(team).st.rush++; return rushEnd(team); }
  r.locked.push(team); r.buzz = null;
  fx("bad", { team });
  if (r.locked.length >= nT()) return rushEnd(null);
  armRush();
}
function rushEnd(win) {
  const r = S.rush;
  r.st = "res"; r.right = SECRET.right; r.win = win; r.buzz = null; r.until = Date.now() + 3600;
  fx(win === null ? "none" : "good", { team: win, rush: true, pts: RUSH_PTS });
  armAt(r.until, () => { if (S.phase === "rush" && S.rush && S.rush.st === "res") rushNext(); });
}

// ---------- الرهان الأخير: كل فريق بيراهن بالسر وبيجاوب بالسر ----------
const round50 = (n) => Math.round(n / 50) * 50;
const betOptions = (ti) => { const m = Math.max(T(ti).score, 300); return [...new Set([0, round50(m / 4), round50(m / 2), m])]; };
function startFinal() {
  const cid = pick(S.cats), q = takeQ(cid, 3, new Set(SECRET.taken));
  const order = shuffle([0, 1, 2, 3]);
  markSeen(cid, q);
  SECRET.fin = { right: order.indexOf(0), bets: {}, ans: {}, q: { text: q[1], img: q[3] || null, opts: order.map((k) => q[2][k]) } };
  S.fin = { cid, st: "bet", done: [], deadline: Date.now() + FIN_BET_MS };
  S.phase = "final";
  fx("final");
  armAt(S.fin.deadline, () => { if (S.phase === "final" && S.fin.st === "bet") finQ(); });
}
function finBet(team, amt) {
  const f = S.fin;
  if (S.phase !== "final" || f.st !== "bet" || f.done.includes(team) || !betOptions(team).includes(amt)) return;
  SECRET.fin.bets[team] = amt; f.done.push(team);
  if (f.done.length >= nT()) finQ();
}
function finQ() {
  const f = S.fin;
  S.teams.forEach((_, k) => { if (!(k in SECRET.fin.bets)) SECRET.fin.bets[k] = 0; });
  Object.assign(f, { st: "q", done: [], q: SECRET.fin.q, deadline: Date.now() + FIN_Q_MS });
  fx("finq");
  armAt(f.deadline, () => { if (S.phase === "final" && S.fin.st === "q") finReveal(); });
}
function finAns(team, k) {
  const f = S.fin;
  if (S.phase !== "final" || f.st !== "q" || f.done.includes(team) || !(k >= 0 && k < 4)) return;
  SECRET.fin.ans[team] = k; f.done.push(team);
  if (f.done.length >= nT()) finReveal();
}
function finReveal() {
  clearTimeout(timer);
  const f = S.fin, R = SECRET.fin;
  f.right = R.right;
  f.res = S.teams.map((t, k) => { const bet = R.bets[k] || 0, a = k in R.ans ? R.ans[k] : -1, ok = a === R.right; const delta = ok ? bet : -bet; t.score += delta; return { bet, a, ok, delta }; });
  f.st = "rev"; f.until = Date.now() + 3500 + nT() * 1300;
  fx("finrev");
  armAt(f.until, () => { if (S.phase === "final" && S.fin.st === "rev") gameOver(); });
}
function gameOver() {
  clearTimeout(timer);
  S.phase = "over"; S.cur = null;
  const best = (f) => { let b = -1, v = 0; S.teams.forEach((t, k) => { if (f(t) > v) { v = f(t); b = k; } }); return b < 0 ? null : { t: b, v }; };
  S.awards = [
    ["🎯", "القنّاصين", "أكثر أجوبة صح", best((t) => t.st.right)],
    ["🦊", "الثعالب", "أكثر سرقات", best((t) => t.st.steal)],
    ["🔥", "المولّعين", "أطول سلسلة صح", best((t) => (t.st.best >= 2 ? t.st.best : 0))],
    ["⚡", "البرق", "أسرع بجولة السرعة", best((t) => t.st.rush)],
    ["🕳️", "حفّارين الحفر", "أكثر نقاط بالحفرة", best((t) => t.st.pit)],
  ].filter((a) => a[3]).map(([e, title, why, b]) => ({ e, title, why, t: b.t, v: b.v }));
  fx("win");
}

function act(a) {
  const team = mode === "local" ? a.team : teamOf(a.pid);
  const boss = mode === "local" || a.pid === S.host;
  switch (a.t) {
    case "join": return join(a);
    case "begin": if (mode !== "host" || !boss || S.phase !== "lobby" || nT() < 2) return; S.phase = "cats"; break;
    case "cfg": {
      if (!boss || S.phase !== "cats") return;
      const c = a.cfg || {}, cfg = S.cfg;
      if (SECS.includes(c.secs)) cfg.secs = c.secs;
      if (Array.isArray(c.aids) && c.aids.length === 3 && c.aids.every((k) => AIDS[k])) cfg.aids = c.aids.slice();
      if (typeof c.rush === "boolean") cfg.rush = c.rush;
      if (typeof c.final === "boolean") cfg.final = c.final;
      if (CATS_N.includes(c.n)) cfg.n = c.n;
      break;
    }
    case "cats":
      if (!boss || S.phase !== "cats" || !Array.isArray(a.cats) || !CATS_N.includes(a.cats.length) || a.cats.some((c) => !CAT.has(c)) || new Set(a.cats).size !== a.cats.length) return;
      if (needsPlayers(a.cats) && !PL) return;
      newGame(a.cats); break;
    case "open": if (!openCell(team, a.cid, a.li)) return; break;
    case "ans": answer(team, a.k); break;
    case "card": if (!useCard(team)) return; break;
    case "decline": if (!decline(a.all ? "all" : team)) return; break;
    case "help": useHelp(team, a.h); break;
    case "next":
      if (S.phase === "res") afterRes();
      else if (S.phase === "rush" && S.rush.st === "intro" && boss) rushNext();
      else if (S.phase === "rush" && S.rush.st === "res") rushNext();
      else if (S.phase === "final" && S.fin.st === "rev" && boss) gameOver();
      else return;
      break;
    case "rbuzz": if (!rushBuzz(team)) return; break;
    case "rans": rushAnswer(team, a.k); break;
    case "bet": finBet(team, a.amt); break;
    case "fans": finAns(team, a.k); break;
    case "skipbet": if (!boss || S.phase !== "final") return; if (S.fin.st === "bet") finQ(); else if (S.fin.st === "q") finReveal(); else return; break;
    case "again": if (!boss || S.phase !== "over") return; S.phase = "cats"; S.cats = []; S.board = {}; S.fin = null; S.rush = null; break;
    case "end": if (!boss || ["lobby", "cats", "over"].includes(S.phase)) return; gameOver(); break;
    default: return;
  }
  commit();
}
function teamOf(pid) { return S.teams.findIndex((t) => t.pid === pid); }
function join(a) {
  if (mode !== "host") return;
  const i = teamOf(a.pid);
  if (i >= 0) { if (a.name) T(i).name = String(a.name).slice(0, 16); return commit(); }
  if (S.phase !== "lobby" || nT() >= MAX_TEAMS) return commit();
  S.teams.push(newTeam(a.pid, String(a.name || `الفريق ${nT() + 1}`).slice(0, 16)));
  fx("join");
  commit();
}
// لما صاحب الغرفة يرجع (أو التلفون الواحد): نرجّع المؤقتات حسب المرحلة
function rearm() {
  if (!S) return;
  if (S.phase === "q") armQ();
  else if (S.phase === "res") armAt(S.res.until, () => { if (S.phase === "res") afterRes(); });
  else if (S.phase === "rush") { const r = S.rush; if (r.st === "intro") armAt(r.until, () => { if (S.phase === "rush" && S.rush.st === "intro") rushNext(); }); else if (r.st === "q") armRush(); else armAt(r.until, () => { if (S.phase === "rush" && S.rush && S.rush.st === "res") rushNext(); }); }
  else if (S.phase === "final") { const f = S.fin; if (f.st === "bet") armAt(f.deadline, () => { if (S.phase === "final" && S.fin.st === "bet") finQ(); }); else if (f.st === "q") armAt(f.deadline, () => { if (S.phase === "final" && S.fin.st === "q") finReveal(); }); else armAt(f.until, () => { if (S.phase === "final" && S.fin.st === "rev") gameOver(); }); }
}

// ---------- الاتصال (MQTT) ----------
const BROKERS = ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081/mqtt"];
const qs = new URLSearchParams(location.search);
const ROOT = "abuodeh-points-v3";
let client = null, room = null, offset = 0, lastFx = null, ticker = null;
const me = { id: store.get("pid", null), name: store.get("team", "") };
if (!me.id) { me.id = Math.random().toString(36).slice(2, 10); store.set("pid", me.id); }
const topic = (k) => `${ROOT}/${room}/${k}`;
const now = () => Date.now() + offset;
const snap = () => ({ S, SECRET });
// لعبة محفوظة فيها قسم انشال (زي الصوت والفيديو) ما بتكمل
const validSave = (sv) => !!(sv && sv.S && (sv.S.cats || []).every((id) => CAT.has(id)));
function unsnap(saved) { S = saved.S; SECRET = saved.SECRET || { pre: {}, taken: [], dbl: [] }; if (!SECRET.taken) SECRET.taken = []; if (!SECRET.dbl) SECRET.dbl = []; rearm(); }

function commit() {
  S.v = (S.v || 0) + 1; S.now = Date.now();
  if (mode === "host") {
    store.set("host-" + room, snap());
    store.set("online", { room, host: true, at: Date.now() });
    try { client.publish(topic("s"), JSON.stringify(S), { qos: 1, retain: true }); } catch {}
  } else if (mode === "local") store.set("local", snap());
  onState(S);
}
function send(a) {
  a.pid = me.id;
  if (mode === "host" || mode === "local") return act(a);
  if (client) client.publish(topic("a"), JSON.stringify(a), { qos: 1 });
}
function connect(onReady, k = 0) {
  if (typeof mqtt === "undefined") { if ((connect.w = (connect.w || 0) + 1) < 25) return setTimeout(() => connect(onReady, k), 300); return fail("ما قدرت أحمّل الاتصال. تأكدوا من الإنترنت وارجعوا جرّبوا."); }
  connect.w = 0;
  const url = qs.get("broker") || BROKERS[k % BROKERS.length];
  let ready = false;
  const c = mqtt.connect(url, { clientId: "ap_" + me.id + "_" + Math.random().toString(36).slice(2, 6), reconnectPeriod: 2000, connectTimeout: 8000, clean: true });
  const giveUp = setTimeout(() => { if (!ready) { c.end(true); if (k + 1 < BROKERS.length && !qs.get("broker")) connect(onReady, k + 1); else fail("ما قدرت أتصل. جرّبوا كمان شوي."); } }, 9000);
  c.on("connect", () => {
    if (!ready) { ready = true; clearTimeout(giveUp); client = c; onReady(); return; }
    if (!room) return;
    c.subscribe(topic("s"), { qos: 1 });
    if (mode === "host") { c.subscribe(topic("a"), { qos: 1 }); commit(); } else send({ t: "join", name: me.name });
  });
  c.on("message", (t, buf) => {
    const s = buf.toString();
    if (!s) { if (t === topic("s") && mode === "guest" && S) fail("صاحب الغرفة سكّرها."); return; }
    let m; try { m = JSON.parse(s); } catch { return; }
    if (t === topic("s") && mode === "guest") onState(m);
    else if (t === topic("a") && mode === "host") act(m);
  });
}
function fail(msg) { render(`<section class="card stack center"><h1>مشكلة بالاتصال</h1><p class="sub">${esc(msg)}</p><button class="btn" id="back" type="button">رجوع</button></section>`); bind({ back: leave }); }
function leave() {
  try { if (client && mode === "host" && room) client.publish(topic("s"), "", { qos: 1, retain: true }); } catch {}
  const c = client; setTimeout(() => { try { c && c.end(true); } catch {} }, 300);
  client = null; room = null; S = null; SECRET = null; mode = null; clearTimeout(timer); clearInterval(ticker);
  store.set("online", null);
  history.replaceState(null, "", location.pathname);
  intro();
}
function hostRoom(code, saved) {
  mode = "host";
  room = code || String(Math.floor(10000 + Math.random() * 90000));
  loading("عم بفتح الغرفة...");
  connect(() => {
    client.subscribe([topic("s"), topic("a")], { qos: 1 });
    if (validSave(saved)) unsnap(saved);
    else S = { room, host: me.id, phase: "lobby", cfg: defCfg(), teams: [], cats: [], board: {}, turn: 0 };
    if (!S.teams.length) S.teams.push(newTeam(me.id, me.name || "الفريق الأول"));
    commit();
  });
}
function joinRoom(code) {
  mode = "guest"; room = code;
  store.set("online", { room, host: false, at: Date.now() });
  loading("عم بدخل الغرفة...");
  connect(() => {
    client.subscribe(topic("s"), { qos: 1 });
    send({ t: "join", name: me.name });
    setTimeout(() => {
      if (S) return;
      render(`<section class="card stack center"><h1>ما في رد من الغرفة ${esc(room)}</h1><p class="sub">تأكدوا من الكود، وإنه تلفون صاحب الغرفة مفتوح على اللعبة.</p><button class="btn" id="again" type="button">جرّبوا كمان مرة</button><button class="btn alt" id="back" type="button">رجوع</button></section>`);
      bind({ again: () => send({ t: "join", name: me.name }), back: leave });
    }, 7000);
  });
}
function localGame(saved) {
  mode = "local"; room = null;
  if (validSave(saved)) { unsnap(saved); return commit(); }
  localNames(store.get("nteams", 2));
}
const DEF_NAMES = ["الصقور", "النمور", "الأسود", "الذيابة", "النسور"];
function localNames(n) {
  const names = store.get("names", DEF_NAMES);
  render(`<section class="hero small"><h1>على تلفون واحد</h1><p class="sub">التلفون بيلف على الفرق. كل فريق إله لون.</p></section>
    <h2>كم فريق؟</h2>
    <div class="seg">${[2, 3, 4, 5].map((k) => `<button type="button" data-n="${k}" aria-pressed="${n === k}">${k} فرق</button>`).join("")}</div>
    <h2>أسماء الفرق</h2>
    <div class="teamlist">${Array.from({ length: n }, (_, i) => `<label class="trow t${i}"><i></i><input class="input bare" id="n${i}" type="text" maxlength="16" value="${esc(names[i] || DEF_NAMES[i])}" autocomplete="off"></label>`).join("")}</div>
    <button class="btn" id="go" type="button">اختاروا الأقسام</button>
    <button class="btn alt" id="back" type="button">رجوع</button>`);
  const keep = () => { const cur = store.get("names", DEF_NAMES).slice(); for (let i = 0; i < n; i++) cur[i] = $("n" + i).value.trim() || cur[i] || DEF_NAMES[i]; store.set("names", cur); };
  document.querySelectorAll("[data-n]").forEach((b) => (b.onclick = () => { keep(); store.set("nteams", +b.dataset.n); localNames(+b.dataset.n); }));
  bind({
    back: () => { mode = null; intro(); },
    go: () => {
      keep();
      const all = store.get("names", DEF_NAMES);
      S = { room: null, host: me.id, phase: "cats", cfg: defCfg(), teams: [], cats: [], board: {}, turn: 0 };
      S.teams = Array.from({ length: n }, (_, i) => newTeam("local" + i, all[i] || DEF_NAMES[i]));
      commit();
    },
  });
}

// ---------- الواجهة ----------
const myTeam = () => (mode === "local" ? -2 : S ? teamOf(me.id) : -1);
const canAct = (team) => mode === "local" || myTeam() === team;
const isBoss = () => mode === "local" || (S && S.host === me.id);
const loading = (m) => render(`<div class="loading"><span class="nuqat" aria-hidden="true"><i></i><i></i></span><p>${esc(m)}</p></div>`);
let prevScores = null, prevLeader = null;
window.leaveGuard = () => (S && !["lobby", "over"].includes(S.phase) && mode === "local" ? false : S && !["lobby", "over", "cats"].includes(S.phase) ? "اللعبة شغّالة، بدكم تطلعوا؟" : false);

function onState(st) {
  if (!st) return;
  if (mode === "guest") {
    if (st.room !== room) return;
    if (S && st.v <= S.v && st.host === S.host) return;
    if (st.teams && !st.teams.some((t) => t.pid === me.id) && (st.phase !== "lobby" || st.teams.length >= MAX_TEAMS)) { S = st; return full(); }
  }
  S = st;
  offset = (st.now || Date.now()) - Date.now();
  if (mode === "host" || mode === "guest") store.set("online", { room, host: mode === "host", at: Date.now() });
  const f = S.fxId;
  if (f && f.id !== lastFx) { lastFx = f.id; if (now() - (f.at || 0) < 8000) effects(f); }
  draw();
}
function full() { render(`<section class="card stack center"><h1>الغرفة مليانة</h1><p class="sub">في ${MAX_TEAMS} فرق جوّا، أو اللعبة بلّشت.</p><button class="btn alt" id="back" type="button">رجوع</button></section>`); bind({ back: leave }); }
const tname = (i) => (i === null || i === undefined || i < 0 || !S.teams[i] ? "" : S.teams[i].name);
const mineT = (i) => mode === "local" || i === myTeam();

function effects(f) {
  const mine = f.team !== undefined && f.team !== null && mineT(f.team);
  switch (f.kind) {
    case "start": FXL.wipe("#FFC533"); sfx("stage"); break;
    case "join": sfx("join"); break;
    case "dbl": FXL.big("دبل 🔥", mode === "local" ? `«${tname(f.team)}» نقاطهم ضعف` : mine ? "نقاط السؤال ضعف" : `«${tname(f.team)}» فتحوا الدبل`, { color: "#FF5638", ms: 1900 }); sfx("gold"); break;
    case "good":
      if (mine || mode === "local") { FXL.float(`+${f.pts || ""}`); sfx("ok"); sfx("cheer", 0.08); haptic("success"); if (f.pts >= 500) FXL.burst(); }
      else sfx("ding");
      if (f.fire) setTimeout(() => { FXL.banner(`🔥 «${tname(f.team)}» مولّعين! كل صح +${FIRE_BONUS}`, "fire"); sfx("fire"); }, 700);
      break;
    case "pit": FXL.big("الحفرة 🕳️", `«${tname(f.pitOn)}» خسروا ${f.pts}`, { color: "#B9A4FF", ms: 2000 }); sfx("boom"); haptic("error"); break;
    case "bad": if (mine) { sfx("bad"); FXL.shake(); haptic("error"); } else sfx("tick"); break;
    case "none": sfx("ooh"); break;
    case "steal": FXL.banner("🦊 فرصة سرقة! الأسرع بياخذها"); sfx("whistle"); break;
    case "buzz": sfx("pass"); haptic("success"); break;
    case "aid": sfx("gold"); break;
    case "rush": FXL.wipe("#FF5638"); FXL.big("جولة السرعة ⚡", `${RUSH_N} أسئلة · الأسرع بياخذ ${RUSH_PTS}`, { color: "#FF5638", ms: 2300 }); sfx("stage"); sfx("crowd", 0.4); break;
    case "rushend": FXL.banner("رجعنا للوحة 👀"); sfx("whistle"); break;
    case "final": FXL.wipe("#B9A4FF"); FXL.big("الرهان الأخير 🎰", "راهنوا بالسر على سؤال واحد", { color: "#B9A4FF", ms: 2300, quiet: true }); sfx("finalcall"); break;
    case "finq": sfx("drum", 0, 1.2); break;
    case "finrev": sfx("drum", 0, 1.6); break;
    case "win": sfx("final"); FXL.confetti(5000); break;
  }
}
function haptic(kind) {
  try { window.webkit?.messageHandlers?.haptic?.postMessage(kind); } catch {}
  try { navigator.vibrate && navigator.vibrate(kind === "error" ? [80, 60, 120] : [40]); } catch {}
}
// بعد كل رسمة: النقاط بتنعدّ، وإشعار لما الصدارة تتغيّر
function afterDraw() {
  const sc = S.teams.map((t) => t.score);
  if (prevScores && prevScores.length === sc.length) document.querySelectorAll(".pod b.sc").forEach((b) => { const i = +b.dataset.i; if (prevScores[i] !== sc[i]) FXL.countUp(b, prevScores[i], sc[i], 700); });
  prevScores = sc;
  if (!["board", "res", "rush", "final"].includes(S.phase)) { prevLeader = null; return; }
  const top = Math.max(...sc), lead = sc.filter((x) => x === top).length === 1 && top > 0 ? sc.indexOf(top) : null;
  if (lead !== null && prevLeader !== null && lead !== prevLeader) setTimeout(() => { FXL.banner(`👑 صدارة جديدة: «${tname(lead)}»`, "gold"); sfx("lead"); }, 900);
  if (lead !== null) prevLeader = lead;
}

function pods(active = -1) {
  const top = Math.max(...S.teams.map((t) => t.score));
  return `<div class="pods n${nT()}" style="--n:${nT()}">${S.teams.map((t, i) => `<div class="pod t${i} ${active === i ? "on" : ""}">
    <div class="nm">${t.score === top && top > 0 ? "👑 " : ""}${esc(t.name)}${mode !== "local" && t.pid === me.id ? " · إنتو" : ""}</div>
    <b class="sc" data-i="${i}">${t.score}</b>
    ${t.help ? `<div class="chips">${Object.keys(t.help).map((k) => `<span class="${t.help[k] ? "" : "off"}">${AIDS[k] ? AIDS[k].icon : ""}</span>`).join("")}<span class="${t.cards > 0 ? "" : "off"}">🦊${t.cards}</span>${t.st && t.st.streak >= FIRE_AT ? `<span class="fire">🔥${t.st.streak}</span>` : ""}</div>` : ""}</div>`).join("")}</div>`;
}
function draw() {
  clearInterval(ticker);
  if (!S) return;
  const ph = S.phase;
  if (ph === "lobby") drawLobby();
  else if (ph === "cats") drawCats();
  else if (ph === "board") drawBoard();
  else if (ph === "q") drawQ();
  else if (ph === "res") drawRes();
  else if (ph === "rush") drawRush();
  else if (ph === "final") drawFinal();
  else drawOver();
  afterDraw();
  if (lastPhase !== ph + (S.cur ? S.cur.cid + S.cur.li : "")) { lastPhase = ph + (S.cur ? S.cur.cid + S.cur.li : ""); window.scrollTo(0, 0); }
}
let lastPhase = "";

function drawLobby() {
  const link = location.origin + location.pathname + "?room=" + room;
  render(`<section class="hero small center"><p class="sub">كود الغرفة</p><div class="code">${esc(room)}</div>
      ${mode === "host" ? `<button class="btn alt sm" id="share" type="button">ابعتوا الرابط للفرق</button>` : ""}</section>
    <h2>الفرق (${nT()} من ${MAX_TEAMS})</h2>
    <div class="teamlist">${S.teams.map((t, i) => `<div class="trow t${i}"><i></i><span>${esc(t.name)}</span><small>${i === 0 ? "صاحب الغرفة" : t.pid === me.id ? "إنتو" : "دخلوا"}</small></div>`).join("")}
      ${nT() < MAX_TEAMS ? `<div class="trow slot">${nT() < 2 ? "مستنيين الفريق الثاني..." : "في مكان لفرق كمان"}</div>` : ""}</div>
    ${mode === "host" ? `<button class="btn" id="begin" type="button" ${nT() < 2 ? "disabled" : ""}>${nT() < 2 ? "لازم فريق ثاني يدخل" : `يلا نبلّش بـ${nT()} فرق`}</button>` : `<p class="note">صاحب الغرفة بيبلّش لما الكل يدخل.</p>`}
    <button class="linkish" id="out" type="button">${mode === "host" ? "سكّروا الغرفة" : "اطلعوا"}</button>`);
  bind({
    out: leave, begin: () => send({ t: "begin" }),
    share: async () => {
      const text = `تعالوا نتحدّى بـ«جمع نقاط»! كود الغرفة ${room}`;
      try { if (navigator.share) { await navigator.share({ title: "جمع نقاط", text, url: link }); return; } } catch { return; }
      try { await navigator.clipboard.writeText(text + "\n" + link); $("share").textContent = "انسخ الرابط ✓"; } catch {}
    },
  });
}

// ---------- اختيار الأقسام والإعدادات ----------
let picked = [];
const GROUPS = [
  ["⚽", "كورة", ["g_face", "g_club", "g_nat", "g_team", "g_old", "football", "worldcup", "ucl", "epl", "europe", "arabfoot", "nashama", "arabplayers", "guessplayer", "emojiplayers", "coaches", "commentators", "crests", "stadiums", "live2627", "sports", "athletes"]],
  ["🎉", "ألعاب ممتعة", ["g_math", "zoom", "blur", "emoji", "lies", "whoami", "estimate", "math", "childhood", "first", "riddles", "translate", "nicknames"]],
  ["🇯🇴", "عربي وأردني", ["jordan", "jocities", "proverbs", "dialects", "singers", "islamic", "jofood"]],
  ["🧠", "ثقافة عامة", ["general", "history", "science", "tech", "movies", "cartoons", "videogames", "paintings", "dances"]],
  ["🌍", "دول وأماكن", ["globe", "flags", "capitals", "cities", "landmarks", "castles", "mosques", "currency", "bridges", "towers", "waterfalls", "mountains", "islands", "museums", "ancient"]],
  ["👤", "مشاهير", ["celebs", "actors", "singerspics", "wrestlers", "historic", "scientists"]],
  ["🏷️", "شعارات", ["applogos", "carlogos", "brands", "airlines", "techlogos", "orglogos"]],
  ["🐾", "حيوانات وطبيعة", ["animals", "pets", "sealife", "insects", "dinos", "plants", "space", "birds", "reptiles", "trees", "gems"]],
  ["🍽️", "أكل ولبس وأشياء", ["food", "fruits", "drinks", "desserts", "spices", "costumes", "cars", "instruments", "tools", "sportsgear", "planes", "inventions"]],
];
let catFilter = "all", catSearch = "", showSet = false;
const kindOf = (c) => (c.gen ? (GEN[c.id].img ? ["📷", "صور"] : ["♾️", "ما بتخلص"]) : c.qs.some((q) => q[3] && /^(zoom|blur):/.test(q[3])) ? ["✨", "تأثير"] : c.qs.some((q) => q[3]) ? ["📷", "صور"] : ["✍️", "أسئلة"]);
const countOf = (c) => (c.gen ? "+1000" : String(c.qs.length));
function catGroups() {
  const seen = new Set(), out = [];
  for (const [ic, g, ids] of GROUPS) { const list = ids.filter((id) => !seen.has(id)).map((id) => CAT.get(id)).filter(Boolean); list.forEach((c) => seen.add(c.id)); if (list.length) out.push([ic, g, list]); }
  const rest = [...CAT.values()].filter((c) => !seen.has(c.id));
  if (rest.length) out.push(["➕", "غيرها", rest]);
  return out;
}
const catsN = () => (S.cfg && CATS_N.includes(S.cfg.n) ? S.cfg.n : nT() >= 4 ? 3 : 4);
function sendCfg(patch) { const c = Object.assign({}, S.cfg, patch); store.set("cfg", { secs: c.secs, aids: c.aids, rush: c.rush, final: c.final }); send({ t: "cfg", cfg: c, team: 0 }); }
function drawCats() {
  if (!isBoss()) {
    render(`${pods()}<section class="card stack center"><h1>صاحب الغرفة عم يختار الأقسام</h1><p class="note">ثواني وبتبلّش اللعبة.</p><span class="nuqat" aria-hidden="true"><i></i><i></i></span></section><button class="linkish" id="out" type="button">اطلعوا</button>`);
    return bind({ out: () => { if (confirm("أكيد بدكم تطلعوا؟")) leave(); } });
  }
  if (!PL && mode !== "guest") loadPlayers().catch(() => {});
  const N = catsN(), cfg = S.cfg;
  picked = picked.filter((c) => CAT.has(c)).slice(0, N);
  const groups = catGroups(), q = catSearch.trim();
  const shown = groups.filter(([, g]) => catFilter === "all" || catFilter === g).map(([ic, g, list]) => [ic, g, list.filter((c) => !q || c.name.includes(q))]).filter(([, , l]) => l.length);
  const nq = N * 4 * nT();
  render(`<div class="pickhead"><h1>اختاروا ${N} أقسام</h1><p class="sub">${CAT.size} قسم · كل فريق إله سؤال من كل مستوى بكل قسم</p></div>
    <div class="lenbox"><div class="seg">${CATS_N.map((k) => `<button type="button" data-cn="${k}" aria-pressed="${N === k}">${k}</button>`).join("")}</div>
      <p class="len"><b>${nq}</b> سؤال · حوالي <b>${minutes(N, nT())}</b> دقيقة${cfg.rush ? " · ⚡ جولة سرعة" : ""}${cfg.final ? " · 🎰 رهان أخير" : ""}</p></div>
    <button class="setbtn" id="sett" type="button" aria-expanded="${showSet}">⚙️ إعدادات اللعبة <small>${cfg.secs} ثانية · ${cfg.aids.map((k) => AIDS[k].icon).join(" ")}</small></button>
    ${showSet ? `<section class="card stack sett">
      <div class="label">وقت السؤال</div><div class="seg">${SECS.map((s) => `<button type="button" data-secs="${s}" aria-pressed="${cfg.secs === s}">${s} ث</button>`).join("")}</div>
      <div class="label">وسائل المساعدة (اختاروا 3، كل فريق بياخذهم مرة وحدة)</div>
      <div class="aidpick">${Object.entries(AIDS).map(([k, a]) => `<button type="button" data-aid="${k}" aria-pressed="${cfg.aids.includes(k)}"><span>${a.icon}</span><b>${a.name}</b><small>${a.tip}</small></button>`).join("")}</div>
      <div class="label">المراحل</div>
      <div class="toggles"><button type="button" data-tg="rush" aria-pressed="${cfg.rush}">⚡ جولة السرعة بنص اللعبة</button><button type="button" data-tg="final" aria-pressed="${cfg.final}">🎰 الرهان الأخير بالآخر</button></div>
    </section>` : ""}
    <div class="quick"><button type="button" data-qk="ball">⚽ سهرة كورة</button><button type="button" data-qk="mix">🎉 منوّعة</button><button type="button" data-qk="rnd">🎲 عشوائي</button></div>
    <div class="filters" role="tablist"><button type="button" data-f="all" aria-pressed="${catFilter === "all"}">الكل</button>${groups.map(([ic, g]) => `<button type="button" data-f="${esc(g)}" aria-pressed="${catFilter === g}">${ic} ${esc(g)}</button>`).join("")}</div>
    <input class="input search" id="csearch" type="search" placeholder="🔎 دوّروا على قسم..." value="${esc(catSearch)}" autocomplete="off">
    ${shown.map(([ic, g, list]) => `<section class="cgroup"><h3><span>${ic}</span>${esc(g)}<small>${list.length}</small></h3>
      <div class="ccards">${list.map((c) => { const k = picked.indexOf(c.id), [ki, kn] = kindOf(c);
        return `<button type="button" class="ccard ${c.gen ? "gen" : ""}" data-c="${c.id}" aria-pressed="${k >= 0}"><span class="cic">${c.icon}</span><span class="cbody"><b>${esc(c.name)}</b><small><i>${ki} ${kn}</i> ${countOf(c)}</small></span>${k >= 0 ? `<span class="ord">${k + 1}</span>` : ""}</button>`; }).join("")}</div></section>`).join("") || `<p class="note">ما في قسم بهالاسم.</p>`}
    <div class="dock"><div class="chosen">${Array.from({ length: N }, (_, i) => (picked[i] ? `<span class="on" data-un="${picked[i]}" title="${esc(CAT.get(picked[i]).name)}">${CAT.get(picked[i]).icon}</span>` : "<span></span>")).join("")}</div>
      <button class="btn" id="go" type="button" ${picked.length === N ? "" : "disabled"}>${picked.length === N ? "يلا ▶" : `باقي ${N - picked.length}`}</button></div>
    <button class="linkish" id="out" type="button">${mode === "local" ? "رجوع" : "سكّروا الغرفة"}</button>`);
  const keepY = (fn) => () => { const y = window.scrollY; fn(); drawCats(); window.scrollTo(0, y); };
  document.querySelectorAll("[data-f]").forEach((b) => (b.onclick = () => { catFilter = b.dataset.f; drawCats(); }));
  document.querySelectorAll("[data-un]").forEach((b) => (b.onclick = keepY(() => { picked = picked.filter((x) => x !== b.dataset.un); })));
  document.querySelectorAll("[data-cn]").forEach((b) => (b.onclick = () => sendCfg({ n: +b.dataset.cn })));
  document.querySelectorAll("[data-secs]").forEach((b) => (b.onclick = () => sendCfg({ secs: +b.dataset.secs })));
  document.querySelectorAll("[data-tg]").forEach((b) => (b.onclick = () => sendCfg({ [b.dataset.tg]: !cfg[b.dataset.tg] })));
  document.querySelectorAll("[data-aid]").forEach((b) => (b.onclick = () => { const k = b.dataset.aid; let a = cfg.aids.filter((x) => x !== k); if (a.length === cfg.aids.length) { a = cfg.aids.slice(1).concat(k); } else return; sendCfg({ aids: a }); }));
  const si = $("csearch"); if (si) si.oninput = () => { catSearch = si.value; const pos = si.selectionStart; drawCats(); const n = $("csearch"); n.focus(); n.setSelectionRange(pos, pos); };
  document.querySelectorAll("[data-c]").forEach((b) => (b.onclick = keepY(() => { const c = b.dataset.c; if (picked.includes(c)) picked = picked.filter((x) => x !== c); else if (picked.length < N) picked.push(c); else { picked.shift(); picked.push(c); } })));
  document.querySelectorAll("[data-qk]").forEach((b) => (b.onclick = keepY(() => {
    const g = (name) => (catGroups().find(([, n]) => n === name) || [, , []])[2].map((c) => c.id);
    if (b.dataset.qk === "ball") picked = shuffle(g("كورة")).slice(0, N);
    else if (b.dataset.qk === "mix") { const gs = shuffle(catGroups()); picked = gs.slice(0, N).map(([, , l]) => pick(l).id); }
    else picked = shuffle([...CAT.keys()]).slice(0, N);
  })));
  bind({
    sett: () => { showSet = !showSet; const y = window.scrollY; drawCats(); window.scrollTo(0, y); },
    go: async () => {
      if (picked.length !== N) return;
      if (needsPlayers(picked) && !PL) { $("go").disabled = true; $("go").textContent = "لحظة..."; try { await loadPlayers(); } catch { $("go").textContent = "ما انحمّلت بيانات اللاعبين"; return; } }
      Sound.unlock && Sound.unlock();
      send({ t: "cats", cats: picked.slice(), team: 0 });
    },
    out: () => { if (mode === "local") { store.set("local", null); leave(); } else if (confirm("أكيد بدكم تسكّروا الغرفة؟")) leave(); },
  });
}

// ---------- اللوحة ----------
const LVC = ["", "d1", "d2", "d3", "d4"];
function drawBoard() {
  const ti = S.turn, t = T(ti), mine = canAct(ti);
  const pct = Math.round((S.done / S.total) * 100);
  const rushAt = Math.ceil(S.total / 2);
  render(`${pods(ti)}
    <div class="turnbar t${ti}"><i></i>${mode === "local" ? `دور «${esc(t.name)}» يختار سؤال` : mine ? "دوركم، اختاروا سؤال" : `«${esc(t.name)}» عم يختاروا...`}</div>
    <div class="prog"><i style="width:${pct}%"></i>${!S.rushDone ? `<b style="inset-inline-start:${Math.round((rushAt / S.total) * 100)}%" title="جولة السرعة">⚡</b>` : ""}</div>
    <div class="board ${mine ? "" : "wait"}">${S.cats.map((cid) => { const c = CAT.get(cid);
      return `<div class="catrow"><div class="ci"><span>${c.icon}</span><b>${esc(c.name)}</b></div><div class="lvls">${LV.map((d, li) => { const row = S.board[cid][li], st = row[ti];
        const dots = `<span class="dots">${row.map((w, k) => `<i class="${w === null ? "" : w === -1 ? "x" : "w t" + w} ${k === ti ? "me" : ""}"></i>`).join("")}</span>`;
        return st === null ? `<button class="lv ${LVC[d]}" type="button" data-cid="${cid}" data-li="${li}">${LEVELS[d].pts}${dots}</button>`
          : `<button class="lv done ${st === -1 ? "miss" : "w t" + st}" type="button" disabled>${st === -1 ? "✕" : "✓"}${dots}</button>`; }).join("")}</div></div>`; }).join("")}</div>
    <div class="legend"><span class="d1">سهل</span><span class="d2">متوسط</span><span class="d3">صعب</span><span class="d4">صعب جداً</span></div>
    <p class="note">🔥 في سؤال دبل مخفي لكل فريق${!S.rushDone ? " · ⚡ جولة السرعة بنص اللعبة" : ""}${S.cfg.final ? " · 🎰 الرهان الأخير بالآخر" : ""}</p>
    ${isBoss() ? `<button class="linkish" id="end" type="button">إنهاء اللعبة هسا</button>` : ""}
    <button class="linkish" id="out" type="button">${mode === "local" ? "طلوع (اللعبة بتنحفظ)" : "اطلعوا من اللعبة"}</button>`);
  if (mine) document.querySelectorAll(".lv:not(.done)").forEach((b) => (b.onclick = () => { Sound.unlock && Sound.unlock(); send({ t: "open", cid: b.dataset.cid, li: +b.dataset.li, team: ti }); }));
  bind({
    end: () => { if (confirm("أكيد بدكم تنهوا اللعبة هسا؟")) send({ t: "end", team: 0 }); },
    out: () => { if (mode === "local") { mode = null; S = null; intro(); } else if (confirm("أكيد؟")) leave(); },
  });
}

// ---------- الوسائط ----------
function imgUrl(u) {
  const m = String(u || "").match(/\/wikipedia\/([a-z]+)\/thumb\/[^/]+\/[^/]+\/([^/?]+)\//);
  return m ? `https://${m[1] === "commons" ? "commons.wikimedia.org" : m[1] + ".wikipedia.org"}/wiki/Special:FilePath/${m[2]}?width=640` : u;
}
function media(c, key, live, total, deadline) {
  if (!c.img) return "";
  if (c.img.startsWith("zoom:") || c.img.startsWith("blur:")) {
    const kind = c.img.slice(0, 4), url = imgUrl(c.img.slice(5));
    const T0 = total / 1000, left = Math.max(0, (deadline - now()) / 1000);
    const style = live ? `animation-duration:${T0}s;animation-delay:-${Math.max(0, T0 - left).toFixed(1)}s` : "animation:none";
    return `<div class="fxwrap"><img class="qimg fx-${kind}" style="${style}" src="${esc(url)}" alt="" referrerpolicy="no-referrer" onerror="this.style.display='none'"></div>
      ${live ? `<p class="note">${kind === "zoom" ? "🔍 الصورة بتبعد شوي شوي" : "🌫️ الصورة بتوضح شوي شوي"}، جاوبوا بأسرع وقت</p>` : ""}`;
  }
  const cls = c.img.includes("flagcdn") ? "flag" : c.img.includes("teamlogos") || /\.svg/i.test(c.img) ? "crest" : "";
  return `<img class="qimg ${cls}" src="${esc(imgUrl(c.img))}" data-alt="${esc(c.img)}" alt="" referrerpolicy="no-referrer" onerror="if(this.dataset.alt&&this.src!==this.dataset.alt){this.src=this.dataset.alt;this.dataset.alt='';}else{this.style.display='none'}">`;
}
const RING = 2 * Math.PI * 20;
const ringHTML = () => `<div class="ring" id="ring"><svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="20" class="bg"/><circle cx="24" cy="24" r="20" class="fg" id="ringfg" stroke-dasharray="${RING}" stroke-dashoffset="0"/></svg><b id="secs"></b></div>`;
function runClock(deadline, total, beepOn) {
  let lastBeep = -1;
  const tick = () => {
    const ms = Math.max(0, deadline - now()), s = Math.ceil(ms / 1000), fg = $("ringfg"), sec = $("secs");
    if (!fg) return clearInterval(ticker);
    fg.setAttribute("stroke-dashoffset", String(RING * (1 - Math.min(1, ms / total))));
    sec.textContent = s;
    const hot = s <= 5; $("ring").classList.toggle("hot", hot);
    if (hot && s > 0 && s !== lastBeep && beepOn) { lastBeep = s; sfx("tick"); }
  };
  tick(); ticker = setInterval(tick, 200);
}
function qTop(c, pts, clock) {
  const cat = CAT.get(c.cid);
  return `<div class="qtop"><span class="qcat">${cat.icon} ${esc(cat.name)}</span><span class="lvb ${LVC[c.lvl || c.d || 1]}">${LEVELS[c.lvl || c.d || 1].name}</span><span class="ptchip ${c.dbl || c.x2 ? "x2" : ""}">${pts}${c.dbl ? " 🔥" : ""}${c.x2 ? " 🎯" : ""}</span>${clock ? ringHTML() : ""}</div>`;
}
const LET = ["أ", "ب", "ج", "د"];
function optsHtml(c, enabled, reveal, extraCls = () => "") {
  return `<div class="opts ${reveal ? "locked" : ""}">${c.opts.map((o, k) => {
    const cls = reveal ? (k === c.right ? "right" : (c.wrong || []).includes(k) ? "wrong" : (c.gone || []).includes(k) ? "gone" : "") : (c.gone || []).includes(k) ? "gone" : (c.wrong || []).includes(k) ? "wrong" : "";
    const off = !enabled || (c.gone || []).includes(k) || (c.wrong || []).includes(k);
    return `<button class="opt ${cls} ${extraCls(k)}" type="button" data-k="${k}" ${off ? "disabled" : ""}><span class="k">${LET[k]}</span><span>${esc(o)}</span></button>`; }).join("")}</div>`;
}

// ---------- السؤال ----------
let lastQKey = "";
function drawQ() {
  const c = S.cur;
  const qk = c.cid + ":" + c.li + ":" + c.text + ":" + (c.img || "");
  const enter = qk !== lastQKey; lastQKey = qk;
  const buzzing = c.steal === "offer";
  const t = c.team !== null && c.team !== undefined ? T(c.team) : null;
  const mine = !buzzing && canAct(c.team);
  const myT = myTeam();
  const iCanBuzz = buzzing && (mode === "local" || (c.offer.includes(myT) && !c.declined.includes(myT)));
  const full = cellPoints(c), half = Math.round(full / 2);
  let top = "";
  if (buzzing) {
    const who = mode === "local" ? c.offer : iCanBuzz ? [myT] : [];
    top = `<div class="steal"><b>🦊 مين بدّه يسرق؟</b>
      <small>«${esc(tname(c.lastWrong))}» ما جابوها. الصح <b>+${full}</b>، والغلط <b>−${half}</b>. ${mode === "local" ? "أول فريق بيكبس بياخذها" : iCanBuzz ? "الأسرع بياخذها!" : "الفرق الثانية عم تقرر..."}</small>
      ${who.length ? `<div class="buzz">${who.map((k) => `<button class="t${k}" type="button" data-card="${k}">${mode === "local" ? esc(T(k).name) : "اسرقوها!"}<small>🦊 باقي ${T(k).cards}</small></button>`).join("")}</div>
        <button class="linkish" id="nosteal" type="button">${mode === "local" ? "ما حدا بدّه يسرق" : "لا، مش هالمرة"}</button>` : ""}</div>`;
  } else if (c.steal === "answer") top = `<div class="whoans t${c.team}"><i></i>🦊 «${esc(t.name)}» بيسرقوا · صح <b>+${full}</b> · غلط <b>−${half}</b></div>`;
  else top = `<div class="whoans t${c.team}"><i></i>${mode === "local" ? `«${esc(t.name)}» بيجاوبوا` : mine ? "إنتو بتجاوبوا" : `«${esc(t.name)}» بيجاوبوا...`}${c.pit ? ` · 🕳️ حفرة على «${esc(tname(leaderExcept(c.team)))}»` : ""}</div>`;
  const aids = !c.steal && t && t.help ? Object.keys(t.help) : [];
  render(`${pods(buzzing ? -1 : c.team)}
    ${qTop(c, full, true)}
    ${top}
    <section class="qcard ${enter ? "enter" : ""}">${media(c, c.cid + ":" + c.li, !c.steal, c.total, c.deadline)}<div class="qtext">${esc(c.text)}</div></section>
    <div class="${enter ? "enteropts" : ""}">${optsHtml(c, mine, false)}</div>
    ${c.tries > 1 && !c.steal ? `<p class="note">✌️ معكم محاولتين بهالسؤال</p>` : ""}
    ${aids.length ? `<div class="aids">${aids.map((k) => `<button type="button" data-h="${k}" ${mine && t.help[k] && !(k === "pit" && c.pit) && !(k === "dbl" && c.x2) ? "" : "disabled"}><span>${AIDS[k].icon}</span>${AIDS[k].name}</button>`).join("")}</div>` : ""}`);
  if (mine) {
    document.querySelectorAll(".opt:not([disabled])").forEach((b) => (b.onclick = () => { document.querySelectorAll(".opt").forEach((x) => (x.disabled = true)); b.classList.add("chosen"); send({ t: "ans", k: +b.dataset.k, team: c.team }); }));
    document.querySelectorAll("[data-h]:not([disabled])").forEach((b) => (b.onclick = () => {
      if (b.dataset.h === "swap" && !confirm("بدكم سؤال ثاني بداله؟ (مرة وحدة باللعبة)")) return;
      send({ t: "help", h: b.dataset.h, team: c.team });
    }));
  }
  document.querySelectorAll("[data-card]").forEach((b) => (b.onclick = () => { document.querySelectorAll("[data-card]").forEach((x) => (x.disabled = true)); send({ t: "card", team: +b.dataset.card }); }));
  bind({ nosteal: () => send(mode === "local" ? { t: "decline", all: true } : { t: "decline", team: myT }) });
  runClock(c.deadline, c.total, mine || iCanBuzz);
}
function drawRes() {
  const r = S.res, c = S.cur;
  const w = r.winner !== null ? T(r.winner) : null;
  const mineWin = w && mineT(r.winner);
  const head = w
    ? `<div class="verdict good t${r.winner}"><div><b>${mode === "local" ? `«${esc(w.name)}» جابوها` : mineWin ? "صح عليكم!" : `«${esc(w.name)}» جابوها`}</b><small>${r.steal ? "سرقة ناجحة 🦊" : r.dbl ? "سؤال دبل 🔥" : "جواب صح"}${r.bonus ? ` · 🔥 مولّعين +${r.bonus}` : ""}${r.pitOn !== null && r.pitOn !== undefined ? ` · 🕳️ «${esc(tname(r.pitOn))}» خسروا ${r.pts}` : ""}</small></div><span class="plus">+${r.pts + (r.bonus || 0)}</span></div>`
    : r.thief !== null && r.thief !== undefined
    ? `<div class="verdict bad t${r.thief}"><div><b>«${esc(tname(r.thief))}» سرقوا وغلطوا</b><small>راح عليهم نص نقاط السؤال 🦊</small></div><span class="plus neg">−${r.minus}</span></div>`
    : `<div class="verdict none"><div><b>ولا فريق جابها</b><small>${r.dbl ? "راح الدبل بلاش 🔥" : "الجواب الصح بالأخضر"}</small></div></div>`;
  const left = S.cats.some((cid) => S.board[cid].some((row) => row.some((x) => x === null)));
  const nextTxt = !left ? (S.cfg.final ? "على الرهان الأخير..." : "النتيجة النهائية...") : !S.rushDone && S.done >= Math.ceil(S.total / 2) ? "جاية جولة السرعة ⚡" : "راجعين للوحة...";
  render(`${pods(r.winner === null ? -1 : r.winner)}
    ${qTop(c, cellPoints(c), false)}
    ${head}
    <section class="qcard">${media(c, c.cid + ":" + c.li, false, 1, 0)}<div class="qtext">${esc(c.text)}</div></section>
    ${optsHtml(c, false, true)}
    <button class="autonext" id="next" type="button"><i id="nbar"></i><span>${nextTxt} (اكبسوا للتسريع)</span></button>`);
  bind({ next: () => send({ t: "next", team: 0 }) });
  autoBar(r.until, NEXT_MS);
}
function autoBar(until, total) {
  const tick = () => { const el = $("nbar"); if (!el) return clearInterval(ticker); el.style.width = Math.min(100, (1 - Math.max(0, until - now()) / total) * 100) + "%"; };
  tick(); ticker = setInterval(tick, 100);
}

// ---------- جولة السرعة ----------
function drawRush() {
  const r = S.rush;
  if (r.st === "intro") {
    render(`${pods()}<section class="stagecard rush"><span class="big">⚡</span><h1>جولة السرعة</h1>
      <p>${RUSH_N} أسئلة سريعة للكل. ${mode === "local" ? "أول فريق بيكبس على زرّه بيجاوب" : "كل فريق بيجاوب من تلفونه"}، والجواب الصح الأسرع بياخذ <b>${RUSH_PTS}</b>.</p>
      <p class="sub">الغلط ما بيخصم، بس بيقفل عليكم هالسؤال.</p></section>
      <button class="autonext" id="next" type="button"><i id="nbar"></i><span>${isBoss() ? "بلّشوا هسا ⚡" : "ثواني وبتبلّش..."}</span></button>`);
    bind({ next: () => send({ t: "next", team: 0 }) });
    return autoBar(r.until, 4200);
  }
  const c = { cid: r.cid, lvl: r.i < 3 ? 1 : 2, d: 1, opts: r.opts, img: r.img, text: r.text, right: r.right, gone: [], wrong: [] };
  const myT = myTeam();
  const rev = r.st === "res";
  let ctl = "";
  if (!rev) {
    if (mode === "local") {
      if (r.buzz === null) ctl = `<div class="buzz big">${S.teams.map((t, k) => `<button class="t${k}" type="button" data-rb="${k}" ${r.locked.includes(k) ? "disabled" : ""}>${esc(t.name)}${r.locked.includes(k) ? "<small>غلطوا ✕</small>" : "<small>اكبسوا!</small>"}</button>`).join("")}</div>`;
      else ctl = `<div class="whoans t${r.buzz}"><i></i>«${esc(tname(r.buzz))}» كبسوا أول! جاوبوا</div>`;
    } else ctl = r.locked.includes(myT) ? `<p class="note">غلطتوا، استنوا الباقي...</p>` : "";
  } else ctl = r.win !== null ? `<div class="verdict good t${r.win}"><div><b>${mineT(r.win) && mode !== "local" ? "إنتو الأسرع!" : `«${esc(tname(r.win))}» الأسرع`}</b><small>جولة السرعة ⚡</small></div><span class="plus">+${RUSH_PTS}</span></div>` : `<div class="verdict none"><div><b>ولا فريق جابها</b><small>الجواب الصح بالأخضر</small></div></div>`;
  const canAns = !rev && (mode === "local" ? r.buzz !== null : myT >= 0 && !r.locked.includes(myT));
  const lockedPick = mode !== "local" && r.picks && r.picks[myT] !== undefined;
  render(`${pods(r.buzz === null ? -1 : r.buzz)}
    <div class="rushbar"><b>⚡ جولة السرعة</b><span>${r.i + 1} / ${r.n}</span>${rev ? "" : ringHTML()}</div>
    ${ctl}
    <section class="qcard">${media(c, "rush" + r.i, false, 1, 0)}<div class="qtext">${esc(r.text)}</div></section>
    ${optsHtml(c, canAns && !lockedPick, rev, (k) => (mode !== "local" && r.picks && r.picks[myT] === k && !rev ? "chosen" : ""))}
    ${rev ? `<button class="autonext" id="next" type="button"><i id="nbar"></i><span>${r.i + 1 >= r.n ? "راجعين للوحة..." : "السؤال الجاي..."}</span></button>` : ""}`);
  document.querySelectorAll("[data-rb]").forEach((b) => (b.onclick = () => send({ t: "rbuzz", team: +b.dataset.rb })));
  if (canAns) document.querySelectorAll(".opt:not([disabled])").forEach((b) => (b.onclick = () => { document.querySelectorAll(".opt").forEach((x) => (x.disabled = true)); b.classList.add("chosen"); send({ t: "rans", k: +b.dataset.k, team: mode === "local" ? r.buzz : myT }); }));
  bind({ next: () => send({ t: "next", team: 0 }) });
  if (rev) autoBar(r.until, 3600);
  else runClock(r.buzz !== null ? r.bdl : r.deadline, r.buzz !== null ? BUZZ_MS : RUSH_MS, true);
}

// ---------- الرهان الأخير ----------
let finHand = "";   // على التلفون الواحد: الفريق اللي استلم التلفون هسا
function drawFinal() {
  const f = S.fin, cat = CAT.get(f.cid);
  const myT = myTeam();
  const head = `<section class="stagecard fin"><span class="big">🎰</span><h1>الرهان الأخير</h1><p>قسم السؤال: <b>${cat.icon} ${esc(cat.name)}</b></p></section>`;
  if (f.st === "bet" || f.st === "q") {
    const isBet = f.st === "bet";
    const waiting = S.teams.map((t, k) => `<span class="t${k} ${f.done.includes(k) ? "ok" : ""}"><i></i>${esc(t.name)} ${f.done.includes(k) ? "✓" : "…"}</span>`).join("");
    let body = "";
    const who = mode === "local" ? S.teams.findIndex((_, k) => !f.done.includes(k)) : myT;
    const handKey = f.st + ":" + who;
    if (who >= 0 && !f.done.includes(who)) {
      if (mode === "local" && finHand !== handKey) body = `<section class="handoff t${who}"><i></i><b>سلّموا التلفون لـ«${esc(tname(who))}»</b><p class="sub">${isBet ? "الرهان بالسر، الباقي ما يطّلعوا" : "الجواب بالسر، الباقي ما يطّلعوا"}</p><button class="btn" id="ready" type="button">إحنا «${esc(tname(who))}»، جاهزين</button></section>`;
      else if (isBet) body = `<div class="whoans t${who}"><i></i>${mode === "local" ? `«${esc(tname(who))}»` : "إنتو"}: نقاطكم ${T(who).score}. قدّيش بتراهنوا؟</div>
        <div class="bets">${betOptions(who).map((a, i, arr) => `<button type="button" data-bet="${a}"><b>${a}</b><small>${a === 0 ? "بدون مخاطرة" : i === arr.length - 1 ? "كل إشي 🔥" : i === 1 ? "ربع" : "نص"}</small></button>`).join("")}</div>
        <p class="note">صح = بتربحوا الرهان · غلط = بتخسروه</p>`;
      else body = `<div class="whoans t${who}"><i></i>${mode === "local" ? `«${esc(tname(who))}» جاوبوا بالسر` : "جاوبوا بالسر"}</div>
        <section class="qcard">${media(Object.assign({ cid: f.cid }, f.q), "fin", false, 1, 0)}<div class="qtext">${esc(f.q.text)}</div></section>${optsHtml(Object.assign({}, f.q, { gone: [], wrong: [] }), true, false)}`;
    } else body = `<p class="note">${isBet ? "استنوا باقي الفرق يراهنوا..." : "استنوا باقي الفرق يجاوبوا..."}</p>`;
    render(`${pods()}${head}<div class="waitrow">${waiting}</div>${body}
      <div class="rushbar slim"><span>${isBet ? "وقت الرهان" : "وقت الجواب"}</span>${ringHTML()}</div>
      ${isBoss() && mode !== "local" ? `<button class="linkish" id="skip" type="button">كمّلوا بدون اللي ما خلّصوا</button>` : ""}`);
    bind({ ready: () => { finHand = handKey; drawFinal(); }, skip: () => send({ t: "skipbet", team: 0 }) });
    document.querySelectorAll("[data-bet]").forEach((b) => (b.onclick = () => { document.querySelectorAll("[data-bet]").forEach((x) => (x.disabled = true)); send({ t: "bet", amt: +b.dataset.bet, team: who }); }));
    if (!isBet && who >= 0 && !f.done.includes(who) && (mode !== "local" || finHand === handKey)) document.querySelectorAll(".opt").forEach((b) => (b.onclick = () => { document.querySelectorAll(".opt").forEach((x) => (x.disabled = true)); b.classList.add("chosen"); send({ t: "fans", k: +b.dataset.k, team: who }); }));
    return runClock(f.deadline, isBet ? FIN_BET_MS : FIN_Q_MS, false);
  }
  // الكشف: فريق ورا فريق
  const q = Object.assign({}, f.q, { right: f.right, gone: [], wrong: [] });
  render(`${pods()}${head}
    <section class="qcard"><div class="qtext">${esc(f.q.text)}</div></section>
    ${optsHtml(q, false, true)}
    <div class="finres">${f.res.map((x, k) => `<div class="fr t${k} ${x.ok ? "ok" : "no"}" style="animation-delay:${0.6 + k * 1.1}s"><i></i><b>${esc(tname(k))}</b><span>${x.a >= 0 ? LET[x.a] : "—"}</span><em>${x.bet ? (x.ok ? "+" : "−") + x.bet : "0"}</em></div>`).join("")}</div>
    <button class="autonext" id="next" type="button"><i id="nbar"></i><span>${isBoss() ? "النتيجة النهائية 🏆" : "ثواني والنتيجة..."}</span></button>`);
  bind({ next: () => send({ t: "next", team: 0 }) });
  autoBar(f.until, 3500 + nT() * 1300);
}

// ---------- النهاية ----------
function drawOver() {
  const order = S.teams.map((_, i) => i).sort((x, y) => T(y).score - T(x).score);
  const top = T(order[0]).score, winners = order.filter((i) => T(i).score === top), tie = winners.length > 1;
  const max = Math.max(1, ...S.teams.map((t) => Math.max(0, t.score)));
  const podOrder = order.length >= 3 ? [order[1], order[0], ...order.slice(2)] : [order[1], order[0]];
  const rank = (i) => order.indexOf(i);
  const mine = myTeam();
  if (!rewarded) { rewarded = true; try { const sc = mode === "local" ? top : mine >= 0 ? T(mine).score : 0; Rewards.finish("points", Math.max(5, Math.min(60, Math.round(sc / 60)))); } catch {} }
  render(`<section class="hero center"><span class="crown">🏆</span><h1>${tie ? "تعادل! 🤝" : `«${esc(T(order[0]).name)}» أبطال الليلة`}</h1>
      <p class="sub">${tie ? `${winners.map((i) => `«${esc(T(i).name)}»`).join(" و")} بنفس النقاط` : order.length > 1 ? `بفرق ${top - T(order[1]).score} نقطة عن اللي بعدهم` : ""}</p></section>
    <div class="podium n${nT()}">${podOrder.map((i) => { const t = T(i), k = rank(i);
      return `<div class="col t${i}"><span class="medal">${["🥇", "🥈", "🥉"][k] || k + 1}</span><b>${esc(t.name)}</b><div class="blk" style="height:${64 + Math.round((Math.max(0, t.score) / max) * 120)}px">${t.score}</div></div>`; }).join("")}</div>
    ${S.awards && S.awards.length ? `<h2 class="center">ألقاب الليلة</h2><div class="awards">${S.awards.map((a, i) => `<div class="award t${a.t}" style="animation-delay:${0.4 + i * 0.15}s"><span class="e">${a.e}</span><span><b>${a.title}: «${esc(tname(a.t))}»</b><small>${a.why} (${a.v})</small></span></div>`).join("")}</div>` : ""}
    <div class="stats">${S.teams.map((t, i) => `<div class="t${i}"><i></i><b>${esc(t.name)}</b><span>✓ ${t.st.right}</span><span>✕ ${t.st.wrong}</span><span>🦊 ${t.st.steal}</span><span>🔥 ${t.st.best}</span></div>`).join("")}</div>
    <button class="btn alt" id="shareres" type="button">شاركوا النتيجة</button>
    ${isBoss() ? `<button class="btn" id="again" type="button">لعبة جديدة بأقسام جديدة</button>` : `<p class="note">صاحب الغرفة بيقدر يبدأ لعبة جديدة.</p>`}
    <button class="btn alt" id="out" type="button">خروج</button>`);
  bind({
    again: () => { picked = []; rewarded = false; send({ t: "again", team: 0 }); },
    out: () => { store.set("local", null); leave(); },
    shareres: async () => {
      const text = `🏆 نتيجة «جمع نقاط» بتعليلة:\n${order.map((i, k) => `${["🥇", "🥈", "🥉"][k] || k + 1 + "."} ${T(i).name}: ${T(i).score}`).join("\n")}`;
      try { if (navigator.share) { await navigator.share({ title: "جمع نقاط", text, url: location.origin + location.pathname }); return; } } catch { return; }
      try { await navigator.clipboard.writeText(text); $("shareres").textContent = "انسخت ✓"; } catch {}
    },
  });
}
let rewarded = false;

// ---------- البداية ----------
function intro() {
  const local = store.get("local", null);
  const nCats = CAT ? CAT.size : 0;
  rewarded = false; prevScores = null; prevLeader = null;
  render(`<section class="hero"><span class="badge">النسخة الجديدة</span><h1>جمع نقاط</h1>
      <p class="sub">فرق ضد بعض على لوحة أسئلة. كل فريق إله سؤال من كل مستوى بكل قسم، وفي النص جولة سرعة، وبالآخر رهان بيقلب كل إشي.</p>
      <div class="feats"><span>📚 ${nCats} قسم</span><span>♾️ أقسام ما بتخلص</span><span>⚡ جولة السرعة</span><span>🎰 الرهان الأخير</span></div></section>
    ${validSave(local) && !["over", "cats", "lobby"].includes(local.S.phase) ? `<button class="btn" id="resume" type="button">كمّلوا لعبتكم (${local.S.teams.map((t) => t.score).join(" - ")})</button>` : ""}
    <button class="btn ${validSave(local) && !["over", "cats", "lobby"].includes(local.S.phase) ? "alt" : ""}" id="one" type="button">📱 كل الفرق على تلفون واحد</button>
    <section class="card stack roombox"><b class="rt">🌐 كل فريق من تلفونه</b>
      <input class="input" id="tname" type="text" maxlength="16" placeholder="اسم فريقكم" value="${esc(me.name)}" autocomplete="off">
      <button class="btn alt" id="create" type="button">اعملوا غرفة</button>
      <div class="joinrow"><input class="input code-in" id="code" type="text" inputmode="numeric" maxlength="5" placeholder="كود الغرفة" value="${esc(qs.get("room") || "")}" autocomplete="off"><button type="button" class="btn alt sm" id="join">ادخلوا</button></div>
      <p class="err" id="err" hidden></p></section>
    <button class="soundtg" id="snd" type="button">${Sound.muted ? "🔇 الصوت مسكّر" : "🔊 الصوت شغّال"}</button>
    ${howto("points", `<ul class="rules">
      <li>بالدور، كل فريق بيختار سؤال من <b>أسئلته</b> باللوحة: <b>100</b> سهل، <b>200</b> متوسط، <b>300</b> صعب، <b>500</b> صعب جداً. كل فريق إله نفس العدد بكل قسم.</li>
      <li>4 خيارات و<b>30 ثانية</b> (بتقدروا تغيّروها).</li>
      <li>🦊 كل فريق معه <b>3 كروت سرقة</b>: إذا فريق غلط، الأسرع بيسرق السؤال. الصح بكامل النقاط، والغلط بينخصم نصها.</li>
      <li>🛟 3 وسائل مساعدة لكل فريق (بتختاروها): احذف ثنتين، جاوب جوابين، الحفرة، دبّلها، وقت زيادة، سؤال ثاني.</li>
      <li>🔥 3 أجوبة صح ورا بعض = مولّعين، وكل صح بعدها +50. وفي سؤال دبل مخفي لكل فريق.</li>
      <li>⚡ بنص اللعبة: جولة السرعة، 5 أسئلة للكل والأسرع بياخذ 150.</li>
      <li>🎰 بالآخر: الرهان الأخير. كل فريق بيراهن بالسر على سؤال واحد.</li>
    </ul>`)}`);
  const getName = () => {
    const n = $("tname").value.trim();
    if (!n) { $("err").hidden = false; $("err").textContent = "اكتبوا اسم فريقكم أول."; $("tname").focus(); return null; }
    me.name = n; store.set("team", n); return n;
  };
  bind({
    create: () => { if (getName()) hostRoom(); },
    join: () => {
      if (!getName()) return;
      const code = $("code").value.replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d)).replace(/\D/g, "");
      if (code.length !== 5) { $("err").hidden = false; $("err").textContent = "الكود 5 أرقام."; return; }
      joinRoom(code);
    },
    one: () => { store.set("local", null); localGame(); },
    resume: () => localGame(store.get("local", null)),
    snd: () => { Sound.mute(!Sound.muted); store.set("muted", Sound.muted); $("snd").textContent = Sound.muted ? "🔇 الصوت مسكّر" : "🔊 الصوت شغّال"; if (!Sound.muted) sfx("ok"); },
  });
}
function boot() {
  const saved = store.get("online", null);
  if (qs.get("room")) return false;
  if (saved && saved.room && Date.now() - (saved.at || 0) < 6 * 3600e3) {
    render(`<section class="card stack center"><h1>في لعبة مفتوحة</h1><p class="sub">الغرفة ${esc(saved.room)}${saved.host ? " (إنتو صاحبينها)" : ""}.</p>
      <button class="btn" id="re" type="button">ارجعوا للعبة</button><button class="btn alt" id="no" type="button">لا، طلّعني</button></section>`);
    bind({ re: () => (saved.host ? hostRoom(saved.room, store.get("host-" + saved.room, null)) : joinRoom(saved.room)), no: () => { store.set("online", null); intro(); } });
    return true;
  }
  return false;
}

try { Sound.mute(store.get("muted", false)); } catch {}
fetch("points_q.json?t=" + Math.floor(Date.now() / 3.6e6)).then((r) => r.json()).then((d) => {
  DATA = d;
  CAT = new Map();
  for (const id of GEN_IDS) CAT.set(id, { id, name: GEN[id].name, icon: GEN[id].icon, qs: [], gen: true });
  for (const c of d.cats) CAT.set(c.id, c);
  if (!d.cats.length) { loading("الأسئلة لسا بتتجهز. جرّبوا كمان شوي."); return; }
  if (boot()) return;
  intro();
}).catch(() => loading("ما قدرت أحمّل الأسئلة. تأكدوا من الإنترنت."));
if ("serviceWorker" in navigator) navigator.serviceWorker.register("../sw.js").catch(() => {});
