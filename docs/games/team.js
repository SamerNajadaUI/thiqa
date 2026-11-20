// محرك «فريق ضد فريق» على تلفون واحد: فريقين (أزرق وأحمر)، جولات، مؤقت، شاشة «الدور على»، وكشف.
// نوعين:
//  - closest: نفس السؤال للفريقين بالسر، والأقرب للجواب بياخذ النقاط (خريطة، أرقام، عدّ).
//  - turn: كل فريق إله سؤال بدوره، والصح بياخذ النقاط (ترتيب، المختلف).
// كل لعبة بتنادي TEAM({ id, title, desc, howto, kind, rounds: [4,6,8], load, round(data, rng, r, N) }).
(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const NAMES = ["صقور الديرة", "شباب الحوش", "نمور الحارة", "نشامى السهرة", "أسود البلد", "فرسان الليل", "ملوك الكورة", "ذيبان الوادي", "عيال العم", "نجوم الحي", "أبطال القعدة", "عقارب الساعة"];
  const TC = ["var(--c-toot)", "var(--c-jamr)"];
  const ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>';
  const BACK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
  const DICE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="8.5" cy="8.5" r="1.3" fill="currentColor"/><circle cx="15.5" cy="15.5" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/></svg>';
  const DEL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 5H9l-6 7 6 7h12a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1z"/><path d="M17 9l-6 6M11 9l6 6"/></svg>';
  const store = { get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} } };
  const rngOf = (seed) => () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const shuffle = (a, r = Math.random) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const fmtN = (n) => (Math.abs(n) >= 1000 ? Math.round(n).toLocaleString("en") : String(+(+n).toFixed(1)));
  window.TeamKit = { esc, shuffle, rngOf, fmtN, store };

  let G, S, data, dataP, timer = null;
  const app = () => $("app");
  const dock = (html) => { $("dock").innerHTML = html ? `<div>${html}</div>` : ""; $("dock").hidden = !html; };
  const vib = (ms) => { try { navigator.vibrate && navigator.vibrate(ms); } catch {} };

  window.TEAM = function (cfg) {
    G = Object.assign({ kind: "closest", rounds: [4, 6, 8], pts: 100 }, cfg);
    const saved = store.get("team-cfg", {});
    S = { time: saved.time ?? 60, rounds: G.rounds.includes(saved.rounds) ? saved.rounds : G.rounds[1] || G.rounds[0],
      names: saved.names || shuffle(NAMES).slice(0, 2), score: [0, 0], r: 0, log: [] };
    dataP = Promise.resolve(G.load ? G.load() : null).then((d) => (data = d)).catch(() => (data = null));
    try { AppStore.set("app-last", G.id); } catch {}
    setup();
  };

  function top() {
    return `<header class="t-top"><a class="brandi" href="./"><img src="icons/${G.id}.webp" alt=""><b>${esc(G.title)}</b></a>
      <span class="end">${typeof themeToggle === "function" ? themeToggle() : ""}<a class="icon-btn" href="./" aria-label="رجوع للألعاب">${BACK}</a></span></header>`;
  }

  function setup() {
    clearInterval(timer);
    const times = [[30, "٣٠"], [60, "٦٠"], [90, "٩٠"], [0, "بلا وقت"]];
    app().innerHTML = `${top()}
      <h1 class="t-h1">جهّزوا فرقكم</h1>
      <p class="t-sub">${esc(G.desc)}</p>
      ${G.howto ? `<p class="howto-mini">${G.howto}</p>` : ""}
      <p class="t-label">ثواني لكل سؤال</p>
      <div class="uline" id="u-time">${times.map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${S.time === v}">${l}</button>`).join("")}</div>
      <p class="t-label">عدد الجولات</p>
      <div class="uline" id="u-rounds">${G.rounds.map((v) => `<button type="button" data-v="${v}" aria-pressed="${S.rounds === v}">${v}</button>`).join("")}</div>
      <div class="teams">${[0, 1].map((i) => `<div class="team-row" style="--tc:${TC[i]}"><span class="team-av">${esc(S.names[i][0] || "؟")}</span>
        <input class="team-in" id="tn${i}" value="${esc(S.names[i])}" maxlength="18" aria-label="اسم الفريق ${i + 1}">
        <button class="team-dice" type="button" data-dice="${i}" aria-label="اسم عشوائي">${DICE}</button></div>`).join("")}</div>`;
    dock(`<button class="t-btn" id="go" type="button">ابدأ اللعب ${ARROW}</button>`);
    app().querySelectorAll("#u-time button").forEach((b) => b.onclick = () => { S.time = +b.dataset.v; setup(); });
    app().querySelectorAll("#u-rounds button").forEach((b) => b.onclick = () => { S.rounds = +b.dataset.v; setup(); });
    app().querySelectorAll("[data-dice]").forEach((b) => b.onclick = () => { const i = +b.dataset.dice; S.names[i] = shuffle(NAMES.filter((n) => !S.names.includes(n)))[0]; setup(); });
    [0, 1].forEach((i) => $("tn" + i).oninput = (e) => { S.names[i] = e.target.value.trim() || NAMES[i]; e.target.previousElementSibling.textContent = S.names[i][0]; });
    $("go").onclick = async () => {
      $("go").disabled = true; $("go").textContent = "لحظة...";
      await dataP;
      if (G.load && !data) { $("go").disabled = false; $("go").innerHTML = "ما زبط التحميل، جرّبوا كمان مرة"; dataP = Promise.resolve(G.load()).then((d) => (data = d)).catch(() => null); return; }
      store.set("team-cfg", { time: S.time, rounds: S.rounds, names: S.names });
      S.score = [0, 0]; S.r = 0; S.log = []; S.rng = Math.random;
      nextRound();
    };
  }

  // ===== الجولات =====
  function nextRound() {
    if (S.r >= S.rounds) return finish();
    S.r++;
    const first = (S.r - 1) % 2;
    S.order = [first, 1 - first];
    if (G.kind === "closest") { S.R = G.round(data, S.rng, S.r, S.rounds); S.ans = [null, null]; }
    S.step = 0;
    turn();
  }
  function turn() {
    const t = S.order[S.step];
    if (G.kind === "turn") S.R = G.round(data, S.rng, S.r, S.rounds, t);
    splash(t, () => ask(t));
  }
  function splash(t, then) {
    dock("");
    const el = document.createElement("div");
    el.className = "splash"; el.style.setProperty("--tc", TC[t]);
    el.innerHTML = `<small>الدور على</small><b>${esc(S.names[t])}</b><span class="tap">${G.kind === "closest" && S.step === 1 ? "الفريق الثاني ما يتطلّع على الشاشة · " : ""}اضغطوا لما تكونوا جاهزين</span>`;
    document.body.appendChild(el); vib(30);
    el.onclick = () => { el.remove(); then(); };
  }

  function head(t) {
    return `<div class="q-top" style="--tc:${TC[t]}"><span class="q-timer" id="qt">${S.time || "∞"}</span>
      <span class="q-team"><i></i>${esc(S.names[t])}</span><span class="q-pts">جولة <b>${S.r}</b> من ${S.rounds}</span></div>`;
  }

  function ask(t) {
    const R = S.R;
    document.documentElement.style.setProperty("--tc", TC[t]);
    app().innerHTML = `${head(t)}<div class="q-card" style="--tc:${TC[t]}">${R.kind ? `<span class="q-kind">${esc(R.kind)}</span>` : ""}<p class="q-text">${R.prompt}</p><div id="inp"></div></div>`;
    let val = null; const set = (v) => { val = v; $("ok").disabled = v == null; };
    dock(`<button class="t-btn" id="ok" type="button" disabled>ثبّتوا</button>`);
    const ui = INPUTS[R.input](R, $("inp"), set, t);
    let left = S.time;
    clearInterval(timer);
    const submit = () => { clearInterval(timer); const v = ui && ui.value ? ui.value(val) : val; done(t, v); };
    $("ok").onclick = submit;
    if (S.time) timer = setInterval(() => {
      left--; const q = $("qt"); if (!q) return clearInterval(timer);
      q.textContent = left; q.classList.toggle("low", left <= 5);
      if (left <= 5 && left > 0) vib(15);
      if (left <= 0) submit();
    }, 1000);
  }

  function done(t, v) {
    if (G.kind === "closest") {
      S.ans[t] = v; S.step++;
      if (S.step < 2) return turn();
      return revealClosest();
    }
    // turn: صحّح وورّي النتيجة على نفس الشاشة
    const res = S.R.grade(v);
    S.score[t] += res.gain;
    S.log.push({ t, gain: res.gain });
    if (res.html) $("inp").innerHTML = res.html;
    const card = app().querySelector(".q-card");
    card.insertAdjacentHTML("beforeend", `<div class="ans-row ${res.gain ? "win" : ""}" style="--tc:${TC[t]}"><span class="team-av" style="--tc:${TC[t]}">${esc(S.names[t][0])}</span>
      <span class="grow"><b>${res.gain ? (res.full ? "صح!" : "قريب") : v == null ? "خلص الوقت" : "غلط"}</b><small>${res.note || ""}</small></span><span class="gain">+${res.gain}</span></div>`);
    vib(res.gain ? 40 : [60, 40, 60]);
    S.step++;
    dock(`<button class="t-btn" id="nx" type="button">${S.step < 2 ? "دور الفريق الثاني" : "النتيجة"} ${ARROW}</button>`);
    $("nx").onclick = () => (S.step < 2 ? turn() : scoreboard());
  }

  function revealClosest() {
    const R = S.R, d = [0, 1].map((t) => (S.ans[t] == null ? Infinity : R.dist(S.ans[t])));
    const gain = [0, 0];
    if (d[0] < d[1]) gain[0] = G.pts; else if (d[1] < d[0]) gain[1] = G.pts; else if (isFinite(d[0])) { gain[0] = gain[1] = G.pts / 2; }
    [0, 1].forEach((t) => { if (d[t] === 0) gain[t] += 50; S.score[t] += gain[t]; });
    S.log.push({ gain });
    app().innerHTML = `<div class="reveal">
      <div class="truth"><small>الجواب الصح</small><b>${R.truth}</b>${R.truthSub ? `<small>${R.truthSub}</small>` : ""}</div>
      ${R.revealHTML ? R.revealHTML(S.ans, TC) : ""}
      ${[0, 1].map((t) => `<div class="ans-row ${gain[t] ? "win" : ""}" style="--tc:${TC[t]}"><span class="team-av" style="--tc:${TC[t]}">${esc(S.names[t][0])}</span>
        <span class="grow"><b>${esc(S.names[t])}</b><small>${S.ans[t] == null ? "ما جاوبوا" : R.show(S.ans[t]) + " · " + R.diffText(d[t])}</small></span>
        <span class="gain">+${gain[t]}</span></div>`).join("")}
    </div>`;
    if (R.afterReveal) R.afterReveal(S.ans);
    vib(40);
    dock(`<button class="t-btn" id="nx" type="button">النتيجة ${ARROW}</button>`);
    $("nx").onclick = scoreboard;
  }

  function scoreboard() {
    const last = S.r >= S.rounds;
    app().innerHTML = `${top()}<h1 class="t-h1">${last ? "آخر جولة خلصت" : `بعد جولة ${S.r}`}</h1>
      <div class="board">${[0, 1].map((t) => `<div style="--tc:${TC[t]}"><small>${esc(S.names[t])}</small><b>${S.score[t]}</b></div>`).join("")}</div>
      <p class="t-sub" style="text-align:center">${S.score[0] === S.score[1] ? "متعادلين!" : `${esc(S.names[S.score[0] > S.score[1] ? 0 : 1])} متقدّمين بـ${Math.abs(S.score[0] - S.score[1])}`}</p>`;
    dock(`<button class="t-btn" id="nx" type="button">${last ? "مين فاز؟" : "الجولة الجاية"} ${ARROW}</button>`);
    $("nx").onclick = last ? finish : nextRound;
  }

  function finish() {
    clearInterval(timer);
    const w = S.score[0] === S.score[1] ? -1 : S.score[0] > S.score[1] ? 0 : 1;
    app().innerHTML = `${top()}<div class="winner" style="--tc:${w < 0 ? "var(--c-layl-2)" : TC[w]}"><img src="icons/hasm.webp" alt=""><small>${w < 0 ? "النتيجة" : "الفايزين"}</small><b>${w < 0 ? "تعادل!" : esc(S.names[w])}</b></div>
      <div class="board">${[0, 1].map((t) => `<div style="--tc:${TC[t]}"><small>${esc(S.names[t])}</small><b>${S.score[t]}</b></div>`).join("")}</div>`;
    dock(`<button class="t-btn" id="again" type="button">العبوا كمان</button><a class="t-btn ghost" href="./" style="margin-top:10px;text-decoration:none">رجوع للألعاب</a>`);
    $("again").onclick = setup;
    try { if (!S.paid) { S.paid = 1; const r = Rewards.finish(G.id, Math.max(5, Math.min(40, Math.round(Math.max(...S.score) / 25)))); Rewards.toast && Rewards.toast(r); } } catch {}
    vib([40, 60, 40]);
  }

  // ===== المدخلات =====
  const INPUTS = {
    number(R, el, set) {
      let s = "";
      el.innerHTML = `<div class="num-show"><b id="nv" class="ph">0</b>${R.unit ? `<span>${esc(R.unit)}</span>` : ""}</div>
        <div class="keypad">${["1", "2", "3", "4", "5", "6", "7", "8", "9", R.dec ? "." : "", "0", "del"].map((k) => k ? `<button type="button" data-k="${k}" aria-label="${k === "del" ? "امسح" : k}">${k === "del" ? DEL : k}</button>` : "<span></span>").join("")}</div>`;
      el.querySelectorAll("[data-k]").forEach((b) => b.onclick = () => {
        const k = b.dataset.k;
        if (k === "del") s = s.slice(0, -1); else if (k === "." ? !s.includes(".") && s : s.replace(".", "").length < 12) s = s === "0" && k !== "." ? k : s + k;
        const v = s ? Number(s) : null;
        $("nv").textContent = s ? (s.includes(".") ? s : Number(s).toLocaleString("en")) : "0"; $("nv").classList.toggle("ph", !s);
        set(v != null && isFinite(v) ? v : null);
      });
    },
    choice(R, el, set) {
      el.innerHTML = `<div class="opts">${R.options.map((o, i) => `<button class="opt" type="button" data-i="${i}">${esc(o)}</button>`).join("")}</div>`;
      el.querySelectorAll(".opt").forEach((b) => b.onclick = () => { el.querySelectorAll(".opt").forEach((x) => x.classList.toggle("dim", x !== b)); set(+b.dataset.i); });
    },
    order(R, el, set) {
      const pick = [];
      const draw = () => {
        el.innerHTML = `<div class="olist">${R.items.map((it, i) => { const k = pick.indexOf(i); return `<button class="oitem ${k >= 0 ? "on" : ""}" type="button" data-i="${i}"><span class="rk">${k >= 0 ? k + 1 : ""}</span>${esc(it[0])}</button>`; }).join("")}</div>`;
        el.querySelectorAll(".oitem").forEach((b) => b.onclick = () => { const i = +b.dataset.i, k = pick.indexOf(i); if (k >= 0) pick.splice(k); else pick.push(i); if (pick.length === R.items.length - 1) pick.push(R.items.findIndex((_, j) => !pick.includes(j))); draw(); set(pick.length === R.items.length ? pick.slice() : null); });
      };
      draw();
    },
  };
  window.TeamInputs = INPUTS;
})();
