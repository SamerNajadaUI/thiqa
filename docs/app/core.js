// نواة التطبيق: تخزين + حسابات + نقاط وخطط + حارس الدخول. بتتحمّل بسطر واحد وبشكل متزامن.
// المنطق الصافي (مستوى، مضاعف، سقف، رقم هاتف) بيصدّر لـNode للفحص (tools/test/app_core.test.js).
(function (root) {
  "use strict";

  // ===== منطق صافي =====
  const PLANS = {
    free:    { id: "free",    name: "مجاني",       mult: 1, price: 0,     per: "" },
    plus_m:  { id: "plus_m",  name: "بلس شهري",    mult: 2, price: 2.99,  per: "بالشهر" },
    plus_y:  { id: "plus_y",  name: "بلس سنوي",    mult: 2, price: 24.99, per: "بالسنة" },
    admin:   { id: "admin",   name: "أدمن",        mult: 2, price: 0,     per: "" },
  };
  const LOCKED = { auction: "plus", wheel: "plus", pictionary: "plus", connect: "plus" };   // الألعاب اللي بدها بلس
  const DAILY_CAP = 300;       // سقف نقاط اللعب باليوم (غير بونص الدخول). الأدمن بدون سقف
  const DAILY_BONUS = 10;
  const LEVEL_NAMES = ["مبتدئ", "هاوي", "لاعب", "محترف", "نجم", "أسطورة"];
  const ADMIN_CREDENTIALS = { username: "admin", password: "admin" };   // بطلب سامر: ظاهرة بالكود، بدّلها من هون
  const TEST_SMS_CODE = "123456";   // الوضع المحلي بس

  const isPlus = (plan) => plan === "plus_m" || plan === "plus_y" || plan === "admin";
  const multiplier = (plan) => (PLANS[plan] || PLANS.free).mult;
  const canPlay = (plan, gameId) => !LOCKED[gameId] || isPlus(plan);
  // المستوى n بيبدأ عند 50*(n-1)^2 نقطة
  function levelInfo(points) {
    const p = Math.max(0, Math.floor(points || 0));
    const level = Math.floor(Math.sqrt(p / 50)) + 1;
    const base = 50 * (level - 1) ** 2, next = 50 * level ** 2;
    return { level, name: LEVEL_NAMES[Math.min(LEVEL_NAMES.length - 1, Math.floor((level - 1) / 2))], into: p - base, need: next - base, pct: Math.round(((p - base) / (next - base)) * 100) };
  }
  // كم نقطة بتنضاف فعلاً بعد المضاعف والسقف اليومي
  function awardAmount(user, base) {
    const mult = multiplier(user.plan);
    const want = Math.round(Math.max(0, base) * mult);
    if (user.plan === "admin") return want;
    const left = Math.max(0, DAILY_CAP - (user.dayPlay || 0));
    return Math.min(want, left);
  }
  const dayKey = (d = new Date()) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  // رقم أردني: 07[789]xxxxxxx أو 9627... أو +9627... أو 00962...
  function normalizePhone(raw) {
    let d = String(raw || "").replace(/[\s\-()]/g, "").replace(/[٠-٩]/g, (c) => "٠١٢٣٤٥٦٧٨٩".indexOf(c));
    if (d.startsWith("00")) d = d.slice(2); else if (d.startsWith("+")) d = d.slice(1);
    if (d.startsWith("962")) d = d.slice(3);
    if (d.startsWith("0")) d = d.slice(1);
    return /^7[789]\d{7}$/.test(d) ? "+962" + d : null;
  }

  const Rewards = { PLANS, LOCKED, DAILY_CAP, DAILY_BONUS, LEVEL_NAMES, levelInfo, multiplier, canPlay, isPlus, awardAmount, dayKey, tierOf: (id) => LOCKED[id] || null };
  const Pure = { Rewards, Auth: { normalizePhone, ADMIN_CREDENTIALS, TEST_SMS_CODE } };
  if (typeof module !== "undefined" && module.exports) { module.exports = Pure; return; }

  // ===== من هون وتحت: المتصفح فقط =====
  const script = document.currentScript;
  const ROOT = new URL("../", script ? script.src : location.href).href;   // مجلد docs/
  const KEY_USERS = "app-users", KEY_SESSION = "app-session", KEY_PEND = "app-pending", KEY_LAST = "app-last";
  const J = { get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} } };
  const AppStore = { get: J.get, set: J.set };

  // ----- حسابات (محلي، وFirebase لما firebase-config.js ينعبّى) -----
  const listeners = new Set();
  const emit = () => listeners.forEach((f) => { try { f(Auth.user()); } catch {} });
  const users = () => J.get(KEY_USERS, {});
  function saveUser(u) { const all = users(); all[u.uid] = u; J.set(KEY_USERS, all); return u; }
  function blank(uid, extra) {
    return Object.assign({ uid, name: "لاعب", provider: "local", plan: "free", points: 0, dayKey: "", dayPlay: 0, lastDaily: "", createdAt: Date.now() }, extra);
  }
  function startSession(u) { J.set(KEY_SESSION, u.uid); emit(); return u; }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const fbCfg = () => root.APP_FIREBASE_CONFIG || null;

  const Auth = {
    mode: fbCfg() ? "firebase" : "local",
    normalizePhone, ADMIN_CREDENTIALS,
    user() { const id = J.get(KEY_SESSION, null); return id ? users()[id] || null : null; },
    onChange(cb) { listeners.add(cb); return () => listeners.delete(cb); },
    update(patch) { const u = Auth.user(); if (!u) return null; Object.assign(u, patch); saveUser(u); if (Auth.mode === "firebase" && root.AppFirebase) root.AppFirebase.push(u); emit(); return u; },
    signOut() { J.set(KEY_SESSION, null); if (root.AppFirebase) root.AppFirebase.signOut(); emit(); },
    async signInAdmin(username, password) {
      if (String(username).trim().toLowerCase() !== ADMIN_CREDENTIALS.username || password !== ADMIN_CREDENTIALS.password) throw new Error("اليوزر أو الباسورد مش صحيح");
      const u = users().admin || blank("admin", { name: "الأدمن", provider: "admin", plan: "admin" });
      u.plan = "admin"; saveUser(u); return startSession(u);
    },
    async signInGoogle() { return social("google", "جوجل"); },
    async signInApple() { return social("apple", "أبل"); },
    async sendPhoneCode(raw) {
      const phone = normalizePhone(raw);
      if (!phone) throw new Error("اكتب رقم أردني صحيح، مثل 0791234567");
      if (Auth.mode === "firebase") { await root.AppFirebase.sendCode(phone); }
      else { await sleep(350); J.set(KEY_PEND, { phone, t: Date.now() }); }
      return phone;
    },
    async confirmPhoneCode(code) {
      const c = String(code || "").replace(/\D/g, "");
      if (c.length < 4) throw new Error("اكتب الكود كامل");
      if (Auth.mode === "firebase") return startSession(await root.AppFirebase.confirm(c, users, saveUser, blank));
      const pend = J.get(KEY_PEND, null);
      if (!pend) throw new Error("ابعت الكود أول");
      if (c !== TEST_SMS_CODE) throw new Error("الكود غلط");
      const uid = "ph" + pend.phone.replace("+", "");
      const u = users()[uid] || blank(uid, { name: "لاعب " + pend.phone.slice(-4), provider: "phone", phone: pend.phone });
      saveUser(u); J.set(KEY_PEND, null); return startSession(u);
    },
  };
  async function social(kind, label) {
    if (Auth.mode === "firebase") return startSession(await root.AppFirebase.social(kind, users, saveUser, blank));
    await sleep(350);
    const uid = "demo-" + kind;
    const u = users()[uid] || blank(uid, { name: "لاعب " + label, provider: kind });
    saveUser(u); return startSession(u);
  }

  // ----- نقاط وخطط -----
  function roll(u) { const k = dayKey(); if (u.dayKey !== k) { u.dayKey = k; u.dayPlay = 0; } return u; }
  Rewards.dailyRemaining = (u) => (u.plan === "admin" ? Infinity : Math.max(0, DAILY_CAP - (roll(u).dayPlay || 0)));
  Rewards.add = function (base, reason) {
    const u = Auth.user(); if (!u) return 0;
    roll(u); const add = awardAmount(u, base);
    if (add > 0) { u.points = (u.points || 0) + add; u.dayPlay = (u.dayPlay || 0) + add; Auth.update(u); document.dispatchEvent(new CustomEvent("app:points", { detail: { add, reason, total: u.points } })); }
    return add;
  };
  Rewards.finish = function (gameId, base) { return Rewards.add(base == null ? 20 : base, "finish:" + gameId); };
  Rewards.daily = function () {
    const u = Auth.user(); if (!u) return 0; const k = dayKey();
    if (u.lastDaily === k) return 0;
    u.lastDaily = k; u.points = (u.points || 0) + DAILY_BONUS; Auth.update(u); return DAILY_BONUS;
  };
  // الاشتراك تجريبي: بدون دفع حقيقي
  Rewards.setPlan = function (plan) { const u = Auth.user(); if (!u || u.plan === "admin" || !PLANS[plan] || plan === "admin") return null; return Auth.update({ plan }); };
  Rewards.toast = (n) => { if (n > 0 && typeof window.uiToast === "function") window.uiToast("+" + n + " نقطة"); };

  // ----- حارس الدخول والقفل -----
  const path = location.pathname.replace(/\/+$/, "");
  const gameId = /\/games\/([\w-]+)\.html$/.test(path) ? RegExp.$1 : null;
  const here = location.pathname + location.search + location.hash;
  function go(url) { location.replace(url); }
  const Gate = { gameId, ROOT, lastPlayed: () => J.get(KEY_LAST, null) };
  if (!root.APP_PUBLIC) {
    const u = Auth.user();
    if (!u) { go(ROOT + "login.html?next=" + encodeURIComponent(here)); return finishExport(); }
    if (gameId && !canPlay(u.plan, gameId)) { go(ROOT + "rewards.html?locked=" + gameId + "#plans"); return finishExport(); }
    const bonus = Rewards.daily();
    if (gameId) {
      J.set(KEY_LAST, gameId);
      // نقطة كل 30 ثانية لعب فعلي (والصفحة ظاهرة)، وبسقف الجلسة 20
      let given = 0;
      setInterval(() => { if (document.visibilityState === "visible" && given < 20) { given += Rewards.add(1, "time:" + gameId); } }, 30000);
    }
    if (bonus) document.addEventListener("DOMContentLoaded", () => Rewards.toast(bonus));
  }
  function finishExport() { root.Auth = Auth; root.Rewards = Rewards; root.AppStore = AppStore; root.AppGate = Gate; }
  finishExport();

  if (Auth.mode === "firebase") {
    // وسيط: الوحدة (auth-firebase.js) بتسجّل نفسها لما تخلص تحميل
    const implP = new Promise((r) => { root.__fbResolve = r; });
    root.AppFirebase = new Proxy({}, { get: (_, k) => (...a) => implP.then((i) => i[k](...a)) });
    const s = document.createElement("script"); s.type = "module"; s.src = ROOT + "app/auth-firebase.js"; document.head.appendChild(s);
  }
})(typeof window !== "undefined" ? window : globalThis);
