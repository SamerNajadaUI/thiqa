// الرقم الأقرب أونلاين: كل واحد من تلفونه.
// صاحب الغرفة هو اللي بيمسك اللعبة: بيختار السؤال، وبيخبّي الجواب لحد الكشف، وبيحسب النقاط.
// التواصل عبر وسيط MQTT عام ومجاني (ما بدو حساب)، وكل غرفة إلها كود من 5 أرقام.
/* global mqtt, QUESTIONS, render, bind, esc, store, parseNum, fmt, intro */
(function () {
  const Q_MS = 40000;
  const MAX_PLAYERS = 8;
  const BROKERS = ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081/mqtt"];
  const ROOT = "abuodeh-near-v1";
  const PCOL = ["#F04438", "#0BA5EC", "#12B76A", "#F79009", "#7A5AF8", "#EE46BC", "#0E9384", "#475467"];
  const qs = new URLSearchParams(location.search);
  const $ = (id) => document.getElementById(id);

  let client = null, room = null, isHost = false, S = null, offset = 0, ticker = null, hostTimer = null;
  let P = null;   // أسرار المضيف: الجواب الحالي وأرقام اللاعبين لحد الكشف
  const me = { id: store.get("pid", null), name: store.get("myname", "") };
  if (!me.id) { me.id = Math.random().toString(36).slice(2, 10); store.set("pid", me.id); }

  const topic = (k) => `${ROOT}/${room}/${k}`;
  const now = () => Date.now() + offset;
  const myIndex = () => (S ? S.players.findIndex((p) => p.id === me.id) : -1);
  const chip = (i) => `<span class="tchip" style="background:${PCOL[i % PCOL.length]}"></span>`;
  const loading = (m) => render(`<div class="loading" style="text-align:center;padding:40px 0">${esc(m)}</div>`);

  // ---------- الاتصال ----------
  function connect(onReady, k = 0) {
    if (typeof mqtt === "undefined") { fail("ما قدرت أحمّل مكتبة الاتصال. تأكد من الإنترنت وجرّب كمان مرة."); return; }
    const url = qs.get("broker") || BROKERS[k % BROKERS.length];
    let ready = false;
    const c = mqtt.connect(url, { clientId: "an_" + me.id + "_" + Math.random().toString(36).slice(2, 6), reconnectPeriod: 2000, connectTimeout: 8000, clean: true });
    const giveUp = setTimeout(() => { if (!ready) { c.end(true); if (k + 1 < BROKERS.length && !qs.get("broker")) connect(onReady, k + 1); else fail("ما قدرت أتصل. جرّب كمان شوي."); } }, 9000);
    c.on("connect", () => {
      if (!ready) { ready = true; clearTimeout(giveUp); client = c; onReady(); }
      else if (room) { c.subscribe(topic("s"), { qos: 1 }); if (isHost) { c.subscribe(topic("a"), { qos: 1 }); publish(); } else send({ t: "join", name: me.name }); }
    });
    c.on("message", (t, buf) => {
      let m; try { m = JSON.parse(buf.toString()); } catch { return; }
      if (t === topic("s")) onState(m);
      else if (t === topic("a") && isHost) onAction(m);
    });
  }
  function fail(msg) {
    render(`<h1>مشكلة بالاتصال</h1><p class="note">${esc(msg)}</p><button class="big" id="back" type="button">رجوع</button>`);
    bind({ back: leave });
  }

  // ---------- القائمة ----------
  window.nearOnlineMenu = function (prefill = qs.get("room") || "") {
    render(`<h1>كل واحد من تلفونه</h1>
      <p class="note">واحد بيعمل غرفة وبيبعت الكود لأصحابه، والباقي بيدخلوا بالكود. كل تلفون لاعب (أو فريق). تلفون صاحب الغرفة لازم يضل مفتوح لآخر اللعبة.</p>
      <div class="card"><h2>اسمك</h2>
        <div class="teams"><input id="myname" type="text" maxlength="16" placeholder="اسمك أو اسم فريقك" value="${esc(me.name)}" autocomplete="off"></div></div>
      <button class="big" id="create" type="button">اعمل غرفة جديدة</button>
      <div class="card"><h2>أو ادخل غرفة صاحبك</h2>
        <input class="numin" id="code" type="text" inputmode="numeric" maxlength="5" placeholder="كود الغرفة" value="${esc(prefill)}" autocomplete="off" style="letter-spacing:6px"></div>
      <p class="note" id="err" hidden></p>
      <button class="big" id="join" type="button" style="background:#12B76A;box-shadow:0 6px 0 #087443">ادخل</button>
      <button class="big ghost" id="back" type="button">رجوع</button>`);
    const getName = () => {
      const n = $("myname").value.trim();
      if (!n) { $("err").hidden = false; $("err").textContent = "اكتب اسمك أول."; return null; }
      me.name = n; store.set("myname", n); return n;
    };
    bind({
      create: () => { if (getName()) hostRoom(); },
      join: () => {
        if (!getName()) return;
        const code = parseNum($("code").value);
        if (!code || String(code).length !== 5) { $("err").hidden = false; $("err").textContent = "الكود 5 أرقام."; return; }
        joinRoom(String(code));
      },
      back: leave,
    });
  };

  window.nearOnlineBoot = function () {
    if (qs.get("room")) { nearOnlineMenu(qs.get("room")); return true; }
    const saved = store.get("online", null);
    if (saved && saved.room && Date.now() - (saved.at || 0) < 6 * 3600e3) {
      render(`<h1>في لعبة أونلاين مفتوحة</h1><p class="note">الغرفة ${esc(saved.room)}${saved.host ? " (إنت صاحبها)" : ""}.</p>
        <button class="big" id="re" type="button">ارجع للعبة</button><button class="big ghost" id="no" type="button">لا، طلّعني</button>`);
      bind({
        re: () => { if (saved.host) hostRoom(saved.room, store.get("hoststate-" + saved.room, null)); else joinRoom(saved.room); },
        no: () => { store.set("online", null); intro(); },
      });
      return true;
    }
    return false;
  };

  function leave() {
    try { if (client && isHost && room) client.publish(topic("s"), "", { qos: 1, retain: true }); } catch {}
    const c = client;
    setTimeout(() => { try { c && c.end(true); } catch {} }, 300);
    client = null; room = null; S = null; P = null; isHost = false;
    clearInterval(ticker); clearTimeout(hostTimer);
    store.set("online", null);
    history.replaceState(null, "", location.pathname);
    intro();
  }

  // ---------- المضيف ----------
  function hostRoom(code, restored) {
    isHost = true;
    room = code || String(Math.floor(10000 + Math.random() * 90000));
    store.set("online", { room, host: true, at: Date.now() });
    loading("عم بفتح الغرفة...");
    connect(() => {
      client.subscribe([topic("s"), topic("a")], { qos: 1 });
      if (restored) { S = restored.S; P = restored.P; }
      else {
        S = { v: 0, room, host: me.id, phase: "lobby", round: 0, players: [{ id: me.id, name: me.name, score: 0 }], cats: [], done: [] };
        P = { used: [], ans: null, guesses: {} };
      }
      publish();
      if (S.phase === "q") armTimer();
    });
  }

  function publish() {
    S.v++; S.now = Date.now();
    store.set("hoststate-" + room, { S, P });
    store.set("online", { room, host: true, at: Date.now() });
    client.publish(topic("s"), JSON.stringify(S), { qos: 1, retain: true });
    onState(S);
  }

  function onAction(a) {
    if (!S || !a || !a.pid) return;
    const i = S.players.findIndex((p) => p.id === a.pid);
    const host = a.pid === S.host;
    switch (a.t) {
      case "join":
        if (i >= 0) { if (a.name) S.players[i].name = a.name; return publish(); }
        if (S.players.length >= MAX_PLAYERS) return publish();
        S.players.push({ id: a.pid, name: uniqueName(a.name), score: 0 });
        return publish();
      case "kick":
        if (!host) return;
        S.players = S.players.filter((p) => p.id !== a.who);
        return publish();
      case "cat":
        if (!host || S.phase !== "lobby") return;
        S.cats = S.cats.includes(a.c) ? S.cats.filter((x) => x !== a.c) : [...S.cats, a.c];
        return publish();
      case "start":
        if (!host || S.players.length < 2) return;
        return nextQuestion();
      case "guess":
        if (S.phase !== "q" || i < 0 || P.guesses[a.pid] !== undefined) return;
        if (typeof a.n !== "number" || !Number.isFinite(a.n)) return;
        P.guesses[a.pid] = a.n;
        S.done = Object.keys(P.guesses);
        if (S.players.every((p) => P.guesses[p.id] !== undefined)) return reveal();
        return publish();
      case "reveal":
        if (!host || S.phase !== "q") return;
        return reveal();
      case "next":
        if (!host || S.phase !== "reveal") return;
        return nextQuestion();
      case "end":
        if (!host) return;
        clearTimeout(hostTimer);
        S.phase = "over"; S.deadline = null;
        return publish();
      case "again":
        if (!host) return;
        S.players.forEach((p) => { p.score = 0; });
        S.round = 0; S.phase = "lobby"; S.last = null; S.q = null;
        return publish();
    }
  }

  function uniqueName(n) {
    let name = String(n || "لاعب").slice(0, 16), k = 2;
    while (S.players.some((p) => p.name === name)) name = `${String(n).slice(0, 14)} ${k++}`;
    return name;
  }

  function nextQuestion() {
    const cats = S.cats.length ? S.cats : Object.keys(QUESTIONS);
    const pool = cats.flatMap((c) => QUESTIONS[c].map((q) => ({ c, q })));
    let fresh = pool.filter((x) => !P.used.includes(x.q[0]));
    if (!fresh.length) { P.used = []; fresh = pool; }
    const pick = fresh[Math.floor(Math.random() * fresh.length)];
    P.used.push(pick.q[0]);
    P.ans = pick.q[1]; P.guesses = {};
    S.round++;
    S.q = { c: pick.c, text: pick.q[0], unit: pick.q[2] };
    S.note = pick.q[3];
    S.phase = "q"; S.done = []; S.last = null;
    S.deadline = Date.now() + Q_MS;
    armTimer();
    publish();
  }

  function armTimer() {
    clearTimeout(hostTimer);
    const r = S.round;
    hostTimer = setTimeout(() => { if (S && S.phase === "q" && S.round === r) reveal(); }, Math.max(0, S.deadline - Date.now()) + 300);
  }

  function reveal() {
    clearTimeout(hostTimer);
    const ans = P.ans;
    const rows = S.players.map((p) => {
      const g = P.guesses[p.id];
      return { id: p.id, g: g === undefined ? null : g, d: g === undefined ? null : Math.abs(g - ans) };
    });
    const ds = rows.filter((r) => r.d !== null).map((r) => r.d);
    const best = ds.length ? Math.min(...ds) : null;
    rows.forEach((r) => { r.pts = r.d !== null && r.d === best ? (r.d === 0 ? 2 : 1) : 0; });
    rows.forEach((r) => { const p = S.players.find((x) => x.id === r.id); if (p) p.score += r.pts; });
    S.last = { ans, note: S.note, rows };
    S.phase = "reveal"; S.deadline = null;
    publish();
  }

  // ---------- اللاعب ----------
  function joinRoom(code) {
    isHost = false; room = code;
    store.set("online", { room, host: false, at: Date.now() });
    loading("عم بدخل الغرفة...");
    connect(() => {
      client.subscribe(topic("s"), { qos: 1 });
      send({ t: "join", name: me.name });
      setTimeout(() => {
        if (S) return;
        render(`<h1>ما في رد من الغرفة ${esc(room)}</h1><p class="note">تأكد من الكود، وإنه تلفون صاحب الغرفة مفتوح على اللعبة.</p>
          <button class="big" id="again" type="button">جرّب كمان مرة</button><button class="big ghost" id="back" type="button">رجوع</button>`);
        bind({ again: () => send({ t: "join", name: me.name }), back: leave });
      }, 6000);
    });
  }

  function send(a) {
    a.pid = me.id;
    if (isHost) { onAction(a); return; }
    if (client) client.publish(topic("a"), JSON.stringify(a), { qos: 1 });
  }

  let typed = "";   // الرقم اللي اللاعب عم يكتبه، عشان ما يضيع لما تتحدث الشاشة
  function onState(st) {
    if (!st || st.room !== room) return;
    if (!isHost && st.now && Date.now() - st.now > 6 * 3600e3) return;
    if (S && st !== S && st.host === S.host && st.v <= S.v) return;
    const prevRound = S && S.round, prevPhase = S && S.phase;
    S = st;
    offset = (st.now || Date.now()) - Date.now();
    if (S.round !== prevRound) typed = "";
    // لو اللاعب عم يكتب رقمه وما تغيّر غير مين جاوب، بنحدّث القائمة بس
    if (S.phase === "q" && prevPhase === "q" && S.round === prevRound && $("num")) {
      if ($("whoDone")) $("whoDone").innerHTML = whoDone();
      return;
    }
    draw();
  }

  function header() {
    return `<p class="note" style="text-align:center">الغرفة <b style="letter-spacing:3px">${esc(room)}</b>${S.round ? ` · السؤال ${S.round}` : ""}</p>`;
  }

  function board(delta) {
    const order = S.players.map((_, i) => i).sort((a, b) => S.players[b].score - S.players[a].score);
    return `<div class="score">${order.map((i, k) => { const p = S.players[i]; const d = delta ? delta[p.id] || 0 : null;
      return `<div class="r"><span class="pos">${k + 1}</span><span class="nm">${chip(i)}${esc(p.name)}${p.id === me.id ? " (إنت)" : ""}</span><span class="d ${d ? "p" : "z"}">${d === null ? "" : d ? "+" + d : "0"}</span><span class="t">${p.score}</span></div>`; }).join("")}</div>`;
  }

  function whoDone() {
    return S.players.map((p, i) => `<span style="display:inline-flex;align-items:center;gap:4px;margin:2px 6px">${chip(i)}${esc(p.name)} ${S.done.includes(p.id) ? "✓" : "…"}</span>`).join("");
  }

  function draw() {
    clearInterval(ticker);
    if (!isHost && myIndex() < 0) {
      render(`${header()}<h1>مش موجود بالغرفة</h1><p class="note">يمكن الغرفة مليانة (${MAX_PLAYERS} لاعبين) أو صاحبها شالك.</p><button class="big ghost" id="back" type="button">رجوع</button>`);
      bind({ back: leave }); return;
    }
    if (S.phase === "lobby") return drawLobby();
    if (S.phase === "q") return drawQuestion();
    if (S.phase === "reveal") return drawReveal();
    return drawOver();
  }

  function drawLobby() {
    const link = location.origin + location.pathname + "?room=" + room;
    const cats = Object.keys(QUESTIONS);
    render(`${header()}<h1>الغرفة ${esc(room)}</h1>
      <p class="note">${isHost ? "ابعت الكود أو الرابط لأصحابك، واختار الأقسام، وبعدين ابدأ." : "استنى صاحب الغرفة يبدأ."}</p>
      ${isHost ? `<button class="big ghost" id="share" type="button">ابعت رابط الغرفة</button>` : ""}
      <div class="card"><h2>اللاعبين (${S.players.length} من ${MAX_PLAYERS})</h2>
        <div class="score">${S.players.map((p, i) => `<div class="r" style="grid-template-columns:minmax(0,1fr) auto"><span class="nm">${chip(i)}${esc(p.name)}${p.id === S.host ? " · صاحب الغرفة" : ""}${p.id === me.id ? " (إنت)" : ""}</span>${isHost && p.id !== me.id ? `<button type="button" class="back" data-kick="${p.id}" style="border:0;background:#FFF;border-radius:12px;padding:6px 10px">شيل</button>` : "<span></span>"}</div>`).join("")}</div></div>
      <div class="card"><h2>الأقسام</h2><p class="note">${S.cats.length ? "" : "ما في إشي مختار، يعني الأسئلة من كل الأقسام."}</p>
        <div class="cats">${cats.map((c) => `<button type="button" data-cat="${esc(c)}" aria-pressed="${S.cats.includes(c)}" ${isHost ? "" : "disabled"}>${esc(c)} (${QUESTIONS[c].length})</button>`).join("")}</div></div>
      ${isHost ? `<button class="big" id="start" type="button" ${S.players.length < 2 ? "disabled" : ""}>${S.players.length < 2 ? "استنى حدا يدخل" : "ابدأ اللعبة"}</button>` : ""}
      <button class="big ghost" id="out" type="button">اطلع من الغرفة</button>`);
    bind({
      start: () => send({ t: "start" }),
      out: confirmLeave,
      share: async () => {
        const text = `تعال العب معي "الرقم الأقرب"، كود الغرفة ${room}`;
        try { if (navigator.share) { await navigator.share({ title: "الرقم الأقرب", text, url: link }); return; } } catch { return; }
        try { await navigator.clipboard.writeText(text + "\n" + link); $("share").textContent = "انسخ الرابط ✓"; } catch {}
      },
    });
    document.querySelectorAll("[data-kick]").forEach((b) => b.onclick = () => send({ t: "kick", who: b.dataset.kick }));
    if (isHost) document.querySelectorAll("[data-cat]").forEach((b) => b.onclick = () => send({ t: "cat", c: b.dataset.cat }));
  }

  const qCard = () => `<div class="q"><small>السؤال ${S.round} · ${esc(S.q.c)}</small><b>${esc(S.q.text)}</b>${S.q.unit ? `<span class="unit">الجواب بـ: ${esc(S.q.unit)}</span>` : ""}</div>`;

  function countdown() {
    const el = $("timer");
    if (!el || !S || !S.deadline) return;
    const left = Math.max(0, Math.ceil((S.deadline - now()) / 1000));
    el.textContent = left;
    el.style.color = left <= 10 ? "#D92D20" : "";
  }

  function drawQuestion() {
    const answered = S.done.includes(me.id);
    render(`${header()}${qCard()}
      <div style="text-align:center"><span class="note">باقي</span> <b id="timer" style="font-family:var(--display);font-size:40px">40</b></div>
      ${answered ? `<div class="card pass"><span class="who">تمام ✓</span><span class="note">بعتّ رقمك. استنى الباقي.</span></div>`
        : `<input class="numin" id="num" type="text" inputmode="decimal" placeholder="رقمك" autocomplete="off" aria-label="رقمك" value="${esc(typed)}">
           <p class="note" id="err" hidden>اكتب رقم.</p>
           <button class="big" id="ok" type="button">ابعت رقمي</button>`}
      <div class="card"><p class="note" style="margin:0" id="whoDone">${whoDone()}</p></div>
      ${isHost ? `<button class="big ghost" id="rev" type="button">اكشف الجواب هلأ</button>` : ""}`);
    if ($("num")) { $("num").oninput = () => { typed = $("num").value; }; $("num").focus(); }
    bind({
      ok: () => {
        const n = parseNum($("num").value);
        if (n === null) { $("err").hidden = false; return; }
        typed = "";
        send({ t: "guess", n });
        if (!isHost) loading("بعتّ رقمك...");
      },
      rev: () => send({ t: "reveal" }),
    });
    countdown(); ticker = setInterval(countdown, 250);
  }

  function drawReveal() {
    const L = S.last;
    const delta = Object.fromEntries(L.rows.map((r) => [r.id, r.pts]));
    const order = L.rows.slice().sort((a, b) => (a.d === null) - (b.d === null) || a.d - b.d);
    render(`${header()}${qCard()}
      <div class="answer"><small>الجواب</small><b>${fmt(L.ans)}${S.q.unit ? ` <span style="font-size:22px">${esc(S.q.unit)}</span>` : ""}</b>${L.note ? `<small>${esc(L.note)}</small>` : ""}</div>
      <div class="guesses">${order.map((r) => { const i = S.players.findIndex((p) => p.id === r.id); const p = S.players[i]; if (!p) return "";
        return `<div class="r ${r.pts ? "win" : ""}"><b>${chip(i)}${esc(p.name)}${r.pts ? ` · <bdi dir="ltr">+${r.pts}</bdi>` : ""}</b><span class="g">${r.g === null ? "—" : fmt(r.g)}</span>
        <small>${r.g === null ? "ما جاوب" : r.d === 0 ? "جابه بالضبط!" : `بعيد ${fmt(+r.d.toFixed(3))}`}</small></div>`; }).join("")}</div>
      <h2>النقاط</h2>${board(delta)}
      ${isHost ? `<button class="big" id="next" type="button">السؤال الجاي</button><button class="big ghost" id="end" type="button">إنهاء اللعبة</button>`
        : `<p class="note" style="text-align:center">استنى صاحب الغرفة يجيب السؤال الجاي.</p>`}
      <button class="big ghost" id="out" type="button">اطلع</button>`);
    bind({ next: () => send({ t: "next" }), end: () => { if (confirm("أكيد بدك تنهي اللعبة؟")) send({ t: "end" }); }, out: confirmLeave });
  }

  function drawOver() {
    const max = Math.max(...S.players.map((p) => p.score));
    const winners = S.players.filter((p) => p.score === max).map((p) => p.name);
    render(`${header()}<div class="verdict good"><span>انتهت اللعبة بعد ${S.round} ${S.round === 1 ? "سؤال" : "أسئلة"}</span>
        <b>${winners.length > 1 ? "تعادل بين " + winners.map(esc).join(" و") : "فاز " + esc(winners[0]) + "!"}</b></div>
      ${board(null)}
      ${isHost ? `<button class="big" id="again" type="button">لعبة جديدة بنفس الغرفة</button>` : `<p class="note" style="text-align:center">صاحب الغرفة بيقدر يبدأ لعبة جديدة.</p>`}
      <button class="big ghost" id="out" type="button">اطلع</button>`);
    bind({ again: () => send({ t: "again" }), out: confirmLeave });
  }

  function confirmLeave() {
    if (isHost && !confirm("إنت صاحب الغرفة. إذا طلعت، اللعبة بتوقف عند الكل. أكيد؟")) return;
    leave();
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && isHost && S && S.phase === "q") {
      if (S.deadline && Date.now() > S.deadline + 300) reveal(); else armTimer();
    }
  });
  nearOnlineBoot();
})();
