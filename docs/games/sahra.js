// ملك السهرة: المحرّك + الاتصال + الواجهة.
// صاحب الغرفة هو المرجع: عنده الحالة S، وكل حركة (act) بتمر عليه وبيبعت الحالة للكل (MQTT retained).
// على تلفون واحد: نفس المحرّك بدون اتصال، والتلفون بيلف على اللاعبين.
"use strict";

const MIN = 3, MAX = 8, ROOT = "abuodeh-sahra-v1";
const BROKERS = ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081/mqtt"];
const qs = new URLSearchParams(location.search);
const FAST = qs.has("fast");   // للفحص الآلي بس: بيقصّر وقت التمثيل والقنبلة
const mem = { get: (k, d) => store.get("sahra-" + k, d), set: (k, v) => store.set("sahra-" + k, v) };

let mode = null;          // "host" | "guest" | "local"
let S = null;             // حالة اللعبة
let client = null, room = null, offset = 0, timer = null, lastFx = null, lastKey = "";
let POOL = null;          // بنك أسئلة المعلومات
const DECK = {}, usedQ = new Set();
const L = { ok: null };   // تلفون واحد: مين أكّد إنه ماسك التلفون
const me = { id: mem.get("pid", null), name: mem.get("name", "") };
if (!me.id) { me.id = Math.random().toString(36).slice(2, 10); mem.set("pid", me.id); }

const topic = (k) => `${ROOT}/${room}/${k}`;
const now = () => Date.now() + offset;
const P = (id) => S.players.find((p) => p.id === id);
const ids = () => S.players.map((p) => p.id);
const stage = () => S.plan[S.si];
const HUES = [262, 28, 160, 340, 200, 48, 300, 100];
const pav = (id) => {
  const i = S.players.findIndex((p) => p.id === id), name = i < 0 ? "؟" : S.players[i].name.trim(), num = /^لاعب (\d)$/.exec(name);
  return `<span class="av" style="--h:${HUES[Math.max(0, i) % HUES.length]}" aria-hidden="true">${esc(num ? num[1] : name.charAt(0) || "؟")}</span>`;
};
const nm = (id) => esc(P(id) ? P(id).name : "؟");
const fx = (k) => { S.fx = { id: Date.now() + Math.random(), k }; };
const after = (pid) => { const o = S.order; return o[(o.indexOf(pid) + 1) % o.length]; };
const maxBet = (pid) => Math.max(P(pid).score, 300);

window.leaveGuard = () => (S && mode && !["lobby", "final"].includes(S.phase) ? "السهرة شغّالة، بدك تطلع؟" : false);

// ======================= المحتوى =======================
async function loadPool() {
  if (POOL) return;
  try {
    const j = await (await fetch("points_q.json")).json();
    const cats = [];
    for (const c of j.cats) {
      const list = c.qs.filter((q) => !q[3] || /^https?:/.test(q[3])).map((q) => ({ d: q[0], q: q[1], opts: q[2], img: q[3] || null }));
      if (list.length) cats.push({ cid: c.id, cat: `${c.icon || ""} ${c.name}`.trim(), qs: list });
    }
    if (cats.length) POOL = cats;
  } catch {}
}
function takeQ(kind) {
  const cats = POOL || [{ cid: "fb", cat: "معلومات عامة", qs: FALLBACK_Q }];
  const fits = (c, q) => (kind === "fib" ? q.d >= 2 && !NO_FIB.has(c.cid) && q.opts[0].length <= 28 : kind === "bet" ? q.d >= 2 : q.d <= 2);
  let last = null;
  for (let i = 0; i < 120; i++) {
    const c = pick(cats), q = pick(c.qs), key = c.cid + "|" + q.q + "|" + q.opts[0];
    last = { cat: q.cat || c.cat, q: q.q, opts: q.opts, img: q.img || null };
    if (usedQ.has(key) || (i < 90 && !fits(c, q))) continue;
    usedQ.add(key);
    return last;
  }
  return last;
}
function take(k) {
  if (!DECK[k] || !DECK[k].length) DECK[k] = shuffle(CONTENT[k]);
  return DECK[k].pop();
}

// ======================= المحرّك =======================
const newPlayer = (id, name) => ({ id, name, score: 0, joker: true, st: {} });
const newState = (players) => ({ room, host: me.id, phase: "lobby", players, cfg: { len: mem.get("len", "full") }, plan: [], si: 0, r: 0, order: [], jok: {}, gain: {}, cur: null });

async function begin() {
  S.phase = "loading"; commit();
  await loadPool();
  S.players.forEach((p) => { p.score = 0; p.joker = true; p.st = { right: 0, fooled: 0, herd: 0, star: 0, laugh: 0, boom: 0, acted: 0 }; });
  S.plan = PLANS[S.cfg.len](S.players.length).map(([id, rounds]) => ({ id, rounds }));
  S.order = shuffle(ids());
  S.si = 0; S.r = 0; S.jok = {}; S.gain = {}; S.cur = null; S.awards = null;
  S.phase = "stage"; fx("stage");
  commit();
}

function startRound() {
  const id = stage().id, all = ids(), turn = S.order[S.r % S.order.length];
  const base = { ans: {}, need: all, delta: {} };
  if (id === "warm") {
    const q = takeQ("warm"), opts = shuffle(q.opts);
    S.cur = { ...base, kind: "mcq", q: q.q, img: q.img, cat: q.cat, opts, c: opts.indexOf(q.opts[0]) };
  } else if (id === "fib") {
    const q = takeQ("fib");
    S.cur = { ...base, kind: "fibw", q: q.q, img: q.img, cat: q.cat, truth: q.opts[0], rej: {} };
  } else if (id === "most") {
    S.cur = { ...base, kind: "most", q: `مين فينا أكثر واحد ممكن ${take("most")}؟` };
  } else if (id === "quip") {
    S.cur = { ...base, kind: "quipw", q: take("quip") };
  } else if (id === "wave") {
    const [a, b] = take("wave");
    S.cur = { ...base, kind: "wavec", psy: turn, need: [turn], A: a, B: b, target: 6 + Math.floor(Math.random() * 89) };
  } else if (id === "bet") {
    const q = takeQ("bet");
    S.cur = { ...base, kind: "bet", cat: q.cat, Q: q };
  } else if (id === "act") {
    S.cur = { kind: "act", actor: turn, st: "ready", words: Array.from({ length: 14 }, () => take("act")), wi: 0, got: [], skips: 3, dur: FAST ? 4 : all.length > 5 ? 30 : 40, delta: {} };
    S.phase = "live"; return;
  } else if (id === "bomb") {
    S.cur = { kind: "bomb", q: take("bomb"), holder: turn, st: "ready", passes: 0, delta: {} };
    S.phase = "live"; return;
  }
  S.phase = "ask";
}

function give(pid, pts) {
  const p = P(pid);
  if (!p || !pts) return;
  const before = p.score;
  p.score = Math.max(0, p.score + pts);
  const real = p.score - before;
  S.gain[pid] = (S.gain[pid] || 0) + real;
  S.cur.delta[pid] = (S.cur.delta[pid] || 0) + real;
}

function answer(pid, val) {
  const c = S.cur;
  if (S.phase !== "ask" || !c.need.includes(pid) || pid in c.ans) return;
  const text = (max) => String(val ?? "").trim().replace(/\s+/g, " ").slice(0, max);
  const k = c.kind;
  if (k === "mcq" || k === "betq") { val = +val; if (!(val >= 0 && val < 4)) return; }
  else if (k === "fibw") {
    val = text(40); if (!val) return;
    if (normAr(val) === normAr(c.truth)) { c.rej[pid] = (c.rej[pid] || 0) + 1; return; }  // كتب الجواب الصح بالغلط
  }
  else if (k === "quipw") { val = text(60); if (!val) return; }
  else if (k === "wavec") { val = text(24); if (!val) return; }
  else if (k === "fibp" || k === "quipv") { val = +val; const o = c.opts[val]; if (!o || o.by.includes(pid)) return; }
  else if (k === "most") { if (!P(val)) return; }
  else if (k === "waveg") { val = clamp(Math.round(+val), 0, 100); if (Number.isNaN(val)) return; }
  else if (k === "bet") { val = clamp(Math.round(+val / 50) * 50, 0, maxBet(pid)); if (Number.isNaN(val)) return; }
  c.ans[pid] = val;
  if (c.need.every((id) => id in c.ans)) closeAsk();
}

// كل اللاعبين جاوبوا (أو صاحب الغرفة كمّل بدونهم): احسب النقاط أو انتقل للخطوة الجاية
function closeAsk() {
  const c = S.cur, all = ids(), A = Object.entries(c.ans);
  const reveal = () => { S.phase = "show"; fx("show"); };
  switch (c.kind) {
    case "mcq":
      for (const [pid, v] of A) if (v === c.c) { give(pid, 100); P(pid).st.right++; }
      return reveal();
    case "fibw": {
      const map = new Map();
      for (const [pid, t] of A) { const key = normAr(t); if (!map.has(key)) map.set(key, { t, by: [] }); map.get(key).by.push(pid); }
      c.opts = shuffle([...map.values(), { t: c.truth, by: [], truth: true }]);
      c.kind = "fibp"; c.ans = {}; c.need = all; return;
    }
    case "fibp":
      for (const [pid, v] of A) {
        const o = c.opts[v];
        if (o.truth) { give(pid, 200); P(pid).st.right++; }
        else o.by.forEach((liar) => { give(liar, 100); P(liar).st.fooled++; });
      }
      return reveal();
    case "most": {
      const count = {}; A.forEach(([, v]) => { count[v] = (count[v] || 0) + 1; });
      const top = Math.max(0, ...Object.values(count));
      c.count = count;
      c.top = top >= 2 ? Object.keys(count).filter((id) => count[id] === top) : [];
      c.top.forEach((id) => P(id).st.star++);
      for (const [pid, v] of A) if (c.top.includes(v)) { give(pid, 100); P(pid).st.herd++; }
      return reveal();
    }
    case "quipw":
      c.opts = shuffle(A.map(([pid, t]) => ({ t, by: [pid] })));
      if (c.opts.length < 2) { c.votes = c.opts.map(() => 0); return reveal(); }
      c.kind = "quipv"; c.ans = {}; c.need = all; return;
    case "quipv": {
      c.votes = c.opts.map(() => 0);
      A.forEach(([, v]) => c.votes[v]++);
      const top = Math.max(...c.votes);
      c.best = top > 0 && c.votes.filter((x) => x === top).length === 1 ? c.votes.indexOf(top) : -1;
      c.opts.forEach((o, i) => { const who = o.by[0]; give(who, c.votes[i] * 100 + (i === c.best ? 100 : 0)); P(who).st.laugh += c.votes[i]; });
      return reveal();
    }
    case "wavec":
      c.clue = c.ans[c.psy] || "—";
      c.kind = "waveg"; c.ans = {}; c.need = all.filter((id) => id !== c.psy); return;
    case "waveg": {
      let sum = 0;
      for (const [pid, g] of A) { const d = Math.abs(g - c.target), pts = d <= 6 ? 300 : d <= 14 ? 200 : d <= 25 ? 100 : 0; give(pid, pts); sum += pts; }
      if (A.length) give(c.psy, Math.round(sum / A.length / 50) * 50);
      return reveal();
    }
    case "bet": {
      const opts = shuffle(c.Q.opts);
      S.cur = { kind: "betq", bets: c.ans, cat: c.cat, q: c.Q.q, img: c.Q.img, opts, c: opts.indexOf(c.Q.opts[0]), ans: {}, need: all, delta: {} };
      return;
    }
    case "betq":
      for (const [pid, v] of A) { const b = c.bets[pid] || 0; if (v === c.c) { give(pid, b); P(pid).st.right++; } else give(pid, -b); }
      return reveal();
  }
}

// ----- المراحل الحية: تمثيل وقنبلة -----
function arm(ms, fn) { clearTimeout(timer); timer = setTimeout(() => { fn(); commit(); }, Math.max(0, ms)); }
function rearm() {
  const c = S && S.cur;
  if (!c || S.phase !== "live" || c.st !== "run") return;
  if (c.kind === "act") arm(c.until - Date.now(), endAct); else arm(c.boomAt - Date.now(), boom);
}
function endAct() { clearTimeout(timer); S.cur.st = "done"; S.phase = "show"; fx("show"); }
function boom() {
  clearTimeout(timer);
  const c = S.cur;
  c.st = "boom"; give(c.holder, -150); P(c.holder).st.boom++;
  ids().forEach((id) => { if (id !== c.holder) give(id, 50); });
  S.phase = "show"; fx("boom");
}
function live(a, who) {
  const c = S.cur;
  if (S.phase !== "live") return;
  if (c.kind === "act" && who === c.actor) {
    if (a.t === "cgo" && c.st === "ready") { c.st = "run"; c.until = Date.now() + c.dur * 1000; arm(c.dur * 1000, endAct); fx("go"); }
    else if (c.st === "run" && a.t === "cok" && P(a.g) && a.g !== c.actor) {
      c.got.push({ w: c.words[c.wi], by: a.g }); give(c.actor, 50); give(a.g, 100); P(c.actor).st.acted++; c.wi++; fx("ok");
      if (c.wi >= c.words.length) endAct();
    } else if (c.st === "run" && a.t === "cskip" && c.skips > 0) {
      c.got.push({ w: c.words[c.wi], by: null }); c.skips--; c.wi++;
      if (c.wi >= c.words.length) endAct();
    }
  } else if (c.kind === "bomb" && who === c.holder) {
    if (a.t === "bgo" && c.st === "ready") { c.st = "run"; c.last = Date.now(); c.boomAt = Date.now() + (FAST ? 2500 : 13000 + Math.random() * 19000); arm(c.boomAt - Date.now(), boom); fx("go"); }
    else if (a.t === "bpass" && c.st === "run" && Date.now() - c.last > 900) { c.holder = after(c.holder); c.passes++; c.last = Date.now(); fx("pass"); }
  }
}

// صاحب الغرفة بيكمّل: من بطاقة المرحلة للجولة، ومن النتيجة للجولة الجاية، وهكذا
function advance() {
  if (S.phase === "stage") {
    Object.keys(S.jok).forEach((pid) => { P(pid).joker = false; });
    S.r = 0; startRound();
  } else if (S.phase === "show") {
    S.r++;
    if (S.r < stage().rounds) return startRound();
    S.bonus = {};
    for (const pid of Object.keys(S.jok)) { const g = S.gain[pid] || 0; if (g > 0) { P(pid).score += g; S.bonus[pid] = g; } }
    S.phase = "board"; fx("show");
  } else if (S.phase === "board") {
    S.si++; S.jok = {}; S.gain = {}; S.bonus = {}; S.cur = null;
    if (S.si >= S.plan.length) return finale();
    S.phase = "stage"; fx("stage");
  }
}

function finale() {
  S.si = S.plan.length - 1;
  const AW = [
    ["right", "🎯", "القنّاص", "أكثر واحد جاوب صح"], ["fooled", "🤥", "أكبر كذّاب", "أكثر واحد صدّقوا كذبه"], ["star", "⭐", "حديث السهرة", "أكثر واحد انصوّت عليه بـ«مين فينا»"],
    ["herd", "🐑", "مع القطيع", "أكثر واحد صوّت مع الأغلبية"], ["laugh", "😂", "مهضوم السهرة", "أكثر واحد ضحّكهم"], ["acted", "🎭", "الممثل", "أكثر واحد فهّمهم كلمات"], ["boom", "💣", "المفجوع", "أكثر واحد انفجرت عنده"],
  ];
  S.awards = [];
  for (const [k, e, title, why] of AW) {
    const best = S.players.reduce((a, p) => (p.st[k] > (a ? a.st[k] : 0) ? p : a), null);
    if (best) S.awards.push({ e, title, why, pid: best.id });
  }
  S.dare = take("dare");
  S.phase = "final"; fx("final");
}

function act(a) {
  if (!S) return;
  const boss = mode === "local" || a.pid === S.host;
  const who = mode === "local" ? a.as : a.pid;
  switch (a.t) {
    case "join": {
      const p = P(a.pid);
      if (p) { if (S.phase === "lobby" && a.name) p.name = a.name; }
      else if (S.phase === "lobby" && S.players.length < MAX) { S.players.push(newPlayer(a.pid, String(a.name || "لاعب").slice(0, 14))); fx("join"); }
      else return;
      break;
    }
    case "cfg": if (!boss || S.phase !== "lobby") return; S.cfg.len = a.len === "quick" ? "quick" : "full"; mem.set("len", S.cfg.len); break;
    case "kick": if (!boss || S.phase !== "lobby" || a.who === S.host) return; S.players = S.players.filter((p) => p.id !== a.who); break;
    case "start": if (!boss || S.phase !== "lobby" || S.players.length < MIN) return; begin(); return;
    case "joker": {
      const p = P(mode === "local" ? a.who : a.pid);
      if (S.phase !== "stage" || stage().id === "bet" || !p || !p.joker) return;
      if (S.jok[p.id]) delete S.jok[p.id]; else S.jok[p.id] = true;
      break;
    }
    case "go": if (!boss) return; advance(); break;
    case "ans": answer(who, a.val); break;
    case "force": if (!boss || S.phase !== "ask") return; closeAsk(); break;
    case "cgo": case "cok": case "cskip": case "bgo": case "bpass": live(a, who); break;
    case "skipturn": if (!boss || S.phase !== "live") return; clearTimeout(timer); S.cur.st = "skipped"; S.phase = "show"; break;
    case "dare": if (!boss || S.phase !== "final") return; S.dare = take("dare"); break;
    case "again": if (!boss || S.phase !== "final") return; if (mode === "local") { begin(); return; } S.phase = "lobby"; break;
    default: return;
  }
  commit();
}

// ======================= الاتصال =======================
function commit() {
  S.v = (S.v || 0) + 1; S.now = Date.now();
  if (mode === "host") {
    mem.set("host-" + room, S); mem.set("online", { room, host: true, at: Date.now() });
    try { client.publish(topic("s"), JSON.stringify(S), { qos: 1, retain: true }); } catch {}
  } else if (mode === "local") mem.set("local", S);
  onState(S);
}
function send(a) {
  a.pid = me.id;
  if (mode === "host" || mode === "local") return act(a);
  if (client) client.publish(topic("a"), JSON.stringify(a), { qos: 1 });
}
function connect(onReady, k = 0) {
  if (typeof mqtt === "undefined") return fail("ما قدرت أحمّل الاتصال. تأكد من الإنترنت.");
  const url = qs.get("broker") || BROKERS[k % BROKERS.length];
  let ready = false;
  const c = mqtt.connect(url, { clientId: "sh_" + me.id + "_" + Math.random().toString(36).slice(2, 6), reconnectPeriod: 2000, connectTimeout: 8000, clean: true });
  const giveUp = setTimeout(() => {
    if (ready) return;
    c.end(true);
    if (k + 1 < BROKERS.length && !qs.get("broker")) connect(onReady, k + 1); else fail("ما قدرت أتصل. جرّب كمان شوي.");
  }, 9000);
  c.on("connect", () => {
    if (!ready) { ready = true; clearTimeout(giveUp); client = c; onReady(); return; }
    if (!room) return;                       // رجع الاتصال بعد انقطاع
    c.subscribe(topic("s"), { qos: 1 });
    if (mode === "host") { c.subscribe(topic("a"), { qos: 1 }); commit(); } else send({ t: "join", name: me.name });
  });
  c.on("message", (t, buf) => {
    let m; try { m = JSON.parse(buf.toString()); } catch { return; }
    if (t === topic("s") && mode === "guest") onState(m);
    else if (t === topic("a") && mode === "host") act(m);
  });
}
function fail(msg) { render(`<h1>مشكلة بالاتصال</h1><p class="sub">${esc(msg)}</p><button class="btn" data-a="leave">رجوع</button>`); }
function leave() {
  try { if (client && mode === "host" && room) client.publish(topic("s"), "", { qos: 1, retain: true }); } catch {}
  const c = client; setTimeout(() => { try { c && c.end(true); } catch {} }, 400);
  if (mode === "host") mem.set("host-" + room, null);
  if (mode === "local") mem.set("local", null);
  client = null; room = null; S = null; mode = null; lastKey = ""; clearTimeout(timer);
  mem.set("online", null);
  history.replaceState(null, "", location.pathname + (qs.get("broker") ? "?broker=" + encodeURIComponent(qs.get("broker")) : ""));
  intro();
}
function hostRoom(code) {
  mode = "host"; room = code || String(Math.floor(10000 + Math.random() * 90000));
  render(`<div class="loading">عم بفتح الغرفة...</div>`);
  connect(() => {
    client.subscribe([topic("s"), topic("a")], { qos: 1 });
    const saved = code && mem.get("host-" + code, null);
    if (saved && saved.players) { S = saved; rearm(); loadPool(); } else S = newState([newPlayer(me.id, me.name)]);
    commit();
  });
}
function joinRoom(code) {
  mode = "guest"; room = code;
  mem.set("online", { room, host: false, at: Date.now() });
  render(`<div class="loading">عم بدخل الغرفة...</div>`);
  connect(() => {
    client.subscribe(topic("s"), { qos: 1 });
    send({ t: "join", name: me.name });
    setTimeout(() => {
      if (S || mode !== "guest") return;
      render(`<h1>ما في رد من الغرفة ${esc(room)}</h1><p class="sub">تأكد من الكود، وإن تلفون صاحب الغرفة مفتوح على اللعبة.</p>
        <button class="btn" data-a="rejoin">جرّب كمان مرة</button><button class="btn alt" data-a="leave">رجوع</button>`);
    }, 6000);
  });
}

function onState(st) {
  if (!st || !st.players) return;
  if (mode === "guest") {
    if (st.room !== room) return;
    if (S && st.v <= S.v && st.host === S.host) return;
    if (!st.players.some((p) => p.id === me.id) && st.phase !== "lobby") {
      S = st;
      return render(`<h1>السهرة بلّشت</h1><p class="sub">ما لحقت تدخل. استنى الجولة الجاية.</p><button class="btn alt" data-a="leave">رجوع</button>`);
    }
    offset = (st.now || Date.now()) - Date.now();
  }
  S = st;
  const f = S.fx;
  if (f && f.id !== lastFx) { lastFx = f.id; effects(f.k); }
  draw();
}

// ======================= مؤثرات =======================
function haptic(kind) {
  try { window.webkit?.messageHandlers?.haptic?.postMessage(kind); } catch {}
  try { navigator.vibrate && navigator.vibrate(kind === "error" ? [80, 60, 160] : [35]); } catch {}
}
function notes(list, type = "triangle") { list.forEach(([f, at]) => setTimeout(() => beep(f, 220, type, 0.09), at)); }
function effects(k) {
  if (k === "stage") notes([[523, 0], [659, 130], [784, 260], [1046, 420]]);
  else if (k === "show") notes([[784, 0], [988, 120]], "sine");
  else if (k === "ok") { beep(988, 120); haptic(); }
  else if (k === "go") notes([[440, 0], [660, 150]]);
  else if (k === "pass") { beep(520, 70, "square", 0.05); if (S.cur && S.cur.holder === me.id) haptic("error"); }
  else if (k === "join") beep(700, 90);
  else if (k === "boom") { notes([[110, 0], [82, 90], [55, 200]], "sawtooth"); haptic("error"); }
  else if (k === "final") { notes([[523, 0], [659, 150], [784, 300], [1046, 450], [1318, 650]]); confetti(); }
}
function confetti() {
  const box = document.createElement("div");
  box.className = "confetti";
  const colors = ["#FFC53D", "#8B74FF", "#E5539B", "#12B5A6", "#F0683A", "#FFFFFF"];
  box.innerHTML = Array.from({ length: 70 }, () => `<i style="left:${Math.random() * 100}%;background:${pick(colors)};animation-duration:${2.2 + Math.random() * 2.5}s;animation-delay:${Math.random() * 1.2}s"></i>`).join("");
  document.body.appendChild(box);
  setTimeout(() => box.remove(), 6500);
}
// الساعة والتكتكة
setInterval(() => {
  const c = S && S.cur, el = $("clock");
  if (!c || S.phase !== "live" || c.st !== "run") return;
  if (c.kind === "act" && el) {
    const left = Math.max(0, Math.ceil((c.until - now()) / 1000));
    el.textContent = left; el.classList.toggle("low", left <= 10);
  }
  if (c.kind === "bomb") beep(1200, 30, "square", 0.03);
}, 500);

// ======================= الواجهة =======================
// مين اللي قدام الشاشة؟ بالغرفة: أنا. على تلفون واحد: اللي عليه الدور.
function viewer() {
  if (mode !== "local") return me.id;
  const c = S.cur;
  if (S.phase === "ask") { const pend = c.need.find((id) => !(id in c.ans)); return L.ok === pend ? pend : null; }
  if (S.phase === "live") return c.kind === "act" ? c.actor : c.holder;
  return null;
}
const isBoss = () => mode === "local" || me.id === S.host;
const pchip = (id, cls = "") => `<span class="c ${cls}">${pav(id)}${nm(id)}</span>`;
const sorted = () => [...S.players].sort((a, b) => b.score - a.score);

function hud() {
  const s = stage(), info = STAGES[s.id];
  const round = ["ask", "show", "live"].includes(S.phase) && s.rounds > 1 ? ` · جولة ${S.r + 1}/${s.rounds}` : "";
  return `<div class="hud"><span class="hs">${info.icon} ${info.name}</span><span>مرحلة ${S.si + 1}/${S.plan.length}${round}</span>${room ? `<span class="code">#${esc(room)}</span>` : ""}</div>${scorebar()}`;
}
function scorebar() {
  const top = Math.max(...S.players.map((p) => p.score));
  return `<div class="sb">${sorted().map((p) => `<span class="s ${p.score === top && top > 0 ? "lead" : ""} ${mode !== "local" && p.id === me.id ? "meS" : ""}">${pav(p.id)}${esc(p.name)}${S.jok[p.id] ? " 🃏" : ""}<b>${p.score}</b></span>`).join("")}</div>`;
}
function qCard(c, extra = "") {
  return `<section class="q">${c.cat ? `<span class="cat">${esc(c.cat)}</span>` : ""}<b>${esc(c.q)}</b>${c.img ? `<img src="${esc(c.img)}" alt="" referrerpolicy="no-referrer">` : ""}${extra}</section>`;
}
const bossBtn = (label, a = "go", cls = "gold") => (isBoss() ? `<button class="btn ${cls}" data-a="${a}">${label}</button>` : `<p class="wait">استنى صاحب الغرفة يكمّل <span class="dots"><i></i><i></i><i></i></span></p>`);
function waveBar(c, inner) {
  return `<div class="wave"><div class="ends"><span>⬅️ ${esc(c.A)}</span><span style="text-align:right">${esc(c.B)} ➡️</span></div><div class="bar">${inner}</div></div>`;
}
function deltasHTML() {
  const d = Object.entries(S.cur.delta || {}).filter(([, v]) => v).sort((a, b) => b[1] - a[1]);
  if (!d.length) return `<p class="wait">ما حدا أخذ نقاط بهالجولة 😅</p>`;
  return `<div class="deltas">${d.map(([pid, v]) => `<span class="${v < 0 ? "neg" : ""}">${nm(pid)} ${v > 0 ? "+" : ""}${v}</span>`).join("")}</div>`;
}

// ----- البداية -----
function intro() {
  document.documentElement.style.setProperty("--sc", "#8B74FF");
  const online = mem.get("online", null), local = mem.get("local", null);
  const fresh = online && Date.now() - online.at < 3 * 3600e3;
  render(`
    <div class="hero"><span class="crown">👑</span><h1>ملك السهرة</h1><p class="sub">8 مراحل، وكل مرحلة لعبة شكل. مين بيطلع ملك السهرة؟</p></div>
    <div class="strip">${Object.values(STAGES).map((s) => `<span>${s.icon} ${s.name}</span>`).join("")}</div>
    <input class="input" id="name" type="text" maxlength="14" placeholder="اسمك" value="${esc(me.name)}" autocomplete="off">
    <button class="btn gold" data-a="create">افتح غرفة (كل واحد من تلفونه)</button>
    <div class="row" style="flex-wrap:nowrap"><input class="input codein" id="code" type="text" inputmode="numeric" maxlength="5" placeholder="كود الغرفة" value="${esc(qs.get("room") || "")}" style="flex:1.4">
      <button class="btn" data-a="join" style="flex:1">ادخل</button></div>
    <p class="err" id="err" hidden></p>
    ${fresh ? `<button class="btn alt" data-a="back2room">ارجع للغرفة ${esc(online.room)}</button>` : ""}
    ${local && local.players && !["lobby", "final"].includes(local.phase) ? `<button class="btn alt" data-a="resume">كمّلوا السهرة اللي على هالتلفون</button>` : ""}
    <button class="btn alt" data-a="one">على تلفون واحد (بنمرّره)</button>
    ${howto("sahra", `<ul class="rules">
      <li>من <b>${MIN}</b> لـ<b>${MAX}</b> لاعبين. كل واحد لحاله، والنقاط بتتجمع من مرحلة لمرحلة.</li>
      ${Object.values(STAGES).map((s) => `<li><b>${s.icon} ${s.name}</b>: ${s.how}</li>`).join("")}
      <li><b>🃏 الجوكر</b>: مرة وحدة بالسهرة، بتضاعف ربحك بمرحلة بتختارها (قبل ما تبلّش).</li>
      <li>بالآخر: تتويج الملك، ألقاب مضحكة، وحكم على آخر واحد.</li>
    </ul>`)}`);
}
function getName() {
  const n = $("name").value.trim();
  if (!n) { $("err").hidden = false; $("err").textContent = "اكتب اسمك أول."; $("name").focus(); return null; }
  me.name = n; mem.set("name", n); return n;
}
function localSetup() {
  const names = mem.get("names", ["", "", "", ""]), len = mem.get("len", "full");
  render(`<h1>على تلفون واحد</h1><p class="sub">التلفون بيلف على الكل: كل واحد بيجاوب بالسر وبيمرّره.</p>
    <div class="stack" id="nl">${names.map((v, i) => `<input class="input" type="text" maxlength="14" placeholder="لاعب ${i + 1}" value="${esc(v)}">`).join("")}</div>
    <div class="row" style="flex-wrap:nowrap"><button class="btn alt" data-a="addp">+ لاعب</button><button class="btn alt" data-a="remp">− لاعب</button></div>
    <div class="label">طول السهرة</div>
    <div class="seg"><button data-a="llen" data-v="quick" aria-pressed="${len === "quick"}">سريعة · 5 مراحل</button><button data-a="llen" data-v="full" aria-pressed="${len === "full"}">كاملة · 8 مراحل</button></div>
    <p class="err" id="err" hidden></p>
    <button class="btn gold" data-a="lgo">يلا نبدأ</button><button class="linkish" data-a="home">رجوع</button>`);
}
const localNames = () => Array.from(document.querySelectorAll("#nl input")).map((x) => x.value.trim());

// ----- الشاشات حسب الحالة: كل شاشة بترجع {key, html, dyn} -----
function vLobby() {
  const boss = isBoss(), n = S.players.length;
  const dyn = `
    <div class="plist">${S.players.map((p) => `<div class="pl">${pav(p.id)}<span class="n">${esc(p.name)}${p.id === S.host ? " 👑" : ""}</span>${boss && p.id !== S.host ? `<button data-a="kick" data-v="${p.id}" aria-label="شيل ${esc(p.name)}">✕</button>` : ""}</div>`).join("")}</div>
    ${boss ? `<div class="label">طول السهرة</div>
      <div class="seg"><button data-a="len" data-v="quick" aria-pressed="${S.cfg.len === "quick"}">سريعة · 5 مراحل</button><button data-a="len" data-v="full" aria-pressed="${S.cfg.len === "full"}">كاملة · 8 مراحل</button></div>
      <button class="btn gold" data-a="start" ${n < MIN ? "disabled" : ""}>${n < MIN ? `لازم ${MIN} لاعبين عالأقل (${n}/${MIN})` : `يلا نبدأ · ${n} لاعبين`}</button>`
    : `<p class="wait">استنى صاحب الغرفة يبلّش <span class="dots"><i></i><i></i><i></i></span></p>`}`;
  return { key: "lobby", dyn, html: `
    <section class="card roomcode"><span class="sub">كود الغرفة</span><b>${esc(room)}</b><button class="btn sm alt" data-a="share">شارك الرابط</button></section>
    <!--dyn--><button class="linkish" data-a="leave">اطلع من الغرفة</button>` };
}

function vStage() {
  const s = stage(), info = STAGES[s.id], canJoker = s.id !== "bet";
  let jokers = "";
  if (canJoker && mode === "local") {
    jokers = `<p class="note">🃏 مين بده يستعمل الجوكر (ضعف الربح) بهالمرحلة؟</p><div class="jokers">${S.players.map((p) => `<button class="jk" data-a="joker" data-v="${p.id}" aria-pressed="${!!S.jok[p.id]}" ${p.joker ? "" : "disabled"}>🃏 ${esc(p.name)}</button>`).join("")}</div>`;
  } else if (canJoker) {
    const mine = P(me.id), active = Object.keys(S.jok);
    jokers = `${mine && mine.joker ? `<div class="jokers"><button class="jk" data-a="joker" aria-pressed="${!!S.jok[me.id]}">${S.jok[me.id] ? "🃏 الجوكر شغّال: ربحك ×2" : "🃏 استعمل الجوكر (ربحك ×2 بهالمرحلة)"}</button></div>` : `<p class="note">الجوكر تبعك راح 🃏</p>`}
      ${active.length ? `<p class="note">حاطّين جوكر: ${active.map(nm).join("، ")}</p>` : ""}`;
  }
  return { key: `stage|${S.si}`, dyn: jokers + bossBtn("يلا 🚀"), html: `${hud()}
    <section class="stagecard"><span class="ico">${info.icon}</span><span class="k">المرحلة ${S.si + 1} من ${S.plan.length}</span><h1>${info.name}</h1><span class="from">${info.from}</span><p>${info.how}</p></section><!--dyn-->` };
}

function progHTML() {
  const c = S.cur, done = c.need.filter((id) => id in c.ans).length;
  return `<div class="prog"><div class="chips">${c.need.map((id) => pchip(id, id in c.ans ? "done" : "")).join("")}</div>
    ${isBoss() && done < c.need.length ? `<button class="linkish" data-a="force">كمّل بدون الباقي (${done}/${c.need.length})</button>` : ""}</div>`;
}

function vAsk(v) {
  const c = S.cur;
  if (mode === "local" && !v) {
    const pend = c.need.find((id) => !(id in c.ans));
    const what = { wavec: "صاحب التلميح", waveg: "دورك تحزر", bet: "حط رهانك بالسر" }[c.kind] || "جاوب بالسر";
    return { key: `hand|${S.v}`, dyn: "", html: `${hud()}<div class="handoff pop"><span class="sub">أعطوا التلفون لـ</span><div class="big">${nm(pend)}</div><p>${what}، والباقي لا يطّلعوا 👀</p><button class="btn gold" data-a="hand" data-v="${pend}">أنا ${nm(pend)}، جاهز</button></div>` };
  }
  const mine = c.need.includes(v) && !(v in c.ans);
  const key = `ask|${S.si}|${S.r}|${c.kind}|${v}|${mine}|${(c.rej && c.rej[v]) || 0}`;
  const textRow = (ph, max, btn = "ابعث") => `<div class="textrow"><input class="input" id="txt" type="text" maxlength="${max}" placeholder="${ph}" autocomplete="off"><button class="btn sm" data-a="text">${btn}</button></div>`;
  let body;
  if (!mine) {
    const lead = c.kind === "wavec" ? `📡 ${nm(c.psy)} بيجهّز التلميح` : c.need.includes(v) ? "جوابك وصل ✅" : c.kind === "waveg" ? `تلميحك: «${esc(c.clue)}». خليهم يحزروا` : "استنى الباقي";
    body = `${c.q ? qCard(c) : c.kind === "bet" ? qCard({ cat: "قسم السؤال الأخير", q: c.cat }) : ""}<p class="wait">${lead} <span class="dots"><i></i><i></i><i></i></span></p>`;
  } else if (c.kind === "mcq" || c.kind === "betq") {
    body = `${qCard(c, c.kind === "betq" ? `<span class="sub">رهانك: ${c.bets[v] || 0}</span>` : "")}<div class="opts two">${c.opts.map((o, i) => `<button class="opt o${i}" data-a="ans" data-v="${i}">${esc(o)}</button>`).join("")}</div>`;
  } else if (c.kind === "fibw") {
    body = `${qCard(c)}${c.rej[v] ? `<p class="err">قريب كثير من الجواب الصح 😳 اكتب كذبة ثانية</p>` : `<p class="note">اكتب جواب <b>غلط</b> بس مقنع، عشان الباقي يصدّقوه</p>`}${textRow("كذبتك المقنعة", 40)}`;
  } else if (c.kind === "fibp") {
    body = `${qCard(c)}<p class="note">وحدة بس هي الحقيقة. وينها؟</p><div class="opts">${c.opts.map((o, i) => `<button class="opt plain" data-a="ans" data-v="${i}" ${o.by.includes(v) ? "disabled" : ""}>${esc(o.t)}${o.by.includes(v) ? `<span class="tag">كذبتك</span>` : ""}</button>`).join("")}</div>`;
  } else if (c.kind === "most") {
    body = `${qCard(c)}<div class="who">${S.players.map((p) => `<button data-a="ans" data-v="${p.id}">${pav(p.id)}<span class="n">${esc(p.name)}${p.id === v ? " (أنا)" : ""}</span></button>`).join("")}</div>`;
  } else if (c.kind === "quipw") {
    body = `${qCard(c)}<p class="note">اكتب أضحك جواب عندك. الباقي بيصوّتوا</p>${textRow("جوابك", 60)}`;
  } else if (c.kind === "quipv") {
    body = `${qCard(c)}<p class="note">أي جواب أضحك؟</p><div class="opts">${c.opts.map((o, i) => `<button class="opt plain" data-a="ans" data-v="${i}" ${o.by.includes(v) ? "disabled" : ""}>${esc(o.t)}${o.by.includes(v) ? `<span class="tag">جوابك</span>` : ""}</button>`).join("")}</div>`;
  } else if (c.kind === "wavec") {
    body = `<section class="q"><span class="cat">إنت صاحب التلميح، وإنت بس شايف الهدف</span>${waveBar(c, `<span class="zone" style="left:${c.target}%"></span>`)}<span class="sub">اكتب إشي مكانه بين الطرفين عند الهدف 🎯 بالضبط</span></section>${textRow("تلميحك (كلمة أو كلمتين)", 24)}`;
  } else if (c.kind === "waveg") {
    body = `<section class="q"><span class="cat">تلميح ${nm(c.psy)}</span><span class="clue">«${esc(c.clue)}»</span>
      <div class="wave" style="width:100%;padding-top:6px"><div class="ends"><span>⬅️ ${esc(c.A)}</span><span style="text-align:right">${esc(c.B)} ➡️</span></div><div class="bar"></div><input type="range" id="rng" min="0" max="100" value="50" aria-label="مكان الهدف"></div></section>
      <button class="btn" data-a="num">ثبّت مكاني</button>`;
  } else if (c.kind === "bet") {
    const max = maxBet(v);
    body = `${qCard({ cat: "قسم السؤال الأخير", q: c.cat })}<section class="q"><span class="sub">نقاطك ${P(v).score} · أقصى رهان ${max}</span><span class="clue" id="betv">${Math.round(max / 100) * 50}</span>
      <input type="range" id="rng" min="0" max="${max}" step="50" value="${Math.round(max / 100) * 50}" style="width:100%;accent-color:var(--gold)" aria-label="الرهان">
      <div class="row" style="justify-content:center">${[["0", 0], ["ربع", .25], ["نص", .5], ["كله 🔥", 1]].map(([t, f]) => `<button class="btn sm alt" data-a="betq" data-v="${Math.round(max * f / 50) * 50}">${t}</button>`).join("")}</div></section>
      <button class="btn gold" data-a="num">ثبّت الرهان</button>`;
  }
  return { key, html: `${hud()}${body}<!--dyn-->`, dyn: mode === "local" ? "" : progHTML() };
}

function vShow() {
  const c = S.cur, s = stage();
  const voters = (list) => (list.length ? `<span class="voters">${list.map((id) => pav(id)).join("")}</span>` : "");
  const picked = (i) => Object.keys(c.ans).filter((id) => c.ans[id] === i);
  let body = "";
  if (c.kind === "mcq" || c.kind === "betq") {
    body = `${qCard(c)}<div class="opts two">${c.opts.map((o, i) => `<div class="opt ${i === c.c ? "right" : "wrong"}">${esc(o)}${voters(picked(i))}</div>`).join("")}</div>`;
    if (c.kind === "betq") body += `<p class="note">الرهانات: ${ids().map((id) => `${nm(id)} ${c.bets[id] || 0}`).join(" · ")}</p>`;
  } else if (c.kind === "fibp") {
    body = `${qCard(c)}<div class="opts">${c.opts.map((o, i) => `<div class="opt ${o.truth ? "right" : "plain"}">${esc(o.t)}<span class="tag">${o.truth ? "✅ الحقيقة" : `🤥 كذبة ${o.by.map(nm).join(" و")}`}</span>${voters(picked(i))}</div>`).join("")}</div>`;
  } else if (c.kind === "most") {
    const rows = S.players.map((p) => ({ p, n: c.count[p.id] || 0, who: Object.keys(c.ans).filter((id) => c.ans[id] === p.id) })).filter((x) => x.n).sort((a, b) => b.n - a.n);
    const total = Object.keys(c.ans).length || 1;
    body = `${qCard(c)}<div class="rows">${rows.map((x) => `<div class="rowi ${c.top.includes(x.p.id) ? "first" : ""}">${pav(x.p.id)}<span class="n">${esc(x.p.name)}<small>صوّتوله: ${x.who.map(nm).join("، ")}</small><div class="meter"><i style="width:${(x.n / total) * 100}%"></i></div></span><b>${x.n}</b></div>`).join("")}</div>
      ${c.top.length ? "" : `<p class="note">كل واحد صوّت لحدا شكل، ما في أغلبية!</p>`}`;
  } else if (c.kind === "quipv" || c.kind === "quipw") {
    body = `${qCard(c)}<div class="opts">${c.opts.map((o, i) => `<div class="opt ${i === c.best ? "right" : "plain"}">${i === c.best ? "😂 " : ""}${esc(o.t)}<span class="tag">${nm(o.by[0])} · ${c.votes[i]} صوت</span>${c.kind === "quipv" ? voters(picked(i)) : ""}</div>`).join("")}</div>`;
  } else if (c.kind === "waveg") {
    const pins = Object.entries(c.ans).map(([id, g]) => `<span class="pin" style="left:${g}%">${pav(id)}</span>`).join("");
    body = `<section class="q"><span class="cat">تلميح ${nm(c.psy)}</span><span class="clue">«${esc(c.clue)}»</span>${waveBar(c, `<span class="zone" style="left:${c.target}%"></span>${pins}`)}</section>`;
  } else if (c.kind === "act") {
    const ok = c.got.filter((g) => g.by).length;
    body = c.st === "skipped" ? `<p class="wait">انتخطّى الدور</p>` : `<section class="q"><span class="cat">🎭 ${nm(c.actor)}</span><b>${ok ? `فهّمهم ${ok} ${ok > 2 && ok < 11 ? "كلمات" : "كلمة"}!` : "ولا كلمة انحزرت 🙈"}</b></section>
      <div class="rows">${c.got.map((g) => `<div class="rowi"><span class="rk">${g.by ? "✅" : "⏭️"}</span><span class="n">${esc(g.w)}${g.by ? `<small>حزرها ${nm(g.by)}</small>` : ""}</span></div>`).join("")}</div>`;
  } else if (c.kind === "bomb") {
    body = c.st === "skipped" ? `<p class="wait">انتخطّى الدور</p>` : `<div class="boom">💥</div><section class="q"><b>انفجرت عند ${nm(c.holder)}!</b><span class="sub">«${esc(c.q)}» · انمرّرت ${c.passes} مرة</span></section>`;
  }
  const last = S.r + 1 >= s.rounds;
  return { key: `show|${S.v}`, dyn: "", html: `${hud()}${body}${deltasHTML()}${bossBtn(last ? "نتيجة المرحلة 📊" : "الجولة الجاية")}` };
}

function vLive(v) {
  const c = S.cur, boss = isBoss();
  const skip = boss && v !== (c.actor || c.holder) ? `<button class="linkish" data-a="skipturn">تخطّي هالدور</button>` : "";
  let body;
  if (c.kind === "act") {
    const mine = v === c.actor, ok = c.got.filter((g) => g.by).length;
    if (c.st === "ready") body = mine
      ? `<div class="handoff pop"><span class="sub">${mode === "local" ? "أعطوا التلفون لـ" : "دورك يا"}</span><div class="big">${nm(c.actor)}</div><p>بتطلعلك كلمات. مثّلها أو اشرحها بدون ما تقولها أو تقول جزء منها. عندك ${c.dur} ثانية، وكل ما حدا يحزر اضغط على اسمه.</p><button class="btn gold" data-a="cgo">جاهز، ابدأ ⏱️</button></div>`
      : `<p class="wait">🎭 ${nm(c.actor)} بيتجهّز <span class="dots"><i></i><i></i><i></i></span></p>`;
    else body = mine
      ? `<div class="clock" id="clock">${c.dur}</div><div class="bigword"><small>مثّلها أو اشرحها بدون ما تقولها</small><b>${esc(c.words[c.wi])}</b></div>
        <p class="note">مين حزرها؟ (انحزر ${ok})</p><div class="who">${S.players.filter((p) => p.id !== c.actor).map((p) => `<button data-a="cok" data-v="${p.id}">${pav(p.id)}<span class="n">${esc(p.name)}</span></button>`).join("")}</div>
        <button class="btn alt" data-a="cskip" ${c.skips ? "" : "disabled"}>تخطّي الكلمة (باقي ${c.skips})</button>`
      : `<div class="clock" id="clock">${c.dur}</div><div class="bigword"><small>${nm(c.actor)} بيمثّل أو بيشرح</small><b>احزروا بصوت عالي!</b></div><p class="note">انحزر لهلأ: ${ok}</p>`;
  } else {
    const mine = v === c.holder, next = after(c.holder);
    if (c.st === "ready") body = mine
      ? `<div class="handoff pop"><span class="sub">${mode === "local" ? "القنبلة بتبلّش عند" : "القنبلة بتبلّش عندك يا"}</span><div class="big">${nm(c.holder)}</div><p>سمّي: <b>${esc(c.q)}</b><br>قول جواب بصوت عالي ومرّرها. ممنوع تكرار جواب انقال. الفتيل عشوائي!</p><button class="btn bad" data-a="bgo">شعّل الفتيل 🔥</button></div>`
      : `<p class="wait">💣 القنبلة بتبلّش عند ${nm(c.holder)} <span class="dots"><i></i><i></i><i></i></span></p>`;
    else body = mine
      ? `<div class="bomb">💣</div><section class="q"><span class="cat">${mode === "local" ? `القنبلة مع ${nm(c.holder)}` : "القنبلة معك!"}</span><b>سمّي: ${esc(c.q)}</b></section>
        <button class="btn bad" data-a="bpass">قلت! ${mode === "local" ? "أعطي التلفون" : "مرّرها"} لـ${nm(next)} 💨</button>`
      : `<div class="bomb calm">💣</div><section class="q"><span class="cat">القنبلة مع ${nm(c.holder)}</span><b>سمّي: ${esc(c.q)}</b><span class="sub">بعده: ${nm(next)}${next === v ? " (إنت! استعد)" : ""}</span></section>`;
  }
  return { key: `live|${S.v}`, dyn: "", html: `${hud()}${body}${skip}` };
}

function vBoard() {
  const info = STAGES[stage().id], lastStage = S.si + 1 >= S.plan.length;
  return { key: `board|${S.v}`, dyn: "", html: `${hud()}
    <h2 class="center">📊 بعد ${info.icon} ${info.name}</h2>
    <div class="rows">${sorted().map((p, i) => { const g = (S.gain[p.id] || 0), b = S.bonus[p.id] || 0; return `<div class="rowi ${i === 0 ? "first" : ""}" style="animation-delay:${i * 70}ms"><span class="rk">${medals[i] || i + 1}</span>${pav(p.id)}<span class="n">${esc(p.name)}${b ? `<small>🃏 الجوكر ضاعفها: +${b} زيادة</small>` : ""}</span><span class="g ${g < 0 ? "neg" : ""}">${g + b ? (g + b > 0 ? "+" : "") + (g + b) : ""}</span><b>${p.score}</b></div>`; }).join("")}</div>
    ${bossBtn(lastStage ? "التتويج 👑" : "المرحلة الجاية ⏭️")}` };
}

function vFinal() {
  const list = sorted(), top = list[0].score, kings = list.filter((p) => p.score === top), loser = list[list.length - 1];
  return { key: `final|${S.v}`, dyn: "", html: `
    <section class="king"><span class="crown">👑</span><span class="sub">${kings.length > 1 ? "ملوك السهرة (تعادل)" : "ملك السهرة"}</span><b>${kings.map((p) => esc(p.name)).join(" و ")}</b><span class="sub">${top} نقطة</span></section>
    <div class="rows">${list.map((p, i) => `<div class="rowi ${i === 0 ? "first" : ""}" style="animation-delay:${i * 80}ms"><span class="rk">${medals[i] || i + 1}</span>${pav(p.id)}<span class="n">${esc(p.name)}</span><b>${p.score}</b></div>`).join("")}</div>
    ${S.awards.length ? `<h2 class="center">🏅 ألقاب السهرة</h2><div class="rows">${S.awards.map((a) => `<div class="award"><span class="e">${a.e}</span><span><b>${a.title}: ${nm(a.pid)}</b><small>${a.why}</small></span></div>`).join("")}</div>` : ""}
    ${kings.length < list.length ? `<section class="dare"><span class="sub">⚖️ الحكم على ${esc(loser.name)}</span><b>${esc(S.dare)}</b>${isBoss() ? `<button class="linkish" data-a="dare">حكم ثاني 🎲</button>` : ""}</section>` : ""}
    ${isBoss() ? `<button class="btn gold" data-a="again">سهرة جديدة 🔁</button>` : ""}<button class="btn alt" data-a="leave">خروج</button>` };
}

const VIEWS = { lobby: vLobby, stage: vStage, ask: vAsk, show: vShow, live: vLive, board: vBoard, final: vFinal };
function draw() {
  if (!S) return;
  if (S.phase === "loading") { lastKey = ""; return render(`<div class="loading">عم بجهّز السهرة...</div>`); }
  document.documentElement.style.setProperty("--sc", S.plan.length && S.phase !== "lobby" ? STAGES[stage().id].color : "#8B74FF");
  const view = VIEWS[S.phase](viewer());
  if (view.key === lastKey && $("dyn")) { $("dyn").innerHTML = view.dyn; return; }
  lastKey = view.key;
  const dyn = `<div id="dyn" class="stack">${view.dyn}</div>`;
  render(view.html.includes("<!--dyn-->") ? view.html.replace("<!--dyn-->", dyn) : view.html + dyn);
  window.scrollTo(0, 0);
  const t = $("txt"); if (t) t.focus();
  const r = $("rng"), bv = $("betv"); if (r && bv) r.oninput = () => { bv.textContent = r.value; };
}

// ======================= الضغطات =======================
const UI = {
  create: () => { if (getName()) hostRoom(); },
  join: () => { if (!getName()) return; const code = $("code").value.trim(); if (!/^\d{5}$/.test(code)) { $("err").hidden = false; $("err").textContent = "الكود 5 أرقام."; return; } joinRoom(code); },
  back2room: () => { const o = mem.get("online", null); if (!o) return intro(); if (!me.name) me.name = "لاعب"; o.host ? hostRoom(o.room) : joinRoom(o.room); },
  rejoin: () => send({ t: "join", name: me.name }),
  resume: () => { mode = "local"; room = null; S = mem.get("local", null); L.ok = null; loadPool(); rearm(); lastKey = ""; draw(); },
  one: () => { const n = $("name").value.trim(); if (n) { me.name = n; mem.set("name", n); } localSetup(); },
  home: intro,
  addp: () => { const v = localNames(); if (v.length < MAX) v.push(""); mem.set("names", v); localSetup(); },
  remp: () => { const v = localNames(); if (v.length > MIN) v.pop(); mem.set("names", v); localSetup(); },
  llen: (v) => { mem.set("names", localNames()); mem.set("len", v); localSetup(); },
  lgo: () => {
    const v = localNames().map((x, i) => x || `لاعب ${i + 1}`);
    if (new Set(v).size !== v.length) { $("err").hidden = false; $("err").textContent = "في اسمين متشابهين."; return; }
    mem.set("names", v);
    mode = "local"; room = null; L.ok = null;
    S = newState(v.map((name, i) => newPlayer("l" + i, name)));
    begin();
  },
  leave: () => { const g = window.leaveGuard(); if (!g || confirm(g)) leave(); },
  share: () => {
    const url = `${location.origin}${location.pathname}?room=${room}`, text = `تعال العب معي «ملك السهرة» 👑 كود الغرفة: ${room}`;
    if (navigator.share) navigator.share({ title: "ملك السهرة", text, url }).catch(() => {});
    else if (navigator.clipboard) navigator.clipboard.writeText(`${text}\n${url}`).then(() => window.uiToast && uiToast("انسخ الرابط ✅"));
  },
  len: (v) => send({ t: "cfg", len: v }),
  kick: (v) => send({ t: "kick", who: v }),
  start: () => send({ t: "start" }),
  joker: (v) => send({ t: "joker", who: v }),
  go: () => send({ t: "go" }),
  force: () => send({ t: "force" }),
  hand: (v) => { L.ok = v; draw(); },
  ans: (v) => send({ t: "ans", as: viewer(), val: v }),
  text: () => { const t = $("txt"); if (t && t.value.trim()) send({ t: "ans", as: viewer(), val: t.value }); },
  num: () => { const r = $("rng"); if (r) send({ t: "ans", as: viewer(), val: +r.value }); },
  betq: (v) => { const r = $("rng"); if (r) { r.value = v; $("betv").textContent = r.value; } },
  cgo: () => send({ t: "cgo", as: viewer() }),
  cok: (v) => send({ t: "cok", as: viewer(), g: v }),
  cskip: () => send({ t: "cskip", as: viewer() }),
  bgo: () => send({ t: "bgo", as: viewer() }),
  bpass: () => send({ t: "bpass", as: viewer() }),
  skipturn: () => send({ t: "skipturn" }),
  dare: () => send({ t: "dare" }),
  again: () => send({ t: "again" }),
};
$("app").addEventListener("click", (e) => {
  const b = e.target.closest("[data-a]");
  if (!b || b.disabled) return;
  const fn = UI[b.dataset.a];
  if (fn) fn(b.dataset.v, b);
});
$("app").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  if (e.target.id === "txt") UI.text();
  else if (e.target.id === "code") UI.join();
});

intro();
