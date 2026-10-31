// تحدي الأصحاب أونلاين: كل واحد من تلفونه.
// تلفون واحد هو "المضيف": هو اللي بيمسك اللعبة وبيقرر (الدور، الوقت، النقاط)، والباقي بيبعتوا حركاتهم.
// التواصل عبر وسيط MQTT عام ومجاني (ما بدو حساب): كل غرفة إلها كود، والحالة بتنشر لكل اللي بالغرفة.
/* global mqtt, DATA, byId, render, bind, esc, face, store, shuffle, hintsFor, optionsFor, easyWrong,
   pointsFor, ROUNDS, MAX_HINTS, LIVES, WRONG, CUT, POS_AR, posCat, pickLeague, onPicked:writable, intro */
(function () {
  const TURN_MS = 30000;
  const MAX_PLAYERS = 5;
  const BROKERS = ["wss://broker.emqx.io:8084/mqtt", "wss://broker.hivemq.com:8884/mqtt", "wss://test.mosquitto.org:8081/mqtt"];
  const qs = new URLSearchParams(location.search);
  const ROOT = "abuodeh-party-v1";

  let client = null, room = null, isHost = false, S = null, offset = 0, ticker = null, hostTimer = null;
  let view = "main";            // واجهة محلية: main | guess | pick
  let lastSeen = -1;
  const me = { id: store.get("pid", null), name: store.get("myname", "") };
  if (!me.id) { me.id = Math.random().toString(36).slice(2, 10); store.set("pid", me.id); }

  const myIndex = () => (S ? S.players.findIndex((p) => p.id === me.id) : -1);
  const now = () => Date.now() + offset;
  const topic = (k) => `${ROOT}/${room}/${k}`;

  // ---------- الاتصال ----------
  function connect(onReady, k = 0) {
    if (typeof mqtt === "undefined") { fail("ما قدرت أحمّل مكتبة الاتصال. تأكد من الإنترنت وجرّب كمان مرة."); return; }
    const url = qs.get("broker") || BROKERS[k % BROKERS.length];
    let ready = false;
    const c = mqtt.connect(url, { clientId: "ao_" + me.id + "_" + Math.random().toString(36).slice(2, 6), reconnectPeriod: 2000, connectTimeout: 8000, clean: true });
    const giveUp = setTimeout(() => { if (!ready) { c.end(true); if (k + 1 < BROKERS.length && !qs.get("broker")) connect(onReady, k + 1); else fail("ما قدرت أتصل. جرّب كمان شوي."); } }, 9000);
    c.on("connect", () => {
      if (!ready) { ready = true; clearTimeout(giveUp); client = c; onReady(); }
      else onReconnect();
    });
    c.on("message", (t, buf) => {
      let m; try { m = JSON.parse(buf.toString()); } catch { return; }
      if (t === topic("s")) onState(m);
      else if (t === topic("a") && isHost) onAction(m);
    });
  }
  function onReconnect() {
    if (!room) return;
    client.subscribe(topic("s"), { qos: 1 });
    if (isHost) { client.subscribe(topic("a"), { qos: 1 }); publish(); }
    else send({ t: "join", name: me.name });
  }
  function fail(msg) {
    render(`<h1>مشكلة بالاتصال</h1><p class="sub">${esc(msg)}</p><button class="big" id="back" type="button">رجوع</button>`);
    bind({ back: leave });
  }

  // ---------- القوائم ----------
  window.onlineMenu = function (prefill = qs.get("room") || "") {
    render(`<h1>كل واحد من تلفونه</h1>
      <p class="sub">واحد بيعمل غرفة وبيبعت الكود لأصحابه، والباقي بيدخلوا بالكود. تلفون صاحب الغرفة لازم يضل مفتوح لآخر اللعبة.</p>
      <h2>اسمك</h2>
      <input class="search" id="myname" type="text" maxlength="14" placeholder="اسمك" value="${esc(me.name)}" autocomplete="off">
      <button class="big" id="create" type="button">اعمل غرفة جديدة</button>
      <h2>أو ادخل غرفة صاحبك</h2>
      <input class="search" id="code" type="text" inputmode="numeric" maxlength="5" placeholder="كود الغرفة (5 أرقام)" value="${esc(prefill)}" autocomplete="off" style="letter-spacing:4px;text-align:center;font-size:22px">
      <p class="note" id="err" hidden></p>
      <button class="big green" id="join" type="button">ادخل</button>
      <button class="big ghost" id="back" type="button">رجوع</button>`);
    const getName = () => {
      const n = $("myname").value.trim();
      if (!n) { $("err").hidden = false; $("err").textContent = "اكتب اسمك أول."; return null; }
      me.name = n; store.set("myname", n); return n;
    };
    bind({
      create: () => { if (!getName()) return; hostRoom(); },
      join: () => {
        if (!getName()) return;
        const code = $("code").value.replace(/[^\d٠-٩]/g, "").replace(/[٠-٩]/g, (d) => "٠١٢٣٤٥٦٧٨٩".indexOf(d));
        if (code.length !== 5) { $("err").hidden = false; $("err").textContent = "الكود 5 أرقام."; return; }
        joinRoom(code);
      },
      back: leave,
    });
  };

  window.onlineBoot = function () {
    const saved = store.get("online", null);
    if (qs.get("room")) { onlineMenu(qs.get("room")); return true; }
    if (saved && saved.room && Date.now() - (saved.at || 0) < 6 * 3600e3) {
      render(`<h1>في لعبة أونلاين مفتوحة</h1><p class="sub">الغرفة ${esc(saved.room)}${saved.host ? " (إنت صاحبها)" : ""}.</p>
        <button class="big green" id="re" type="button">ارجع للعبة</button><button class="big ghost" id="no" type="button">لا، طلّعني</button>`);
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
    try { if (client) setTimeout(() => client && client.end(true), 300); } catch {}
    setTimeout(() => { client = null; }, 400); room = null; S = null; isHost = false; onPicked = null;
    clearInterval(ticker); clearTimeout(hostTimer);
    store.set("online", null);
    history.replaceState(null, "", location.pathname);
    intro();
  }

  function loading(msg) { render(`<div class="loading">${esc(msg)}</div>`); }

  // ---------- المضيف ----------
  function hostRoom(code, restored) {
    isHost = true;
    room = code || String(Math.floor(10000 + Math.random() * 90000));
    store.set("online", { room, host: true, at: Date.now() });
    loading("عم بفتح الغرفة...");
    connect(() => {
      client.subscribe([topic("s"), topic("a")], { qos: 1 });
      S = restored || { v: 0, room, host: me.id, phase: "lobby", round: 1, players: [{ id: me.id, name: me.name, total: 0, help: newHelp() }], picks: [], hist: [] };
      publish();
      if (S.phase === "play" && S.deadline) armTimer();
    });
  }

  function publish() {
    S.v++; S.now = Date.now();
    store.set("hoststate-" + room, S);
    store.set("online", { room, host: true, at: Date.now() });
    client.publish(topic("s"), JSON.stringify(S), { qos: 1, retain: true });
    onState(S);
  }

  function onAction(a) {
    if (!S || !a || !a.pid) return;
    const i = S.players.findIndex((p) => p.id === a.pid);
    switch (a.t) {
      case "join":
        if (i >= 0) { if (a.name && S.players[i].name !== a.name) { S.players[i].name = a.name; } publish(); return; }
        if (S.phase !== "lobby" || S.players.length >= MAX_PLAYERS) { publish(); return; }
        S.players.push({ id: a.pid, name: uniqueName(a.name), total: 0, help: newHelp() });
        return publish();
      case "kick":
        if (a.pid !== S.host || S.phase !== "lobby") return;
        S.players = S.players.filter((p) => p.id !== a.who);
        return publish();
      case "start":
        if (a.pid !== S.host || S.phase !== "lobby" || S.players.length < 2) return;
        S.phase = "pick"; S.picks = S.players.map(() => null);
        return publish();
      case "pick":
        if (S.phase !== "pick" || i < 0 || !byId.get(a.id)) return;
        S.picks[i] = a.id;
        if (S.picks.every(Boolean)) startPlay(); else publish();
        return;
      case "pass": case "guess": case "help":
        if (S.phase !== "play" || i !== S.turn) return;
        return turnAction(i, a);
      case "next":
        if (a.pid !== S.host || S.phase !== "end") return;
        S.round++; S.phase = "pick"; S.picks = S.players.map(() => null); S.flash = null;
        return publish();
      case "again":
        if (a.pid !== S.host || S.phase !== "over") return;
        S.players.forEach((p) => { p.total = 0; p.help = newHelp(); });
        S.round = 1; S.hist = []; S.phase = "pick"; S.picks = S.players.map(() => null); S.flash = null;
        return publish();
    }
  }

  function uniqueName(n) {
    let name = String(n || "لاعب").slice(0, 14), k = 2;
    while (S.players.some((p) => p.name === name)) name = `${String(n).slice(0, 12)} ${k++}`;
    return name;
  }

  function startPlay() {
    const n = S.players.length;
    S.targets = S.players.map((_, i) => S.picks[(i - 1 + n) % n]);
    const H = S.targets.map((id) => hintsFor(byId.get(id)));
    S.hints = H.map((h) => h.text);
    S.links = H.map((h) => h.link);
    S.st = S.players.map((_, i) => ({ h: 0, lives: LIVES, pts: 0, done: null, opts: optionsFor(byId.get(S.targets[i]), S.links[i]) }));
    S.phase = "play"; S.flash = null;
    beginTurn(0);
  }

  function beginTurn(i) {
    S.turn = i;
    const s = S.st[i];
    if (s.h < MAX_HINTS) s.h++;
    S.deadline = Date.now() + TURN_MS;
    S.turnId = (S.turnId || 0) + 1;
    armTimer();
    publish();
  }

  function armTimer() {
    clearTimeout(hostTimer);
    const id = S.turnId;
    hostTimer = setTimeout(() => {
      if (!S || S.phase !== "play" || S.turnId !== id) return;
      const s = S.st[S.turn];
      S.flash = { who: S.turn, good: false, text: `خلص الوقت على ${S.players[S.turn].name}` };
      if (s.h >= MAX_HINTS) s.done = "out";
      advance();
    }, Math.max(0, S.deadline - Date.now()) + 300);
  }

  function turnAction(i, a) {
    const s = S.st[i], p = S.players[i];
    if (a.t === "pass") {
      if (s.h >= MAX_HINTS) s.done = "out";
      S.flash = { who: i, good: false, text: s.done ? `${p.name} استسلم` : `${p.name} مرّر` };
      return advance();
    }
    if (a.t === "help") {
      const target = byId.get(S.targets[i]);
      if (applyHelp(a.kind, s, p.help, target)) publish();
      return;
    }
    if (a.t === "guess") {
      const target = byId.get(S.targets[i]);
      const ans = a.id ? { id: a.id } : { text: String(a.text || "").slice(0, 60) };
      if (ans.id && !(s.three || []).includes(ans.id)) return;
      if (!ans.id && !ans.text.trim()) return;
      const v = judgeAnswer(target, ans);
      if (v === "close") { s.close = (s.close || 0) + 1; return publish(); }   // قريب كثير: ما بتنحسب، وبيجرّب كمان مرة
      s.close = 0;
      const mult = s.double ? 2 : 1;
      s.double = false;
      if (v === "yes") {
        const pts = pointsFor(s.h) * mult;
        s.pts += pts; s.done = "solved";
        S.flash = { who: i, good: true, text: `${p.name} عرف لاعبه من التلميح ${s.h}${mult > 1 ? " ودبّلها" : ""}: +${pts}` };
      } else {
        const said = ans.id ? (byId.get(ans.id) || {}).a : ans.text;
        if (ans.id && s.three) s.three = s.three.filter((x) => x !== ans.id);
        s.pts += WRONG * mult; s.lives--;
        if (s.lives <= 0) s.done = "out";
        S.flash = { who: i, good: false, text: `${p.name} قال «${said}» وغلط: ${WRONG * mult}${s.done ? "، وطلع من الجولة" : ""}` };
      }
      return advance();
    }
  }

  function advance() {
    const n = S.players.length;
    const alive = S.st.map((s, i) => (s.done ? -1 : i)).filter((i) => i >= 0);
    if (!alive.length) return roundEnd();
    let t = S.turn;
    for (let k = 0; k < n; k++) { t = (t + 1) % n; if (!S.st[t].done) break; }
    beginTurn(t);
  }

  function roundEnd() {
    clearTimeout(hostTimer);
    S.players.forEach((p, i) => { p.total += S.st[i].pts; });
    S.hist.push(S.players.map((p, i) => ({ name: p.name, target: S.targets[i], pts: S.st[i].pts, done: S.st[i].done, h: S.st[i].h })));
    S.phase = S.round >= ROUNDS ? "over" : "end";
    S.deadline = null;
    publish();
  }

  // ---------- اللاعب (وكمان المضيف) ----------
  function joinRoom(code) {
    isHost = false; room = code;
    store.set("online", { room, host: false, at: Date.now() });
    loading("عم بدخل الغرفة...");
    connect(() => {
      client.subscribe(topic("s"), { qos: 1 });
      send({ t: "join", name: me.name });
      setTimeout(() => { if (!S) render(`<h1>ما في رد من الغرفة ${esc(room)}</h1><p class="sub">تأكد من الكود، وإنه تلفون صاحب الغرفة مفتوح على اللعبة.</p><button class="big" id="again" type="button">جرّب كمان مرة</button><button class="big ghost" id="back" type="button">رجوع</button>`) || bind({ again: () => send({ t: "join", name: me.name }), back: leave }); }, 6000);
    });
  }

  function send(a) {
    a.pid = me.id;
    if (isHost) { onAction(a); return; }
    if (client) client.publish(topic("a"), JSON.stringify(a), { qos: 1 });
  }

  function onState(st) {
    if (!st || st.room !== room) return;
    if (st.now && Date.now() - st.now > 6 * 3600e3 && !isHost) return;   // غرفة قديمة مهجورة
    if (S && st !== S && st.host === S.host && st.v <= S.v) return;     // نسخة قديمة أو مكررة
    const fresh = !S || st.phase !== S.phase || st.round !== S.round || st.turnId !== S.turnId;
    S = st;
    offset = (st.now || Date.now()) - Date.now();
    if (!isHost && myIndex() < 0 && st.phase !== "lobby") { render(`<h1>اللعبة بلّشت</h1><p class="sub">ما لحقت تدخل هالمرة. استنى الجولة الجاية أو اطلب منهم يعملوا لعبة جديدة.</p><button class="big ghost" id="back" type="button">رجوع</button>`); bind({ back: leave }); return; }
    if (fresh && view !== "pick") view = "main";
    if (view === "pick" && (S.phase !== "pick" || S.picks[myIndex()])) view = "main";
    if (view === "pick") return;          // ما نقطع على اللي عم يختار
    draw();
  }

  function scoreBar() {
    return `<div class="status3">${S.players.map((p, i) => {
      const s = S.st && S.phase === "play" ? S.st[i] : null;
      const sub = !s ? `${p.total}` : s.done === "solved" ? "عرفه" : s.done === "out" ? "طلع" : `<span class="hearts">${"♥".repeat(s.lives)}</span> · ${s.h}`;
      return `<div class="${S.phase === "play" && i === S.turn ? "me" : ""}"><b>${esc(p.name)}${p.id === me.id ? " (إنت)" : ""}</b><span>${p.total + (s ? s.pts : 0)}</span><small>${sub}</small></div>`;
    }).join("")}</div>`;
  }

  function header() {
    return `<div class="sub" style="text-align:center">الغرفة <b style="letter-spacing:3px">${esc(room)}</b>${S.phase !== "lobby" ? ` · الجولة ${S.round} من ${ROUNDS}` : ""}</div>`;
  }

  function draw() {
    clearInterval(ticker);
    const mi = myIndex();
    if (S.phase === "lobby") return drawLobby();
    if (S.phase === "pick") return drawPickWait(mi);
    if (S.phase === "play") return view === "guess" && S.turn === mi && !S.st[mi].done ? drawGuess(mi) : drawPlay(mi);
    return drawEnd();
  }

  function drawLobby() {
    const link = location.origin + location.pathname + "?room=" + room;
    render(`${header()}<h1>الغرفة ${esc(room)}</h1>
      <p class="sub">${isHost ? "ابعت الكود أو الرابط لأصحابك. لما يدخلوا كلهم، اضغط ابدأ." : "استنى صاحب الغرفة يبدأ اللعبة."}</p>
      ${isHost ? `<button class="big ghost" id="share" type="button">ابعت رابط الغرفة</button>` : ""}
      <h2>اللاعبين (${S.players.length} من ${MAX_PLAYERS})</h2>
      <div class="stack" style="gap:8px">${S.players.map((p) => `<div class="pickbtn prow" style="grid-template-columns:1fr auto"><b>${esc(p.name)}${p.id === S.host ? " · صاحب الغرفة" : ""}${p.id === me.id ? " (إنت)" : ""}</b>${isHost && p.id !== me.id ? `<button type="button" class="back" data-kick="${p.id}">شيل</button>` : ""}</div>`).join("")}</div>
      ${isHost ? `<button class="big green" id="start" type="button" ${S.players.length < 2 ? "disabled" : ""}>ابدأ اللعبة</button>` : ""}
      <button class="big ghost" id="out" type="button">اطلع من الغرفة</button>`);
    bind({
      start: () => send({ t: "start" }),
      out: leave,
      share: async () => {
        const text = `تعال العب معي "تحدي الأصحاب"، كود الغرفة ${room}`;
        try { if (navigator.share) { await navigator.share({ title: "تحدي الأصحاب", text, url: link }); return; } } catch { return; }
        try { await navigator.clipboard.writeText(text + "\n" + link); $("share").textContent = "انسخ الرابط ✓"; } catch {}
      },
    });
    document.querySelectorAll("[data-kick]").forEach((b) => b.onclick = () => send({ t: "kick", who: b.dataset.kick }));
  }

  function drawPickWait(mi) {
    const n = S.players.length;
    const forWho = S.players[(mi + 1) % n];
    if (!S.picks[mi]) {
      render(`${header()}${scoreBar()}
        <div class="pass2"><span class="sub">دورك تختار لاعب لـ</span><span class="who">${esc(forWho.name)}</span><span class="note">بالسر، ومحدا رح يشوف اختيارك.</span></div>
        <button class="big" id="go" type="button">يلا اختار</button>
        <p class="note" style="text-align:center">خلصوا: ${S.picks.filter(Boolean).length} من ${n}</p>`);
      bind({ go: startPicking });
      return;
    }
    render(`${header()}${scoreBar()}
      <div class="pass2"><span class="sub">تمام، اخترت لـ${esc(forWho.name)}.</span><span class="who">${S.picks.filter(Boolean).length} من ${n}</span><span class="note">استنى الباقي يختاروا: ${S.players.filter((_, i) => !S.picks[i]).map((p) => esc(p.name)).join("، ")}</span></div>`);
  }

  function startPicking() {
    view = "pick";
    onPicked = (p) => {
      const forWho = S.players[(myIndex() + 1) % S.players.length];
      render(`<div class="prow pickbtn" style="grid-template-columns:72px 1fr">${face(p, "mini2").replace('class="mini2"', 'class="mini2" style="width:72px;height:72px"').replace("<img ", '<img style="width:72px;height:72px" ')}<span><b style="font-size:20px">${esc(p.a)}</b><small>${esc(p.n)}</small></span></div>
        <p class="sub">هاد اللاعب لـ${esc(forWho.name)}؟</p>
        <button class="big green" id="yes" type="button">آه، هاد هو</button>
        <button class="big ghost" id="no" type="button">بدي غيره</button>`);
      bind({ yes: () => { onPicked = null; view = "main"; send({ t: "pick", id: p.id }); loading("بعتّ اختيارك..."); setTimeout(() => S && view === "main" && draw(), 1500); }, no: pickLeague });
    };
    pickLeague();
  }

  function countdown() {
    const el = document.getElementById("timer");
    if (!el || !S || !S.deadline) return;
    const left = Math.max(0, Math.ceil((S.deadline - now()) / 1000));
    el.textContent = left;
    el.style.color = left <= 10 ? "var(--l3, #D92D20)" : "";
  }
  function startTicker() { clearInterval(ticker); countdown(); ticker = setInterval(countdown, 250); }

  function flashBox() {
    if (!S.flash) return "";
    return `<div class="flash ${S.flash.good ? "good" : "badf"}" style="padding:12px"><span>${esc(S.flash.text)}</span></div>`;
  }

  function drawPlay(mi) {
    const s = S.st[mi], myTurn = S.turn === mi && !s.done;
    const hs = (S.hints[mi] || []).slice(0, s.h);
    const timer = `<div style="text-align:center"><span class="sub">${myTurn ? "دورك! باقي" : `دور ${esc(S.players[S.turn].name)}، باقي`}</span>
      <div id="timer" style="font-family:var(--display);font-size:44px;line-height:1.1">30</div></div>`;
    const mine = s.done === "solved" ? `<div class="flash good"><span>عرفته!</span><b>${esc(byId.get(S.targets[mi]).a)}</b></div>`
      : s.done === "out" ? `<div class="flash badf"><span>طلعت من الجولة</span><b>استنى الجولة الجاية</b></div>`
      : `<h2>تلميحاتك</h2><ol class="hints">${hs.map((t, k) => `<li class="${k === hs.length - 1 && myTurn ? "new" : ""}"><span>${k + 1}</span><b>${esc(t)}</b></li>`).join("") || `<li><span>…</span><b>أول تلميح بيجي لما يجي دورك</b></li>`}</ol>`;
    render(`${header()}${scoreBar()}${flashBox()}${timer}${mine}
      ${myTurn ? `<p class="ptsnow">إذا عرفته هلأ بتاخذ <b>${pointsFor(s.h)}</b> نقاط. والغلط <b>${WRONG}</b>.</p>
        <button class="big green" id="guess" type="button">بدي أحكي الاسم</button>
        <button class="big ghost" id="pass" type="button">${s.h >= MAX_HINTS ? "استسلم (بتطلع من الجولة)" : "مرّر الدور"}</button>` : ""}
      <button class="big ghost" id="out" type="button" style="margin-top:6px">اطلع من اللعبة</button>`);
    bind({ guess: () => { view = "guess"; draw(); }, pass: () => send({ t: "pass" }), out: confirmLeave });
    startTicker();
  }

  let typedName = "";
  function drawGuess(mi) {
    const s = S.st[mi], help = S.players[mi].help;
    const target = byId.get(S.targets[mi]);
    render(`${header()}<div style="text-align:center"><span class="sub">باقي</span> <b id="timer" style="font-family:var(--display);font-size:30px">30</b></div>
      <h2>مين لاعبك؟</h2>
      ${guessPanel(s, help, target)}
      <button class="big ghost" id="back2" type="button">رجوع للتلميحات</button>`);
    if (s.close) { $("close").hidden = false; $("close").textContent = "قريب كثير! تأكد من الكتابة وجرّب كمان مرة (ما انحسبت)."; }
    const inp = $("nameIn");
    inp.value = typedName; inp.oninput = () => { typedName = inp.value; };
    inp.onkeydown = (e) => { if (e.key === "Enter") $("sayIt").click(); };
    bind({
      sayIt: () => { const t = inp.value.trim(); if (!t) return; typedName = ""; send({ t: "guess", text: t }); loading("لحظة..."); },
      back2: () => { view = "main"; draw(); },
    });
    document.querySelectorAll("[data-help]").forEach((b) => b.onclick = () => send({ t: "help", kind: b.dataset.help }));
    document.querySelectorAll("[data-g]").forEach((b) => b.onclick = () => { send({ t: "guess", id: b.dataset.g }); loading("لحظة..."); });
    startTicker();
  }

  function drawEnd() {
    const rows = S.hist[S.hist.length - 1] || [];
    const over = S.phase === "over";
    const board = S.players.map((p, i) => i).sort((a, b) => S.players[b].total - S.players[a].total);
    const top = Math.max(...S.players.map((p) => p.total));
    const winners = S.players.filter((p) => p.total === top).map((p) => p.name);
    render(`${header()}${over ? `<div class="flash good"><span>انتهت اللعبة!</span><b>${winners.length > 1 ? "تعادل: " + winners.map(esc).join(" و") : "الفائز " + esc(winners[0])}</b></div>` : `<h1>خلصت الجولة ${S.round}</h1>`}
      <div class="stack" style="gap:8px">${rows.map((r) => { const p = byId.get(r.target);
        return `<div class="pickbtn prow">${face(p, "mini2")}<span><b>${esc(r.name)}: ${esc(p.a)}</b><small>${r.done === "solved" ? `عرفه من التلميح ${r.h}` : "ما عرفه"} · <bdi dir="ltr">${r.pts > 0 ? "+" : ""}${r.pts}</bdi></small></span></div>`; }).join("")}</div>
      <h2>المجموع</h2>
      <div class="board">${board.map((i, k) => `<div class="r"><span class="pos">${k + 1}</span><b>${esc(S.players[i].name)}</b><span class="t">${S.players[i].total}</span></div>`).join("")}</div>
      ${isHost ? (over ? `<button class="big" id="again" type="button">لعبة جديدة بنفس الغرفة</button>` : `<button class="big" id="next" type="button">الجولة ${S.round + 1}</button>`) : `<p class="note" style="text-align:center">استنى صاحب الغرفة يكمّل.</p>`}
      <button class="big ghost" id="out" type="button">اطلع</button>`);
    bind({ next: () => send({ t: "next" }), again: () => send({ t: "again" }), out: confirmLeave });
  }

  function confirmLeave() {
    if (isHost && !confirm("إنت صاحب الغرفة. إذا طلعت، اللعبة بتوقف عند الكل. أكيد؟")) return;
    leave();
  }

  // المضيف: لما يرجع التلفون من الخلفية، نرجّع المؤقت
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && isHost && S && S.phase === "play") {
      if (S.deadline && Date.now() > S.deadline + 300) { S.flash = { who: S.turn, good: false, text: `خلص الوقت على ${S.players[S.turn].name}` }; if (S.st[S.turn].h >= MAX_HINTS) S.st[S.turn].done = "out"; advance(); }
      else armTimer();
    }
  });
})();
