// محرك مشترك لألعاب الكورة: أسئلة بأربع خيارات، إما من تلفون واحد (بالدور) أو غرفة (كل واحد من تلفونه).
// بيتحمّل بعد mini.js. كل لعبة بتنادي KORA({ id, title, desc, root, load }) وload بترجع أسئلة:
// { q, opts: [الصح, غلط, غلط, غلط], vis?: html فوق السؤال, rev?: html بيبين بعد الجواب, hints?: [تلميحات بتبين مع الوقت], fixed?: الخيارات بترتيبها }
/* global mqtt, Rewards */
"use strict";

// ---------- الاتصال (MQTT عام، صاحب الغرفة هو المرجع) ----------
const KoraNet = (() => {
  const BROKERS = ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081/mqtt"];
  const qs = new URLSearchParams(location.search);
  const me = { id: store.get("pid", null), name: store.get("myname", "") };
  if (!me.id) { me.id = Math.random().toString(36).slice(2, 10); store.set("pid", me.id); }
  let c = null, root = "", room = null, host = false, H = {}, offset = 0;
  const tp = (k) => `${root}/${room}/${k}`;
  function tryConnect(k) {
    if (typeof mqtt === "undefined") return H.onFail && H.onFail("ما قدرت أحمّل مكتبة الاتصال. تأكد من النت وجرّب كمان مرة.");
    const url = qs.get("broker") || BROKERS[k % BROKERS.length];
    let ready = false;
    const cl = mqtt.connect(url, { clientId: "k_" + me.id + "_" + Math.random().toString(36).slice(2, 6), reconnectPeriod: 2000, connectTimeout: 8000, clean: true });
    const give = setTimeout(() => {
      if (ready) return;
      try { cl.end(true); } catch {}
      if (k + 1 < BROKERS.length && !qs.get("broker")) tryConnect(k + 1);
      else H.onFail && H.onFail("ما قدرت أتصل. جرّب كمان شوي.");
    }, 9000);
    cl.on("connect", () => {
      const subs = [tp("p/" + me.id)];
      if (host) subs.push(tp("a")); else subs.push(tp("s"));
      cl.subscribe(subs, { qos: 1 });
      if (!ready) { ready = true; clearTimeout(give); c = cl; H.onReady && H.onReady(); }
      else H.onReconnect && H.onReconnect();
    });
    cl.on("message", (t, buf) => {
      const s = buf.toString();
      if (t === tp("s") && !s) { H.onClosed && H.onClosed(); return; }
      let m; try { m = JSON.parse(s); } catch { return; }
      if (t === tp("s")) { if (m.now) offset = m.now - Date.now(); H.onState && H.onState(m); }
      else if (t === tp("a") && host) H.onAction && H.onAction(m);
      else if (t === tp("p/" + me.id)) H.onPrivate && H.onPrivate(m);
    });
  }
  return {
    me,
    now: () => Date.now() + offset,
    get room() { return room; },
    get host() { return host; },
    get on() { return !!c; },
    open(o) { root = o.root; room = o.room; host = !!o.host; H = o; offset = 0; tryConnect(0); },
    publish(S) { S.now = Date.now(); if (c) c.publish(tp("s"), JSON.stringify(S), { qos: 1, retain: true }); },
    send(a) { a.pid = me.id; if (host) H.onAction && H.onAction(a); else if (c) c.publish(tp("a"), JSON.stringify(a), { qos: 1 }); },
    priv(pid, m) { if (pid === me.id) H.onPrivate && H.onPrivate(m); else if (c) c.publish(tp("p/" + pid), JSON.stringify(m), { qos: 1 }); },
    close() {
      try { if (c && host) c.publish(tp("s"), "", { qos: 1, retain: true }); } catch {}
      const x = c; setTimeout(() => { try { x && x.end(true); } catch {} }, 300);
      c = null; room = null; host = false; H = {};
    },
  };
})();

// شاشات مشتركة للغرفة
const KoraUI = {
  newCode: () => String(Math.floor(10000 + Math.random() * 90000)),
  // قائمة الغرفة: اسمك + اعمل غرفة أو ادخل بكود
  roomMenu({ onHost, onJoin, onBack, note }) {
    const pre = new URLSearchParams(location.search).get("room") || "";
    render(`
      <section class="card stack">
        <h2>غرفة أونلاين</h2>
        <p class="sub">${esc(note || "واحد بيعمل غرفة وبيبعت الكود لأصحابه، وكل واحد بيلعب من تلفونه. خلّي تلفون صاحب الغرفة مفتوح لآخر اللعبة.")}</p>
        <div class="label">اسمك</div>
        <input class="input" id="kn" maxlength="14" placeholder="اسمك" value="${esc(KoraNet.me.name)}" autocomplete="off">
        <button class="btn" id="kh">اعمل غرفة جديدة</button>
        <div class="label">أو ادخل غرفة صاحبك</div>
        <div class="row"><input class="input grow" id="kc" inputmode="numeric" maxlength="5" placeholder="كود من 5 أرقام" value="${esc(pre)}" style="letter-spacing:5px;text-align:center"><button class="btn sm" id="kj">ادخل</button></div>
        <p class="msg bad" id="ke"></p>
        <button class="linkish" id="kb">رجوع</button>
      </section>`);
    const nm = () => { const n = $("kn").value.trim(); if (!n) { $("ke").textContent = "اكتب اسمك أول"; return null; } KoraNet.me.name = n; store.set("myname", n); return n; };
    $("kh").onclick = () => { if (nm()) onHost(); };
    $("kj").onclick = () => { if (!nm()) return; const code = $("kc").value.replace(/\D/g, ""); if (code.length !== 5) { $("ke").textContent = "الكود 5 أرقام"; return; } onJoin(code); };
    $("kb").onclick = onBack;
  },
  loading: (m) => render(`<section class="card center"><span class="nuqat" aria-hidden="true"><i></i><i></i></span><p class="sub">${esc(m)}</p></section>`),
  fail(m, back) { render(`<section class="card stack center"><h2>مشكلة بالاتصال</h2><p class="sub">${esc(m)}</p><button class="btn" id="kb">رجوع</button></section>`); $("kb").onclick = back; },
  codeCard(code) {
    const url = location.origin + location.pathname + "?room=" + code;
    setTimeout(() => {
      const b = $("kshare"); if (!b) return;
      b.onclick = async () => {
        try { if (navigator.share) { await navigator.share({ title: document.title, text: "ادخل غرفتي بتعليلة: " + code, url }); return; } } catch { return; }
        try { await navigator.clipboard.writeText(url); b.textContent = "انسخ الرابط ✓"; } catch {}
      };
    }, 0);
    return `<section class="card center kcode"><span class="label">كود الغرفة</span><b>${code}</b><button class="btn alt sm" id="kshare">ابعت الرابط لأصحابك</button></section>`;
  },
  players(list, hostId, extra = () => "") {
    return `<ul class="klist">${list.map((p) => `<li>${av(p.name)}<span>${esc(p.name)}</span>${p.id === hostId ? `<small>صاحب الغرفة</small>` : ""}${extra(p)}</li>`).join("")}</ul>`;
  },
};

// ---------- لعبة أسئلة بخيارات ----------
function KORA(cfg) {
  const SECS = cfg.secs || 20;
  const COUNTS = [10, 15, 20];
  let POOL = null, L = null, S = null, P = null, tick = null, hostT = null, rewarded = false;
  const net = KoraNet;
  window.leaveGuard = () => ((L && L.phase !== "end") || (S && S.phase !== "end" && S.phase !== "lobby") ? "اللعبة شغّالة، بدك تطلع؟" : false);

  async function pool() {
    if (POOL) return POOL;
    POOL = (await cfg.load()).filter((q) => q && q.opts && q.opts.length === 4 && new Set(q.opts).size === 4);
    return POOL;
  }
  function deal(n) {
    // بنحاول نوزّع الصعوبة: سهل بالأول وصعب بالآخر
    const seen = store.get("seen-" + cfg.id, []);
    const fresh = POOL.filter((q) => !seen.includes(q.q + (q.vis || "").length));
    const src = fresh.length >= n ? fresh : POOL;
    const picked = shuffle(src).slice(0, n).sort((a, b) => (a.d || 2) - (b.d || 2));
    store.set("seen-" + cfg.id, seen.concat(picked.map((q) => q.q + (q.vis || "").length)).slice(-400));
    return picked.map((q) => {
      const order = q.fixed ? [0, 1, 2, 3] : shuffle([0, 1, 2, 3]);
      return { q: q.q, opts: order.map((k) => q.opts[k]), c: q.fixed ? (q.c || 0) : order.indexOf(0), vis: q.vis || "", rev: q.rev || "", hints: q.hints || null, fixed: !!q.fixed };
    });
  }

  // ---------- الإعداد ----------
  let mode = new URLSearchParams(location.search).get("room") ? "room" : store.get("kmode", "one");
  let cnt = store.get("kcnt", 3), qn = store.get("kqn-" + cfg.id, 10);
  function setup() {
    clearInterval(tick); clearTimeout(hostT); L = null;
    if (mode === "room") return KoraUI.roomMenu({ onHost: () => hostRoom(), onJoin: (c) => joinRoom(c), onBack: () => { mode = "one"; store.set("kmode", "one"); history.replaceState(null, "", location.pathname); setup(); } });
    render(`
      <section class="card stack">
        <h1>${esc(cfg.title)}</h1>
        <p class="sub">${esc(cfg.desc)}</p>
        <div class="seg" id="md"><button data-m="one" aria-pressed="true">تلفون واحد</button><button data-m="room" aria-pressed="false">غرفة أونلاين</button></div>
        <div class="label">عدد اللاعبين</div>
        <div class="seg" id="cnt">${[1, 2, 3, 4, 5, 6].map((k) => `<button data-n="${k}" aria-pressed="${k === cnt}">${k === 1 ? "لحالي" : k}</button>`).join("")}</div>
        <div class="stack" id="names">${nameFields(cnt, store.get("knames", []))}</div>
        <div class="label">عدد الأسئلة</div>
        <div class="seg" id="qn">${COUNTS.map((k) => `<button data-q="${k}" aria-pressed="${k === qn}">${k}</button>`).join("")}</div>
        <button class="btn" id="go">يلا نلعب</button>
      </section>`);
    $("md").onclick = (e) => { const b = e.target.closest("[data-m]"); if (!b) return; mode = b.dataset.m; store.set("kmode", mode); setup(); };
    $("cnt").onclick = (e) => { const b = e.target.closest("[data-n]"); if (!b) return; store.set("knames", readNames(cnt)); cnt = +b.dataset.n; store.set("kcnt", cnt); setup(); };
    $("qn").onclick = (e) => { const b = e.target.closest("[data-q]"); if (!b) return; qn = +b.dataset.q; store.set("kqn-" + cfg.id, qn); setup(); };
    $("go").onclick = async () => {
      const names = readNames(cnt); store.set("knames", names);
      $("go").disabled = true; $("go").textContent = "لحظة...";
      try { await pool(); } catch { $("go").disabled = false; $("go").textContent = "ما انحمّلت الأسئلة، جرّب كمان مرة"; return; }
      startLocal(names);
    };
  }

  // ---------- رسم السؤال (مشترك) ----------
  function qHTML(q, o) {
    // o: { head, pick, reveal, locked, wait }
    const st = (i) => (o.reveal ? (i === q.c ? "right" : i === o.pick ? "wrong" : "dim") : i === o.pick ? "picked" : "");
    return `${o.head || ""}
      <div class="kbar"><i id="kbar" style="width:${o.reveal ? 0 : 100}%"></i></div>
      <section class="card kq pop">
        ${q.vis ? `<div class="kvis">${o.reveal && q.rev ? q.rev : q.vis}</div>` : ""}
        ${q.hints ? `<ol class="khints" id="khints">${hintsHTML(q, o.reveal ? q.hints.length : o.shown || 1)}</ol>` : ""}
        <p class="kqt">${esc(q.q)}</p>
      </section>
      <div class="kopts ${q.fixed ? "four" : ""}">${q.opts.map((t, i) => `<button class="kopt ${st(i)}" data-i="${i}" ${o.locked || o.reveal ? "disabled" : ""}>${esc(t)}</button>`).join("")}</div>
      ${o.foot || ""}`;
  }
  const hintsHTML = (q, n) => q.hints.slice(0, n).map((h, i) => `<li class="pop"><span>${i + 1}</span>${esc(h)}</li>`).join("");
  // عدّاد: بيحرّك الشريط وبيكشف التلميحات، وبينادي done لما يخلص
  function runTimer(q, startAt, dur, done) {
    clearInterval(tick);
    let shown = 1, fired = false;
    const step = () => {
      const left = Math.max(0, startAt + dur - (net.on ? net.now() : Date.now()));
      const b = $("kbar"); if (b) b.style.width = (left / dur) * 100 + "%";
      if (q.hints) {
        const want = Math.min(q.hints.length, 1 + Math.floor(((dur - left) / dur) * q.hints.length));
        if (want !== shown) { shown = want; const h = $("khints"); if (h) h.innerHTML = hintsHTML(q, shown); }
      }
      if (left <= 3000 && left > 0 && Math.floor(left / 1000) !== Math.floor((left + 120) / 1000)) beep(520, 50);
      if (left <= 0 && !fired) { fired = true; clearInterval(tick); done && done(); }
    };
    step(); tick = setInterval(step, 120);
    return () => shown;
  }
  const gainFor = (left, dur, hintsShown, hints) => {
    const speed = Math.round((left / dur) * 10);
    return hints ? Math.max(4, 10 + speed - (hintsShown - 1) * 3) : 10 + speed;
  };

  // ---------- تلفون واحد ----------
  function startLocal(names) {
    L = { names, pts: names.map(() => 0), qs: deal(qn), i: -1, phase: "q" };
    rewarded = false;
    nextLocal();
  }
  function podsLocal(turn) {
    if (L.names.length === 1) return `<div class="kscore"><span>نقاطك</span><b>${L.pts[0]}</b></div>`;
    return `<div class="pods">${L.names.map((n, i) => `<div class="pod ${i === turn ? "turn" : ""}">${av(n)}<div><small>${esc(n)}</small><b>${L.pts[i]}</b></div></div>`).join("")}</div>`;
  }
  function nextLocal() {
    L.i++;
    if (L.i >= L.qs.length) return endLocal();
    const q = L.qs[L.i], turn = L.i % L.names.length;
    const t0 = Date.now(), dur = SECS * 1000;
    const head = `${podsLocal(turn)}<div class="kmeta"><span>${L.names.length > 1 ? `دور <b>${esc(L.names[turn])}</b>` : "جاوب بسرعة"}</span><span>سؤال ${L.i + 1} من ${L.qs.length}</span></div>`;
    render(qHTML(q, { head }));
    const shown = runTimer(q, t0, dur, () => answerLocal(-1));
    document.querySelectorAll(".kopt").forEach((b) => (b.onclick = () => answerLocal(+b.dataset.i)));
    L.cur = { t0, dur, shown, turn };
  }
  function answerLocal(i) {
    clearInterval(tick);
    const q = L.qs[L.i], { t0, dur, shown, turn } = L.cur;
    const ok = i === q.c;
    const g = ok ? gainFor(Math.max(0, t0 + dur - Date.now()), dur, shown(), q.hints) : 0;
    L.pts[turn] += g;
    beep(ok ? 880 : 240, 180, ok ? "sine" : "square");
    const msg = ok ? `صح! +${g}` : i < 0 ? `خلص الوقت. الجواب: ${q.opts[q.c]}` : `غلط. الجواب: ${q.opts[q.c]}`;
    render(qHTML(q, { head: `${podsLocal(turn)}<div class="kmeta"><span>سؤال ${L.i + 1} من ${L.qs.length}</span></div>`, pick: i, reveal: true,
      foot: `<p class="msg ${ok ? "good" : "bad"}">${esc(msg)}</p><button class="btn" id="nx">${L.i + 1 >= L.qs.length ? "النتيجة" : "التالي"}</button>` }));
    $("nx").onclick = nextLocal;
  }
  function endLocal() {
    L.phase = "end";
    const list = L.names.map((name, i) => ({ name, score: L.pts[i] })).sort((a, b) => b.score - a.score);
    let best = "";
    if (L.names.length === 1) { const b = Math.max(store.get("best-" + cfg.id, 0), L.pts[0]); store.set("best-" + cfg.id, b); best = `<span class="sub">أفضل نتيجة: ${b}</span>`; }
    render(`
      <section class="banner gold pop"><b>${L.names.length === 1 ? `${L.pts[0]} نقطة` : winnerLine(list)}</b>${best}</section>
      ${L.names.length > 1 ? standingsHTML(list, "نقطة") : ""}
      <button class="btn" id="again">العب مرة ثانية</button>
      <button class="btn alt" id="menu">تغيير الإعدادات</button>`);
    if (!rewarded) { rewarded = true; try { Rewards.finish(cfg.id, Math.min(60, Math.round(list[0].score / 5))); } catch {} }
    $("again").onclick = () => startLocal(L.names);
    $("menu").onclick = setup;
  }

  // ---------- غرفة ----------
  const ROOT = "abuodeh-" + cfg.id + "-v1";
  function leave() {
    clearInterval(tick); clearTimeout(hostT);
    net.close(); S = null; P = null;
    store.set("kroom-" + cfg.id, null);
    history.replaceState(null, "", location.pathname);
    mode = "one"; setup();
  }
  async function hostRoom() {
    KoraUI.loading("عم بحضّر الأسئلة...");
    try { await pool(); } catch { return KoraUI.fail("ما انحمّلت الأسئلة.", setup); }
    const room = KoraUI.newCode();
    KoraUI.loading("عم بفتح الغرفة...");
    net.open({
      root: ROOT, room, host: true,
      onFail: (m) => KoraUI.fail(m, leave),
      onReady: () => {
        S = { phase: "lobby", room, host: net.me.id, players: [{ id: net.me.id, name: net.me.name, score: 0 }], i: 0, n: qn };
        P = { qs: [], ans: {} };
        pub();
      },
      onReconnect: () => pub(),
      onAction,
    });
  }
  function joinRoom(code) {
    KoraUI.loading("عم بدخل الغرفة...");
    let got = false;
    net.open({
      root: ROOT, room: code, host: false,
      onFail: (m) => KoraUI.fail(m, leave),
      onReady: () => { net.send({ t: "join", name: net.me.name }); setTimeout(() => { if (!got) KoraUI.fail("ما لقيت الغرفة. تأكد من الكود، وإنه تلفون صاحب الغرفة مفتوح.", leave); }, 8000); },
      onReconnect: () => net.send({ t: "join", name: net.me.name }),
      onClosed: () => { if (S && S.phase !== "end") KoraUI.fail("صاحب الغرفة سكّرها.", leave); },
      onState: (m) => { got = true; onState(m); },
    });
  }
  function pub() { net.publish(S); onState(S); }
  function onAction(a) {
    if (!S) return;
    const i = S.players.findIndex((p) => p.id === a.pid);
    if (a.t === "join") {
      if (i < 0) { if (S.players.length >= 10) return; let n = String(a.name || "لاعب").slice(0, 14); while (S.players.some((p) => p.name === n)) n += "+"; S.players.push({ id: a.pid, name: n, score: 0 }); }
      return pub();
    }
    if (a.t === "start" && a.pid === S.host && S.phase === "lobby") {
      P.qs = deal(S.n); S.players.forEach((p) => (p.score = 0)); S.i = -1; S.last = null; return hostNext();
    }
    if (a.t === "ans" && S.phase === "q" && i >= 0 && P.ans[a.pid] == null) {
      P.ans[a.pid] = { i: +a.i, at: Date.now(), shown: Math.max(1, +a.shown || 1) };
      S.got = Object.keys(P.ans);
      if (S.got.length >= S.players.length) return hostReveal();
      return pub();
    }
    if (a.t === "next" && a.pid === S.host && S.phase === "rev") return hostNext();
    if (a.t === "again" && a.pid === S.host && S.phase === "end") { S.phase = "lobby"; S.players.forEach((p) => (p.score = 0)); return pub(); }
  }
  function hostNext() {
    clearTimeout(hostT);
    S.i++;
    if (S.i >= P.qs.length) { S.phase = "end"; S.q = null; return pub(); }
    const q = P.qs[S.i];
    P.ans = {}; S.got = [];
    S.phase = "q"; S.q = { q: q.q, opts: q.opts, vis: q.vis, hints: q.hints, fixed: q.fixed }; S.start = Date.now() + 600; S.dur = SECS * 1000; S.last = null;
    pub();
    hostT = setTimeout(hostReveal, S.dur + 900);
  }
  function hostReveal() {
    clearTimeout(hostT);
    if (S.phase !== "q") return;
    const q = P.qs[S.i], gains = {}, picks = {};
    S.players.forEach((p) => {
      const a = P.ans[p.id]; picks[p.id] = a ? a.i : -1;
      const g = a && a.i === q.c ? gainFor(Math.max(0, S.start + S.dur - a.at), S.dur, a.shown, q.hints) : 0;
      gains[p.id] = g; p.score += g;
    });
    S.phase = "rev"; S.last = { c: q.c, picks, gains, rev: q.rev };
    pub();
    hostT = setTimeout(hostNext, 5500);
  }
  let lastKey = "";
  function onState(m) {
    S = m;
    store.set("kroom-" + cfg.id, { room: net.room, at: Date.now() });
    const host = net.host;
    const key = m.phase + ":" + m.i;
    if (m.phase === "lobby") {
      clearInterval(tick); lastKey = key;
      render(`${KoraUI.codeCard(net.room)}
        <section class="card stack"><div class="kmeta"><span>اللاعبين (${m.players.length})</span><span>${m.n} سؤال</span></div>${KoraUI.players(m.players, m.host)}</section>
        ${host ? `<button class="btn" id="st" ${m.players.length < 2 ? "disabled" : ""}>${m.players.length < 2 ? "استنى حدا يدخل..." : "ابدأ اللعبة"}</button>` : `<p class="note">استنى صاحب الغرفة يبدأ...</p>`}
        <button class="linkish" id="lv">اطلع من الغرفة</button>`);
      if ($("st")) $("st").onclick = () => net.send({ t: "start" });
      $("lv").onclick = leave;
      return;
    }
    if (m.phase === "q") {
      const answered = (m.got || []).includes(net.me.id);
      const head = `${roomPods(m)}<div class="kmeta"><span>سؤال ${m.i + 1} من ${m.n}</span><span>جاوب ${(m.got || []).length} من ${m.players.length}</span></div>`;
      if (key === lastKey && $("kbar")) {
        // نفس السؤال: بس حدّث مين جاوب
        const h = document.querySelector(".kmeta span:last-child"); if (h) h.textContent = `جاوب ${(m.got || []).length} من ${m.players.length}`;
        const pd = document.querySelector(".pods"); if (pd) pd.outerHTML = roomPods(m);
        return;
      }
      lastKey = key;
      const q = m.q; const mine = { pick: null };
      render(qHTML(q, { head, locked: answered, foot: `<p class="note" id="kw">${answered ? "استنى الباقي..." : ""}</p>` }));
      const shown = runTimer(q, m.start, m.dur, null);
      document.querySelectorAll(".kopt").forEach((b) => (b.onclick = () => {
        if (mine.pick != null) return;
        mine.pick = +b.dataset.i; b.classList.add("picked");
        document.querySelectorAll(".kopt").forEach((x) => (x.disabled = true));
        $("kw").textContent = "استنى الباقي...";
        net.send({ t: "ans", i: mine.pick, shown: shown() });
      }));
      return;
    }
    if (m.phase === "rev") {
      clearInterval(tick);
      if (key + "r" === lastKey) return; lastKey = key + "r";
      const q = Object.assign({}, m.q, { c: m.last.c, rev: m.last.rev });
      const mp = m.last.picks[net.me.id], g = m.last.gains[net.me.id] || 0;
      const ok = mp === m.last.c;
      beep(ok ? 880 : 240, 180, ok ? "sine" : "square");
      const gl = m.players.slice().sort((a, b) => b.score - a.score).map((p) => `<li>${av(p.name)}<span>${esc(p.name)}</span>${m.last.gains[p.id] ? `<em>+${m.last.gains[p.id]}</em>` : `<em class="z">0</em>`}<b>${p.score}</b></li>`).join("");
      render(qHTML(q, { head: `<div class="kmeta"><span>سؤال ${m.i + 1} من ${m.n}</span></div>`, pick: mp, reveal: true,
        foot: `<p class="msg ${ok ? "good" : "bad"}">${ok ? `صح! +${g}` : mp < 0 || mp == null ? "ما جاوبت" : "غلط"}</p><ul class="klist score">${gl}</ul>${net.host ? `<button class="btn" id="nx">التالي</button>` : ""}` }));
      if ($("nx")) $("nx").onclick = () => net.send({ t: "next" });
      return;
    }
    if (m.phase === "end") {
      clearInterval(tick);
      if (lastKey === "end") return; lastKey = "end";
      const list = m.players.map((p) => ({ name: p.name, score: p.score })).sort((a, b) => b.score - a.score);
      const mine = (m.players.find((p) => p.id === net.me.id) || {}).score || 0;
      try { Rewards.finish(cfg.id, Math.min(60, Math.round(mine / 5))); } catch {}
      render(`<section class="banner gold pop"><b>${winnerLine(list)}</b></section>${standingsHTML(list, "نقطة")}
        ${net.host ? `<button class="btn" id="ag">جولة جديدة بنفس الغرفة</button>` : `<p class="note">صاحب الغرفة ممكن يبدأ جولة جديدة.</p>`}
        <button class="btn alt" id="lv">اطلع</button>`);
      if ($("ag")) $("ag").onclick = () => net.send({ t: "again" });
      $("lv").onclick = leave;
    }
  }
  const roomPods = (m) => `<div class="pods">${m.players.map((p) => `<div class="pod ${(m.got || []).includes(p.id) ? "turn" : ""}">${av(p.name)}<div><small>${esc(p.name)}</small><b>${p.score}</b></div></div>`).join("")}</div>`;

  setup();
}

// ---------- أدوات بيانات ----------
// أسئلة من بنك «جمع نقاط» (points_q.json) حسب الأقسام، مع فلتر اختياري على نص السؤال
async function koraFromPoints(cats, filter) {
  const r = await fetch("points_q.json?t=" + Math.floor(Date.now() / 3.6e6));
  if (!r.ok) throw new Error("load");
  const d = await r.json();
  const out = [];
  for (const c of d.cats) {
    const want = cats[c.id];
    if (!want) continue;
    for (const [dd, q, opts, img] of c.qs) {
      if (want !== true && !want.test(q + " " + opts[0])) continue;
      if (filter && !filter(q, opts)) continue;
      out.push({ d: dd, q, opts, vis: img ? `<img src="${esc(img)}" alt="" loading="eager" onerror="this.closest('.kvis').classList.add('nopic')">` : "" });
    }
  }
  return out;
}
let _players = null;
async function koraPlayers() {
  if (_players) return _players;
  const r = await fetch("players.json?t=" + Math.floor(Date.now() / 3.6e6));
  if (!r.ok) throw new Error("load");
  _players = (await r.json()).players.filter((p) => p.a && !/[A-Za-z]/.test(p.a));
  return _players;
}
// 3 لاعبين غلط قريبين من اللاعب (نفس المستوى، ويفضّل نفس المركز)
function koraDecoys(p, all) {
  const same = all.filter((x) => x.id !== p.id && x.a !== p.a && x.lv <= Math.max(2, p.lv) && (x.pos || [])[0] === (p.pos || [])[0]);
  const rest = all.filter((x) => x.id !== p.id && x.a !== p.a && x.lv <= Math.max(2, p.lv));
  const out = [];
  for (const x of shuffle(same).concat(shuffle(rest))) { if (!out.includes(x.a)) out.push(x.a); if (out.length === 3) break; }
  return out;
}
