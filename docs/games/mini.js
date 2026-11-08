// أدوات مشتركة للألعاب الجديدة (تحميل قبل كود كل لعبة)
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const rand = (lo, hi) => lo + Math.random() * (hi - lo);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const hue = (s) => { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
const av = (name) => `<span class="av" style="--h:${hue(name)}" aria-hidden="true">${esc(String(name).trim().charAt(0) || "؟")}</span>`;
const render = (html) => { $("app").innerHTML = html; };
const bind = (map) => { for (const [id, fn] of Object.entries(map)) { const el = $(id); if (el) el.onclick = fn; } };
// تطبيع العربي عشان المقارنة ما تتأثر بالهمزات والتاء المربوطة
const normAr = (s) => String(s).replace(/[ً-ْـ]/g, "").replace(/[أإآ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه").replace(/\s+/g, "").toLowerCase();

// حفظ بسيط (أفضل نتيجة مثلاً). لو المتصفح ما بسمح، ما بوقّف اللعب.
const store = {
  get(k, d) { try { const v = localStorage.getItem("mini-" + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("mini-" + k, JSON.stringify(v)); } catch {} },
};

// أسماء اللاعبين من الحقول #p0..#pN (لو فاضية بنعطي اسم افتراضي)
const nameFields = (count, saved = []) => Array.from({ length: count }, (_, i) =>
  `<input class="input" id="p${i}" maxlength="14" placeholder="لاعب ${i + 1}" value="${esc(saved[i] || "")}" aria-label="اسم اللاعب ${i + 1}">`).join("");
const readNames = (count) => Array.from({ length: count }, (_, i) => (($(`p${i}`)?.value || "").trim()) || `لاعب ${i + 1}`);

// ترتيب نهائي: [{name, score}] من الأعلى
const medals = ["🥇", "🥈", "🥉"];
const standingsHTML = (list, unit = "نقطة") => `<ol class="standings">${list.map((p, i) =>
  `<li class="pop"><span class="medal">${medals[i] || (i + 1)}</span>${av(p.name)}<span>${esc(p.name)}</span><b>${p.score}</b><small class="sub">${unit}</small></li>`).join("")}</ol>`;

// نص الفايز: لو تعادل بنقول تعادل
const winnerLine = (list) => {
  const top = list[0]?.score ?? 0;
  const tops = list.filter((p) => p.score === top);
  return tops.length === 1 ? `🏆 الفايز: ${esc(tops[0].name)}` : `🤝 تعادل بين ${tops.map((p) => esc(p.name)).join(" و ")}`;
};

// فيديو صوت بسيط (بدون ملفات): نغمات قصيرة بالـ WebAudio. ما بتشتغل إلا بعد أي لمسة (قيود المتصفح).
let _ac = null;
function beep(freq = 660, ms = 110, type = "sine", vol = 0.08) {
  try {
    _ac = _ac || new (window.AudioContext || window.webkitAudioContext)();
    const o = _ac.createOscillator(), g = _ac.createGain();
    o.type = type; o.frequency.value = freq; g.gain.value = vol;
    o.connect(g); g.connect(_ac.destination); o.start();
    g.gain.exponentialRampToValueAtTime(0.0001, _ac.currentTime + ms / 1000);
    o.stop(_ac.currentTime + ms / 1000);
  } catch {}
}
