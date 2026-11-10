// «ليلة الحسم»: الواجهة، تلفون واحد، والغرفة الأونلاين. القواعد كلها بـhasm-core.js.
// صاحب الغرفة هو المرجع: بينشر الحالة العامة S، والأسرار H (عروض واختيارات) بتضل عنده لحد الكشف.
"use strict";
const C = HASM, K = HasmCore, Snd = HasmSound;
const ROOT = "abuodeh-hasm-v1";
const BROKERS = ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081/mqtt"];
const qs = new URLSearchParams(location.search);
const FAST = qs.has("fast");   // للفحص الآلي بس: بيقصّر العروض
const mem = { get: (k, d) => store.get("hasm-" + k, d), set: (k, v) => store.set("hasm-" + k, v) };

let mode = null;               // "host" | "guest" | "local"
let S = null, H = null;        // الحالة العامة والأسرار
let client = null, room = null, offset = 0, timer = null, lastKey = "", runId = 0, lastV = -1;
let CAREER;                    // undefined = لسا ما تحمّل، null = فشل
let D = {};                    // مسودة مدخل اللاعب الحالي (قبل ما يثبّت)
let skipFn = null, wasIn = false;
const shown = {};              // أي عرض خلص (عشان يبين زر «كمّل»)
const L = { pid: null };       // تلفون واحد: مين ماسك التلفون هسا
const me = { id: mem.get("pid", null), name: mem.get("name", "") };
if (!me.id) { me.id = "u" + Math.random().toString(36).slice(2, 9); mem.set("pid", me.id); }

const now = () => Date.now() + offset;
const topic = (k) => `${ROOT}/${room}/${k}`;
const cl = (id) => K.club(S, id);
const isBoss = () => mode === "local" || (S && me.id === S.host);
const T = (ms) => (FAST ? Math.min(ms * 0.04, 40) : ms);
const wait = (ms) => new Promise((r) => setTimeout(r, T(ms)));
const STOP = { stop: true };
const step = async (id, ms) => { await wait(ms); if (id !== runId) throw STOP; };
const crest = (c, cls = "") => `<span class="crest ${cls}" style="--ch:${c.hue}">${c.crest}</span>`;
const say1 = (k, a, d) => pick(C.SAY[k]).replace("{a}", a ? a.name : "").replace("{d}", d ? d.name : "");
const SEG_NAME = ["الشوط الأول", "الشوط الثاني", "الوقت القاتل"];
const phaseKey = () => (S.clubs ? `${S.phase}:${S.md}:${S.seg}` : "lobby");
const isInput = () => S.phase === "prep" || S.phase === "seg";

function viewer() {
  if (!S || !S.clubs) return null;
  if (mode !== "local") return cl(me.id) ? me.id : null;
  const hs = K.humans(S);
  return hs.length === 1 ? hs[0].id : L.pid;
}
function loadCareer() {
  const t = new Promise((r) => setTimeout(() => r(null), 5000));
  const f = fetch("career.json").then((r) => (r.ok ? r.json() : null)).then((j) => K.prepCareer(j)).catch(() => null);
  return Promise.race([f, t]).then((c) => { CAREER = c || null; });
}

// ======================= المحرك (عند صاحب الغرفة أو التلفون الواحد) =======================
async function startSeason() {
  const keep = { room: S.room, host: S.host, players: S.players.slice(0, C.MAX_P), v: S.v || 0 };
  render(`<div class="loading">عم بجهّز الملعب...</div>`); lastKey = "";
  if (CAREER === undefined) await loadCareer();
  const g = K.newGame(keep.players, S.cfg, (Math.random() * 2147483647) | 0);
  S = Object.assign(g.S, keep); H = g.H; L.pid = null;
  commit();
}
function act(a) {
  if (!S || !a) return;
  const boss = mode === "local" || a.sys || a.pid === S.host;
  if (a.t === "join") {
    if (mode !== "host") return;
    const name = String(a.name || "لاعب").slice(0, 14), p = S.players.find((x) => x.id === a.pid);
    if (S.phase === "lobby") { if (p) p.name = name; else if (S.players.length < C.MAX_P) S.players.push({ id: a.pid, name }); }
    return commit();           // بننشر الحالة عشان اللي رجع يلحق
  }
  if (S.phase === "lobby") {
    if (!boss) return;
    if (a.t === "cfg" && (a.len === "quick" || a.len === "full")) { S.cfg.len = a.len; mem.set("len", a.len); return commit(); }
    if (a.t === "kick") { S.players = S.players.filter((p) => p.id !== a.who || p.id === S.host); return commit(); }
    if (a.t === "start") return startSeason();
    return;
  }
  if (a.t === "again") { if (boss && S.phase === "final") startSeason(); return; }
  if (a.t === "go" && !boss) return;
  const before = phaseKey();
  if (!K.apply({ S, H }, a, { career: CAREER })) return;
  if (phaseKey() !== before) S.dl = null;
  rearm(); commit();
}
// وقت المدخلات بالغرفة: لما يخلص، بنسكّر المرحلة واللي ما اختار بينحط له عشوائي
function rearm() {
  clearTimeout(timer);
  if (mode !== "host" || !S || !S.clubs || !isInput()) return;
  if (!S.dl) S.dl = now() + (S.phase === "prep" ? C.TIME.puzzle + C.TIME.bid : C.TIME.seg) * 1000;
  timer = setTimeout(() => act({ t: "go", sys: true }), Math.max(0, S.dl - now()));
}
function commit() {
  S.v = (S.v || 0) + 1; S.now = Date.now();
  if (mode === "host") {
    mem.set("host-" + room, { S, H }); mem.set("online", { room, host: true, at: Date.now() });
    try { client.publish(topic("s"), JSON.stringify(Object.assign({}, S, { rs: 0 })), { qos: 1, retain: true }); } catch {}
  } else if (mode === "local") mem.set("local", { S, H });
  onState(S);
}
function send(a) {
  if (mode === "host" || mode === "local") { if (!a.pid) a.pid = mode === "local" ? viewer() || "local" : me.id; return act(a); }
  a.pid = me.id;
  if (client) client.publish(topic("a"), JSON.stringify(a), { qos: 1 });
}

// ======================= الاتصال =======================
function connect(onReady, k = 0) {
  if (typeof mqtt === "undefined") return fail("ما قدرت أحمّل الاتصال. تأكد من الإنترنت، أو العبوا على تلفون واحد.");
  const url = qs.get("broker") || BROKERS[k % BROKERS.length];
  let ready = false;
  const c = mqtt.connect(url, { clientId: "hs_" + me.id + "_" + Math.random().toString(36).slice(2, 6), reconnectPeriod: 2000, connectTimeout: 8000, clean: true });
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
function fail(msg) { lastKey = ""; render(`<h1>مشكلة بالاتصال</h1><p class="sub">${esc(msg)}</p><button class="btn" data-a="leave">رجوع</button>`); }
function leave() {
  try { if (client && mode === "host" && room) client.publish(topic("s"), "", { qos: 1, retain: true }); } catch {}
  const c = client; setTimeout(() => { try { c && c.end(true); } catch {} }, 400);
  if (mode === "host") mem.set("host-" + room, null);
  if (mode === "local") mem.set("local", null);
  client = null; room = null; S = null; H = null; mode = null; lastKey = ""; wasIn = false; runId++; clearTimeout(timer);
  mem.set("online", null);
  history.replaceState(null, "", location.pathname + (qs.get("broker") ? "?broker=" + encodeURIComponent(qs.get("broker")) : ""));
  home();
}
function hostRoom(code) {
  mode = "host"; room = code || String(Math.floor(10000 + Math.random() * 90000));
  render(`<div class="loading">عم بفتح الغرفة...</div>`);
  connect(() => {
    client.subscribe([topic("s"), topic("a")], { qos: 1 });
    const saved = code && mem.get("host-" + code, null);
    if (saved && saved.S && saved.S.players) { S = saved.S; H = saved.H; if (S.clubs && CAREER === undefined) loadCareer(); rearm(); }
    else S = { v: 0, room, host: me.id, phase: "lobby", players: [{ id: me.id, name: me.name }], cfg: { len: mem.get("len", "quick") } };
    commit();
  });
}
function joinRoom(code) {
  mode = "guest"; room = code; S = null;
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
    offset = (st.now || Date.now()) - Date.now();
    const inList = st.players.some((p) => p.id === me.id);
    if (st.phase === "lobby" && wasIn && !inList) { leave(); if (window.uiToast) uiToast("صاحب الغرفة شالك من الغرفة"); return; }
    if (inList) wasIn = true;
  }
  S = st;
  draw();
}

// ======================= أدوات العرض =======================
function haptic(kind) {
  try { window.webkit?.messageHandlers?.haptic?.postMessage(kind); } catch {}
  try { navigator.vibrate && navigator.vibrate(kind === "error" ? [80, 60, 160] : kind === "goal" ? [60, 40, 60, 40, 200] : [35]); } catch {}
}
const musicPref = () => { const m = mem.get("music", null); return m === null ? mode !== "guest" : m; };   // الضيوف ساكتين إلا إذا شغّلوها
const musBtn = () => `<button class="mus" data-a="music" aria-label="الصوت" aria-pressed="${musicPref()}">${musicPref() ? "🔊" : "🔇"}</button>`;
function confetti(n = 80) {
  const box = document.createElement("div");
  box.className = "confetti";
  const colors = ["#F6C544", "#F0473E", "#35D788", "#58C7FA", "#FFFFFF"];
  box.innerHTML = Array.from({ length: n }, () => `<i style="left:${Math.random() * 100}%;background:${pick(colors)};animation-duration:${2.2 + Math.random() * 2.5}s;animation-delay:${Math.random() * 1.2}s"></i>`).join("");
  $("fxlayer").appendChild(box);
  setTimeout(() => box.remove(), 6500);
}
function overlay(cls, html, ms) {
  const el = document.createElement("div");
  el.className = cls; el.innerHTML = html;
  $("fxlayer").appendChild(el);
  if (ms) setTimeout(() => el.remove(), T(ms));
  return el;
}
const banner = (title, sub = "") => overlay("bannerfx", `${title}${sub ? `<small>${sub}</small>` : ""}`, 1500);
function hud(v) {
  const c = v && cl(v);
  const md = S.md >= 0 && S.md < S.mds ? (S.md === S.mds - 1 ? `<span class="pill hot">🔥 ليلة الحسم</span>` : `<span class="pill">الجولة ${S.md + 1}/${S.mds}</span>`) : "";
  return `<div class="hud">${md}${c ? `<span class="who">${crest(c, "sm")}<span>${esc(c.name)}</span></span><span class="money">${c.budget}M</span>` : ""}<span class="sp"></span>${room ? `<span class="pill">غرفة ${esc(room)}</span>` : ""}${musBtn()}</div>`;
}
const tbar = () => (S.dl && mode !== "local" ? `<div class="tbar"><i style="animation-duration:${Math.max(0, S.dl - now())}ms"></i></div>` : "");
const bossBtn = (label, a = "go", cls = "") => (isBoss() ? `<button class="btn ${cls}" data-a="${a}">${label}</button>` : `<p class="wait center">استنى صاحب الغرفة <span class="dots"><i></i><i></i><i></i></span></p>`);
const showBtn = (label) => (shown[phaseKey()] ? bossBtn(label) : isBoss() ? `<button class="linkish" data-a="skip">تخطي العرض ⏭</button>` : "");
const starMini = (i, off) => { const s = K.starOf(i); return `<span class="star mini ${off ? "off" : ""}">${C.ROLES[s.role].icon} ${esc(s.name)}</span>`; };
const starsOf = (c, off) => (c.stars.length ? `<div class="stars">${c.stars.map((i) => starMini(i, off)).join("")}</div>` : "");
const cardChip = (k, cls = "sm") => `<span class="tcard ${cls}">${C.CARDS[k].icon} ${C.CARDS[k].name}</span>`;
function starCard(i, cls = "") {
  const s = K.starOf(i), r = C.ROLES[s.role];
  return `<div class="star ${cls}"><span class="role">${r.icon}</span><span class="tier">${"★".repeat(s.tier)}</span><div class="flag">${s.flag}</div><b>${esc(s.name)}</b><small>«${esc(s.tag)}» · ${r.name}</small><div class="pw">${r.how}</div></div>`;
}
function fixtureRow(m, v, score) {
  const h = cl(m.h), a = cl(m.a);
  return `<div class="fx ${v && (m.h === v || m.a === v) ? "mine" : ""}"><span class="t">${crest(h, "sm")}<span>${esc(h.name)}</span></span>
    <span class="vs">${score ? `<b>${m.hg}</b><span>-</span><b>${m.ag}</b>` : "ضد"}</span><span class="t a">${crest(a, "sm")}<span>${esc(a.name)}</span></span></div>`;
}
function tableHTML(rows, v, mini) {
  return `<div class="tbl ${mini ? "mini" : ""}" id="tbl"><div class="hd"><span>#</span><span>النادي</span><span>لعب</span><span>+/-</span><span>نقاط</span></div>${rows.map((r, i) => {
    const c = cl(r.id);
    return `<div class="r ${r.id === v ? "me" : ""}" data-id="${r.id}"><span class="p">${i + 1}</span><span class="n">${crest(c, "sm")}<span>${esc(c.name)}</span></span><span class="x">${r.pl}</span><span class="x">${r.gd > 0 ? "+" : ""}${r.gd}</span><span class="pts">${r.pts}</span></div>`;
  }).join("")}</div>`;
}
// FLIP: بنرسم الجدول الجديد وبنحرّك كل صف من مكانه القديم
function flipTable(rows, v, mini) {
  const box = $("tbl"); if (!box) return;
  const old = {}, oldPos = {};
  box.querySelectorAll(".r").forEach((r, i) => { old[r.dataset.id] = r.getBoundingClientRect().top; oldPos[r.dataset.id] = i; });
  box.outerHTML = tableHTML(rows, v, mini);
  $("tbl").querySelectorAll(".r").forEach((r, i) => {
    const dy = (old[r.dataset.id] ?? r.getBoundingClientRect().top) - r.getBoundingClientRect().top;
    if (!dy) return;
    r.classList.add(i < oldPos[r.dataset.id] ? "up" : "down");
    if (r.animate) r.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: T(600), easing: "cubic-bezier(.2,.8,.3,1)" });
  });
}

// ======================= الشاشات =======================
function home() {
  Snd.setMusic(musicPref()); Snd.mood("anthem"); Snd.crowd(0);
  const online = mem.get("online", null), local = mem.get("local", null);
  const fresh = online && Date.now() - online.at < 3 * 3600e3;
  const A = C.ATT, DF = C.DEF;
  lastKey = "";
  render(`
    <div class="hero"><div class="top">${musBtn()}</div><span class="cup">🏆</span><h1>ليلة الحسم</h1><p class="sub">كل واحد رئيس نادي. مزاد نجوم، ألغاز، وحرب أعصاب بالملعب. مين بيرفع الكاس؟</p></div>
    <div class="strip"><span>📰 خبر عاجل</span><span>🧩 لغز</span><span>💰 مزاد سري</span><span>⚽ هجمة ضد دفاع</span><span>📊 جدول حي</span><span>🏆 تتويج</span></div>
    <input class="input" id="name" type="text" maxlength="14" placeholder="اسمك (اسم ناديك)" value="${esc(me.name)}" autocomplete="off">
    <button class="btn" data-a="create">افتح غرفة (كل واحد من تلفونه)</button>
    <div class="row" style="flex-wrap:nowrap"><input class="input codein" id="code" type="text" inputmode="numeric" maxlength="5" placeholder="كود الغرفة" value="${esc(qs.get("room") || "")}" style="flex:1.4">
      <button class="btn green" data-a="join" style="flex:1">ادخل</button></div>
    <p class="err" id="err" hidden></p>
    ${fresh ? `<button class="btn alt" data-a="back2room">ارجع للغرفة ${esc(online.room)}</button>` : ""}
    ${local && local.S && local.S.clubs && local.S.phase !== "final" ? `<button class="btn alt" data-a="resume">كمّلوا الموسم اللي على هالتلفون</button>` : ""}
    <button class="btn alt" data-a="one">📱 على تلفون واحد (بنمرّره)</button>
    <button class="btn alt" data-a="solo">🤖 لحالي ضد الكمبيوتر</button>
    ${howto("hasm", `<ul class="rules">
      <li>من <b>1</b> لـ<b>6</b> لاعبين، وكل واحد رئيس نادي. الكمبيوتر بيعبي باقي الأندية.</li>
      <li><b>📰 خبر عاجل</b> بأول كل جولة بيغيّر قاعدة.</li>
      <li><b>🧩 اللغز</b>: الجواب الصح بيعطيك كرت تكتيكي.</li>
      <li><b>💰 المزاد</b>: كل واحد بيكتب عرضه بالسر، والأعلى بيدفع وبياخد النجم. الكل بيبلّش بـ${C.BUDGET} مليون.</li>
      <li><b>⚽ المباراة</b>: بكل شوط بتختار هجمة ودفاع بالسر. لازم تقرا خصمك:
        <table class="mtx"><tr><th>هجمتك</th><th>هدف أكيد ضد</th><th>بتموت ضد</th><th>50/50 ضد</th></tr>
        ${Object.keys(A).map((a) => { const by = (r) => { const d = Object.keys(DF).find((x) => C.MATRIX[a][x] === r); return `${DF[d].icon} ${DF[d].name}`; };
          return `<tr><td>${A[a].icon} ${A[a].name}</td><td>${by("goal")}</td><td>${by("dead")}</td><td>${by("fifty")}</td></tr>`; }).join("")}</table></li>
      <li><b>النجوم</b>: ${Object.values(C.ROLES).map((r) => `${r.icon} ${r.name} (${r.how})`).join("، ")}.</li>
      <li><b>الكروت</b>: ${Object.values(C.CARDS).map((k) => `${k.icon} ${k.name} (${k.how})`).join("، ")}.</li>
      <li><b>🔥 ليلة الحسم</b>: آخر جولة فيها هجمة ثالثة بالوقت القاتل.</li>
      <li>البطل هو المتصدر بعد آخر جولة. وبالآخر ألقاب، قصة الموسم، وحكم على الأخير.</li>
    </ul>`)}`);
}
function getName() {
  const n = $("name").value.trim();
  if (!n) { $("err").hidden = false; $("err").textContent = "اكتب اسمك أول."; $("name").focus(); return null; }
  me.name = n; mem.set("name", n); return n;
}
const lenSeg = (len, a) => `<div class="label">طول الموسم</div>
  <div class="seg"><button data-a="${a}" data-v="quick" aria-pressed="${len === "quick"}">سريع · 3 جولات</button><button data-a="${a}" data-v="full" aria-pressed="${len === "full"}">كامل · 5 جولات</button></div>`;
function localSetup() {
  const names = mem.get("names", ["", ""]);
  lastKey = "";
  render(`<h1>${names.length === 1 ? "لحالك ضد الكمبيوتر" : "على تلفون واحد"}</h1><p class="sub">${names.length === 1 ? "إنت و3 أندية كمبيوتر. بتقدر تزيد لاعبين إذا إجا حدا." : "التلفون بيلف على الكل: كل واحد بيختار بالسر وبيمرّره. والعرض للكل."}</p>
    <div class="stack" id="nl">${names.map((v, i) => `<input class="input" type="text" maxlength="14" placeholder="لاعب ${i + 1}" value="${esc(v)}">`).join("")}</div>
    <div class="row" style="flex-wrap:nowrap"><button class="btn alt" data-a="addp">+ لاعب</button><button class="btn alt" data-a="remp">− لاعب</button></div>
    ${lenSeg(mem.get("len", "quick"), "llen")}
    <p class="note">الكمبيوتر بيعبي باقي الأندية (الدوري 4 أندية، أو 6 إذا كنتوا 5 أو 6).</p>
    <p class="err" id="err" hidden></p>
    <button class="btn" data-a="lgo">يلا عالملعب</button><button class="linkish" data-a="home">رجوع</button>`);
}
const localNames = () => Array.from(document.querySelectorAll("#nl input")).map((x) => x.value.trim());
function startLocal(names) {
  mode = "local"; room = null; L.pid = null;
  S = { v: 0, room: null, host: null, phase: "lobby", players: names.map((name, i) => ({ id: "l" + i, name })), cfg: { len: mem.get("len", "quick") } };
  startSeason();
}

function vLobby() {
  const boss = isBoss(), n = S.players.length, inList = S.players.some((p) => p.id === me.id);
  const dyn = `
    <div class="plist">${S.players.map((p, i) => `<div class="pl"><span class="crest" style="--ch:${C.HUES[i]}">${C.CRESTS[i]}</span><span class="n">${esc(p.name)}${p.id === S.host ? " 👑" : ""}</span>${boss && p.id !== S.host ? `<button data-a="kick" data-v="${p.id}" aria-label="شيل ${esc(p.name)}">✕</button>` : ""}</div>`).join("")}</div>
    <p class="note">🤖 الكمبيوتر بيعبي ${Math.max(0, (n <= 4 ? 4 : 6) - n)} أندية عشان يكمل الدوري.</p>
    ${!inList ? `<p class="err">الغرفة مليانة (${C.MAX_P}). بتقدر تتفرج.</p>` : ""}
    ${boss ? `${lenSeg(S.cfg.len, "cfg")}<button class="btn" data-a="start">يلا عالملعب · ${n} ${n === 1 ? "لاعب" : "لاعبين"}</button>`
    : `<p class="note">${S.cfg.len === "quick" ? "موسم سريع · 3 جولات" : "موسم كامل · 5 جولات"}</p><p class="wait center">استنى صاحب الغرفة يبلّش <span class="dots"><i></i><i></i><i></i></span></p>`}`;
  return { key: "lobby", dyn, html: `
    <section class="roomcode"><div class="top">${musBtn()}</div><span class="sub">كود الغرفة</span><b>${esc(room)}</b><button class="btn sm alt" data-a="share">شارك الرابط</button></section>
    <!--dyn--><button class="linkish" data-a="leave">اطلع من الغرفة</button>` };
}
function vIntro() {
  return { key: "intro", dyn: bossBtn("صافرة البداية 🟢"), html: `${hud(viewer())}
    <span class="kicker gold">🏟️ أندية الدوري</span><p class="lead">${S.mds} جولات، وكاس واحد</p>
    <div class="clubs">${S.clubs.map((c, i) => `<div class="clubcard" style="--ch:${c.hue};--i:${i}">${crest(c, "lg")}<b>${esc(c.name)}</b>
      ${c.bot ? `<span class="tag">🤖 ${esc(c.boss)}</span><small>${C.PERS[c.pers]}</small>` : `<span class="tag">👤 رئيس النادي</span><small>ميزانية ${c.budget} مليون</small>`}</div>`).join("")}</div><!--dyn-->` };
}
function vNews() {
  const n = C.NEWS[S.news], v = viewer(), st = K.starOf(S.star), f = S.newsFx;
  const extra = !f ? "" : S.news === "curse" ? `<p class="note">😷 المتصدر ${esc(cl(f.club).name)} بيلعب بدون نجومه.</p>`
    : `<p class="note">🎁 ${esc(cl(f.club).name)} ${f.card ? `أخذ ${C.CARDS[f.card].icon} ${C.CARDS[f.card].name}` : "إيده مليانة كروت، فما أخذ إشي"}.</p>`;
  return { key: phaseKey(), dyn: bossBtn("يلا عاللغز والمزاد"), run: () => Snd.fx("news"), html: `${hud(v)}
    <div class="news"><div class="bar"><i></i>خبر عاجل</div><div class="body"><span class="ic">${n.icon}</span><div><b>${n.name}</b><p>${n.text}</p></div></div></div>${extra}
    <div class="panel"><div class="seclabel">⭐ نجم المزاد الليلة</div><div class="row">${starMini(S.star)}<span class="sub">${C.ROLES[st.role].name}: ${C.ROLES[st.role].how}</span></div></div>
    <div class="panel"><div class="seclabel">⚽ مباريات الجولة</div><div class="fxl">${S.matches.map((m) => fixtureRow(m, v)).join("")}</div></div><!--dyn-->` };
}
// مرحلة مدخلات: تمرير التلفون، أو شاشة اللاعب، أو انتظار
function vInput(body, kick) {
  const v = viewer(), hs = K.humans(S), pend = hs.filter((c) => !S.done.includes(c.id)), pk = phaseKey();
  if (mode === "local" && hs.length > 1 && (!v || S.done.includes(v))) {
    const nx = pend[0]; L.pid = null;
    if (nx) return { key: `${pk}:pass:${nx.id}`, dyn: "", html: `${hud()}${kick}
      <div class="pass panel"><span class="sub">التلفون هسا لـ</span>${crest(nx, "lg")}<h1>${esc(nx.name)}</h1><p class="sub">والباقي يلفّوا وجوههم 🙈</p>
      <button class="btn" data-a="hand" data-v="${nx.id}">أنا ${esc(nx.name)}، جاهز</button></div>
      <div class="chips">${hs.map((c) => `<span class="chip2 ${S.done.includes(c.id) ? "ok" : ""}">${crest(c, "sm")}${esc(c.name)}${S.done.includes(c.id) ? " ✓" : ""}</span>`).join("")}</div>` };
  }
  if (!v || S.done.includes(v)) return { key: `${pk}:wait`, html: `${hud(v)}${tbar()}${kick}<p class="lead">${v ? "تمام، خطتك مقفولة 🔒" : "اللاعبين عم يختاروا..."}</p><!--dyn-->`,
    dyn: `<div class="chips">${hs.map((c) => `<span class="chip2 ${S.done.includes(c.id) ? "ok" : ""}">${crest(c, "sm")}${esc(c.name)}${S.done.includes(c.id) ? " ✓" : ""}</span>`).join("")}</div>
      <p class="wait center">بنستنى الباقي <span class="dots"><i></i><i></i><i></i></span></p>${isBoss() ? `<button class="linkish" data-a="go">كمّل بدون الباقي</button>` : ""}` };
  const dk = pk + ":" + v;
  if (D.key !== dk) D = { key: dk, step: 0, ans: null, bid: 0, att: null, def: null, card: null, ci: -1 };
  return body(v, cl(v), pk);
}
function vPrep() {
  return vInput((v, c, pk) => {
    const p = S.puzzle, st = K.starOf(S.star);
    if (D.step === 0) return { key: `${pk}:in:${v}:0`, dyn: "", html: `${hud(v)}${tbar()}<span class="kicker green">🧩 لغز غرفة الملابس</span>
      <div class="panel puz"><h2>${p.title}</h2>${p.big ? `<div class="big">${p.big}</div>` : ""}${p.items ? `<div class="items">${p.items.map((x) => `<span>${esc(x)}</span>`).join("")}</div>` : ""}<p class="lead" style="font-size:21px">${esc(p.q)}</p></div>
      <div class="opts">${p.opts.map((o, i) => `<button class="opt" data-a="pans" data-v="${i}">${esc(o)}</button>`).join("")}</div>
      <p class="note">الجواب الصح = كرت تكتيكي 🎴. بتعرف إذا صح وقت الكشف.</p>` };
    const dup = K.roles(c).includes(st.role);
    return { key: `${pk}:in:${v}:1`, dyn: "", html: `${hud(v)}${tbar()}<span class="kicker gold">💰 الميركاتو</span>${starCard(S.star, "flipin")}
      <div class="panel bidbox"><div class="center sub">عرضك السري · معك <span class="money">${c.budget}M</span></div>
        <div class="bidval"><span id="bidv">0</span><small> مليون</small></div>
        <div class="bidrow"><button data-a="bidstep" data-v="-${C.STEP}" aria-label="نقّص">−</button><input type="range" id="bidr" min="0" max="${c.budget}" step="${C.STEP}" value="0" aria-label="العرض"><button data-a="bidstep" data-v="${C.STEP}" aria-label="زيد">+</button></div>
        <div class="quick"><button data-a="bidset" data-v="0">ولا قرش</button><button data-a="bidset" data-v="0.25">ربع</button><button data-a="bidset" data-v="0.5">نص</button><button data-a="bidset" data-v="1">كل إشي</button></div></div>
      <button class="btn" data-a="psend">ثبّت العرض 🔒</button>
      <p class="note">${dup ? `⚠️ عندك ${C.ROLES[st.role].name} من قبل. الثاني ما بيزيدك قوة، بس بتحرم غيرك منه.` : "الأعلى بيدفع وبياخد النجم. الباقي ما بيدفعوا إشي."}</p>` };
  }, `<span class="kicker gold">🧩 اللغز والمزاد</span>`);
}
function vSeg() {
  return vInput((v, c, pk) => {
    const m = K.matchOf(S, v), r = cl(K.rival(S, v)), mine = m.h === v ? m.hg : m.ag, theirs = m.h === v ? m.ag : m.hg;
    const A = C.ATT, DF = C.DEF, n = C.NEWS[S.news];
    const key = (obj, row, res) => Object.keys(obj).find((x) => row(x) === res);
    return { key: `${pk}:in:${v}`, dyn: "", html: `${hud(v)}${tbar()}<span class="kicker ${S.seg === 2 ? "" : "green"}">${S.seg === 2 ? "⏱️" : "⚽"} ${SEG_NAME[S.seg]}</span>
      <div class="panel vsbox"><div class="side">${crest(c)}<b>${esc(c.name)}</b>${starsOf(c, S.cursed === v)}</div>
        <div class="mid"><b>${mine}</b><i>-</i><b>${theirs}</b></div>
        <div class="side">${crest(r)}<b>${esc(r.name)}</b>${starsOf(r, S.cursed === r.id)}${r.cards.length ? `<div class="stars">${r.cards.map((k) => cardChip(k)).join("")}</div>` : ""}</div></div>
      <p class="note">${n.icon} ${n.name}: ${n.text}</p>
      <div class="seclabel">⚔️ هجمتك</div>
      <div class="picks">${Object.keys(A).map((a) => `<button class="pick" data-a="att" data-v="${a}" aria-pressed="false"><span class="i">${A[a].icon}</span><b>${A[a].name}</b>
        <small><em>✅ ضد ${DF[key(DF, (d) => C.MATRIX[a][d], "goal")].icon}</em><em>❌ ضد ${DF[key(DF, (d) => C.MATRIX[a][d], "dead")].icon}</em></small></button>`).join("")}</div>
      <div class="seclabel">🛡️ دفاعك</div>
      <div class="picks">${Object.keys(DF).map((d) => `<button class="pick def" data-a="def" data-v="${d}" aria-pressed="false"><span class="i">${DF[d].icon}</span><b>${DF[d].name}</b>
        <small><em>✅ بيوقف ${A[key(A, (a) => C.MATRIX[a][d], "dead")].icon}</em><em>❌ بينكشف قدام ${A[key(A, (a) => C.MATRIX[a][d], "goal")].icon}</em></small></button>`).join("")}</div>
      <div class="seclabel">🎴 كرت تكتيكي (اختياري)</div>
      <div class="hand">${c.cards.length ? c.cards.map((k, i) => `<button class="tcard" data-a="card" data-v="${i}" aria-pressed="false" ${K.cardAllowed(S, k) ? "" : "disabled"} title="${C.CARDS[k].how}">${C.CARDS[k].icon} ${C.CARDS[k].name}</button>`).join("") : `<span class="sub">ما معك كروت. حل اللغز الجاي صح.</span>`}</div>
      <p class="note" id="cardhow"></p>
      <button class="btn" data-a="ssend" id="ssend" disabled>اختار هجمة ودفاع</button>` };
  }, `<span class="kicker green">⚽ ${SEG_NAME[S.seg]}</span>`);
}
function vPrepShow() {
  const p = S.puzzle, sh = S.show, v = viewer(), st = K.starOf(S.star);
  const got = S.clubs.filter((c) => sh.got[c.id]);
  return { key: phaseKey(), dyn: showBtn("عالملعب ⚽"), run: runPrepShow, html: `${hud(v)}<span class="kicker green">🧩 حل اللغز</span>
    <div class="panel puz">${p.big ? `<div class="big">${p.big}</div>` : ""}${p.items ? `<div class="items">${p.items.map((x) => `<span>${esc(x)}</span>`).join("")}</div>` : ""}<p class="center"><b>${esc(p.q)}</b></p>
      <div class="opts">${p.opts.map((o, i) => `<div class="opt ${i === p.ans ? "right" : "wrong"}">${esc(o)}<div class="who">${S.clubs.filter((c) => sh.picks[c.id] === i).map((c) => crest(c, "sm")).join("")}</div></div>`).join("")}</div>
      ${p.note ? `<p class="note">${esc(p.note)}</p>` : ""}</div>
    <div class="gains">${got.length ? got.map((c) => `<div class="gain ${sh.got[c.id] === "full" ? "no" : ""}">${crest(c, "sm")}<span>${esc(c.name)}</span><b>${sh.got[c.id] === "full" ? "إيده مليانة" : `${C.CARDS[sh.got[c.id]].icon} ${C.CARDS[sh.got[c.id]].name}`}</b></div>`).join("") : `<div class="gain no"><span>ما حدا عرفها!</span><b>ولا كرت</b></div>`}</div>
    <span class="kicker gold" id="auc">💰 كشف العروض</span>${starCard(S.star)}
    <div class="bids" id="bids">${sh.bids.map((b) => `<div class="bid" data-id="${b.id}">${crest(cl(b.id), "sm")}<span class="n">${esc(cl(b.id).name)}</span><span class="money">${b.bid}M</span></div>`).join("")}</div>
    <div id="sold"></div><!--dyn-->` };
}
function soldHTML() {
  const sh = S.show, st = K.starOf(S.star);
  return sh.win ? `<div class="sold">🔨 بيع! ${esc(cl(sh.win).name)} أخذ ${esc(st.name)} بـ${sh.price} مليون</div>` : `<div class="sold">😴 ما حدا دفع قرش! ${esc(st.name)} روّح عالبيت</div>`;
}
async function runPrepShow(id) {
  const sh = S.show, v = viewer();
  skipFn = () => { document.querySelectorAll("#bids .bid").forEach((b) => b.classList.add("on")); if (sh.win) document.querySelector(`#bids [data-id="${sh.win}"]`)?.classList.add("win"); $("sold").innerHTML = soldHTML(); };
  try {
    if (v) Snd.fx(sh.picks[v] === S.puzzle.ans ? "ok" : "bad");
    await step(id, 2600);
    $("auc").scrollIntoView({ behavior: FAST ? "auto" : "smooth", block: "start" });
    await step(id, 500); Snd.fx("roll", 1.1);
    const els = Array.from(document.querySelectorAll("#bids .bid"));
    for (let i = 0; i < els.length; i++) {
      await step(id, i >= els.length - 2 ? 1250 : 700);
      els[i].classList.add("on"); Snd.fx("coin");
    }
    await step(id, 900);
    if (sh.win) { document.querySelector(`#bids [data-id="${sh.win}"]`).classList.add("win"); Snd.fx("sold"); if (sh.win === v) { haptic("goal"); confetti(40); } } else Snd.fx("bad");
    $("sold").innerHTML = soldHTML();
    await step(id, 700);
  } catch (e) { if (e !== STOP) throw e; return; }
  endShow(id);
}
function endShow(id) {
  if (id !== runId) return;
  shown[phaseKey()] = true; skipFn = null;
  const d = $("dyn"); if (d) d.innerHTML = VIEWS[S.phase]().dyn;
  const b = d && d.querySelector(".btn"); if (b) b.scrollIntoView({ behavior: FAST ? "auto" : "smooth", block: "nearest" });
}

// ---------- البث: الملعب ----------
const AT0 = [[150, 262], [78, 246], [222, 246], [150, 214]], DF0 = [[70, 165], [110, 170], [150, 172], [190, 170], [230, 165]], GK0 = [150, 34];
const FORM = { bus: [[96, 72], [124, 62], [150, 58], [176, 62], [204, 72]], press: [[82, 222], [122, 206], [150, 196], [178, 206], [218, 222]], trap: [[70, 135], [110, 135], [150, 135], [190, 135], [230, 135]] };
function pitchSVG() {
  return `<svg class="pitch" viewBox="0 0 300 284" role="img" aria-label="الملعب">
    <rect class="net" id="net" x="120" y="5" width="60" height="19" rx="2"/><path class="ln" d="M4 24h292M4 24v260M296 24v260M60 24v76h180V24M110 24v26h80V24M112 100a40 34 0 0 0 76 0"/>
    <circle class="ln" cx="150" cy="284" r="42"/><circle cx="150" cy="78" r="2.5" fill="#FFF"/>
    ${DF0.map((p, i) => `<circle class="df" id="d${i}" r="8" cx="${p[0]}" cy="${p[1]}"/>`).join("")}<circle class="df" id="gk" r="8" cx="${GK0[0]}" cy="${GK0[1]}"/>
    ${AT0.map((p, i) => `<circle class="at" id="a${i}" r="8" cx="${p[0]}" cy="${p[1]}"/>`).join("")}
    <circle class="ball" id="ball" r="4.6" cx="150" cy="254"/><text class="lbl" id="lbl" x="150" y="150"></text></svg>`;
}
const pos = (el) => [+el.getAttribute("cx"), +el.getAttribute("cy")];
const put = (el, p) => { el.setAttribute("cx", p[0]); el.setAttribute("cy", p[1]); };
// حركة عنصر لنقطة. arc: الكرة بتكبر شوي بالنص كأنها بالهوا
function tween(el, to, ms, arc) {
  return new Promise((res) => {
    if (!el) return res();
    const from = pos(el), dur = T(ms), t0 = performance.now(), r0 = 4.6;
    if (dur < 20) { put(el, to); return res(); }
    const tick = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      put(el, [from[0] + (to[0] - from[0]) * e, from[1] + (to[1] - from[1]) * e]);
      if (arc) el.setAttribute("r", r0 + Math.sin(k * Math.PI) * 3.6);
      if (k < 1 && el.isConnected) requestAnimationFrame(tick); else { if (arc) el.setAttribute("r", r0); res(); }
    };
    requestAnimationFrame(tick);
  });
}
const E = (id) => $(id);
const label = (txt, p) => { const l = $("lbl"); if (!l) return; l.textContent = txt; l.setAttribute("x", clamp(p[0], 60, 240)); l.setAttribute("y", p[1]); l.classList.add("on"); };
function setupPitch(A, Dc) {
  AT0.forEach((p, i) => { put(E("a" + i), p); E("a" + i).setAttribute("fill", `hsl(${A.hue} 88% 56%)`); });
  DF0.forEach((p, i) => { put(E("d" + i), p); E("d" + i).setAttribute("fill", `hsl(${Dc.hue} 78% 42%)`); });
  put(E("gk"), GK0); E("gk").setAttribute("fill", "#111"); E("gk").setAttribute("style", `stroke:hsl(${Dc.hue} 78% 60%)`);
  put(E("ball"), [150, 254]); $("lbl").classList.remove("on"); $("net").classList.remove("hit");
}
const form = (def, ms = 520) => Promise.all(FORM[def].map((p, i) => tween(E("d" + i), p, ms)));
const passTo = async (p, ms = 260, arc) => { Snd.fx(arc ? "kick" : "pass"); await tween(E("ball"), p, ms, arc); };
// الاقتراب: بيوصّل الكرة لنقطة التسديد حسب نوع الهجمة والدفاع
const APPROACH = {
  async counter(def) {
    const to = { press: [212, 118], bus: [214, 150], trap: [222, 110] }[def];
    const line = def === "trap" ? Promise.all(FORM.trap.map((p, i) => tween(E("d" + i), [p[0], p[1] + 16], 420))) : null;
    await Promise.all([passTo([to[0] - 7, to[1] + 5], 680, true), tween(E("a2"), to, 620), line]);
    if (def === "trap") return;                           // واقف بالتسلل، والباقي بيتحدد بعدين
    const sh = def === "press" ? [192, 86] : [206, 112];
    await Promise.all([tween(E("a2"), sh, 380), tween(E("ball"), [sh[0] - 6, sh[1] - 6], 380)]);
  },
  async shot(def) {
    const closing = def === "press" ? Promise.all([tween(E("d1"), [130, 204], 520), tween(E("d2"), [150, 178], 520), tween(E("d3"), [170, 204], 520)]) : null;
    await Promise.all([tween(E("a0"), [150, 196], 520), tween(E("ball"), [150, 186], 520), closing]);
  },
  async tiki(def) {
    const hops = [["a1", [92, 206]], ["a3", [150, 168]], ["a2", [206, 148]], ["a3", [150, 116]]];
    for (const [who, p] of hops) await Promise.all([tween(E(who), p, 250), passTo([p[0], p[1] - 8], 250)]);
    if (def === "press") await Promise.all([tween(E("d1"), [134, 138], 200), tween(E("d3"), [166, 138], 200)]);
  },
};
// الهجمة الميتة
const DEAD = {
  async counter() { Snd.fx("flag"); label("🚩 تسلل!", [222, 96]); await wait(900); },
  async shot() { Snd.fx("save"); await tween(E("d2"), [150, 188], 160); label("⚡ انخطفت!", [150, 160]); await Promise.all([tween(E("d2"), [150, 262], 520), tween(E("ball"), [150, 270], 520)]); },
  async tiki() { await passTo([150, 70], 200); Snd.fx("save"); label("🧱 مسكّرة!", [150, 96]); await tween(E("ball"), [92, 152], 420, true); },
};
// النهاية: هدف، تصدي، أو عارضة
async function finish(kind) {
  const b = E("ball"), from = pos(b), left = Math.random() < 0.5, far = from[1] > 150;
  Snd.fx("kick");
  if (kind === "goal") {
    const tx = left ? 129 : 171;
    await Promise.all([tween(b, [tx, 13], far ? 430 : 260, far), tween(E("gk"), [left ? 160 : 140, 34], 240)]);
    $("net").classList.add("hit");
  } else if (kind === "save") {
    const tx = left ? 134 : 166;
    await Promise.all([tween(b, [tx, 40], far ? 430 : 260, far), tween(E("gk"), [tx, 35], 250)]);
    Snd.fx("save"); label("🧤 تصدي!", [150, 66]);
    await tween(b, [left ? 84 : 216, 84], 340, true);
  } else {
    const tx = left ? 119 : 181;
    await tween(b, [tx, 24], far ? 430 : 260, far);
    Snd.fx("post"); label("😱 العارضة!", [150, 66]);
    await tween(b, [left ? 76 : 224, 90], 380, true);
  }
}

// ---------- البث: الشوط ----------
function vSegShow() {
  const v = viewer(), last = S.seg + 1 >= S.segs;
  return { key: phaseKey(), run: runSegShow, dyn: showBtn(last ? "شوف الجدول 📊" : S.seg === 0 ? "الشوط الثاني ▶" : "الوقت القاتل ⏱️"), html: `<div class="livebox">
    <div class="bug" id="bug"></div>
    <div class="duel"><div class="c" id="dca"></div><span class="x">ضد</span><div class="c d" id="dcd"></div></div>
    <div class="pitchwrap" id="pw">${pitchSVG()}<div class="verdict" id="vd"></div></div>
    <div class="say" id="say"><span>${SEG_NAME[S.seg]}...</span></div>
    ${tableHTML(K.standings(S, segScores(S.seg)), v, true)}
    <div class="foot"><div class="ticker" id="tick"><span>📡 ${S.md === S.mds - 1 ? "🔥 ليلة الحسم" : `الجولة ${S.md + 1}/${S.mds}`} · باقي الملاعب</span></div>${musBtn()}</div></div><!--dyn-->` };
}
// نتيجة كل مباراة قبل الشوط seg (أو النهائية إذا seg كبير)
const segScores = (seg) => S.matches.map((m) => { const sc = { hg: 0, ag: 0 }; m.plays.forEach((p) => { if (p.seg < seg && p.out === "goal") sc[p.side === "h" ? "hg" : "ag"]++; }); return sc; });
const say = (txt) => { const s = $("say"); if (s) s.innerHTML = `<span>${esc(txt)}</span>`; };
function setBug(m, sc, min) {
  const h = cl(m.h), a = cl(m.a), bug = $("bug"); if (!bug) return;
  if (bug.dataset.m !== m.h) {
    bug.dataset.m = m.h;
    bug.innerHTML = `<span class="t">${crest(h, "sm")}<span>${esc(h.name)}</span></span><span class="sc"><b id="sh">${sc.hg}</b><span class="min" id="min"></span><b id="sa">${sc.ag}</b></span><span class="t a">${crest(a, "sm")}<span>${esc(a.name)}</span></span>`;
  }
  $("sh").textContent = sc.hg; $("sa").textContent = sc.ag;
  if (min) $("min").textContent = min > 90 ? `90+${min - 90}′` : `${min}′`;
}
async function runSegShow(id) {
  const v = viewer(), sh = S.show, live = segScores(S.seg), fin = segScores(S.seg + 1);
  const humanIn = (m) => !cl(m.h).bot || !cl(m.a).bot;
  let feat = S.matches.filter((m) => (mode === "local" ? humanIn(m) : v && (m.h === v || m.a === v)));
  if (!feat.length) feat = [S.matches.find(humanIn) || S.matches[0]];
  const all = [];
  S.matches.forEach((m, mi) => m.plays.filter((p) => p.seg === S.seg).forEach((p) => all.push({ m, mi, p })));
  all.sort((x, y) => x.p.min - y.p.min || x.mi - y.mi);
  const table = () => flipTable(K.standings(S, live), v, true);
  setBug(feat[0], live[S.matches.indexOf(feat[0])]);
  skipFn = () => { fin.forEach((s, i) => { live[i] = s; }); const m = feat[feat.length - 1]; setBug(m, live[S.matches.indexOf(m)]); table(); Snd.crowd(0); $("fxlayer").innerHTML = ""; };
  try {
    Snd.crowd(0.35); Snd.fx("whistle");
    say(say1(S.seg === 0 ? "kickoff" : S.seg === 1 ? "half2" : "extra"));
    if (S.seg === 2) banner("⏱️ الوقت القاتل", "هجمة أخيرة لكل فريق");
    await step(id, 1500);
    for (const cid of Object.keys(sh.cards)) {             // الكروت المكشوفة من البداية: الأحمر والراعي
      const k = sh.cards[cid], c = cl(cid), rv = cl(K.rival(S, cid));
      if (k !== "red" && k !== "sponsor") continue;
      if (!feat.some((m) => m.h === cid || m.a === cid)) continue;
      if (k === "red") { banner("🟥 كرت أحمر!", `${esc(c.name)} طيّر نجوم ${esc(rv.name)} هالشوط`); Snd.fx("red"); say(say1("red", c, rv)); }
      else { banner("💼 راعي رسمي!", `${esc(c.name)} +25 مليون`); Snd.fx("coin"); }
      await step(id, 1700);
    }
    if (sh.auto && sh.auto.length) { say(`${sh.auto.map((x) => cl(x).name).join(" و")} ما لحق يختار، والمساعد اختار عنه!`); await step(id, 1400); }
    for (const it of all) {
      const { m, mi, p } = it, A = cl(p.side === "h" ? m.h : m.a), Dc = cl(p.side === "h" ? m.a : m.h);
      const count = () => { live[mi][p.side === "h" ? "hg" : "ag"]++; };
      if (!feat.includes(m)) {                             // ملعب ثاني: خبر بالشريط بس
        if (p.out === "goal") { count(); $("tick").innerHTML = `<span>⚽ الدقيقة ${p.min > 90 ? "90+" + (p.min - 90) : p.min}: هدف لـ${esc(A.name)}! (${esc(cl(m.h).name)} ${live[mi].hg}-${live[mi].ag} ${esc(cl(m.a).name)})</span>`; Snd.fx("tick"); table(); await step(id, 1100); }
        continue;
      }
      setBug(m, live[mi], p.min); setupPitch(A, Dc);
      $("dca").innerHTML = `<i>${C.ATT[p.att].icon}</i>${C.ATT[p.att].name}<small>هجمة ${esc(A.name)}</small>`;
      $("dcd").innerHTML = `<i>${C.DEF[p.def].icon}</i>${C.DEF[p.def].name}<small>دفاع ${esc(Dc.name)}</small>`;
      say(`الدقيقة ${p.min > 90 ? "90+" + (p.min - 90) : p.min}: هجمة لـ${A.name}...`);
      Snd.crowd(0.6); Snd.fx("roll", 0.9);
      await step(id, 900); $("dca").classList.add("on"); Snd.fx("flip");
      await step(id, 800); $("dcd").classList.add("on"); Snd.fx("flip");
      const vd = $("vd");
      const verdict = (cls, txt) => { vd.className = "verdict on " + cls; vd.textContent = txt; };
      await Promise.all([form(p.def), step(id, 600)]);
      verdict(p.base, p.base === "goal" ? "🟢 الدفاع انكشف!" : p.base === "dead" ? "🔴 الدفاع قراها!" : `🟡 50/50${p.p ? ` · فرصة الهدف ${Math.round(p.p * 100)}%` : ""}`);
      await step(id, 900);
      Snd.crowd(0.9);
      await APPROACH[p.att](p.def); if (id !== runId) throw STOP;
      if (p.fl.includes("maestro")) { banner("🎩 لمسة المايسترو!", "الهجمة الميتة رجعت 50/50"); Snd.fx("magic"); say(say1("maestro", A, Dc)); verdict("magic", `🎩 50/50${p.p ? ` · ${Math.round(p.p * 100)}%` : ""}`); await step(id, 1600); }
      if (p.fl.includes("gold")) { banner("🔄 تبديل ذهبي!", "الـ50/50 صارت هدف أكيد"); Snd.fx("magic"); say(say1("gold", A, Dc)); await step(id, 1600); }
      if (p.out === "dead") {
        await DEAD[p.att](); if (id !== runId) throw STOP;
        Snd.fx("ooh"); say(say1("dead_" + p.def, A, Dc)); if (A.id === v) haptic("error");
      } else if (p.out === "goal" || p.out === "varNo") {
        await finish("goal"); if (id !== runId) throw STOP;
        $("pw").classList.add("shake"); setTimeout(() => $("pw") && $("pw").classList.remove("shake"), 600);
        Snd.fx("goal"); haptic("goal");
        overlay("goalfx", `<b>غوووول</b><span>${crest(A)}${esc(A.name)}</span>`, 1900);
        say(say1(p.base === "goal" ? "goalSure" : p.min >= 85 ? "goalLate" : "goal", A, Dc));
        await step(id, 1900);
        if (p.fl.includes("var")) {
          const o = overlay("varfx", `<div class="scr">VAR</div><div class="sub">${esc(Dc.name)} طلب مراجعة 📺</div><div class="res" id="varres"></div>`);
          Snd.fx("var"); say(say1("varCheck", A, Dc));
          await step(id, 2300);
          const ok = p.out === "goal", r = $("varres");
          if (r) { r.textContent = ok ? "✅ الهدف صحيح" : "❌ الهدف ملغي"; r.className = "res " + (ok ? "ok" : "no"); }
          Snd.fx(ok ? "ok" : "ooh"); say(say1(ok ? "varOk" : "varNo", A, Dc));
          await step(id, 1500); o.remove();
        }
        if (p.out === "goal") { count(); setBug(m, live[mi], p.min); $(p.side === "h" ? "sh" : "sa").classList.add("bump"); table(); if (A.id === v) confetti(36); }
      } else {
        await finish(p.out); if (id !== runId) throw STOP;
        Snd.fx("ooh"); say(say1(p.out, A, Dc));
      }
      await step(id, 1500);
      $("dca").classList.remove("on"); $("dcd").classList.remove("on"); vd.className = "verdict"; Snd.crowd(0.35);
      await step(id, 450);
    }
    const wasted = Object.keys(sh.cards).filter((cid) => ["var", "gold"].includes(sh.cards[cid]) && !all.some((it) => it.p.fl.includes(sh.cards[cid]) && [it.m.h, it.m.a].includes(cid)));
    Snd.fx("whistle", true);
    const last = S.seg + 1 >= S.segs, fm = feat[feat.length - 1], fs = live[S.matches.indexOf(fm)];
    say(last ? `صافرة النهاية! ${cl(fm.h).name} ${fs.hg} - ${fs.ag} ${cl(fm.a).name}` : wasted.length ? `${wasted.map((x) => cl(x).name).join(" و")} حرق كرته عالفاضي هالشوط!` : "نهاية الشوط. خذوا نفس!");
    Snd.crowd(0.15);
    await step(id, 900);
  } catch (e) { if (e !== STOP) throw e; return; }
  endShow(id);
}

function vTable() {
  const v = viewer(), rows = K.standings(S), prev = S.show.prev, next = S.md + 1 < S.mds;
  const start = prev.map((pid) => rows.find((r) => r.id === pid));
  return { key: phaseKey(), dyn: bossBtn(next ? (S.md + 2 === S.mds ? "🔥 ليلة الحسم" : "الجولة الجاية ▶") : "التتويج 🏆"), html: `${hud(v)}
    <span class="kicker gold">📊 الجدول بعد الجولة ${S.md + 1}</span>
    <div class="results">${S.matches.map((m) => fixtureRow(m, v, true)).join("")}</div>
    ${tableHTML(start, v)}
    ${next && S.md + 2 === S.mds ? `<div class="panel glow center"><b class="lead">🔥 الجولة الجاية: ليلة الحسم</b><p class="sub">هجمة ثالثة بالوقت القاتل، وكل إشي ممكن ينقلب.</p></div>` : ""}<!--dyn-->`,
    run: async (id) => { Snd.crowd(0); try { await step(id, 800); } catch { return; } flipTable(rows, v); Snd.fx("ok"); } };
}
function vFinal() {
  const f = S.fin, v = viewer(), ch = cl(f.champ);
  const dyn = isBoss() ? `<button class="btn" data-a="again">موسم جديد 🔁</button><button class="linkish" data-a="leave">رجوع للبداية</button>` : `<p class="wait center">صاحب الغرفة بيقرر إذا في موسم جديد</p><button class="linkish" data-a="leave">اطلع</button>`;
  return { key: "final", dyn, run: () => { Snd.crowd(0.5); Snd.fx("champ"); confetti(110); haptic("goal"); }, html: `${hud(v)}
    <div class="champ"><span class="cup">🏆</span><span class="sub">بطل الدوري</span>${crest(ch, "xl")}<h1>${esc(ch.name)}</h1>${ch.id === v ? `<span class="kicker gold">مبروووك! إنت البطل</span>` : ""}</div>
    <div class="panel"><div class="seclabel">📖 قصة الموسم</div><div class="story">${f.story.map((s, i) => `<p style="--i:${i}">${esc(s)}</p>`).join("")}</div></div>
    <div class="seclabel">🏅 ألقاب الموسم</div>
    <div class="awards">${f.awards.map((a, i) => { const w = C.AWARDS[a.k], c = cl(a.id); return `<div class="award" style="--i:${i}"><span class="k">${w[0]} ${w[1]}</span><span class="w">${crest(c, "sm")}<span>${esc(c.name)}</span></span><span class="v">${a.v} ${w[2]}</span></div>`; }).join("")}</div>
    <div class="seclabel">📊 الترتيب النهائي</div>${tableHTML(K.standings(S), v)}
    ${f.loser ? `<div class="dare"><span class="sub">⚖️ حكم على ${esc(cl(f.loser).name)} (آخر واحد فيكم)</span><b>${esc(f.dare)}</b></div>` : ""}<!--dyn-->` };
}
const VIEWS = { lobby: vLobby, intro: vIntro, news: vNews, prep: vPrep, prepShow: vPrepShow, seg: vSeg, segShow: vSegShow, table: vTable, final: vFinal };
const MOOD = { lobby: "anthem", intro: "anthem", news: "show", prep: "pick", prepShow: "show", seg: "pick", segShow: "show", table: "show", final: "champ" };

function draw() {
  if (!S) return;
  Snd.setMusic(musicPref()); Snd.mood(MOOD[S.phase]);
  const view = VIEWS[S.phase]();
  if (view.key === lastKey && $("dyn")) { $("dyn").innerHTML = view.dyn; return; }
  lastKey = view.key; runId++; skipFn = null;
  $("fxlayer").innerHTML = "";
  if (S.phase !== "segShow") Snd.crowd(0);
  const dyn = `<div id="dyn" class="stack">${view.dyn}</div>`;
  render(view.html.includes("<!--dyn-->") ? view.html.replace("<!--dyn-->", dyn) : view.html + dyn);
  window.scrollTo(0, 0);
  const r = $("bidr"); if (r) r.oninput = () => setBid(+r.value);
  if (view.run) { const id = runId; Promise.resolve(view.run(id)).catch((e) => { console.error(e); endShow(id); }); }
}
function setBid(val) {
  const c = cl(viewer()); if (!c) return;
  D.bid = clamp(Math.round(val / C.STEP) * C.STEP, 0, c.budget);
  if ($("bidv")) $("bidv").textContent = D.bid;
  if ($("bidr")) $("bidr").value = D.bid;
}
const press1 = (b) => b.parentNode.querySelectorAll("[aria-pressed]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
function segReady() {
  const b = $("ssend"); if (!b) return;
  b.disabled = !(D.att && D.def);
  b.textContent = D.att && D.def ? "ثبّت الخطة 🔒" : !D.att ? "اختار هجمة" : "اختار دفاع";
}

// ======================= الضغطات =======================
const UI = {
  create: () => { if (getName()) hostRoom(); },
  join: () => { if (!getName()) return; const code = $("code").value.trim(); if (!/^\d{5}$/.test(code)) { $("err").hidden = false; $("err").textContent = "الكود 5 أرقام."; return; } joinRoom(code); },
  back2room: () => { const o = mem.get("online", null); if (!o) return home(); if (!me.name) me.name = "لاعب"; o.host ? hostRoom(o.room) : joinRoom(o.room); },
  rejoin: () => send({ t: "join", name: me.name }),
  resume: () => { const g = mem.get("local", null); if (!g || !g.S) return home(); mode = "local"; room = null; S = g.S; H = g.H; L.pid = null; lastKey = ""; if (CAREER === undefined) loadCareer(); draw(); },
  one: () => { const n = $("name").value.trim(); if (n) { me.name = n; mem.set("name", n); } const v = mem.get("names", ["", ""]); if (n && !v[0]) v[0] = n; while (v.length < 2) v.push(""); mem.set("names", v); localSetup(); },
  solo: () => { const n = $("name").value.trim() || me.name || "إنت"; me.name = n; mem.set("name", n); mem.set("names", [n]); localSetup(); },
  home,
  music: () => { mem.set("music", !musicPref()); Snd.setMusic(musicPref()); if (musicPref()) Snd.mood(S ? MOOD[S.phase] : "anthem"); document.querySelectorAll(".mus").forEach((b) => { b.textContent = musicPref() ? "🔊" : "🔇"; b.setAttribute("aria-pressed", musicPref()); }); },
  addp: () => { const v = localNames(); if (v.length < C.MAX_P) v.push(""); mem.set("names", v); localSetup(); },
  remp: () => { const v = localNames(); if (v.length > 1) v.pop(); mem.set("names", v); localSetup(); },
  llen: (v) => { mem.set("names", localNames()); mem.set("len", v); localSetup(); },
  lgo: () => {
    const v = localNames().map((x, i) => x || `لاعب ${i + 1}`);
    if (new Set(v).size !== v.length) { $("err").hidden = false; $("err").textContent = "في اسمين متشابهين."; return; }
    mem.set("names", v); startLocal(v);
  },
  leave: () => { const g = window.leaveGuard(); if (!g || confirm(g)) leave(); },
  share: () => {
    const url = `${location.origin}${location.pathname}?room=${room}`, text = `تعال العب معي «ليلة الحسم» 🏆 كود الغرفة: ${room}`;
    if (navigator.share) navigator.share({ title: "ليلة الحسم", text, url }).catch(() => {});
    else if (navigator.clipboard) navigator.clipboard.writeText(`${text}\n${url}`).then(() => window.uiToast && uiToast("انسخ الرابط ✅"));
  },
  cfg: (v) => send({ t: "cfg", len: v }),
  kick: (v) => send({ t: "kick", who: v }),
  start: () => send({ t: "start" }),
  again: () => send({ t: "again" }),
  go: () => send({ t: "go" }),
  skip: () => { runId++; const id = runId; if (skipFn) skipFn(); endShow(id); },
  hand: (v) => { L.pid = v; Snd.fx("tap"); draw(); },
  pans: (v) => { D.ans = +v; D.step = 1; Snd.fx("tap"); draw(); },
  bidstep: (v) => { setBid(D.bid + +v); Snd.fx("tick"); },
  bidset: (v) => { const c = cl(viewer()); if (c) setBid(Math.floor(c.budget * +v / C.STEP) * C.STEP); Snd.fx("tick"); },
  psend: () => { const pid = viewer(); Snd.fx("gavel"); if (mode === "local") L.pid = null; send({ t: "prep", pid, ans: D.ans, bid: D.bid }); },
  att: (v, b) => { D.att = v; press1(b); Snd.fx("tap"); segReady(); },
  def: (v, b) => { D.def = v; press1(b); Snd.fx("tap"); segReady(); },
  card: (v, b) => {
    const c = cl(viewer()), i = +v, on = D.ci !== i;
    D.ci = on ? i : -1; D.card = on ? c.cards[i] : null;
    b.parentNode.querySelectorAll("[aria-pressed]").forEach((x) => x.setAttribute("aria-pressed", String(on && x === b)));
    $("cardhow").textContent = on ? `${C.CARDS[D.card].icon} ${C.CARDS[D.card].how}` : "";
    Snd.fx("flip");
  },
  ssend: () => { if (!D.att || !D.def) return; const pid = viewer(); Snd.fx("ok"); if (mode === "local") L.pid = null; send({ t: "seg", pid, att: D.att, def: D.def, card: D.card }); },
};
$("app").addEventListener("click", (e) => {
  const b = e.target.closest("[data-a]");
  if (!b || b.disabled) return;
  const fn = UI[b.dataset.a];
  if (fn) fn(b.dataset.v, b);
});
$("app").addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.id === "code") UI.join(); });
document.addEventListener("pointerdown", () => Snd.unlock(), { passive: true });
// الغرفة بتوقف إذا صاحبها طلع، فبنسأله أول. التلفون الواحد محفوظ وبيكمل.
window.leaveGuard = () => (mode === "host" && S && S.clubs && S.phase !== "final" ? "إنت صاحب الغرفة. إذا طلعت، الموسم بيوقف عند الكل. متأكد؟" : null);

home();
