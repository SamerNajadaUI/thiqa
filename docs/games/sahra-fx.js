// موشن «ملك السهرة»: طبقة ثابتة فوق اللعبة (#fxl) عشان إعادة رسم الشاشة ما تقطع الحركة.
// القاعدة: الانفجار الكبير (big) للحظات قليلة، والباقي حركات صغيرة وسريعة. أي مشهد بينقطع بلمسة.
"use strict";
const FXL = (() => {
  const calm = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const layer = document.createElement("div");
  layer.id = "fxl"; layer.setAttribute("aria-hidden", "true");
  const cv = document.createElement("canvas");
  layer.appendChild(cv);
  document.body.appendChild(layer);
  const g = cv.getContext("2d");
  let parts = [], raf = 0, W = 0, H = 0;
  function size() { const r = Math.min(2, window.devicePixelRatio || 1); W = innerWidth; H = innerHeight; cv.width = W * r; cv.height = H * r; g.setTransform(r, 0, 0, r, 0, 0); }
  size(); addEventListener("resize", size);
  function frame() {
    g.clearRect(0, 0, W, H);
    parts = parts.filter((p) => p.life > 0 && p.y < H + 30);
    for (const p of parts) {
      p.vy += p.g; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life -= 1;
      g.save(); g.globalAlpha = Math.min(1, p.life / 20); g.translate(p.x, p.y); g.rotate(p.rot); g.fillStyle = p.c;
      if (p.round) { g.beginPath(); g.arc(0, 0, p.s / 2, 0, 7); g.fill(); } else g.fillRect(-p.s / 2, -p.s / 3, p.s, p.s * 0.66);
      g.restore();
    }
    raf = parts.length ? requestAnimationFrame(frame) : 0;
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
  const COLORS = ["#FFD21F", "#E8323C", "#19A35B", "#39B8FF", "#FFFFFF"];
  function burst(x = W / 2, y = H * 0.42, n = 26, colors = COLORS) {
    if (calm()) return;
    for (let i = 0; i < n; i++) { const a = Math.random() * 6.28, v = 4 + Math.random() * 9; parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 3, g: 0.35, rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.4, s: 6 + Math.random() * 7, c: colors[i % colors.length], life: 50 + Math.random() * 30, round: i % 3 === 0 }); }
    kick();
  }
  function confetti(ms = 4200) {
    if (calm()) return;
    const end = Date.now() + ms;
    (function rain() {
      for (let i = 0; i < 7; i++) parts.push({ x: Math.random() * W, y: -12, vx: (Math.random() - 0.5) * 2.4, vy: 2 + Math.random() * 3, g: 0.04, rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.3, s: 7 + Math.random() * 7, c: COLORS[Math.floor(Math.random() * COLORS.length)], life: 260 });
      kick();
      if (Date.now() < end) setTimeout(rain, 70);
    })();
  }
  function el(cls, html, ms) {
    const d = document.createElement("div");
    d.className = cls; d.innerHTML = html;
    layer.appendChild(d);
    const kill = () => d.remove();
    if (ms) setTimeout(kill, ms);
    return d;
  }
  const esc2 = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function shake(strong) {
    if (calm()) return;
    const w = document.querySelector(".wrap"); if (!w) return;
    w.classList.remove("shk", "shk2"); void w.offsetWidth; w.classList.add(strong ? "shk2" : "shk");
    setTimeout(() => w.classList.remove("shk", "shk2"), 420);
  }
  const flash = (color = "#FFF") => { if (!calm()) el("fx-flash", "", 220).style.background = color; };
  const wipe = (color) => { if (!calm()) el("fx-wipe", "", 620).style.setProperty("--c", color || "#FFD21F"); };
  // اللحظة الكبيرة: «غوووول»
  function big(title, sub = "", opt = {}) {
    document.querySelectorAll("#fxl .fx-big").forEach((x) => x.remove());
    const d = el(`fx-big ${opt.cls || ""}`, `<div class="bg"></div><b>${esc2(title)}</b>${sub ? `<span>${esc2(sub)}</span>` : ""}`, opt.ms || 1700);
    if (opt.color) d.style.setProperty("--c", opt.color);
    d.style.pointerEvents = "auto";
    d.addEventListener("pointerdown", () => d.remove());
    if (!opt.quiet) { flash(); setTimeout(() => { shake(true); burst(W / 2, H * 0.42, opt.n || 30); }, 380); }
    try { navigator.vibrate && navigator.vibrate(opt.quiet ? 40 : [60, 40, 140]); } catch {}
  }
  // شريط البث السفلي (المعلّق، مولّع، صدارة جديدة)
  function banner(text, cls = "") {
    document.querySelectorAll("#fxl .fx-ban").forEach((x) => x.remove());
    el(`fx-ban ${cls}`, `<i>${esc2(text)}</i>`, 2600);
  }
  const float = (text, good = true) => el(`fx-float ${good ? "" : "neg"}`, esc2(text), 1300);
  // فحص الـVAR: شاشة مسح لمدة ms
  function varScan(ms) {
    document.querySelectorAll("#fxl .fx-var").forEach((x) => x.remove());
    const d = el("fx-var", `<div class="box"><em>VAR</em><span>جاري فحص اللقطة</span><u></u></div>`, ms);
    d.style.setProperty("--ms", ms + "ms");
  }
  function countUp(node, from, to, ms = 800) {
    if (!node) return;
    if (calm() || from === to) { node.textContent = to; return; }
    const t0 = performance.now();
    (function tick(now) {
      const k = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - k, 3);
      node.textContent = Math.round(from + (to - from) * e);
      if (k < 1) requestAnimationFrame(tick); else { node.classList.add("bump"); setTimeout(() => node.classList.remove("bump"), 300); }
    })(t0);
  }
  // FLIP: احفظ أماكن الصفوف، غيّر الترتيب، وحرّكهم من مكانهم القديم
  function reorder(box, order, ms = 520) {
    if (!box) return;
    const rows = [...box.children], top0 = new Map(rows.map((r) => [r.dataset.id, r.getBoundingClientRect().top]));
    order.forEach((id) => { const r = rows.find((x) => x.dataset.id === id); if (r) box.appendChild(r); });
    if (calm()) return;
    [...box.children].forEach((r, i) => {
      const dy = top0.get(r.dataset.id) - r.getBoundingClientRect().top;
      if (!dy) return;
      r.style.zIndex = dy > 0 ? 2 : 1;
      r.animate([{ transform: `translateY(${dy}px) scale(${dy > 0 ? 1.04 : 1})` }, { transform: "none" }], { duration: ms, delay: i * 50, easing: "cubic-bezier(.2,.9,.3,1.1)", fill: "backwards" });
    });
  }
  function clear() { layer.querySelectorAll(".fx-big,.fx-var,.fx-ban").forEach((x) => x.remove()); }
  return { big, banner, float, varScan, shake, flash, wipe, burst, confetti, countUp, reorder, clear, calm };
})();
